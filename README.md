# Arguing Opus

A tool for creating and publishing AI debates where Claude models argue different positions on a topic.

## Publishing Debates

The `publish.py` script allows you to publish debates to a static HTML gallery:

```bash
# Publish a debate
./publish.py conversations/debate_123456789.html
```

This will:
1. Copy the HTML debate file to the `published/` directory
2. Copy the corresponding JSON file to the `published/` directory
3. Create or update an index page at `published/index.html`

The index page shows all published debates with:
- Topic title
- Model used (e.g., Claude Opus)
- Number of turns in the debate
- Publication date and time

## Viewing Published Debates

You can view the published debates in two ways:

1. **Direct file access**: Open `published/index.html` in your browser
2. **Local web server**: Run the included server script:

```bash
./serve.py
```

This will start a local web server on port 8000 and automatically open your browser to view the debates. The web server approach provides a better experience as it properly loads all resources and enables proper navigation between debates.

## Creating Debates

Use the main debate tool to create new debates:

```bash
# Create a new debate
python debate.py --topic "Is remote work better than office work?" --model opus
```

This will generate debate files in the `conversations/` directory which you can then publish.

## Requirements

- Python 3.6+
- UV package manager (install with `pip install uv`)

## File Structure

- `debate.py` - Main script for creating debates
- `publish.py` - Script for publishing debates to HTML gallery
- `serve.py` - Script for starting a local web server to view debates
- `json_to_html.py` - Utility for converting JSON debates to HTML
- `conversations/` - Directory containing debate files
- `published/` - Directory containing published debates and index

### Deploying to GitHub Pages

Use the `stage_publish.py` script to copy all finished debates from
`conversations/` into the `published/` folder. Commit the updated `published`
directory and push to trigger the GitHub Pages workflow.

```bash
./stage_publish.py
```

The GitHub Actions workflow in `.github/workflows/static.yml` will then deploy
the contents of `published/` to Pages.

## Quick Start

```bash
# 1. Create a debate
python debate.py --topic "Is AI consciousness possible?" --model opus

# 2. Publish the debate (replace with your actual filename)
./publish.py conversations/debate_1234567890.html

# 3. View the debates in a browser
./serve.py
```