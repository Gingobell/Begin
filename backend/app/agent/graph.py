"""
LangGraph Reactive Agent for FortuneDiary chat.

Uses `create_react_agent` (prebuilt ReAct loop) with:
- Google Gemini as LLM
- AsyncPostgresSaver for conversation memory
- Diary RAG search as first tool
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from psycopg_pool import AsyncConnectionPool

from app.config import SUPABASE_DB_URI, GOOGLE_API_KEY, DEFAULT_CHAT_MODEL
from app.agent.prompts import build_system_prompt
from app.services.vector_service import vector_service
from app.services.bazi_service import bazi_service
from app.services.tarot_service import tarot_service
from app.core.db import supabase

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tools (defined here so they can read RunnableConfig for user_id)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@tool
async def search_diaries(query: str, config: RunnableConfig, max_results: int = 5) -> str:
    """搜索用户过去的日记内容。当用户提到过去写的东西、想回顾某段经历、或者问「我之前有没有写过关于...」时使用这个工具。"""
    user_id = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        return "无法搜索日记：缺少用户信息。"

    try:
        results = await vector_service.search_similar_diaries(
            user_id=user_id,
            query=query,
            max_results=max_results,
        )
        if not results:
            return f"没有找到与「{query}」相关的日记记录。"

        parts = []
        for i, r in enumerate(results, 1):
            preview = r.get("content_preview", "").strip()
            created = r.get("created_at", "未知日期")
            sim = r.get("similarity", 0)
            parts.append(f"[{i}] 日期: {created} (相关度: {sim:.2f})\n{preview}")
        return "\n\n---\n\n".join(parts)

    except Exception as e:
        logger.error(f"Diary search tool error: {e}", exc_info=True)
        return "日记搜索出错了，请稍后再试。"


def _get_user_birth_date(user_id: str):
    """从 profiles 表获取用户生日"""
    from datetime import datetime as dt
    resp = supabase.table("profiles").select("birth_datetime").eq("id", user_id).single().execute()
    if resp.data and resp.data.get("birth_datetime"):
        return dt.fromisoformat(resp.data["birth_datetime"]).date()
    return None


@tool
def query_bazi_info(config: RunnableConfig) -> str:
    """查询用户的八字命盘信息。当用户问到自己的八字、日主、五行、体质强弱、今日流日运势等命理相关问题时使用。"""
    from datetime import date
    user_id = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        return "无法查询八字：缺少用户信息。"
    try:
        birth_date = _get_user_birth_date(user_id)
        if not birth_date:
            return "你还没有设置生日，请先在设置中填写出生日期。"
        bazi = bazi_service.calculate_bazi(birth_date)
        flow = bazi_service.analyze_daily_flow(birth_date, target_date=date.today())
        return (
            f"日主: {bazi['day_master']} | 体质: {bazi['body_strength']}\n"
            f"四柱: {bazi['year_pillar']} {bazi['month_pillar']} {bazi['day_pillar']} {bazi['hour_pillar']}\n"
            f"今日流日: {flow['daily_pillar']['stem']}{flow['daily_pillar']['branch']}\n"
            f"天干影响: {flow['stem_influence']['relation']} — {flow['stem_influence']['analysis']}\n"
            f"地支影响: {flow['branch_influence']['relation']} — {flow['branch_influence']['analysis']}\n"
            f"十二长生: {flow['energy_phase']} | 贵人分: {flow['nobleman_score']}"
        )
    except Exception as e:
        logger.error(f"BaZi tool error: {e}", exc_info=True)
        return "八字查询出错了，请稍后再试。"


@tool
def query_tarot_info(config: RunnableConfig) -> str:
    """查询用户今日塔罗牌信息。当用户问到今天的塔罗牌、牌面含义、抽到了什么牌等塔罗相关问题时使用。"""
    from datetime import date
    user_id = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        return "无法查询塔罗：缺少用户信息。"
    try:
        today = date.today()
        reading = tarot_service.draw_daily_card(user_id, today)
        if "error" in reading:
            return f"塔罗查询失败：{reading['error']}"
        card = reading.get("card", {})
        orientation = reading.get("orientation", "upright")
        ori_label = "正位" if orientation == "upright" else "逆位"
        meaning = card.get("meaning_up") if orientation == "upright" else card.get("meaning_down")
        return (
            f"今日塔罗: {card.get('card_name', '未知')} ({ori_label})\n"
            f"牌义: {meaning}\n"
            f"描述: {card.get('description', '')}"
        )
    except Exception as e:
        logger.error(f"Tarot tool error: {e}", exc_info=True)
        return "塔罗查询出错了，请稍后再试。"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent service
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ChatAgentService:
    """
    Manages the LangGraph reactive agent lifecycle.

    - One shared connection pool + checkpointer
    - One compiled graph (stateless — state lives in the checkpointer)
    - Per-request: pass thread_id + user_id through config
    """

    def __init__(self):
        self.pool: Optional[AsyncConnectionPool] = None
        self.graph = None
        self._initialized = False

    # ── lifecycle ────────────────────────────────────────────────────

    async def initialize(self):
        """Call once at app startup."""
        if self._initialized:
            return

        if not SUPABASE_DB_URI:
            logger.warning("⚠️  SUPABASE_DB_URI not set — agent disabled")
            return
        if not GOOGLE_API_KEY:
            logger.warning("⚠️  GOOGLE_API_KEY not set — agent disabled")
            return

        try:
            # 1. Postgres connection pool
            self.pool = AsyncConnectionPool(
                conninfo=SUPABASE_DB_URI,
                max_size=20,
                min_size=2,
                open=False,
                kwargs={"prepare_threshold": None},
            )
            await self.pool.open()
            logger.info("✅ DB pool opened")

            # 2. Run checkpointer migrations once
            async with self.pool.connection() as conn:
                await conn.set_autocommit(True)
                checkpointer = AsyncPostgresSaver(conn)
                await checkpointer.setup()
            logger.info("✅ Checkpointer tables ready")

            # 3. Build the graph (once — it's reusable)
            model = ChatGoogleGenerativeAI(
                model=DEFAULT_CHAT_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=0.7,
            )

            # We create the checkpointer from the pool for the compiled graph.
            # create_react_agent compiles a graph with the ReAct loop baked in.
            graph_checkpointer = AsyncPostgresSaver(self.pool)
            self.graph = create_react_agent(
                model=model,
                tools=[search_diaries, query_bazi_info, query_tarot_info],
                checkpointer=graph_checkpointer,
            )

            self._initialized = True
            logger.info(f"🎉 Chat agent ready  (model={DEFAULT_CHAT_MODEL})")

        except Exception as e:
            logger.error(f"❌ Agent init failed: {e}", exc_info=True)
            if self.pool:
                try:
                    await self.pool.close()
                except Exception:
                    pass
                self.pool = None
            self._initialized = False

    async def shutdown(self):
        if self.pool:
            await self.pool.close()
            logger.info("Agent pool closed")

    # ── public API ──────────────────────────────────────────────────

    async def chat(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        user_profile: str = "",
        today_fortune: dict | None = None,
    ) -> str:
        """
        Send a message and get a full response.

        The system prompt (with fortune + profile context) is prepended
        as the first message only when starting a new conversation.
        LangGraph's checkpointer handles history automatically.
        """
        if not self._initialized or not self.graph:
            raise RuntimeError("Agent not initialized")

        config = {
            "configurable": {
                "thread_id": conversation_id,
                "user_id": user_id,
            }
        }

        # Build input messages
        messages = []

        # Check if this is a fresh conversation (no checkpoint yet)
        state = await self.graph.aget_state(config)
        if not state or not state.values.get("messages"):
            # First turn — inject system prompt
            system_prompt = build_system_prompt(
                user_profile=user_profile,
                today_fortune=today_fortune,
            )
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        result = await self.graph.ainvoke({"messages": messages}, config)

        # Extract the last AI message
        if result and "messages" in result and result["messages"]:
            last = result["messages"][-1]
            if hasattr(last, "content"):
                content = last.content
                if isinstance(content, list):
                    return "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )
                return content
        return "抱歉，我现在无法回复。"

    async def chat_stream(
        self,
        conversation_id: str,
        user_id: str,
        message: str,
        user_profile: str = "",
        today_fortune: dict | None = None,
    ):
        """
        Streaming version — yields token chunks as they arrive.
        """
        if not self._initialized or not self.graph:
            raise RuntimeError("Agent not initialized")

        config = {
            "configurable": {
                "thread_id": conversation_id,
                "user_id": user_id,
            }
        }

        messages = []
        state = await self.graph.aget_state(config)
        if not state or not state.values.get("messages"):
            system_prompt = build_system_prompt(
                user_profile=user_profile,
                today_fortune=today_fortune,
            )
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        async for chunk, metadata in self.graph.astream(
            {"messages": messages},
            config,
            stream_mode="messages",
        ):
            if hasattr(chunk, "content") and chunk.content:
                content = chunk.content
                if isinstance(content, list):
                    yield "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )
                else:
                    yield content


# ── Singleton ───────────────────────────────────────────────────────

chat_agent = ChatAgentService()
