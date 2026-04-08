"""
JARVIS Server - FastAPI application
------------------------------------
Serves the web UI and handles all API requests including
chat, voice synthesis, and integration management.
"""

import sys
import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.brain import JarvisBrain
from assistant.voice import VoiceEngine
from assistant.priority import PriorityEngine
from integrations.gmail import GmailIntegration
from integrations.calendar_int import CalendarIntegration
from integrations.slack import SlackIntegration
from integrations.notion import NotionIntegration
from integrations.hubspot import HubSpotIntegration

app = FastAPI(title="JARVIS Desktop Assistant", version="1.0.0")

# Core components
brain = JarvisBrain()
voice = VoiceEngine()
priority_engine = PriorityEngine()

# Integrations registry
integrations = {
    "gmail": GmailIntegration(),
    "calendar": CalendarIntegration(),
    "slack": SlackIntegration(),
    "notion": NotionIntegration(),
    "hubspot": HubSpotIntegration(),
}

# Serve static UI files
UI_DIR = Path(__file__).parent.parent / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


# ---- Request / Response models ----

class ChatRequest(BaseModel):
    message: str
    voice_enabled: bool = True


class ChatResponse(BaseModel):
    text: str
    audio_url: str | None = None
    priorities: list[dict] | None = None


# ---- Routes ----

@app.get("/")
async def serve_ui():
    """Serve the JARVIS web interface."""
    return FileResponse(UI_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process a chat message through the JARVIS brain."""
    # Gather context from connected integrations
    context = {}
    for name, integration in integrations.items():
        if integration.connected:
            try:
                context[name] = await integration.get_context_summary()
            except Exception as e:
                context[name] = f"Error fetching {name} data: {e}"

    # Get AI response
    response_text = await brain.think(req.message, context if context else None)

    # Generate voice audio if enabled
    audio_url = None
    if req.voice_enabled:
        try:
            audio_path = await voice.synthesize(response_text)
            audio_url = f"/api/audio/{audio_path.name}"
        except Exception as e:
            print(f"[Voice] TTS error: {e}")

    return ChatResponse(text=response_text, audio_url=audio_url)


@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve a cached audio file."""
    from fastapi.responses import FileResponse as FR
    audio_path = Path(__file__).parent.parent / "audio_cache" / filename
    if audio_path.exists():
        return FR(str(audio_path), media_type="audio/mpeg")
    return JSONResponse({"error": "Audio not found"}, status_code=404)


@app.get("/api/briefing")
async def get_briefing():
    """Get a full priority briefing across all integrations."""
    priority_engine.clear()

    for name, integration in integrations.items():
        if integration.connected:
            try:
                items = await integration.fetch_items()
                priority_engine.add_items(items)
            except Exception as e:
                print(f"[Briefing] Error from {name}: {e}")

    ranked = priority_engine.get_ranked(limit=20)
    briefing_text = priority_engine.get_briefing()

    # Generate voice briefing
    audio_url = None
    if ranked:
        try:
            # Create a concise spoken briefing
            spoken = _create_spoken_briefing(ranked)
            audio_path = await voice.synthesize(spoken)
            audio_url = f"/api/audio/{audio_path.name}"
        except Exception as e:
            print(f"[Voice] Briefing TTS error: {e}")

    return {
        "text": briefing_text,
        "audio_url": audio_url,
        "items": [
            {
                "source": item.source,
                "title": item.title,
                "detail": item.detail,
                "level": item.level,
                "urgency": item.urgency,
                "timestamp": item.timestamp.isoformat(),
                "link": item.link,
                "tags": item.tags,
            }
            for item in ranked
        ],
    }


@app.get("/api/integrations")
async def get_integrations():
    """Return the status of all integrations."""
    return {
        name: integration.status()
        for name, integration in integrations.items()
    }


@app.post("/api/integrations/{name}/connect")
async def connect_integration(name: str):
    """Connect a specific integration."""
    if name not in integrations:
        return JSONResponse({"error": f"Unknown integration: {name}"}, status_code=404)

    success = await integrations[name].connect()
    return {"name": name, "connected": success}


@app.post("/api/integrations/{name}/disconnect")
async def disconnect_integration(name: str):
    """Disconnect a specific integration."""
    if name not in integrations:
        return JSONResponse({"error": f"Unknown integration: {name}"}, status_code=404)

    await integrations[name].disconnect()
    return {"name": name, "connected": False}


@app.post("/api/clear-history")
async def clear_history():
    """Clear conversation history."""
    brain.clear_history()
    return {"status": "ok"}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with streaming."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            voice_enabled = data.get("voice_enabled", True)

            # Gather context
            context = {}
            for name, integration in integrations.items():
                if integration.connected:
                    try:
                        context[name] = await integration.get_context_summary()
                    except Exception:
                        pass

            # Get response
            response_text = await brain.think(message, context if context else None)

            result = {"type": "response", "text": response_text}

            # Generate audio
            if voice_enabled:
                try:
                    audio_path = await voice.synthesize(response_text)
                    result["audio_url"] = f"/api/audio/{audio_path.name}"
                except Exception:
                    pass

            await websocket.send_json(result)

    except WebSocketDisconnect:
        pass


@app.on_event("startup")
async def startup():
    """Auto-connect integrations on startup."""
    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║         J.A.R.V.I.S. Initializing        ║")
    print("  ╚══════════════════════════════════════════╝\n")

    for name, integration in integrations.items():
        try:
            success = await integration.connect()
            status = "ONLINE" if success else "OFFLINE"
            print(f"  [{status:>7}] {name}")
        except Exception as e:
            print(f"  [OFFLINE] {name} - {e}")

    print("\n  JARVIS is ready.\n")


def _create_spoken_briefing(items) -> str:
    """Create a concise spoken version of the priority briefing."""
    urgent = [i for i in items if i.level == "URGENT"]
    high = [i for i in items if i.level == "HIGH"]
    medium = [i for i in items if i.level == "MEDIUM"]

    parts = ["Good morning, sir. Here is your briefing."]

    if urgent:
        parts.append(f"You have {len(urgent)} urgent items requiring immediate attention.")
        for item in urgent[:3]:
            parts.append(f"{item.title}.")

    if high:
        parts.append(f"There are {len(high)} high-priority items for today.")
        for item in high[:3]:
            parts.append(f"{item.title}.")

    if medium:
        parts.append(f"And {len(medium)} items at medium priority.")

    if not urgent and not high and not medium:
        parts.append("Your schedule looks clear. No pressing matters at this time.")

    return " ".join(parts)
