"""
LangGraph ReAct graph for AG-UI / CopilotKit.
"""
from __future__ import annotations

import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode

from copilotkit import CopilotKitState

from app.config import GOOGLE_API_KEY, DEFAULT_CHAT_MODEL
from app.agent.graph import search_diaries, query_bazi_info, query_tarot_info
from app.agent.prompts import build_system_prompt
from app.services.letta_service import letta_service

logger = logging.getLogger(__name__)


# ── State ───────────────────────────────────────────────────────────

class AgentState(CopilotKitState):
    """CopilotKitState carries frontend actions + messages."""
    pass


# ── Tools & model ───────────────────────────────────────────────────

BACKEND_TOOLS = [search_diaries, query_bazi_info, query_tarot_info]

_model: ChatGoogleGenerativeAI | None = None


def _get_model() -> ChatGoogleGenerativeAI:
    global _model
    if _model is None:
        _model = ChatGoogleGenerativeAI(
            model=DEFAULT_CHAT_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=0.7,
            streaming=True,
        )
    return _model


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
    model_with_tools = _get_model().bind_tools(BACKEND_TOOLS)

    response = await model_with_tools.ainvoke(
        [SystemMessage(content=system_prompt), *state["messages"]],
        config,
    )
    return {"messages": [response]}


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
    logger.info("🎉 AG-UI graph compiled (model=%s, tools=%s)",
                DEFAULT_CHAT_MODEL, [t.name for t in BACKEND_TOOLS])
    return _compiled
