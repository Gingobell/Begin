"""
memory_service stub — returns empty data.

The real implementation would pull user memory from Letta or another
store.  For now the fortune pipeline works without it (just less
personalised).
"""
import logging

logger = logging.getLogger(__name__)


async def get_memory(user_id) -> dict:
    logger.debug("memory_service.get_memory (stub): user_id=%s", user_id)
    return {}


def extract_recent_context(user_memory: dict) -> dict:
    return {
        "recent_concerns": [],
        "future_events": [],
        "personality": "",
        "goals": [],
    }


async def get_contextual_memory(user_id: str, query: str) -> dict:
    return {"has_relevant_context": False, "relevant_diary_events": []}
