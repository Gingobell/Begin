"""
enhanced_genai_service — thin wrapper around core genai_service.

Provides the ``generate_*_with_knowledge`` methods that diary.py and
fortune.py expect.  Under the hood it just calls ``genai_service.generate_text``.
"""
import logging
from app.core.genai_service import genai_service as _core

logger = logging.getLogger(__name__)


class EnhancedGenAIService:
    """Drop-in for the old enhanced service; delegates to core genai."""

    async def generate_diary_feedback_with_knowledge(
        self, base_prompt: str, diary_content: str
    ) -> str:
        prompt = f"{base_prompt}\n\n日记内容：{diary_content}" if diary_content else base_prompt
        return await _core.generate_text(prompt)

    async def generate_fortune_with_knowledge(
        self, base_prompt: str, fortune_context: str
    ) -> str:
        prompt = f"{base_prompt}\n\n运势上下文：{fortune_context}" if fortune_context else base_prompt
        return await _core.generate_text(prompt)

    async def generate_chat_response_with_knowledge(
        self, base_prompt: str, conversation_context: str
    ) -> str:
        prompt = f"{base_prompt}\n\n对话上下文：{conversation_context}" if conversation_context else base_prompt
        return await _core.generate_text(prompt)

    # Alias so callers that use genai_service-style .generate_text still work
    async def generate_text(self, prompt: str) -> str:
        return await _core.generate_text(prompt)

    async def generate_embedding(self, text: str, **kw):
        return await _core.generate_embedding(text, **kw)


enhanced_genai_service = EnhancedGenAIService()
