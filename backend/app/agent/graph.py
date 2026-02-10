"""
LangGraph Reactive Agent for FortuneDiary chat.

Uses `create_react_agent` (prebuilt ReAct loop) with:
- Google Gemini as LLM
- AsyncPostgresSaver for conversation memory
- Diary RAG search as first tool
"""
from __future__ import annotations

import logging
from typing import Optional, Annotated

from typing import Literal

from langchain_core.tools import tool
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent, ToolNode, InjectedState
from psycopg_pool import AsyncConnectionPool

from copilotkit import CopilotKitState
from copilotkit.langgraph import copilotkit_emit_state

from app.config import (
    SUPABASE_DB_URI, GOOGLE_API_KEY, DEFAULT_CHAT_MODEL,
    THINKING_ENABLED, THINKING_LEVEL,
)
from app.agent.prompts import build_system_prompt, build_diary_system_prompt, load_fortune_context
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
    if not query or not query.strip():
        return "请提供搜索关键词。"

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


@tool
async def search_fortune_knowledge(query: str, config: RunnableConfig) -> str:
    """搜索专业命理知识库。当用户问到八字理论、五行相生相克、十神含义、格局解读、塔罗牌深层含义等命理专业知识时使用。不同于查询用户个人八字，这个工具用来检索通用的命理学参考资料。"""
    user_id = config.get("configurable", {}).get("user_id", "")
    if not query or not query.strip():
        return "请提供要查询的命理知识关键词。"

    try:
        from app.services.knowledge_service import KnowledgeService
        knowledge_svc = KnowledgeService()

        result = await knowledge_svc.get_relevant_knowledge(
            query=query,
            context=f"user_id={user_id}" if user_id else "",
        )

        items = result.get("knowledge", [])
        if not items:
            return f"没有找到与「{query}」相关的命理知识。"

        parts = []
        for i, item in enumerate(items[:5], 1):
            content = item.get("content", "").strip()[:300]
            source = item.get("source", "知识库")
            sim = item.get("similarity", 0)
            parts.append(f"[{i}] ({source}, 相关度: {sim:.2f})\n{content}")

        meta = result.get("metadata", {})
        summary = meta.get("source_summary", "")
        header = f"找到 {len(items)} 条相关知识" + (f" | {summary}" if summary else "")
        return header + "\n\n" + "\n\n---\n\n".join(parts)

    except Exception as e:
        logger.error(f"Knowledge search tool error: {e}", exc_info=True)
        return "命理知识搜索出错了，请稍后再试。"


def _get_user_birth_date(user_id: str):
    """从 profiles 表获取用户生日。"""
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


