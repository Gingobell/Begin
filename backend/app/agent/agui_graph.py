"""
LangGraph ReAct graph for AG-UI / CopilotKit.

Uses Google GenAI SDK directly (instead of LangChain wrapper) to capture
Gemini's thinking process and expose it via state snapshots.
"""
from __future__ import annotations

import base64
import logging
import uuid
from typing import Annotated, Literal

from google import genai
from google.genai import types as genai_types

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from copilotkit import CopilotKitState

from app.config import (
    GOOGLE_API_KEY,
    DEFAULT_CHAT_MODEL,
    THINKING_ENABLED,
    THINKING_LEVEL,
)
from app.agent.graph import search_diaries, query_bazi_info, query_tarot_info
from app.agent.prompts import build_system_prompt
from app.services.letta_service import letta_service

logger = logging.getLogger(__name__)


# ── State ───────────────────────────────────────────────────────────

class AgentState(CopilotKitState):
    """CopilotKitState + thinking buffer for frontend display."""
    thinking_buffer: str


# ── Tools ───────────────────────────────────────────────────────────

BACKEND_TOOLS = [search_diaries, query_bazi_info, query_tarot_info]

# Map tool name → tool object for invocation by ToolNode
_TOOL_MAP = {t.name: t for t in BACKEND_TOOLS}


# ── Gemini SDK client ──────────────────────────────────────────────

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


# ── LangChain tool → Gemini FunctionDeclaration conversion ─────────

def _build_gemini_tools() -> list[genai_types.Tool]:
    """Convert LangChain @tool definitions to Gemini FunctionDeclarations."""
    declarations = []
    for t in BACKEND_TOOLS:
        schema = t.get_input_schema().model_json_schema()
        # Filter out 'config' (injected by LangGraph, not a user param)
        props = {
            k: _simplify_schema(v)
            for k, v in schema.get("properties", {}).items()
            if k != "config"
        }
        required = [r for r in schema.get("required", []) if r != "config"]

        decl = genai_types.FunctionDeclaration(
            name=t.name,
            description=t.description,
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    k: genai_types.Schema(
                        type=_json_type_to_gemini(v.get("type", "string")),
                        description=v.get("description", v.get("title", "")),
                    )
                    for k, v in props.items()
                },
                required=required if required else None,
            ) if props else None,
        )
        declarations.append(decl)

    return [genai_types.Tool(function_declarations=declarations)]


def _simplify_schema(prop: dict) -> dict:
    """Strip pydantic extras, keep type/description/title/default."""
    return {
        k: v for k, v in prop.items()
        if k in ("type", "description", "title", "default")
    }


def _json_type_to_gemini(json_type: str) -> str:
    """Map JSON Schema type to Gemini Schema type string."""
    mapping = {
        "string": "STRING",
        "integer": "INTEGER",
        "number": "NUMBER",
        "boolean": "BOOLEAN",
        "array": "ARRAY",
        "object": "OBJECT",
    }
    return mapping.get(json_type, "STRING")


# ── Message format conversion ──────────────────────────────────────

def _langchain_to_gemini_contents(
    messages: list[BaseMessage],
) -> tuple[str | None, list[genai_types.Content]]:
    """
    Convert LangChain messages to Gemini Content list.

    Returns (system_instruction, contents).
    SystemMessage is extracted as system_instruction (Gemini API param).
    """
    system_instruction = None
    contents: list[genai_types.Content] = []

    # Pre-build call_id → thought_signature map from all AIMessages
    sig_map: dict[str, str] = {}
    for msg in messages:
        if isinstance(msg, AIMessage):
            sigs = msg.additional_kwargs.get("thought_signatures", {})
            sig_map.update(sigs)

    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_instruction = msg.content
        elif isinstance(msg, HumanMessage):
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=msg.content)],
            ))
        elif isinstance(msg, AIMessage):
            parts = []
            # Retrieve thought_signatures map if present
            sigs = msg.additional_kwargs.get("thought_signatures", {})
            # Text content
            if msg.content:
                text = msg.content if isinstance(msg.content, str) else str(msg.content)
                if text:
                    parts.append(genai_types.Part(text=text))
            # Tool calls — attach thought_signature per call
            for tc in (msg.tool_calls or []):
                call_id = tc.get("id")
                sig_b64 = sigs.get(call_id)
                sig = base64.b64decode(sig_b64) if sig_b64 else None
                part = genai_types.Part(
                    function_call=genai_types.FunctionCall(
                        name=tc["name"],
                        args=tc.get("args", {}),
                        id=call_id,
                    ),
                    thought_signature=sig,
                )
                parts.append(part)
            if parts:
                contents.append(genai_types.Content(role="model", parts=parts))
        elif isinstance(msg, ToolMessage):
            sig_b64 = sig_map.get(msg.tool_call_id)
            sig = base64.b64decode(sig_b64) if sig_b64 else None
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name=msg.name or msg.tool_call_id,
                        response={"result": msg.content},
                        id=msg.tool_call_id,
                    ),
                    thought_signature=sig,
                )],
            ))

    return system_instruction, contents


