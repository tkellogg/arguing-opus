#!/usr/bin/env python3
"""
Test script to verify tool calling is working
"""

import os
from anthropic import Anthropic
import dotenv
dotenv.load_dotenv()

def test_tool_calling():
    # Initialize client
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    # Define a simple test tool
    tools = [
        {
            "name": "simple_test",
            "description": "A simple test tool that just returns a message",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "A test message"
                    }
                },
                "required": ["message"]
            }
        }
    ]
    
    # Simple test message
    messages = [
        {
            "role": "user",
            "content": "Please use the simple_test tool with the message 'hello world'"
        }
    ]
    
    print("Testing tool calling...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=messages,
            tools=tools
        )
        
        print(f"Response content types: {[block.type for block in response.content]}")
        
        for content_block in response.content:
            print(f"Block type: {content_block.type}")
            if content_block.type == "text":
                print(f"Text: {content_block.text}")
            elif content_block.type == "tool_use":
                print(f"Tool call: {content_block.name}")
                print(f"Tool input: {content_block.input}")
                print(f"Tool ID: {content_block.id}")
            else:
                print(f"Unknown type: {content_block}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tool_calling()