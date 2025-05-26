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
    model_name: str = "sonnet"


class WebToolkit:
    """Web search and fetch functionality for Claude participants"""
    
    @staticmethod
    def search_web(query: str, num_results: int = 3) -> str:
        """Perform a web search and return formatted results"""
        try:
            import os
            
            # Get API key from environment
            api_key = os.getenv('BRAVE_SEARCH_API_KEY')
            if not api_key:
                return "Error: BRAVE_SEARCH_API_KEY environment variable not set"
            
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'X-Subscription-Token': api_key
            }
            
            params = {
                'q': query,
                'count': num_results,
                'search_lang': 'en',
                'country': 'US',
                'safesearch': 'moderate',
                'freshness': 'pw'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            if data.get('web', {}).get('results'):
                for i, result in enumerate(data['web']['results'], 1):
                    title = result.get('title', 'No title')
                    url = result.get('url', '')
                    description = result.get('description', 'No description')
                    results.append(f"{i}. {title}\n   {url}\n   {description}\n")
            
            return "\n".join(results) if results else f"No search results found for '{query}'"
            
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
    
    def generate_response(self, conversation_history: List[Message], topic: str, model_name: str) -> tuple[str, List[SearchQuery]]:
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

You have access to web search tools to research your position:
- Use the web_search tool to find current information and evidence
- Use the web_fetch tool to get detailed content from specific URLs

Instructions:
1. First, decide what position you want to take on this topic
2. **IMPORTANT**: Use the web_search tool to research current evidence before making your argument
3. Search for recent data, studies, and current events related to your position
4. Present a compelling opening argument incorporating the search results
5. Your goal is to convince your opponent that your position is correct
6. Keep your response focused but substantive (aim for 200-400 words)

You must use the web_search tool to gather evidence before presenting your argument."""
                user_prompt = f"Choose your position and make your opening argument on: {topic}"
            else:
                # Second Claude must take the opposite position
                opponent_position = self._extract_position_from_history(conversation_history)
                system_prompt = f"""Today's date: {current_date}

You are engaging in a debate on: "{topic}"

Your opponent has taken the position: {opponent_position}

Your task: You MUST take the OPPOSITE position from your opponent and argue AGAINST their stance convincingly.

CRITICAL: Whatever position your opponent took, you must take the opposite side. If they are "for" something, you must be "against" it. If they are "against" something, you must be "for" it. You cannot agree with them - this is a debate where you must oppose their position.

You have access to web search tools to research your counter-position:
- Use the web_search tool to find current information and evidence
- Use the web_fetch tool to get detailed content from specific URLs

Instructions:
1. Analyze your opponent's argument carefully
2. **IMPORTANT**: Use the web_search tool to find counter-evidence and current data
3. Search for information that contradicts or challenges their claims
4. Present a strong counter-argument incorporating your search results
5. Address their specific points while building your own case
6. Your goal is to convince them (and any observers) that you are right
7. Keep responses focused but substantive (aim for 200-400 words)

You must use the web_search tool to gather counter-evidence before presenting your argument."""
                user_prompt = "Present your counter-argument and opposing position."
        else:
            # Continuing debate - position already established
            system_prompt = f"""Today's date: {current_date}

You are participating in an ongoing debate on: "{topic}"

Your established position: {self.position}

You have access to web search tools to research supporting evidence:
- Use the web_search tool to find current information and evidence
- Use the web_fetch tool to get detailed content from specific URLs

Instructions:
1. Respond directly to your opponent's latest argument
2. **IMPORTANT**: Use the web_search tool to find current evidence supporting your position
3. Search for data that refutes their claims and supports your stance
4. Address their points while strengthening your own case with search results
5. Be persuasive and use concrete evidence from your searches
6. Your goal is to convince them they are wrong and you are right
7. Keep responses focused (aim for 200-400 words)

You should use the web_search tool to gather supporting evidence for your response."""
            user_prompt = "Respond to your opponent's argument and continue making your case."

        
        formatted_history.append({"role": "user", "content": user_prompt})
        
        # Define available tools for Claude
        tools = [
            {
                "name": "web_search",
                "description": "Search the web for current information to support your arguments",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up current information"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "web_fetch",
                "description": "Fetch content from a specific URL to get detailed information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch content from"
                        }
                    },
                    "required": ["url"]
                }
            }
        ]


        try:
            max_iterations = 50  # Allow multiple tool calls
            search_queries = []
            all_content = []
            
            for iteration in range(max_iterations):
                response = self.client.messages.create(
                    model=f"claude-{model_name}-4-20250514",
                    max_tokens=8_000,
                    system=system_prompt,
                    messages=formatted_history,
                    tools=tools
                )
                
                # Handle the response
                content_blocks = []
                tool_calls = []
                
                for content_block in response.content:
                    if content_block.type == "text":
                        content_blocks.append(content_block.text)
                    elif content_block.type == "tool_use":
                        tool_calls.append(content_block)
                
                # Add Claude's response to the conversation
                formatted_history.append({
                    "role": "assistant", 
                    "content": response.content
                })
                
                # Store the text content
                if content_blocks:
                    all_content.extend(content_blocks)
                
                # Process any tool calls
                if tool_calls:
                    tool_results = []
                    
                    for tool_call in tool_calls:
                        if tool_call.name == "web_search":
                            query = tool_call.input["query"]
                            result = self.web_toolkit.search_web(query)
                            search_queries.append(SearchQuery(
                                query=query,
                                timestamp=time.time(),
                                participant=self.participant_id
                            ))
                            content = f"Search results for '{query}':\n{result}"
                            print(f"🪲 web_search; text=\"{result}\"")
                            
                        elif tool_call.name == "web_fetch":
                            url = tool_call.input["url"]
                            result = self.web_toolkit.fetch_url(url)
                            search_queries.append(SearchQuery(
                                query=f"Fetched: {url}",
                                timestamp=time.time(),
                                participant=self.participant_id,
                                url=url
                            ))
                            content = f"Content from {url}:\n{result}"
                            print(f"🪲 web_fetch; text=\"{result}\"")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call.id,
                            "content": content
                        })
                    
                    # Add tool results to conversation
                    formatted_history.append({
                        "role": "user",
                        "content": tool_results
                    })
                else:
                    # No tools called, this is the final response
                    break
            
            # Combine all content
            final_content = "\n\n".join(all_content)
            
            # Extract and store position if this is first turn
            if len(conversation_history) == 0:
                self.position = self._extract_position_from_response(final_content, topic)
            
            return final_content, search_queries
            
        except Exception as e:
            return f"Error generating response: {str(e)}", []
    
    
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
        print(f"🔄 Turns per participant: {self.config.max_turns} (total: {self.config.max_turns*2})")
        print("-" * 60)
        
        while self.turn_count < self.config.max_turns*2:
            self.turn_count += 1
            current_participant = "claude_1" if self.current_speaker == self.claude_1 else "claude_2"
            position = self.current_speaker.position
            
            print(f"\n🗣️  Turn {self.turn_count} - Claude {current_participant[-1]} ({position}):")
            print("-" * 40)
            
            # Generate response
            response, search_queries = self.current_speaker.generate_response(
                self.conversation_history, 
                self.config.topic,
                self.config.model_name,
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
        
        print(f"\n🏁 Debate completed after {self.turn_count} total turns ({self.config.max_turns} per participant)")
        return [asdict(msg) for msg in self.conversation_history]
    
    def save_conversation(self, filename: str = None) -> str:
        """Save the conversation to a JSON file"""
        # Create conversations directory if it doesn't exist
        conversations_dir = "conversations"
        os.makedirs(conversations_dir, exist_ok=True)
        
        if filename is None:
            timestamp = int(time.time())
            filename = f"debate_{timestamp}.json"
        
        # Ensure filename goes in conversations directory
        if not filename.startswith(conversations_dir):
            filename = os.path.join(conversations_dir, filename)
        
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


def debug_search(query: str):
    """Debug function to test web search directly"""
    print(f"🔍 Testing search for: {query}")
    print("-" * 50)
    
    toolkit = WebToolkit()
    
    # Test web search
    print("📝 Web Search Results:")
    search_result = toolkit.search_web(query)
    print(search_result)
    print()
    
    # If query looks like a URL, test fetch too
    if query.startswith(('http://', 'https://')):
        print("🌐 Web Fetch Results:")
        fetch_result = toolkit.fetch_url(query)
        print(fetch_result)


def main():
    parser = argparse.ArgumentParser(description="Claude Debate Tool")
    parser.add_argument("topic", nargs='?', help="The debate topic")
    parser.add_argument("--turns", type=int, default=30, help="Number of turns each participant gets (default: 30)")
    parser.add_argument("--model", default="sonnet", help="The model to use, either 'sonnet' or 'opus' (default: sonnet)")
    parser.add_argument("--output", help="Output filename (default: auto-generated)")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--debug-search", help="Test web search functionality with a query")
    
    args = parser.parse_args()
    
    # Handle debug search mode
    if args.debug_search:
        debug_search(args.debug_search)
        return 0
    
    # Require topic for normal debate mode
    if not args.topic:
        parser.error("topic is required unless using --debug-search")
    
    # Create debate configuration
    config = DebateConfig(
        topic=args.topic,
        max_turns=args.turns,
        api_key=args.api_key,
        model_name=args.model
    )
    
    try:
        # Create and run debate
        orchestrator = DebateOrchestrator(config)
        conversation = orchestrator.run_debate()
        
        # Save results
        output_file = orchestrator.save_conversation(args.output)
        
        # Generate HTML
        import platform
        import subprocess
        from json_to_html import DebateHTMLGenerator
        
        # Determine HTML filename
        base_name = os.path.splitext(os.path.basename(output_file))[0]
        html_file = f"conversations/{base_name}.html"
        
        try:
            # Load the JSON data we just saved
            with open(output_file, 'r', encoding='utf-8') as f:
                debate_data = json.load(f)
            
            # Generate HTML using the imported class
            generator = DebateHTMLGenerator()
            html_content = generator.generate_html(debate_data)
            
            # Write HTML file
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"🎨 HTML generated: {html_file}")
            
            # Open HTML file on Mac
            if platform.system() == "Darwin":  # macOS
                html_path = os.path.abspath(html_file)
                subprocess.run(["open", html_path], check=False)
                print(f"🌐 Opened in browser: {html_path}")
                
        except Exception as e:
            print(f"⚠️  Error with HTML generation: {e}")
        
        print(f"\n✅ Debate complete! Results saved to {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
