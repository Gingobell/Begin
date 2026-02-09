"""
CopilotKit SDK endpoint at POST /copilotkit (legacy fallback).

user_id flow:
  CopilotKit <properties={{ user_id }}>
    → context["properties"]["user_id"]
      → langgraph_config["configurable"]["user_id"]
"""
from __future__ import annotations

import logging

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

from app.agent.graph import build_agui_graph

logger = logging.getLogger(__name__)


def _build_agents(context):
    """Per-request agent factory — extracts user_id from CopilotKit properties."""
    props = context.get("properties", {})
    user_id = props.get("user_id", "")
    logger.info("CopilotKit agent factory  user_id=%s", user_id)

    return [
        LangGraphAgent(
            name="fortune_diary",
            description="FortuneDiary chat agent",
            graph=build_agui_graph(),
            langgraph_config={"configurable": {"user_id": user_id}},
        )
    ]


sdk = CopilotKitRemoteEndpoint(agents=_build_agents)


def mount_copilotkit(app) -> None:
    """Mount /copilotkit onto the FastAPI app."""
    add_fastapi_endpoint(app, sdk, "/copilotkit")
    logger.info("✅ CopilotKit endpoint mounted at /copilotkit")
