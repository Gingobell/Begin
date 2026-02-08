"""Letta 用户画像服务"""
import logging
import asyncio
from typing import Optional, Dict
from letta_client import Letta

from app.config import LETTA_BASE_URL, LETTA_CHAT_MODEL, LETTA_EMBEDDING_MODEL
from app.core.db import supabase

logger = logging.getLogger(__name__)

PERSONA_PROMPT = """You are a thoughtful recorder who extracts **facts with long-term value** from diary entries and updates user_profile.

## What to record
✅ Identity info: job, school, location, family members
✅ Interests & hobbies
✅ Preferences & tastes
✅ Major events: job change, moving, relationship changes
✅ Ongoing states: job hunting, studying for exam
✅ Relationships

## What NOT to record
❌ One-time meals
❌ Single-day moods
❌ Temporary behaviors

## Categories
- Work/Personal Context
- Personal Interests/Preferences
- Top of Mind
- Recent Months
- Earlier Context
- Long-term Background
"""

USER_PROFILE_TEMPLATE = """## 基本背景 (Work/Personal Context)
暂无信息。

## 兴趣偏好 (Personal Interests/Preferences)
暂无信息。

## 当前关注 (Top of Mind)
暂无信息。

## 近期动态 (Recent Months)
暂无信息。

## 早期背景 (Earlier Context)
暂无信息。

## 长期特质 (Long-term Background)
暂无信息。
"""


class LettaService:
    def __init__(self):
        self.client = None
        self.agent_cache: Dict[str, str] = {}
        self._init_client()

    def _init_client(self):
        try:
            self.client = Letta(base_url=LETTA_BASE_URL)
            logger.info(f"✅ Letta client 初始化成功 - URL: {LETTA_BASE_URL}")
        except Exception as e:
            logger.error(f"❌ Letta client 初始化失败: {e}")
            self.client = None

    async def get_or_create_agent(self, user_id: str) -> Optional[str]:
        if not self.client:
            return None
        if user_id in self.agent_cache:
            return self.agent_cache[user_id]
        try:
            response = supabase.table("profiles").select("letta_agent_id").eq("id", user_id).single().execute()
            if response.data and response.data.get("letta_agent_id"):
                agent_id = response.data["letta_agent_id"]
                self.agent_cache[user_id] = agent_id
                return agent_id
        except Exception as e:
            logger.warning(f"查询 Agent ID 失败: {e}")
        try:
            agent = await asyncio.to_thread(
                self.client.agents.create,
                name=f"user_{user_id[:8]}",
                model=LETTA_CHAT_MODEL,
                embedding=LETTA_EMBEDDING_MODEL,
                memory_blocks=[
                    {"label": "persona", "value": PERSONA_PROMPT, "limit": 2000},
                    {"label": "user_profile", "value": USER_PROFILE_TEMPLATE, "limit": 5000},
                ],
                tools=["memory_replace", "memory_rethink", "send_message"],
            )
            agent_id = agent.id
            self.agent_cache[user_id] = agent_id
            supabase.table("profiles").update({"letta_agent_id": agent_id}).eq("id", user_id).execute()
            return agent_id
        except Exception as e:
            logger.error(f"❌ 创建 Agent 失败: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> str:
        if not self.client:
            return "暂无用户画像"
        agent_id = await self.get_or_create_agent(user_id)
        if not agent_id:
            return "暂无用户画像"
        try:
            blocks = await asyncio.to_thread(self.client.agents.blocks.list, agent_id=agent_id)
            for block in blocks:
                if block.label == "user_profile":
                    return block.value
            return "暂无用户画像"
        except Exception as e:
            logger.error(f"❌ 读取用户画像失败: {e}")
            return "暂无用户画像"

    async def ingest_diary(self, user_id: str, diary_text: str, diary_date: Optional[str] = None) -> bool:
        if not self.client:
            return False
        agent_id = await self.get_or_create_agent(user_id)
        if not agent_id:
            return False
        try:
            content = f"[Diary Date: {diary_date}]\n\n{diary_text}" if diary_date else diary_text
            content += "\n\nPlease extract features and update your understanding of me."
            await asyncio.to_thread(
                self.client.agents.messages.create,
                agent_id=agent_id,
                messages=[{"role": "user", "content": content}],
            )
            return True
        except Exception as e:
            logger.error(f"❌ 发送日记失败: {e}")
            return False


letta_service = LettaService()
