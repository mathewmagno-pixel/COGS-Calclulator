#!/usr/bin/env python3
"""
J.A.R.V.I.S. — Just A Rather Very Intelligent System
=====================================================
Desktop AI assistant powered by Claude. Aggregates your email,
calendar, Slack, Notion, and HubSpot into a single intelligent
interface with voice interaction.

Usage:
    python main.py              # Start the server
    python main.py --port 8550  # Custom port
    python main.py --no-open    # Don't auto-open browser
"""

import sys
import argparse
import webbrowser
from pathlib import Path

# Ensure project root is on Python path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Desktop Assistant")
    parser.add_argument("--host", default=None, help="Host to bind to")
    parser.add_argument("--port", type=int, default=None, help="Port to listen on")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    from config import HOST, PORT

    host = args.host or HOST
    port = args.port or PORT

    print(r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
    Just A Rather Very Intelligent System
    """)

    print(f"  Starting on http://{host}:{port}")
    print(f"  Press Ctrl+C to shut down\n")

    if not args.no_open:
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    import uvicorn
    uvicorn.run(
        "server.app:app",
        host=host,
        port=port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
