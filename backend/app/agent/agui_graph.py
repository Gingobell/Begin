"""
AG-UI compatible LangGraph graph factory.

Builds a create_react_agent graph WITHOUT a checkpointer,
since the AG-UI protocol (and CopilotKit frontend) manages
conversation history by sending the full message list each request.

The search_diaries tool is reused from graph.py — it reads user_id
from RunnableConfig["configurable"]["user_id"], which the AG-UI
endpoint injects from the frontend's forwardedProps.
"""
from __future__ import annotations

import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from app.config import GOOGLE_API_KEY, DEFAULT_CHAT_MODEL
from app.agent.graph import search_diaries
from app.agent.prompts import build_system_prompt

logger = logging.getLogger(__name__)


def build_agui_graph():
    """
    Build a compiled ReAct agent graph for AG-UI streaming.

    Key differences from the checkpointed graph in graph.py:
    - No checkpointer (AG-UI/CopilotKit owns message history)
    - System prompt baked into the graph via `prompt` parameter
    - Same tools, same model
    """
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set — cannot build AG-UI graph")

    model = ChatGoogleGenerativeAI(
        model=DEFAULT_CHAT_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.7,
        streaming=True,
    )

    # Build a base system prompt (without per-user fortune/profile for now).
    # The AG-UI endpoint can inject dynamic context via prepended system
    # messages in the input when user_profile / fortune data is available.
    base_system_prompt = build_system_prompt(
        user_profile="",
        today_fortune=None,
    )

    graph = create_react_agent(
        model=model,
        tools=[search_diaries],
        prompt=base_system_prompt,
    )

    logger.info(
        f"🎉 AG-UI graph compiled (model={DEFAULT_CHAT_MODEL}, "
        f"tools=[search_diaries])"
    )
    return graph
