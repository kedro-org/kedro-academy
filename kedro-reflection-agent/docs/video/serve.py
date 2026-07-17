#!/usr/bin/env python3
"""
Demo slide server — intro & outro HTML without file:// paths in the browser.

Usage (from project root):
    python docs/video/serve.py          # default port 8765
    python docs/video/serve.py 9000     # custom port
    make demo-slides

Open in the browser (clean URLs for screen recording):
    http://127.0.0.1:8765/intro
    http://127.0.0.1:8765/outro
"""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path

VIDEO_DIR = Path(__file__).resolve().parent
ROUTES = {
    "/": "demo_intro.html",
    "/intro": "demo_intro.html",
    "/outro": "demo_outro.html",
    "/demo_intro.html": "demo_intro.html",
    "/demo_outro.html": "demo_outro.html",
}


class DemoSlideHandler(http.server.SimpleHTTPRequestHandler):
    """Serve demo slides from docs/video/ with short URL aliases."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(VIDEO_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ROUTES:
            self.path = "/" + ROUTES[path]
        super().do_GET()

    def log_message(self, fmt: str, *args) -> None:
        status = args[1] if len(args) > 1 else "?"
        colour = "\033[32m" if str(status).startswith("2") else "\033[33m"
        reset = "\033[0m"
        print(f"  {colour}{status}{reset}  {args[0]}")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    host = "127.0.0.1"
    url = f"http://{host}:{port}/intro"

    os.chdir(VIDEO_DIR)

    with socketserver.TCPServer((host, port), DemoSlideHandler) as httpd:
        print("\n  Demo slides\n")
        print(f"  Intro:  http://{host}:{port}/intro")
        print(f"  Outro:  http://{host}:{port}/outro")
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
