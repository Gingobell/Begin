"""
AG-UI protocol endpoint at POST /agent.

Uses ag-ui-langgraph + LangGraphAGUIAgent for full AG-UI compliance.
"""
from __future__ import annotations

import logging

from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from app.agent.agui_graph import build_agui_graph

logger = logging.getLogger(__name__)


def mount_agui_endpoint(app) -> None:
    """Mount AG-UI streaming endpoint at POST /agent."""
    graph = build_agui_graph()

    add_langgraph_fastapi_endpoint(
        app=app,
        agent=LangGraphAGUIAgent(
            name="fortune_diary",
            description="FortuneDiary chat agent — diary search, fortune insights, daily companion",
            graph=graph,
        ),
        path="/agent",
    )
    logger.info("✅ AG-UI endpoint mounted at /agent")
