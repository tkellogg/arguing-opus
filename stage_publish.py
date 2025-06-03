#!/usr/bin/env uv run
"""Stage all conversation HTML files for deployment."""

import subprocess
from pathlib import Path


def main():
    conv_dir = Path("conversations")
    if not conv_dir.exists():
        print(f"{conv_dir} does not exist. Nothing to stage.")
        return

    html_files = sorted(conv_dir.glob("*.html"))
    if not html_files:
        print("No HTML files found in conversations directory.")
        return

    for html_file in html_files:
        print(f"Publishing {html_file}...")
        subprocess.run(["./publish.py", str(html_file)], check=True)


if __name__ == "__main__":
    main()
