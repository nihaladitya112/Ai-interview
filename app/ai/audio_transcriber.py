"""
Audio Transcriber
=================
Handles transcribing raw audio files using Whisper AI (via Groq or OpenAI).
"""

import io
import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

async def transcribe_audio(filename: str, audio_bytes: bytes) -> str:
    """
    Transcribes audio bytes to text using the Whisper API.
    Uses Groq's whisper model if a Groq key is provided, otherwise falls back to OpenAI's whisper-1.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("No API key provided for transcription. Returning fallback text.")
        return "Audio transcription failed: No API key configured."

    if api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model_name = "whisper-large-v3-turbo"
    else:
        base_url = None
        model_name = "whisper-1"

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        # We pass a tuple to the `file` parameter so httpx handles it as a file upload.
        # Format: (filename, bytes, content_type)
        response = await client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=model_name,
            prompt="Technical software engineering interview answer. Include technical terminology.",
            response_format="json",
            temperature=0.0
        )
        
        return response.text.strip()
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        
        # Fallback to whisper-large-v3 if turbo isn't available
        if model_name == "whisper-large-v3-turbo":
            logger.info("Falling back to whisper-large-v3...")
            try:
                response = await client.audio.transcriptions.create(
                    file=(filename, audio_bytes),
                    model="whisper-large-v3",
                    prompt="Technical software engineering interview answer. Include technical terminology.",
                    response_format="json",
                    temperature=0.0
                )
                return response.text.strip()
            except Exception as e2:
                logger.error(f"Fallback Whisper transcription failed: {e2}")
                raise ValueError(f"Failed to transcribe audio: {e2}")
        raise ValueError(f"Failed to transcribe audio: {e}")
