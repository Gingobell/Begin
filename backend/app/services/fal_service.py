"""fal_service stub — used by fortune audio endpoints."""
import logging

logger = logging.getLogger(__name__)


class FalService:
    def generate_speech(self, text, voice_id=None, speed=1.0, vol=1.0, pitch=0, language_boost=None):
        logger.warning("fal_service.generate_speech (stub): no Fal.ai configured")
        return None


fal_service = FalService()
