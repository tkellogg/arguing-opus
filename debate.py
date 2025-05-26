#!/usr/bin/env python3
"""
Claude Debate Tool - Two Claude instances engage in structured debate
"""

import json
import os
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import argparse
import requests
from anthropic import Anthropic

import dotenv
dotenv.load_dotenv()


@dataclass
class SearchQuery:
    query: str
    timestamp: float
    participant: str
    url: Optional[str] = None  # For fetch operations

@dataclass
class Message:
    role: str
    content: str
    timestamp: float
    participant: str
    searches: List[SearchQuery] = None  # Track searches made in this message
    
    def __post_init__(self):
        if self.searches is None:
            self.searches = []


@dataclass
class DebateConfig:
    topic: str
    max_turns: int = 30
    api_key: Optional[str] = None


class WebToolkit:
    """Web search and fetch functionality for Claude participants"""
    
    @staticmethod
    def search_web(query: str, num_results: int = 3) -> str:
        """Perform a web search and return formatted results"""
        try:
            # Using DuckDuckGo Instant Answer API (no key required)
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            results = []
            if data.get('Abstract'):
                results.append(f"Summary: {data['Abstract']}")
            
            if data.get('RelatedTopics'):
                for i, topic in enumerate(data['RelatedTopics'][:num_results]):
                    if isinstance(topic, dict) and 'Text' in topic:
                        results.append(f"Result {i+1}: {topic['Text']}")
            
            return "\n".join(results) if results else f"No detailed results found for '{query}'"
            
        except Exception as e:
            return f"Search error: {str(e)}"
    
    @staticmethod
    def fetch_url(url: str) -> str:
        """Fetch content from a specific URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Basic content extraction - remove HTML tags
            content = response.text
            import re
            # Remove script and style elements
            content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Truncate if too long
            if len(content) > 3000:
                content = content[:3000] + "... [truncated]"
            
            return f"Content from {url}:\n{content}"
            
        except Exception as e:
            return f"Error fetching {url}: {str(e)}"


class ClaudeDebater:
    """Represents one Claude participant in the debate"""
    
    def __init__(self, client: Anthropic, participant_id: str):
        self.client = client
        self.participant_id = participant_id
        self.position = None  # Will be determined dynamically
        self.web_toolkit = WebToolkit()
    
    def generate_response(self, conversation_history: List[Message], topic: str) -> str:
        """Generate a response from this Claude instance"""
        
        # Convert conversation history to the format this Claude sees
        # Each Claude sees their own messages as "assistant" and opponent's as "user"
        formatted_history = []
        
        for msg in conversation_history:
            if msg.participant == self.participant_id:
                # This Claude's previous messages appear as "assistant"
                formatted_history.append({"role": "assistant", "content": msg.content})
            else:
                # Opponent's messages appear as "user"
                formatted_history.append({"role": "user", "content": msg.content})
        
        # Get current date for context
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Determine position if this is the first turn
        if len(conversation_history) == 0:
            if self.participant_id == "claude_1":
                # First Claude chooses their position
                system_prompt = f"""Today's date: {current_date}

You are about to engage in a debate on: "{topic}"

Your task: Choose which side of this debate you want to argue and present your opening statement.

You have access to web tools:
- [SEARCH: your query] - search the web for information
- [FETCH: url] - download content from a specific URL

Instructions:
1. First, decide what position you want to take on this topic
2. Research the topic thoroughly using web tools to gather current evidence
3. Present a compelling opening argument with supporting evidence
4. Your goal is to convince your opponent that your position is correct
5. Keep your response focused but substantive (aim for 200-400 words)
6. Use current events and recent data where relevant

Begin by choosing your position and making your opening statement."""
                user_prompt = f"Choose your position and make your opening argument on: {topic}"
            else:
                # Second Claude must take the opposite position
                opponent_position = self._extract_position_from_history(conversation_history)
                system_prompt = f"""Today's date: {current_date}

