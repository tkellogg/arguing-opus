#!/usr/bin/env uv run
import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime

def main():
    if len(sys.argv) != 2:
        print("Usage: python publish.py <html_file>")
        print("\nThis script will:")
        print("1. Copy the HTML file to the published/ directory")
        print("2. Find and copy the matching JSON file with the same base name")
        print("3. Update or create published/index.html with a link to the debate")
        print("\nExample: python publish.py conversations/debate_1748273237.html")
        sys.exit(1)
    
    html_file = sys.argv[1]
    if not os.path.exists(html_file) or not html_file.endswith('.html'):
        print(f"Error: {html_file} does not exist or is not an HTML file")
        sys.exit(1)
    
    # Find matching JSON file
    json_file = html_file.replace('.html', '.json')
    if not os.path.exists(json_file):
        print(f"Error: Matching JSON file {json_file} does not exist")
        sys.exit(1)
    
    # Create published directory if it doesn't exist
    published_dir = Path("published")
    published_dir.mkdir(exist_ok=True)
    
    # Copy HTML file to published directory
    html_filename = os.path.basename(html_file)
    html_target_path = published_dir / html_filename
    shutil.copy2(html_file, html_target_path)
    print(f"Copied {html_file} to {html_target_path}")
    
    # Copy JSON file to published directory
    json_filename = os.path.basename(json_file)
    json_target_path = published_dir / json_filename
    shutil.copy2(json_file, json_target_path)
    print(f"Copied {json_file} to {json_target_path}")
    
    # Extract title from JSON file
    debate_title = extract_title_from_json(json_file)
    
    # Update index.html
    index_path = published_dir / "index.html"
    
    # Create basic structure if index doesn't exist
    if not index_path.exists():
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Published Debates</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 900px; 
            margin: 0 auto; 
            padding: 30px;
            background-color: #f5f7fa;
            color: #333;
        }
        h1 { 
            color: #333;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        ul { 
            list-style-type: none; 
            padding: 0; 
        }
        li { 
            margin: 15px 0; 
            padding: 15px; 
            border: 1px solid #ddd; 
            border-radius: 8px;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        li:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        a { 
            color: #667eea; 
            text-decoration: none;
            font-weight: bold;
            font-size: 1.1em;
        }
        a:hover { 
            text-decoration: underline; 
        }
        .date { 
            color: #666; 
            font-size: 0.9em;
            display: block;
            margin-top: 5px;
        }
        .model, .turns {
            display: inline-block;
            font-size: 0.8em;
            background-color: #e2e8f0;
            padding: 2px 8px;
            border-radius: 4px;
            margin-left: 8px;
        }
        footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <h1>Published Debates</h1>
    <ul id="debate-list">
    </ul>
    <footer>
        Generated with the arguing-opus tool
    </footer>
</body>
</html>""")
    
    # Read the current index file
    with open(index_path, "r") as f:
        content = f.read()
    
    # Check if the file is already in the index
    if html_filename in content:
        print(f"{html_filename} is already in the index")
        return
    
    # Add new entry to the list
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Get model name and turns from JSON if available
    model_tag = ""
    turns_info = ""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        if 'config' in data and 'model_name' in data['config']:
            model_name = data['config']['model_name']
            model_tag = f'<span class="model">{model_name}</span>'
            
        # Get number of turns
        if 'metadata' in data and 'total_turns' in data['metadata']:
            turns = data['metadata']['total_turns']
            turns_info = f'<span class="turns">{turns} turns</span>'
        elif 'conversation' in data:
            turns = len(data['conversation'])
            turns_info = f'<span class="turns">{turns} turns</span>'
    except:
        pass
    
    new_entry = f'        <li><a href="{html_filename}">{debate_title}</a>{model_tag} {turns_info}<span class="date">Published: {current_date}</span></li>'
    
    # Insert the new entry at the beginning of the list
    updated_content = content.replace('<ul id="debate-list">', f'<ul id="debate-list">\n{new_entry}')
    
    # Write updated content back
    with open(index_path, "w") as f:
        f.write(updated_content)
    
    print(f"Updated {index_path} with link to {html_filename}")

def extract_title_from_json(json_file):
    """Extract a title from the JSON debate file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            
        # Based on the structure in the sample file
        if 'config' in data and 'topic' in data['config']:
            return data['config']['topic']
        elif 'title' in data:
            return data['title']
        elif 'topic' in data:
            return data['topic']
        elif 'prompt' in data:
            # Extract a shorter title from the prompt
            prompt = data['prompt']
            # Take first line or first 50 chars
            title = prompt.split('\n')[0]
            if len(title) > 50:
                title = title[:47] + "..."
            return title
        elif 'conversation' in data and len(data['conversation']) > 0:
            # Try to extract from first conversation message
            first_msg = data['conversation'][0]
            if 'content' in first_msg:
                title = first_msg['content'].split('\n')[0]
                if len(title) > 50:
                    title = title[:47] + "..."
                return title
        elif 'messages' in data and len(data['messages']) > 0:
            # Use the first message content as title
            first_msg = data['messages'][0]
            if 'content' in first_msg:
                title = first_msg['content'].split('\n')[0]
                if len(title) > 50:
                    title = title[:47] + "..."
                return title
        
        # Fallback to the filename if no title is found
        return os.path.basename(json_file).replace('.json', '')
        
    except Exception as e:
        print(f"Warning: Could not extract title from JSON: {e}")
        return os.path.basename(json_file).replace('.json', '')

if __name__ == "__main__":
    main()