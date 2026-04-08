"""
JARVIS Voice System - Text-to-Speech engine.

Supports two backends:
  - edge-tts: Free, high-quality Microsoft voices (default)
  - elevenlabs: Premium, ultra-realistic voices

Speech-to-text is handled client-side via the Web Speech API.
"""

import hashlib
import asyncio
from pathlib import Path

from config import (
    TTS_ENGINE,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    EDGE_TTS_VOICE,
    AUDIO_CACHE_DIR,
)


class VoiceEngine:
    """Converts text to speech audio files."""

    def __init__(self):
        self.engine = TTS_ENGINE
        self.cache_dir = AUDIO_CACHE_DIR

    def _cache_key(self, text: str) -> str:
        """Generate a cache filename from text content."""
        h = hashlib.md5(text.encode()).hexdigest()[:12]
        return f"jarvis_{h}.mp3"

    def _get_cached(self, text: str) -> Path | None:
        """Return cached audio path if it exists."""
        path = self.cache_dir / self._cache_key(text)
        return path if path.exists() else None

    async def synthesize(self, text: str) -> Path:
        """Convert text to speech and return path to audio file."""
        # Check cache first
        cached = self._get_cached(text)
        if cached:
            return cached

        output_path = self.cache_dir / self._cache_key(text)

        if self.engine == "elevenlabs":
            await self._synthesize_elevenlabs(text, output_path)
        else:
            await self._synthesize_edge(text, output_path)

        return output_path

    async def _synthesize_edge(self, text: str, output_path: Path):
        """Use Edge TTS (free, high quality Microsoft voices)."""
        import edge_tts

        communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
        await communicate.save(str(output_path))

    async def _synthesize_elevenlabs(self, text: str, output_path: Path):
        """Use ElevenLabs API (premium, ultra-realistic)."""
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        audio = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_turbo_v2",
        )

        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

    def clear_cache(self):
        """Remove all cached audio files."""
        for f in self.cache_dir.glob("jarvis_*.mp3"):
            f.unlink()