def _gemini_response_to_ai_message(
    response: genai_types.GenerateContentResponse,
) -> tuple[AIMessage, str]:
    """
    Convert Gemini response to LangChain AIMessage + thinking text.

    Returns (ai_message, thinking_text).
    """
    text_parts: list[str] = []
    thinking_parts: list[str] = []
    tool_calls: list[dict] = []
    thought_sigs: dict[str, str] = {}  # call_id → thought_signature

    for candidate in response.candidates or []:
        for part in candidate.content.parts or []:
            # Thinking part
            if part.thought and part.text:
                thinking_parts.append(part.text)
            # Function call — preserve thought_signature for Gemini 3
            elif part.function_call:
                fc = part.function_call
                call_id = fc.id or f"call_{uuid.uuid4().hex[:8]}"
                tool_calls.append({
                    "name": fc.name,
                    "args": dict(fc.args) if fc.args else {},
                    "id": call_id,
                    "type": "tool_call",
                })
                if getattr(part, "thought_signature", None):
                    thought_sigs[call_id] = base64.b64encode(part.thought_signature).decode("ascii")
            # Regular text
            elif part.text:
                text_parts.append(part.text)

    content = "".join(text_parts)
    thinking = "\n\n".join(thinking_parts)

    additional_kwargs = {}
    if thought_sigs:
        additional_kwargs["thought_signatures"] = thought_sigs

    ai_msg = AIMessage(
        content=content,
        tool_calls=tool_calls if tool_calls else [],
        additional_kwargs=additional_kwargs,
    )

    return ai_msg, thinking


# ── Nodes ───────────────────────────────────────────────────────────

async def agent_node(state: AgentState, config: RunnableConfig):
    user_id: str = config.get("configurable", {}).get("user_id", "")

    user_profile = ""
    if user_id:
        try:
            user_profile = await letta_service.get_user_profile(user_id)
        except Exception as exc:
            logger.warning("Profile fetch failed for %s: %s", user_id, exc)

    system_prompt = build_system_prompt(user_profile=user_profile, today_fortune=None)

    # Convert LangChain messages to Gemini format
    all_messages = [SystemMessage(content=system_prompt), *state["messages"]]
    sys_instruction, contents = _langchain_to_gemini_contents(all_messages)

    # Build config
    gen_config = genai_types.GenerateContentConfig(
        temperature=0.7,
        tools=_build_gemini_tools(),
        system_instruction=sys_instruction,
    )

    # Enable thinking if configured
    if THINKING_ENABLED:
        gen_config.thinking_config = genai_types.ThinkingConfig(
            include_thoughts=True,
            thinking_level=THINKING_LEVEL,
        )

    # Call Gemini directly
    client = _get_client()
    response = await client.aio.models.generate_content(
        model=DEFAULT_CHAT_MODEL,
        contents=contents,
        config=gen_config,
    )

    ai_message, thinking_text = _gemini_response_to_ai_message(response)

    # Build return state update
    result: dict = {"messages": [ai_message]}

    # Accumulate thinking (append to previous buffer with separator)
    if thinking_text:
        prev = state.get("thinking_buffer", "") or ""
        separator = "\n\n---\n\n" if prev else ""
        result["thinking_buffer"] = prev + separator + thinking_text
    else:
        # Preserve existing buffer
        result["thinking_buffer"] = state.get("thinking_buffer", "") or ""

    return result


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


# ── Graph factory ───────────────────────────────────────────────────

_compiled = None


def build_agui_graph():
    global _compiled
    if _compiled is not None:
        return _compiled

    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set")

    wf = StateGraph(AgentState)
    wf.add_node("agent", agent_node)
    wf.add_node("tools", ToolNode(BACKEND_TOOLS))
    wf.set_entry_point("agent")
    wf.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    wf.add_edge("tools", "agent")

    _compiled = wf.compile(checkpointer=InMemorySaver())
    logger.info("AG-UI graph compiled (model=%s, tools=%s, thinking=%s)",
                DEFAULT_CHAT_MODEL, [t.name for t in BACKEND_TOOLS], THINKING_ENABLED)
    return _compiled
