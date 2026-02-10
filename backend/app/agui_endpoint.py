"""
AG-UI protocol endpoint at POST /agent.

Custom endpoint (instead of add_langgraph_fastapi_endpoint) so we can
extract user_id from forwarded_props and inject it into RunnableConfig.
"""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import StreamingResponse

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from copilotkit import LangGraphAGUIAgent

from app.agent.graph import build_agui_graph

logger = logging.getLogger(__name__)


def mount_agui_endpoint(app) -> None:
    """Mount AG-UI streaming endpoint at POST /agent."""
    graph = build_agui_graph()
    agent = LangGraphAGUIAgent(
        name="fortune_diary",
        description="FortuneDiary chat agent — diary search, fortune insights, daily companion",
        graph=graph,
    )

    @app.post("/agent")
    async def agent_endpoint(input_data: RunAgentInput, request: Request):
        props = input_data.forwarded_props or {}
        user_id = props.get("user_id", "")
        chat_type = props.get("chat_type", "fortune")
        language = props.get("language", "zh-CN")
        agent.config = {"configurable": {"user_id": user_id, "chat_type": chat_type, "language": language}}

        encoder = EventEncoder(accept=request.headers.get("accept"))

        async def event_generator():
            async for event in agent.run(input_data):
                yield encoder.encode(event)

        return StreamingResponse(event_generator(), media_type=encoder.get_content_type())

    logger.info("AG-UI endpoint mounted at /agent")
