"""
JARVIS Server - FastAPI application
------------------------------------
Serves the web UI and handles all API requests including
chat, voice synthesis, integration management, and the
priority briefing system.
"""

import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.brain import JarvisBrain
from assistant.voice import VoiceEngine
from assistant.priority import PriorityEngine
from integrations.registry import IntegrationRegistry
from integrations.gmail import GmailIntegration
from integrations.calendar_int import CalendarIntegration
from integrations.slack import SlackIntegration
from integrations.notion import NotionIntegration
from integrations.hubspot import HubSpotIntegration

# ---- Core Components ----
brain = JarvisBrain()
voice = VoiceEngine()
priority_engine = PriorityEngine()
registry = IntegrationRegistry()

# Register all integrations
registry.register(GmailIntegration())
registry.register(CalendarIntegration())
registry.register(SlackIntegration())
registry.register(NotionIntegration())
registry.register(HubSpotIntegration())

# Wire brain to registry and priority engine
brain.set_registry(registry)
brain.set_priority_engine(priority_engine)

# Background refresh task handle
_refresh_task: asyncio.Task | None = None


# ---- Lifespan ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global _refresh_task

    print("\n  ╔══════════════════════════════════════════╗")
    print("  ║         J.A.R.V.I.S. Initializing        ║")
    print("  ╚══════════════════════════════════════════╝\n")

    # Connect all integrations
    results = await registry.connect_all()
    for name, success in results.items():
        status = "ONLINE" if success else "OFFLINE"
        print(f"  [{status:>7}] {name}")

    # Initial priority refresh
    await _refresh_priorities()

    # Start background priority refresh (every 5 minutes)
    _refresh_task = asyncio.create_task(_periodic_refresh())

    print("\n  JARVIS is ready.\n")

    yield

    # Shutdown
    if _refresh_task:
        _refresh_task.cancel()
        try:
            await _refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="JARVIS Desktop Assistant", version="2.0.0", lifespan=lifespan)

# Serve static UI files
UI_DIR = Path(__file__).parent.parent / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


# ---- Background Tasks ----

async def _refresh_priorities():
    """Refresh the priority engine with data from all integrations."""
    priority_engine.clear()
    items = await registry.fetch_all_items()
    priority_engine.add_items(items)


async def _periodic_refresh():
    """Periodically refresh priorities in the background."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        try:
            await _refresh_priorities()
        except Exception as e:
            print(f"[Background] Priority refresh error: {e}")


# ---- Request / Response models ----

class ChatRequest(BaseModel):
    message: str
    voice_enabled: bool = True


class ChatResponse(BaseModel):
    text: str
    audio_url: str | None = None


# ---- Routes ----

@app.get("/")
async def serve_ui():
    """Serve the JARVIS web interface."""
    return FileResponse(UI_DIR / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Process a chat message through the JARVIS brain with tool-use."""
    # Gather live context from connected integrations
    context = await registry.get_all_context()

    # Get AI response (may include tool calls internally)
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
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    audio_path = Path(__file__).parent.parent / "audio_cache" / safe_name
    if audio_path.exists():
        return FileResponse(str(audio_path), media_type="audio/mpeg")
    return JSONResponse({"error": "Audio not found"}, status_code=404)


@app.get("/api/briefing")
async def get_briefing():
    """Get a full priority briefing across all integrations."""
    await _refresh_priorities()

    ranked = priority_engine.get_ranked(limit=20)
    briefing_text = priority_engine.get_briefing()

    # Also ask JARVIS to narrate the briefing
    jarvis_briefing = None
    if ranked:
        try:
            jarvis_briefing = await brain.think(
                "Give me my morning briefing. Summarize my priorities concisely.",
                await registry.get_all_context(),
            )
        except Exception:
            jarvis_briefing = briefing_text

    # Generate voice briefing
    audio_url = None
    text_for_speech = jarvis_briefing or briefing_text
    if ranked and text_for_speech:
        try:
            audio_path = await voice.synthesize(text_for_speech)
            audio_url = f"/api/audio/{audio_path.name}"
        except Exception as e:
            print(f"[Voice] Briefing TTS error: {e}")

    return {
        "text": jarvis_briefing or briefing_text,
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
    return registry.list_status()


@app.post("/api/integrations/{name}/connect")
async def connect_integration(name: str):
    """Connect a specific integration."""
    adapter = registry.get(name)
    if not adapter:
        return JSONResponse({"error": f"Unknown integration: {name}"}, status_code=404)

    success = await adapter.connect()
    return {"name": name, "connected": success}


@app.post("/api/integrations/{name}/disconnect")
async def disconnect_integration(name: str):
    """Disconnect a specific integration."""
    adapter = registry.get(name)
    if not adapter:
        return JSONResponse({"error": f"Unknown integration: {name}"}, status_code=404)

    await adapter.disconnect()
    return {"name": name, "connected": False}


@app.post("/api/clear-history")
async def clear_history():
    """Clear conversation history."""
    brain.clear_history()
    return {"status": "ok"}


@app.get("/api/settings")
async def get_settings():
    """Return current JARVIS settings."""
    from config import TTS_ENGINE, EDGE_TTS_VOICE, CLAUDE_MODEL
    return {
        "tts_engine": TTS_ENGINE,
        "tts_voice": EDGE_TTS_VOICE,
        "claude_model": CLAUDE_MODEL,
        "active_integrations": registry.list_active(),
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with voice."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat_input")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            message = data.get("message", data.get("text", ""))
            voice_enabled = data.get("voice_enabled", True)

            if not message:
                continue

            # Send thinking status
            await websocket.send_json({"type": "status", "message": "Thinking..."})

            # Gather context and get response
            context = await registry.get_all_context()
            response_text = await brain.think(message, context if context else None)

            result = {"type": "response", "text": response_text}

            # Generate audio
            if voice_enabled:
                await websocket.send_json({"type": "status", "message": "Generating voice..."})
                try:
                    audio_path = await voice.synthesize(response_text)
                    result["audio_url"] = f"/api/audio/{audio_path.name}"
                except Exception:
                    pass

            await websocket.send_json(result)

    except WebSocketDisconnect:
        pass