@tool
async def generate_diary(config: RunnableConfig, state: Annotated[dict, InjectedState]) -> str:
    """根据当前对话内容生成一篇日记。当用户说「帮我生成日记」「写日记」「记录一下今天」或点击生成日记按钮时使用这个工具。不需要任何参数，会自动从对话历史中提取内容。"""
    from app.core.genai_service import genai_service
    from app.services.letta_service import letta_service
    from datetime import date, datetime, timezone
    import asyncio
    import json

    user_id = config.get("configurable", {}).get("user_id", "")
    if not user_id:
        return "无法生成日记：缺少用户信息。"

    # 1. Extract conversation history from graph state
    messages = state.get("messages", [])
    if not messages:
        return "无法生成日记：没有找到对话内容。请先和我聊聊今天发生了什么。"

    # Build conversation text from human messages
    conversation_parts = []
    for msg in messages:
        if hasattr(msg, "content") and isinstance(msg.content, str):
            if hasattr(msg, "type"):
                if msg.type == "human":
                    conversation_parts.append(f"用户: {msg.content}")
                elif msg.type == "ai" and msg.content and not getattr(msg, "tool_calls", None):
                    conversation_parts.append(f"助手: {msg.content}")

    conversation_text = "\n".join(conversation_parts[-20:])  # Last 20 messages max

    if not conversation_text.strip():
        return "无法生成日记：对话内容为空。请先和我聊聊今天发生了什么。"

    # 2. Summarize conversation into diary content
    summary_prompt = f"""请根据以下对话内容，生成一篇简短的日记（150-300字）。
要求：
- 用第一人称书写
- 提取对话中的关键事件、情绪和感悟
- 语调自然、真实，像是自己写给自己的记录
- 不要提及"助手"或"AI"的存在

【对话内容】
{conversation_text}

请直接输出日记内容，不要加标题或额外说明。"""

    try:
        diary_content = await genai_service.generate_text(summary_prompt)
    except Exception as e:
        logger.error(f"Diary content generation failed: {e}", exc_info=True)
        return "日记内容生成失败，请稍后再试。"

    # 3. Get today's fortune for instant feedback
    today = date.today()
    battery_fortune = None
    try:
        resp = supabase.table("daily_fortune_details").select("battery_fortune").eq("user_id", user_id).eq("fortune_date", today.isoformat()).single().execute()
        if resp.data:
            battery_fortune = resp.data.get("battery_fortune")
    except Exception:
        pass

    # 4. Generate instant feedback
    if battery_fortune:
        overall = battery_fortune.get("overall", {})
        feedback_prompt = f"""作为一位充满智慧和同理心的朋友，请阅读以下内容并给出温暖反馈。

【朋友今天的日记】
{diary_content}

【今日运势参考】
今日整体: {overall.get('daily_management', '')}
顺手的事: {overall.get('today_actions', '')}

请结合日记内容和运势信息，给出50-100字的温暖、鼓励的反馈。"""
    else:
        feedback_prompt = f"""作为一位充满智慧和同理心的朋友，请阅读以下日记并给出温暖反馈。

【朋友今天的日记】
{diary_content}

请给出50-100字的温暖、鼓励的反馈。语调亲切自然。"""

    try:
        instant_feedback = await genai_service.generate_text(feedback_prompt)
    except Exception:
        instant_feedback = ""

    # 5. Generate embedding
    try:
        embedding = await genai_service.generate_embedding(diary_content)
    except Exception:
        embedding = None

    # 6. Save to database
    diary_data = {
        "user_id": user_id,
        "content": diary_content,
        "emotion_tags": [],
        "instant_feedback": instant_feedback,
        "embedding": embedding,
    }

    try:
        response = supabase.table("diary_entries").insert(diary_data).execute()
        if not response.data:
            return "日记保存失败，请稍后再试。"
        created_entry = response.data[0]
        logger.info(f"Diary generated via agent tool - ID: {created_entry['id']}, User: {user_id}")
    except Exception as e:
        logger.error(f"Diary save failed: {e}", exc_info=True)
        return "日记保存到数据库失败，请稍后再试。"

    # 7. Ingest to Letta (background)
    try:
        diary_date = created_entry["created_at"][:10] if created_entry.get("created_at") else None

        async def _ingest():
            try:
                await letta_service.ingest_diary(user_id=user_id, diary_text=diary_content, diary_date=diary_date)
            except Exception:
                pass

        asyncio.create_task(_ingest())
    except Exception:
        pass

    # 8. Return result as structured JSON for frontend rendering
    result = {
        "diary_id": str(created_entry["id"]),
        "content": diary_content,
        "insight": instant_feedback,
        "created_at": created_entry.get("created_at", ""),
    }
    return json.dumps(result, ensure_ascii=False)


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
                tools=[search_diaries, search_fortune_knowledge, query_bazi_info, query_tarot_info, generate_diary],
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
        language: str = "zh-CN",
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
            # First turn — inject system prompt with full fortune context
            fortune_ctx = await load_fortune_context(user_id)
            system_prompt = build_system_prompt(
                user_profile=user_profile,
                today_fortune=fortune_ctx["today_fortune"] or today_fortune,
                daily_bazi=fortune_ctx["daily_bazi"],
                daily_tarot=fortune_ctx["daily_tarot"],
                recent_recharges_block=fortune_ctx["recent_recharges_block"],
                yesterday_diary_block=fortune_ctx["yesterday_diary_block"],
                language=language,
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
        language: str = "zh-CN",
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
            fortune_ctx = await load_fortune_context(user_id)
            system_prompt = build_system_prompt(
                user_profile=user_profile,
                today_fortune=fortune_ctx["today_fortune"] or today_fortune,
                daily_bazi=fortune_ctx["daily_bazi"],
                daily_tarot=fortune_ctx["daily_tarot"],
                recent_recharges_block=fortune_ctx["recent_recharges_block"],
                yesterday_diary_block=fortune_ctx["yesterday_diary_block"],
                language=language,
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AG-UI / CopilotKit graph (with thinking_buffer for frontend)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Tool sets per chat type
FORTUNE_TOOLS = [search_diaries, search_fortune_knowledge, query_bazi_info, query_tarot_info]
DIARY_TOOLS = [search_diaries, generate_diary]
ALL_TOOLS = [search_diaries, search_fortune_knowledge, query_bazi_info, query_tarot_info, generate_diary]


class AgentState(CopilotKitState):
    """CopilotKitState + thinking buffer for frontend display."""
    thinking_buffer: str


def _extract_thinking(content) -> str:
    """Extract thinking blocks from AIMessage.content (list format when include_thoughts=True)."""
    if not isinstance(content, list):
        return ""
    return "\n\n".join(
        block.get("thinking", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "thinking" and block.get("thinking")
    )


def _build_llm() -> ChatGoogleGenerativeAI:
    kwargs = dict(
        model=DEFAULT_CHAT_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=1.0,
    )
    if THINKING_ENABLED:
        kwargs["thinking_level"] = THINKING_LEVEL.lower()
        kwargs["include_thoughts"] = True
    return ChatGoogleGenerativeAI(**kwargs)


async def _agent_node(state: AgentState, config: RunnableConfig):
    from app.services.letta_service import letta_service

    user_id: str = config.get("configurable", {}).get("user_id", "")
    chat_type: str = config.get("configurable", {}).get("chat_type", "fortune")
    language: str = config.get("configurable", {}).get("language", "zh-CN")

    user_profile = ""
    if user_id:
        try:
            user_profile = await letta_service.get_user_profile(user_id)
        except Exception as exc:
            logger.warning("Profile fetch failed for %s: %s", user_id, exc)

    # Load fortune context from DB
    fortune_ctx = await load_fortune_context(user_id)

    # Select prompt and tools based on chat_type
    if chat_type == "diary":
        system_prompt = build_diary_system_prompt(
            user_profile=user_profile,
            today_fortune=fortune_ctx["today_fortune"],
            language=language,
        )
        tools = DIARY_TOOLS
    else:
        system_prompt = build_system_prompt(
            user_profile=user_profile,
            today_fortune=fortune_ctx["today_fortune"],
            daily_bazi=fortune_ctx["daily_bazi"],
            daily_tarot=fortune_ctx["daily_tarot"],
            recent_recharges_block=fortune_ctx["recent_recharges_block"],
            yesterday_diary_block=fortune_ctx["yesterday_diary_block"],
            language=language,
        )
        tools = FORTUNE_TOOLS

    llm = _build_llm().bind_tools(tools)
    messages = [SystemMessage(content=system_prompt), *state["messages"]]

    # Stream to capture thinking chunks in real-time
    prev = state.get("thinking_buffer", "") or ""
    thinking_buffer = prev
    full_message = None

    async for chunk in llm.astream(messages, config=config):
        if full_message is None:
            full_message = chunk
        else:
            full_message = full_message + chunk

        # Extract thinking from this chunk and emit immediately
        new_thinking = _extract_thinking(chunk.content)
        if new_thinking:
            separator = "\n\n---\n\n" if thinking_buffer else ""
            thinking_buffer = thinking_buffer + separator + new_thinking
            await copilotkit_emit_state(config, {"thinking_buffer": thinking_buffer})
            logger.info("🧠 thinking streamed: +%d chars (total %d)", len(new_thinking), len(thinking_buffer))

    ai_message = AIMessage(
        content=full_message.content,
        tool_calls=full_message.tool_calls,
        additional_kwargs=full_message.additional_kwargs,
    )

    logger.info("🧠 thinking final: %d chars, blocks: %s",
                len(thinking_buffer),
                [b.get("type") for b in ai_message.content if isinstance(b, dict)] if isinstance(ai_message.content, list) else "str")

    return {"messages": [ai_message], "thinking_buffer": thinking_buffer}


def _should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END


_agui_compiled = None


def build_agui_graph():
    global _agui_compiled
    if _agui_compiled is not None:
        return _agui_compiled

    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set")

    wf = StateGraph(AgentState)
    wf.add_node("agent", _agent_node)
    wf.add_node("tools", ToolNode(ALL_TOOLS))
    wf.set_entry_point("agent")
    wf.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    wf.add_edge("tools", "agent")

    _agui_compiled = wf.compile(checkpointer=InMemorySaver())
    logger.info("AG-UI graph compiled (model=%s, tools=%s, thinking=%s)",
                DEFAULT_CHAT_MODEL, [t.name for t in ALL_TOOLS], THINKING_ENABLED)
    return _agui_compiled
