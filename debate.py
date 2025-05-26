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


@dataclass
class Message:
    role: str
    content: str
    timestamp: float
    participant: str


@dataclass
class DebateConfig:
    topic: str
    max_turns: int = 30
    claude_1_position: str = "pro"
    claude_2_position: str = "con"
    api_key: Optional[str] = None


class WebSearchTool:
    """Simple web search functionality for Claude participants"""
    
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


class ClaudeDebater:
    """Represents one Claude participant in the debate"""
    
    def __init__(self, client: Anthropic, position: str, participant_id: str):
        self.client = client
        self.position = position
        self.participant_id = participant_id
        self.search_tool = WebSearchTool()
    
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
        
        # Create system prompt
        system_prompt = f"""You are participating in a structured debate on the topic: "{topic}"

Your position: {self.position}

You have access to a web search function. To use it, include [SEARCH: your query] in your response and I'll provide the results.

Rules:
1. Make substantive arguments supporting your position
2. Address your opponent's points directly
3. Use evidence and reasoning
4. Be respectful but persuasive
5. Keep responses focused and under 300 words
6. You can search for current information to support your arguments

Current turn: Provide a thoughtful response that advances the debate."""

        # Add web search capability prompt
        if len(conversation_history) == 0:
            user_prompt = f"Begin the debate by presenting your opening argument for the {self.position} position on: {topic}"
        else:
            user_prompt = "Please respond to the previous argument and continue the debate."
        
        formatted_history.append({"role": "user", "content": user_prompt})
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                #max_tokens=1000,
                system=system_prompt,
                messages=formatted_history,
            )
            
            content = response.content[0].text
            
            # Process any search requests
            content = self._process_search_requests(content)
            
            return content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _process_search_requests(self, content: str) -> str:
        """Process [SEARCH: query] requests in the content"""
        import re
        
        search_pattern = r'\[SEARCH:\s*([^\]]+)\]'
        searches = re.findall(search_pattern, content)
        
        for query in searches:
            search_results = self.search_tool.search_web(query.strip())
            # Replace the search request with results
            content = content.replace(f"[SEARCH: {query}]", f"\n[Search Results for '{query}':\n{search_results}]\n")
        
        return content


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
        
        # Create two Claude debaters
        self.claude_1 = ClaudeDebater(client, config.claude_1_position, "claude_1")
        self.claude_2 = ClaudeDebater(client, config.claude_2_position, "claude_2")
        
        self.current_speaker = self.claude_1
        self.turn_count = 0
    
    def run_debate(self) -> List[Dict[str, Any]]:
        """Run the complete debate and return the conversation history"""
        
        print(f"🎭 Starting debate: {self.config.topic}")
        print(f"📊 Claude 1 ({self.config.claude_1_position}) vs Claude 2 ({self.config.claude_2_position})")
        print(f"🔄 Maximum turns: {self.config.max_turns}")
        print("-" * 60)
        
        while self.turn_count < self.config.max_turns:
            self.turn_count += 1
            current_participant = "claude_1" if self.current_speaker == self.claude_1 else "claude_2"
            position = self.current_speaker.position
            
            print(f"\n🗣️  Turn {self.turn_count} - Claude {current_participant[-1]} ({position}):")
            print("-" * 40)
            
            # Generate response
            response = self.current_speaker.generate_response(
                self.conversation_history, 
                self.config.topic
            )
            
            # Add to conversation history
            message = Message(
                role="assistant",
                content=response,
                timestamp=time.time(),
                participant=current_participant
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
    parser.add_argument("--position1", default="pro", help="Claude 1's position (default: pro)")
    parser.add_argument("--position2", default="con", help="Claude 2's position (default: con)")
    parser.add_argument("--output", help="Output filename (default: auto-generated)")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    
    args = parser.parse_args()
    
    # Create debate configuration
    config = DebateConfig(
        topic=args.topic,
        max_turns=args.turns,
        claude_1_position=args.position1,
        claude_2_position=args.position2,
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
