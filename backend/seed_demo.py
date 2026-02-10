"""Demo 用户种子脚本 — 创建 Sarah Chen + 7篇日记 + Letta 画像"""
import asyncio
import logging
import sys
import os

# logging 必须在所有 app import 之前配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", force=True)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.config import (
    DEMO_USER_EMAIL, DEMO_USER_PASSWORD, DEMO_USER_NAME,
    DEMO_USER_BIRTH, DEMO_USER_GENDER, DEMO_USER_TIMEZONE,
)
from app.core.db import supabase
from app.core.genai_service import genai_service
from app.services.letta_service import letta_service

# ── 日记数据 ──────────────────────────────────────────────
DIARIES = [
    {
        "date": "2025-02-03T21:30:00",  # Monday
        "emotion_tags": ["mood_3", "anxious", "curious"],
        "content": (
            "First sync with Jake, the new PM. He showed up with spreadsheets and wants every "
            "design decision mapped to a metric — so different from how I work. Grabbed ramen "
            "alone after work, which was exactly what I needed. Mom called about Lunar New Year "
            "again but I can't take time off with the redesign deadline. Stayed up past 1am "
            "sketching — my brain only turns on after midnight."
        ),
    },
    {
        "date": "2025-02-05T22:00:00",  # Wednesday
        "emotion_tags": ["mood_3", "tired", "surprised"],
        "content": (
            "Zombie mode after two morning meetings — I really need to stop with the midnight "
            "sessions. Showed Jake my concepts and he actually said \"the data story is clear,\" "
            "which shocked me. Presentation to VP Morrison is tomorrow and the narrative still "
            "isn't clicking. Yuki invited me climbing this weekend but I already know I'll "
            "probably bail. Back to the deck — midnight Sarah, do your thing."
        ),
    },
    {
        "date": "2025-02-06T23:15:00",  # Thursday
        "emotion_tags": ["mood_2", "embarrassed", "grateful"],
        "content": (
            "Presentation was going great until Morrison asked about my rollback plan and I "
            "completely froze. Jake jumped in and saved me, which I'm grateful for but also "
            "embarrassed about. Morrison said \"promising direction\" which is basically his "
            "green light, but I can't stop replaying the freeze. Skipped team happy hour and "
            "came home to Thai food and a baking show. Texted Mom a heart emoji and she sent "
            "back five — that helped more than she knows."
        ),
    },
    {
        "date": "2025-02-08T18:45:00",  # Saturday
        "emotion_tags": ["mood_4", "reflective", "relieved"],
        "content": (
            "Bailed on climbing with Yuki, spent the morning scrolling in bed. Forced myself "
            "to Dolores Park — sat on the hill with coffee just watching people and realized I "
            "like being around others when I don't have to perform. Called Mom and told her "
            "about the presentation, she said stop being so hard on yourself, cried in public. "
            "Came home feeling lighter and started revising — the rollback plan is actually "
            "making the design better. Jake slacked me \"let's tag-team the next round\" — "
            "okay Jake, maybe you're alright."
        ),
    },
    {
        "date": "2025-02-09T20:00:00",  # Sunday
        "emotion_tags": ["mood_4", "productive", "hopeful"],
        "content": (
            "Productive day — turned Morrison's feedback into a phased rollout with three "
            "checkpoints, it's more elegant now. Booked flights home for Lunar New Year, "
            "planning to surprise Mom. Jake and I are co-presenting the revision — he handles "
            "metrics, I handle design vision, which is how it should've been from the start. "
            "Tried the new matcha place on Valencia, read a real book for an hour without "
            "checking my phone. I was so caught up in proving I could do it solo that I forgot "
            "partnerships can be stronger."
        ),
    },
    {
        "date": "2025-02-10T21:30:00",  # Monday
        "emotion_tags": ["mood_5", "confident", "connected"],
        "content": (
            "Actually looked forward to work today — Jake sync was fun, we make a weirdly good "
            "team. Morrison stopped by my desk just to say the product directors are \"interested "
            "in the direction\" — his version of full endorsement. Had lunch with Yuki and she "
            "wasn't mad about the climbing bail at all — I always assume people are upset and "
            "they never are. Told Mom about the flights tonight and she literally screamed, then "
            "listed every dish she's making. Midnight thought: I do my best creating alone, but "
            "I do my best growing when I let people in."
        ),
    },
    {
        "date": "2025-02-11T23:00:00",  # Tuesday
        "emotion_tags": ["mood_5", "calm", "ready"],
        "content": (
            "Ran through the deck with Jake twice — it's tight, every slide earns its place. "
            "Realized why I froze last Thursday: I was carrying it solo and any gap felt like "
            "personal failure. Yuki dropped by with boba unprompted and said I've seemed lighter "
            "this week — she's right. Three things I'm looking forward to: tomorrow's "
            "presentation, Saturday climbing, flying home to Mom's cooking. It's almost midnight "
            "but tonight I'm going to bed — the deck is done and I'm ready."
        ),
    },
]