You are engaging in a debate on: "{topic}"

Your opponent has taken the position: {opponent_position}

Your task: Take the OPPOSITE position and argue against them convincingly.

You have access to web tools:
- [SEARCH: your query] - search the web for information  
- [FETCH: url] - download content from a specific URL

Instructions:
1. Analyze your opponent's argument carefully
2. Research counter-evidence using web tools and current data
3. Present a strong counter-argument with supporting evidence
4. Address their specific points while building your own case
5. Your goal is to convince them (and any observers) that you are right
6. Keep responses focused but substantive (aim for 200-400 words)
7. Use current events and recent data where relevant

Respond to their argument and present your counter-position."""
                user_prompt = "Present your counter-argument and opposing position."
        else:
            # Continuing debate - position already established
            system_prompt = f"""Today's date: {current_date}

You are participating in an ongoing debate on: "{topic}"

Your established position: {self.position}

You have access to web tools:
- [SEARCH: your query] - search the web for information
- [FETCH: url] - download content from a specific URL

Instructions:
1. Respond directly to your opponent's latest argument
2. Use web tools to find current evidence supporting your position
3. Address their points while strengthening your own case
4. Be persuasive and use concrete evidence
5. Your goal is to convince them they are wrong and you are right
6. Keep responses focused (aim for 200-400 words)
7. Use current events and recent data where relevant

Continue the debate by responding to their latest argument."""
            user_prompt = "Respond to your opponent's argument and continue making your case."

        
        formatted_history.append({"role": "user", "content": user_prompt})
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8_000,
                system=system_prompt,
                messages=formatted_history,
            )
            
            content = response.content[0].text
            
            # Process any web tool requests and track searches
            content, search_queries = self._process_web_requests(content)
            
            # Extract and store position if this is first turn
            if len(conversation_history) == 0:
                self.position = self._extract_position_from_response(content, topic)
            
            return content, search_queries
            
        except Exception as e:
            return f"Error generating response: {str(e)}", []
    
    def _process_web_requests(self, content: str) -> tuple[str, List[SearchQuery]]:
        """Process [SEARCH: query] and [FETCH: url] requests in the content"""
        import re
        
        search_queries = []
        current_time = time.time()
        
        # Process search requests
        search_pattern = r'\[SEARCH:\s*([^\]]+)\]'
        searches = re.findall(search_pattern, content)
        
        for query in searches:
            query_clean = query.strip()
            search_results = self.web_toolkit.search_web(query_clean)
            content = content.replace(f"[SEARCH: {query}]", f"\n[Search Results for '{query_clean}':\n{search_results}]\n")
            
            # Track the search query
            search_queries.append(SearchQuery(
                query=query_clean,
                timestamp=current_time,
                participant=self.participant_id
            ))
        
        # Process fetch requests
        fetch_pattern = r'\[FETCH:\s*([^\]]+)\]'
        fetches = re.findall(fetch_pattern, content)
        
        for url in fetches:
            url_clean = url.strip()
            fetch_results = self.web_toolkit.fetch_url(url_clean)
            content = content.replace(f"[FETCH: {url}]", f"\n[Fetched Content:\n{fetch_results}]\n")
            
            # Track the fetch request as a search query with URL
            search_queries.append(SearchQuery(
                query=f"Fetched: {url_clean}",
                timestamp=current_time,
                participant=self.participant_id,
                url=url_clean
            ))
        
        return content, search_queries
    
    def _extract_position_from_response(self, content: str, topic: str) -> str:
        """Extract the position this Claude has taken from their response"""
        # Simple heuristic - look for key phrases that indicate position
        content_lower = content.lower()
        
        # Try to identify the stance from the content
        if any(phrase in content_lower for phrase in ['i argue that', 'i believe', 'my position is', 'i contend']):
            # Extract a brief position summary
            lines = content.split('\n')
            for line in lines[:5]:  # Look in first few lines
                if any(phrase in line.lower() for phrase in ['argue', 'believe', 'position', 'contend']):
                    return line.strip()[:100] + "..." if len(line) > 100 else line.strip()
        
        # Fallback: use first substantial sentence
        sentences = content.split('. ')
        for sentence in sentences:
            if len(sentence.strip()) > 20:
                return sentence.strip()[:100] + "..." if len(sentence) > 100 else sentence.strip()
        
        return "Position not clearly stated"
    
    def _extract_position_from_history(self, conversation_history: List[Message]) -> str:
        """Extract the opponent's position from conversation history"""
        if conversation_history:
            first_message = conversation_history[0]
            return self._extract_position_from_response(first_message.content, "")
        return "Unknown position"


