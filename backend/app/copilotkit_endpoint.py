"""
CopilotKit SDK endpoint for FortuneDiary.

Wraps the existing LangGraph react agent for CopilotKit frontend consumption.
Maps CopilotKit properties.user_id → LangGraph config["configurable"]["user_id"]
so the search_diaries tool can filter by user.
"""
from __future__ import annotations

import logging

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

from app.agent.agui_graph import build_agui_graph

logger = logging.getLogger(__name__)

# Build graph once at module level
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_agui_graph()
    return _graph


def _build_agents(context):
    """
    Dynamic agent factory — extracts user_id from CopilotKit properties
    and injects it into LangGraph config so the search_diaries tool
    can access it via RunnableConfig["configurable"]["user_id"].
    """
    props = context.get("properties", {})
    user_id = props.get("user_id", "")

    logger.info(f"CopilotKit agent factory: user_id={user_id}")

    return [
        LangGraphAgent(
            name="fortune_diary",
            description="FortuneDiary chat agent — diary search, fortune insights, daily companion",
            graph=_get_graph(),
            langgraph_config={
                "configurable": {
                    "user_id": user_id,
                }
            },
        )
    ]


sdk = CopilotKitRemoteEndpoint(agents=_build_agents)


def mount_copilotkit(app):
    """Call from main.py to mount /copilotkit endpoint onto the FastAPI app."""
    add_fastapi_endpoint(app, sdk, "/copilotkit")
    logger.info("✅ CopilotKit endpoint mounted at /copilotkit")