PROFILE_UPDATE = {
    "full_name": DEMO_USER_NAME,
    "birth_datetime": DEMO_USER_BIRTH,
    "gender": DEMO_USER_GENDER,
    "timezone": DEMO_USER_TIMEZONE,
    "fortune_categories": ["overall", "career", "love", "health"],
}


# ── 核心逻辑 ──────────────────────────────────────────────
async def create_demo_user() -> str:
    """通过 Supabase Admin API 创建用户，返回 user_id"""
    # 检查是否已存在
    try:
        existing = supabase.table("profiles").select("id").eq("email", DEMO_USER_EMAIL).execute()
        if existing.data:
            user_id = existing.data[0]["id"]
            logger.info(f"Demo 用户已存在: {user_id}")
            return user_id
    except Exception:
        pass  # profiles 表可能没有 email 列，走 auth 创建

    # 用 admin API 创建（service_role key 有权限）
    try:
        res = supabase.auth.admin.create_user({
            "email": DEMO_USER_EMAIL,
            "password": DEMO_USER_PASSWORD,
            "email_confirm": True,  # 跳过邮箱验证
            "user_metadata": {"full_name": DEMO_USER_NAME},
        })
        user_id = res.user.id
        logger.info(f"创建 Demo 用户成功: {user_id}")
    except Exception as e:
        # 如果用户已存在于 auth 但不在 profiles 查询中
        if "already been registered" in str(e).lower() or "already exists" in str(e).lower():
            # 通过登录获取 user_id
            login_res = supabase.auth.sign_in_with_password({
                "email": DEMO_USER_EMAIL,
                "password": DEMO_USER_PASSWORD,
            })
            user_id = login_res.user.id
            logger.info(f"Demo 用户已存在于 auth，登录获取 ID: {user_id}")
        else:
            raise

    # 更新 profile
    supabase.table("profiles").update(PROFILE_UPDATE).eq("id", user_id).execute()
    logger.info(f"Profile 更新完成: {DEMO_USER_NAME}")
    return user_id


async def seed_diaries(user_id: str):
    """写入日记 + embedding + Letta 画像"""
    for i, entry in enumerate(DIARIES, 1):
        logger.info(f"[{i}/{len(DIARIES)}] 处理日记: {entry['date'][:10]}")

        # 检查是否已存在（幂等：跳过插入，但仍尝试 Letta）
        check = supabase.table("diary_entries").select("id").eq(
            "user_id", user_id
        ).eq("created_at", entry["date"]).execute()
        if check.data:
            logger.info(f"  日记已存在: {check.data[0]['id']}，跳过插入")
        else:
            # 生成 embedding
            try:
                embedding = await genai_service.generate_embedding(entry["content"])
                logger.info(f"  Embedding 生成成功: {len(embedding)} 维")
            except Exception as e:
                logger.warning(f"  Embedding 生成失败: {e}")
                embedding = None

            # 插入 diary_entries
            diary_data = {
                "user_id": user_id,
                "content": entry["content"],
                "emotion_tags": entry["emotion_tags"],
                "embedding": embedding,
                "created_at": entry["date"],
            }
            res = supabase.table("diary_entries").insert(diary_data).execute()
            logger.info(f"  日记写入成功: {res.data[0]['id']}")

        # 喂给 Letta 构建画像（无论日记是否新建都尝试）
        try:
            ok = await letta_service.ingest_diary(
                user_id=user_id,
                diary_text=entry["content"],
                diary_date=entry["date"][:10],
            )
            logger.info(f"  Letta ingest: {'成功' if ok else '失败（Letta 可能未运行）'}")
        except Exception as e:
            logger.warning(f"  Letta ingest 异常（不影响日记）: {e}")

        await asyncio.sleep(1)


async def verify_profile(user_id: str):
    """验证 Letta 画像是否生成"""
    profile = await letta_service.get_user_profile(user_id)
    logger.info(f"\n{'='*50}\nLetta 用户画像:\n{'='*50}\n{profile}\n{'='*50}")


async def main():
    logger.info("开始 Demo 种子数据填充...")

    user_id = await create_demo_user()
    logger.info(f"Demo User ID: {user_id}")

    await seed_diaries(user_id)

    await verify_profile(user_id)

    logger.info("种子数据填充完成!")
    logger.info(f"登录信息: email={DEMO_USER_EMAIL}, password={DEMO_USER_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
