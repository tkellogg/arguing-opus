#!/usr/bin/env uv run
import os
import sys
import http.server
import socketserver
import webbrowser
from pathlib import Path

def main():
    """Start a local HTTP server to view published debates."""
    port = 8000
    directory = "published"
    
    # Check if published directory exists and has content
    published_dir = Path(directory)
    if not published_dir.exists():
        print(f"Error: {directory} directory does not exist")
        print("You need to publish at least one debate first. Run:")
        print("  ./publish.py conversations/your_debate_file.html")
        sys.exit(1)
    
    index_file = published_dir / "index.html"
    if not index_file.exists():
        print(f"Error: {directory}/index.html does not exist")
        print("You need to publish at least one debate first. Run:")
        print("  ./publish.py conversations/your_debate_file.html")
        sys.exit(1)
    
    # Set up the server
    handler = http.server.SimpleHTTPRequestHandler
    
    # Change to the published directory
    os.chdir(directory)
    
    # Create the server
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}/"
        print(f"Server started at {url}")
        print("Open your browser to view the debates")
        print("Press Ctrl+C to stop the server")
        
        # Open the browser automatically
        webbrowser.open(url)
        
        # Keep the server running until interrupted
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

if __name__ == "__main__":
    main()