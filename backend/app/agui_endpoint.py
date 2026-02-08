"""
Custom AG-UI protocol endpoint for FortuneDiary.

Implements the AG-UI SSE streaming protocol manually so we can:
1. Map forwardedProps.user_id → LangGraph config["configurable"]["user_id"]
2. Inject dynamic system prompts (fortune + profile) per-request
3. Translate LangGraph astream_events → AG-UI protocol events

Compatible with CopilotKit's LangGraphHttpAgent on the frontend.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ag_ui.core import (
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
)
from ag_ui.encoder import EventEncoder

from app.agent.agui_graph import build_agui_graph

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Pydantic models for AG-UI input ────────────────────────────────

class AGUIMessage(BaseModel):
    id: str = ""
    role: str = "user"
    content: str | None = ""
    tool_calls: list[Any] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class AGUITool(BaseModel):
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class RunAgentInput(BaseModel):
    thread_id: str = Field(alias="threadId", default="")
    run_id: str = Field(alias="runId", default="")
    messages: list[AGUIMessage] = Field(default_factory=list)
    tools: list[AGUITool] = Field(default_factory=list)
    context: list[Any] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    forwarded_props: dict[str, Any] = Field(alias="forwardedProps", default_factory=dict)

    model_config = {"populate_by_name": True}


# ── Graph singleton ─────────────────────────────────────────────────

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_agui_graph()
    return _graph


# ── AG-UI event helpers ─────────────────────────────────────────────

def _msg_to_langchain(msg: AGUIMessage) -> dict:
    """Convert an AG-UI message to a LangChain message dict."""
    base = {"role": msg.role, "content": msg.content or ""}
    if msg.role == "tool" and msg.tool_call_id:
        base["tool_call_id"] = msg.tool_call_id
    if msg.name:
        base["name"] = msg.name
    return base


# ── Endpoint ────────────────────────────────────────────────────────

@router.post("/agent")
async def agui_agent_endpoint(request: Request):
    """
    AG-UI compatible endpoint.

    Receives RunAgentInput, runs the LangGraph react agent, and
    streams AG-UI protocol events back as SSE.
    """
    body = await request.json()
    input_data = RunAgentInput(**body)

    accept_header = request.headers.get("accept", "text/event-stream")
    encoder = EventEncoder(accept=accept_header)

    # Extract user_id from forwardedProps (sent by CopilotKit's `properties`)
    user_id = (
        input_data.forwarded_props.get("user_id", "")
        or input_data.state.get("user_id", "")
    )
    thread_id = input_data.thread_id or str(uuid.uuid4())

    logger.info(
        f"AG-UI request: thread={thread_id}, user={user_id}, "
        f"messages={len(input_data.messages)}"
    )

    async def event_stream():
        try:
            graph = get_graph()

            # 1. RUN_STARTED
            yield encoder.encode(
                RunStartedEvent(
                    type=EventType.RUN_STARTED,
                    thread_id=thread_id,
                    run_id=input_data.run_id or str(uuid.uuid4()),
                )
            )

            # 2. Convert AG-UI messages → LangChain format
            messages = [_msg_to_langchain(m) for m in input_data.messages]

            # 3. Build LangGraph config with user_id
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "user_id": user_id,
                }
            }

            # 4. Stream LangGraph events → AG-UI events
            current_message_id: str | None = None
            current_tool_call_ids: set[str] = set()

            async for event in graph.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                data = event.get("data", {})
                tags = event.get("tags", [])

                # ── LLM text tokens ──────────────────────────────
                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk is None:
                        continue

                    # Check for tool_call_chunks first
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        for tc_chunk in chunk.tool_call_chunks:
                            tc_id = tc_chunk.get("id") or tc_chunk.get("index", "")
                            tc_name = tc_chunk.get("name", "")
                            tc_args = tc_chunk.get("args", "")

                            if tc_id and tc_id not in current_tool_call_ids:
                                # New tool call starting
                                current_tool_call_ids.add(tc_id)
                                yield encoder.encode(
                                    ToolCallStartEvent(
                                        type=EventType.TOOL_CALL_START,
                                        tool_call_id=str(tc_id),
                                        tool_call_name=tc_name or "",
                                        parent_message_id=current_message_id,
                                    )
                                )

                            if tc_args:
                                yield encoder.encode(
                                    ToolCallArgsEvent(
                                        type=EventType.TOOL_CALL_ARGS,
                                        tool_call_id=str(tc_id or ""),
                                        delta=tc_args if isinstance(tc_args, str) else json.dumps(tc_args),
                                    )
                                )
                        continue

                    # Regular text content
                    content = ""
                    if hasattr(chunk, "content"):
                        if isinstance(chunk.content, str):
                            content = chunk.content
                        elif isinstance(chunk.content, list):
                            content = "".join(
                                item.get("text", "") if isinstance(item, dict) else str(item)
                                for item in chunk.content
                            )

                    if content:
                        if current_message_id is None:
                            current_message_id = str(uuid.uuid4())
                            yield encoder.encode(
                                TextMessageStartEvent(
                                    type=EventType.TEXT_MESSAGE_START,
                                    message_id=current_message_id,
                                    role="assistant",
                                )
                            )

                        yield encoder.encode(
                            TextMessageContentEvent(
                                type=EventType.TEXT_MESSAGE_CONTENT,
                                message_id=current_message_id,
                                delta=content,
                            )
                        )

                # ── LLM stream end ───────────────────────────────
                elif kind == "on_chat_model_end":
                    # Close any open tool calls
                    for tc_id in list(current_tool_call_ids):
                        yield encoder.encode(
                            ToolCallEndEvent(
                                type=EventType.TOOL_CALL_END,
                                tool_call_id=str(tc_id),
                            )
                        )
                    current_tool_call_ids.clear()

                    # Close any open text message
                    if current_message_id is not None:
                        yield encoder.encode(
                            TextMessageEndEvent(
                                type=EventType.TEXT_MESSAGE_END,
                                message_id=current_message_id,
                            )
                        )
                        current_message_id = None

                # ── Tool execution ───────────────────────────────
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown_tool")
                    tool_input = data.get("input", {})
                    logger.info(f"Tool executing: {tool_name}({tool_input})")

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown_tool")
                    tool_output = data.get("output", "")
                    logger.info(f"Tool finished: {tool_name} → {str(tool_output)[:200]}")

            # 5. RUN_FINISHED
            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=thread_id,
                    run_id=input_data.run_id or str(uuid.uuid4()),
                )
            )

        except Exception as e:
            logger.error(f"AG-UI stream error: {e}", exc_info=True)
            # Emit error as a text message so the frontend shows it
            err_id = str(uuid.uuid4())
            yield encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=err_id,
                    role="assistant",
                )
            )
            yield encoder.encode(
                TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=err_id,
                    delta="抱歉，出了点问题，请稍后再试。",
                )
            )
            yield encoder.encode(
                TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=err_id,
                )
            )
            yield encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=thread_id,
                    run_id=input_data.run_id or str(uuid.uuid4()),
                )
            )

    return StreamingResponse(
        event_stream(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