class DebateOrchestrator:
    """Manages the debate between two Claude instances"""
    
    def __init__(self, config: DebateConfig):
        self.config = config
        self.conversation_history: List[Message] = []
        
        # Initialize Anthropic client
        api_key = config.api_key or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable or api_key parameter required")
        
        client = Anthropic(api_key=api_key)
        
        # Create two Claude debaters (positions will be determined dynamically)
        self.claude_1 = ClaudeDebater(client, "claude_1")
        self.claude_2 = ClaudeDebater(client, "claude_2")
        
        self.current_speaker = self.claude_1
        self.turn_count = 0
    
    def run_debate(self) -> List[Dict[str, Any]]:
        """Run the complete debate and return the conversation history"""
        
        print(f"🎭 Starting debate: {self.config.topic}")
        print(f"📊 Claude 1 and Claude 2 will choose their own positions")
        print(f"🔄 Maximum turns: {self.config.max_turns}")
        print("-" * 60)
        
        while self.turn_count < self.config.max_turns:
            self.turn_count += 1
            current_participant = "claude_1" if self.current_speaker == self.claude_1 else "claude_2"
            position = self.current_speaker.position
            
            print(f"\n🗣️  Turn {self.turn_count} - Claude {current_participant[-1]} ({position}):")
            print("-" * 40)
            
            # Generate response
            response, search_queries = self.current_speaker.generate_response(
                self.conversation_history, 
                self.config.topic
            )
            
            # Add to conversation history
            message = Message(
                role="assistant",
                content=response,
                timestamp=time.time(),
                participant=current_participant,
                searches=search_queries
            )
            self.conversation_history.append(message)
            
            # Print the response
            print(response)
            
            # Switch speakers
            self.current_speaker = self.claude_2 if self.current_speaker == self.claude_1 else self.claude_1
            
            # Brief pause between turns
            time.sleep(1)
        
        print(f"\n🏁 Debate completed after {self.config.max_turns} turns")
        return [asdict(msg) for msg in self.conversation_history]
    
    def save_conversation(self, filename: str = None) -> str:
        """Save the conversation to a JSON file"""
        if filename is None:
            timestamp = int(time.time())
            filename = f"debate_{timestamp}.json"
        
        debate_data = {
            "config": asdict(self.config),
            "conversation": [asdict(msg) for msg in self.conversation_history],
            "metadata": {
                "total_turns": len(self.conversation_history),
                "start_time": self.conversation_history[0].timestamp if self.conversation_history else None,
                "end_time": self.conversation_history[-1].timestamp if self.conversation_history else None
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(debate_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Conversation saved to: {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description="Claude Debate Tool")
    parser.add_argument("topic", help="The debate topic")
    parser.add_argument("--turns", type=int, default=30, help="Maximum number of turns (default: 30)")
    parser.add_argument("--output", help="Output filename (default: auto-generated)")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Create debate configuration
    config = DebateConfig(
        topic=args.topic,
        max_turns=args.turns,
        api_key=args.api_key
    )
    
    try:
        # Create and run debate
        orchestrator = DebateOrchestrator(config)
        conversation = orchestrator.run_debate()
        
        # Save results
        output_file = orchestrator.save_conversation(args.output)
        
        print(f"\n✅ Debate complete! Results saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
