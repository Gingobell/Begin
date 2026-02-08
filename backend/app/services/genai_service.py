"""Re-export core genai_service so ``from ..services.genai_service`` works."""
from app.core.genai_service import genai_service  # noqa: F401

__all__ = ["genai_service"]
