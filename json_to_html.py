#!/usr/bin/env python3
"""
JSON to HTML Converter for Claude Debate Files
Converts debate JSON files into well-formatted HTML pages
"""

import json
import argparse
import os
from datetime import datetime
from typing import Dict, Any, List
import re
import markdown


class DebateHTMLGenerator:
    """Converts debate JSON files to HTML format"""
    
    def __init__(self):
        self.css_template = """
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                backdrop-filter: blur(10px);
            }
            
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                font-weight: 300;
            }
            
            .header .topic {
                font-size: 1.2em;
                opacity: 0.9;
                font-style: italic;
            }
            
            .metadata {
                background: #f8f9fa;
                padding: 20px 30px;
                border-bottom: 1px solid #e9ecef;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
            }
            
            .metadata-item {
                text-align: center;
            }
            
            .metadata-label {
                font-weight: 600;
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .metadata-value {
                font-size: 1.1em;
                color: #2c3e50;
                margin-top: 5px;
            }
            
            .debate-content {
                padding: 0;
            }
            
            .message {
                padding: 25px 30px;
                border-bottom: 1px solid #e9ecef;
                position: relative;
            }
            
            .message:last-child {
                border-bottom: none;
            }
            
            .claude-1 {
                background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                border-left: 5px solid #2196f3;
            }
            
            .claude-2 {
                background: linear-gradient(135deg, #f3e5f5 0%, #e8f5e8 100%);
                border-left: 5px solid #4caf50;
            }
            
            .message-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .participant {
                font-weight: 600;
                font-size: 1.1em;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .participant::before {
                content: "🤖";
                font-size: 1.2em;
            }
            
            .claude-1 .participant {
                color: #1976d2;
            }
            
            .claude-2 .participant {
                color: #388e3c;
            }
            
            .timestamp {
                color: #666;
                font-size: 0.9em;
                font-family: 'Monaco', 'Menlo', monospace;
            }
            
            .turn-number {
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(255, 255, 255, 0.8);
                color: #666;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.8em;
                font-weight: 600;
            }
            
            .message-content {
                font-size: 1.05em;
                line-height: 1.7;
                color: #2c3e50;
            }
            
            .message-content p {
                margin-bottom: 15px;
            }
            
            .message-content p:last-child {
                margin-bottom: 0;
            }
            
            .search-results, .fetched-content {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
                font-size: 0.95em;
            }
            
            .search-results {
                border-left: 4px solid #ff9800;
            }
            
            .fetched-content {
                border-left: 4px solid #9c27b0;
            }
            
            .search-results h4, .fetched-content h4 {
                color: #666;
                font-size: 0.9em;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .search-queries {
                background: rgba(255, 255, 255, 0.8);
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px 15px;
                margin: 10px 0;
                border-left: 4px solid #007bff;
            }
            
            .search-queries h5 {
                color: #666;
                font-size: 0.8em;
                margin: 0 0 8px 0;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .search-link {
                display: inline-block;
                margin: 2px 4px;
                padding: 4px 8px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 12px;
                font-size: 0.85em;
                transition: background 0.2s;
            }
            
            .search-link:hover {
                background: #0056b3;
                text-decoration: none;
                color: white;
            }
            
            .fetch-link {
                background: #6f42c1;
            }
            
            .fetch-link:hover {
                background: #5a2d91;
            }
            
            /* Markdown formatting within messages */
            .message-content h1, .message-content h2, .message-content h3 {
                color: #2c3e50;
                margin: 20px 0 10px 0;
            }
            
            .message-content h1 { font-size: 1.4em; }
            .message-content h2 { font-size: 1.3em; }
            .message-content h3 { font-size: 1.2em; }
            
            .message-content ul, .message-content ol {
                margin: 15px 0;
                padding-left: 25px;
            }
            
            .message-content li {
                margin: 5px 0;
            }
            
            .message-content blockquote {
                border-left: 4px solid #ddd;
                margin: 15px 0;
                padding: 10px 20px;
                background: rgba(255, 255, 255, 0.5);
                font-style: italic;
            }
            
            .message-content code {
                background: rgba(255, 255, 255, 0.8);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 0.9em;
            }
            
            .message-content pre {
                background: rgba(255, 255, 255, 0.8);
                padding: 15px;
                border-radius: 8px;
                overflow-x: auto;
                margin: 15px 0;
            }
            
            .message-content pre code {
                background: none;
                padding: 0;
            }
            
            .message-content strong {
                font-weight: 600;
                color: #1a1a1a;
            }
            
            .message-content em {
                font-style: italic;
                color: #555;
            }
            
            .footer {
                background: #f8f9fa;
                padding: 20px 30px;
                text-align: center;
                color: #666;
                font-size: 0.9em;
                border-top: 1px solid #e9ecef;
            }
            
            .summary {
                background: #e8f5e8;
                padding: 20px 30px;
                border-bottom: 1px solid #e9ecef;
            }
            
            .summary h3 {
                color: #2e7d32;
                margin-bottom: 10px;
            }
            
            @media (max-width: 768px) {
                body {
                    padding: 10px;
                }
                
                .header {
                    padding: 20px;
                }
                
                .header h1 {
                    font-size: 2em;
                }
                
                .message {
                    padding: 20px 15px;
                }
                
                .metadata {
                    padding: 15px;
                    grid-template-columns: 1fr;
                    gap: 10px;
                }
            }
        </style>
        """
    
    def format_timestamp(self, timestamp: float) -> str:
        """Format Unix timestamp to readable date/time"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%B %d, %Y at %I:%M:%S %p")
    
    def format_duration(self, start_time: float, end_time: float) -> str:
        """Calculate and format debate duration"""
        duration_seconds = int(end_time - start_time)
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def process_message_content(self, content: str) -> str:
        """Process message content to format search results and convert markdown"""
        # First, extract and temporarily replace search results and fetched content
        search_results = []
        fetched_contents = []
        
        # Extract search results
        search_pattern = r'\[Search Results for \'([^\']+)\':\n([^\]]+)\]'
        def replace_search(match):
            search_results.append((match.group(1), match.group(2)))
            return f"__SEARCH_RESULT_{len(search_results)-1}__"
        content = re.sub(search_pattern, replace_search, content, flags=re.DOTALL)
        
        # Extract fetched content
        fetch_pattern = r'\[Fetched Content:\n([^\]]+)\]'
        def replace_fetch(match):
            fetched_contents.append(match.group(1))
            return f"__FETCHED_CONTENT_{len(fetched_contents)-1}__"
        content = re.sub(fetch_pattern, replace_fetch, content, flags=re.DOTALL)
        
        # Convert markdown to HTML
        html_content = markdown.markdown(content, extensions=['nl2br', 'codehilite', 'fenced_code'])
        
        # Restore search results with proper formatting (preserve original simple format)
        for i, (query, results) in enumerate(search_results):
            # Keep search results as plain text with line breaks
            formatted_results = results.replace('\n', '<br>')
            search_html = f'<div class="search-results"><h4>🔍 Search Results for "{query}"</h4>{formatted_results}</div>'
            html_content = html_content.replace(f"__SEARCH_RESULT_{i}__", search_html)
        
        # Restore fetched content with proper formatting (preserve original simple format)
        for i, content_text in enumerate(fetched_contents):
            # Keep fetched content as plain text with line breaks
            formatted_content = content_text.replace('\n', '<br>')
            fetch_html = f'<div class="fetched-content"><h4>🌐 Fetched Content</h4>{formatted_content}</div>'
            html_content = html_content.replace(f"__FETCHED_CONTENT_{i}__", fetch_html)
        
        return html_content
    
    def extract_positions(self, conversation: List[Dict]) -> tuple:
        """Extract the positions taken by each Claude"""
        claude_1_position = "Position not clearly stated"
        claude_2_position = "Position not clearly stated"
        
        for msg in conversation[:2]:  # Look at first two messages
            content_lower = msg['content'].lower()
            participant = msg['participant']
            
            # Try to extract position from content
            if any(phrase in content_lower for phrase in ['i argue', 'i believe', 'my position', 'i contend']):
                lines = msg['content'].split('\n')
                for line in lines[:5]:
                    if any(phrase in line.lower() for phrase in ['argue', 'believe', 'position', 'contend']):
                        position = line.strip()[:100]
                        if participant == 'claude_1':
                            claude_1_position = position
                        else:
                            claude_2_position = position
                        break
        
        return claude_1_position, claude_2_position
    
    def generate_html(self, debate_data: Dict[str, Any]) -> str:
        """Generate complete HTML from debate JSON data"""
        config = debate_data['config']
        conversation = debate_data['conversation']
        metadata = debate_data['metadata']
        
        # Extract positions
        claude_1_pos, claude_2_pos = self.extract_positions(conversation)
        
        # Calculate duration
        duration = ""
        if metadata.get('start_time') and metadata.get('end_time'):
            duration = self.format_duration(metadata['start_time'], metadata['end_time'])
        
        # Generate messages HTML
        messages_html = ""
        for i, msg in enumerate(conversation, 1):
            participant_class = msg['participant'].replace('_', '-')
            participant_name = f"Claude {msg['participant'][-1]}"
            timestamp = self.format_timestamp(msg['timestamp'])
            content = self.process_message_content(msg['content'])
            
            # Generate search queries section
            search_queries_html = ""
            if msg.get('searches') and len(msg['searches']) > 0:
                search_links = []
                for search in msg['searches']:
                    if search.get('url'):  # This is a fetch operation
                        search_links.append(f'<a href="{search["url"]}" class="search-link fetch-link" target="_blank" title="Fetched: {search["url"]}">{search["query"]}</a>')
                    else:  # This is a search operation
                        # Create Google search URL
                        search_url = f"https://www.google.com/search?q={search['query'].replace(' ', '+')}"
                        search_links.append(f'<a href="{search_url}" class="search-link" target="_blank" title="Search: {search["query"]}">{search["query"]}</a>')
                
                if search_links:
                    search_queries_html = f'''
                    <div class="search-queries">
                        <h5>🔍 Web Searches & Fetches</h5>
                        {''.join(search_links)}
                    </div>
                    '''
            
            messages_html += f'''
            <div class="message {participant_class}">
                <div class="turn-number">Turn {i}</div>
                <div class="message-header">
                    <div class="participant">{participant_name}</div>
                    <div class="timestamp">{timestamp}</div>
                </div>
                {search_queries_html}
                <div class="message-content">
                    {content}
                </div>
            </div>
            '''
        
        # Generate complete HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Debate: {config['topic']}</title>
    {self.css_template}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎭 Claude Debate</h1>
            <div class="topic">"{config['topic']}"</div>
        </div>
        
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">Total Turns</div>
                <div class="metadata-value">{metadata.get('total_turns', len(conversation))}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Duration</div>
                <div class="metadata-value">{duration or 'Unknown'}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Start Time</div>
                <div class="metadata-value">{self.format_timestamp(metadata['start_time']) if metadata.get('start_time') else 'Unknown'}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Max Turns</div>
                <div class="metadata-value">{config.get('max_turns', 'Unknown')}</div>
            </div>
        </div>
        
        <div class="summary">
            <h3>📊 Debate Positions</h3>
            <p><strong>Claude 1:</strong> {claude_1_pos}</p>
            <p><strong>Claude 2:</strong> {claude_2_pos}</p>
        </div>
        
        <div class="debate-content">
            {messages_html}
        </div>
        
        <div class="footer">
            Generated on {datetime.now().strftime("%B %d, %Y at %I:%M:%S %p")} • 
            Claude Debate Tool
        </div>
    </div>
</body>
</html>'''
        
        return html


def main():
    parser = argparse.ArgumentParser(description="Convert Claude debate JSON to HTML")
    parser.add_argument("json_file", help="Path to the debate JSON file")
    parser.add_argument("-o", "--output", help="Output HTML filename (default: same name as JSON with .html extension)")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.json_file):
        print(f"❌ Error: File '{args.json_file}' not found")
        return 1
    
    if not args.json_file.endswith('.json'):
        print(f"❌ Error: Input file must be a JSON file")
        return 1
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.json_file))[0]
        output_file = f"conversations/{base_name}.html"
    
    # Create conversations directory if it doesn't exist
    os.makedirs("conversations", exist_ok=True)
    
    try:
        # Load JSON data
        print(f"📖 Loading debate data from {args.json_file}")
        with open(args.json_file, 'r', encoding='utf-8') as f:
            debate_data = json.load(f)
        
        # Validate JSON structure
        required_keys = ['config', 'conversation', 'metadata']
        if not all(key in debate_data for key in required_keys):
            print(f"❌ Error: Invalid debate JSON format. Missing required keys: {required_keys}")
            return 1
        
        # Generate HTML
        print(f"🎨 Generating HTML...")
        generator = DebateHTMLGenerator()
        html_content = generator.generate_html(debate_data)
        
        # Write HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML generated successfully: {output_file}")
        print(f"🌐 Open in browser: file://{os.path.abspath(output_file)}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format - {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())