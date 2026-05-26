#!/usr/bin/env python3
"""
Reflection Hub — dev server
────────────────────────────
Serves the UI prototype from docs/ui/ on http://localhost:8080

Usage (from anywhere in the project):
    python docs/serve.py             # default port 8080
    python docs/serve.py 3000        # custom port

Then open: http://localhost:8080/reflection-hub.html
"""

import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    # Resolve docs/ui/ relative to this script's location
    ui_dir = Path(__file__).parent / "ui"
    if not ui_dir.is_dir():
        sys.exit(f"❌  UI directory not found: {ui_dir}\n   Run from the project root.")

    os.chdir(ui_dir)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: N802
            # Clean, coloured output
            status = args[1] if len(args) > 1 else "?"
            colour = "\033[32m" if str(status).startswith("2") else "\033[33m"
            reset = "\033[0m"
            print(f"  {colour}{status}{reset}  {args[0]}")

    url = f"http://localhost:{port}/index.html"

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"\n  🚀  Reflection Hub\n")
        print(f"  Local:   {url}")
        print(f"  Serving: {ui_dir}")
        print(f"\n  Press Ctrl+C to stop.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n  Server stopped.\n")


if __name__ == "__main__":
    main()
