"""
JARVIS Configuration
--------------------
All API keys and settings are loaded from environment variables.
Copy .env.example to .env and fill in your credentials.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# ---------------------------------------------------------------------------
# Core AI
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# ---------------------------------------------------------------------------
# Voice / TTS
# ---------------------------------------------------------------------------
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")  # "edge" (free) or "elevenlabs"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # "Adam"
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural")  # Deep, professional voice

# ---------------------------------------------------------------------------
# Gmail / Google Calendar  (OAuth2)
# ---------------------------------------------------------------------------
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
GMAIL_MAX_RESULTS = int(os.getenv("GMAIL_MAX_RESULTS", "20"))

# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN", "")

# ---------------------------------------------------------------------------
# Notion
# ---------------------------------------------------------------------------
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_IDS = os.getenv("NOTION_DATABASE_IDS", "").split(",")

# ---------------------------------------------------------------------------
# HubSpot
# ---------------------------------------------------------------------------
HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
HOST = os.getenv("JARVIS_HOST", "127.0.0.1")
PORT = int(os.getenv("JARVIS_PORT", "8550"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
AUDIO_CACHE_DIR = Path(__file__).parent / "audio_cache"
AUDIO_CACHE_DIR.mkdir(exist_ok=True)
