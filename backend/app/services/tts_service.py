"""tts_service stub — used by fortune audio endpoints."""
import logging

logger = logging.getLogger(__name__)


class TTSService:
    def synthesize_speech(self, text, output_filepath, provider="openai", voice_id=None, speed=1.0):
        logger.warning("tts_service.synthesize_speech (stub): no real TTS configured")
        return False

    def get_available_voices(self, provider="openai"):
        return []


tts_service = TTSService()
