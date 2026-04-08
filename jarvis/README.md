# J.A.R.V.I.S. — Just A Rather Very Intelligent System

A desktop AI assistant inspired by Iron Man's JARVIS. Aggregates your email, calendar, Slack, Notion, and HubSpot into a single intelligent interface with voice interaction, powered by Claude.

## Features

- **AI Brain** — Claude-powered with JARVIS personality, tool-use for live data queries, and conversation memory
- **Voice I/O** — Speak to it (browser speech recognition) and it speaks back with realistic TTS
- **Priority Engine** — Ranks items across all services by urgency (URGENT / HIGH / MEDIUM / LOW)
- **Morning Briefing** — One-click summary of everything that needs your attention
- **5 Integrations** — Gmail, Google Calendar, Slack, Notion, HubSpot
- **Quick Actions** — Pre-built buttons for common queries
- **Dark Holographic UI** — Animated grid, glowing accents, waveform visualizer

## Quick Start

```bash
cd jarvis
chmod +x setup.sh && ./setup.sh
```

This creates a virtual environment, installs dependencies, and generates a `.env` file.

Then:

```bash
# Edit .env with your API keys (at minimum: ANTHROPIC_API_KEY)
nano .env

# Start JARVIS
source venv/bin/activate
python main.py
```

JARVIS opens in your browser at **http://127.0.0.1:8550**

## Configuration

Copy `.env.example` to `.env` and fill in your keys:

| Key | Required | Description |
|-----|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key from console.anthropic.com |
| `TTS_ENGINE` | No | `edge` (free, default) or `elevenlabs` (premium) |
| `GOOGLE_CREDENTIALS_FILE` | No | Path to Google OAuth `credentials.json` |
| `SLACK_BOT_TOKEN` | No | Slack bot token (`xoxb-...`) |
| `NOTION_API_KEY` | No | Notion integration key |
| `HUBSPOT_API_KEY` | No | HubSpot API key |

Each integration is optional — JARVIS works with any combination connected.

## Architecture

```
jarvis/
├── main.py                    # Entry point
├── config.py                  # Settings from .env
├── assistant/
│   ├── brain.py               # Claude AI with tool-use loop
│   ├── tools.py               # Dynamic tool definitions per integration
│   ├── priority.py            # Priority scoring engine
│   └── voice.py               # TTS (Edge-TTS / ElevenLabs)
├── integrations/
│   ├── base.py                # Common interface (ABC)
│   ├── registry.py            # Auto-discovery and concurrent fetching
│   ├── gmail.py               # Gmail (unread, search, urgency scoring)
│   ├── calendar_int.py        # Google Calendar (events, conflicts)
│   ├── slack.py               # Slack (DMs, mentions, channels)
│   ├── notion.py              # Notion (tasks, databases, due dates)
│   └── hubspot.py             # HubSpot (deals, tasks, pipeline)
├── server/
│   └── app.py                 # FastAPI server (REST + WebSocket)
└── ui/
    └── index.html             # JARVIS web interface
```

### How It Works

1. **You speak or type** → Browser captures via Web Speech API or text input
2. **Server receives** → FastAPI routes to the JARVIS brain
3. **Claude thinks** → Uses tool-use to query live data from your integrations
4. **Response generated** → Text + TTS audio via Edge-TTS or ElevenLabs
5. **JARVIS speaks** → Audio plays in browser with waveform visualization

### Tool-Use Flow

When you ask "Do I have any urgent emails?", Claude doesn't just read cached context — it actively calls the `get_unread_emails` tool, fetches live data from Gmail, and synthesizes a response. This happens transparently in a tool-use loop that supports up to 5 rounds of tool calls per message.

## Voice

**Input:** Hold `Space` to talk, or click the microphone button. Uses the browser's built-in Web Speech API (works best in Chrome).

**Output:** Two TTS options:

| Engine | Quality | Cost |
|--------|---------|------|
| **Edge TTS** (default) | Good — natural Microsoft voices | Free |
| **ElevenLabs** | Excellent — ultra-realistic | Paid API |

Set `TTS_ENGINE=elevenlabs` in `.env` to use premium voices.

## Setting Up Integrations

### Gmail & Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable Gmail API + Calendar API
3. Create OAuth 2.0 credentials → download as `credentials.json`
4. Place `credentials.json` in the `jarvis/` directory
5. On first connect, a browser window opens for OAuth authorization

### Slack

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add scopes: `channels:history`, `channels:read`, `im:history`, `im:read`, `users:read`
3. Install to workspace and copy the Bot Token
4. Set `SLACK_BOT_TOKEN` in `.env`

### Notion

1. Create an integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Share your databases with the integration
3. Set `NOTION_API_KEY` and `NOTION_DATABASE_IDS` in `.env`

### HubSpot

1. Go to HubSpot Settings → Integrations → Private Apps
2. Create a private app with CRM scopes
3. Set `HUBSPOT_API_KEY` in `.env`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | JARVIS web UI |
| `POST` | `/api/chat` | Send message, get response + audio |
| `GET` | `/api/briefing` | Full priority briefing |
| `GET` | `/api/integrations` | Integration status |
| `POST` | `/api/integrations/{name}/connect` | Connect integration |
| `GET` | `/api/settings` | Current settings |
| `WS` | `/ws/chat` | Real-time WebSocket chat |
