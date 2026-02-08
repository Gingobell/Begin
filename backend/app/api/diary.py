import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID
import logging

from ..models.diary import DiaryCreate, DiaryPublic, DiaryUpdate
from ..models.chat import VoiceDiaryStyleRequest
from pydantic import BaseModel

# Mock 数据专用模型 - 直接匹配前端 UI 需求
class MockDiaryDTO(BaseModel):
    id: str
    user_id: str
    day: str  # UI: "15"
    weekday: str  # UI: "THU"
    time: str  # UI: "21:30"
    mood: int  # UI: 1-5
    mood_label: str  # UI: "愉悦"
    title: str  # UI: "和朋友的夜谈"
    content: str
    tags: list[str]  # UI: ["友谊", "灵感"]
    insight: str  # UI: instant_feedback
    has_viewed_insight: bool
    created_at: str  # 保留用于排序
from ..models.user import User
from .auth import get_current_user
from ..core.db import supabase
from ..services.vector_service import vector_service
from ..core.genai_service import genai_service
# from ..services.mem0_service import mem0_service  # 已注释：使用 Letta 替代
from datetime import date, datetime, timezone, timedelta

router = APIRouter()

# Mock 数据配置
USE_MOCK = os.environ.get("USE_MOCK_DATA", "false").lower() == "true"

# Mock 数据 - 直接返回 UI 需要的格式
MOCK_DIARIES = [
    {
        "id": "aaaaaaaa-1111-1111-1111-111111111111",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "day": "15",
        "weekday": "THU",
        "time": "21:30",
        "mood": 4,
        "mood_label": "不错",
        "title": "和朋友的夜谈",
        "content": "晚上和许久未见的朋友Ran视讯，聊到各自的下一步计划。听到对方的坚持，突然也对自己的节奏更有信心。挂断后写了两页长长的碎念，感觉很释放。",
        "tags": ["友谊", "灵感"],
        "insight": "人与人的连接是你能量的充电座，记得在周五前回信那句鼓励的话。",
        "has_viewed_insight": False,
        "created_at": datetime.now(timezone.utc).replace(hour=21, minute=30).isoformat()
    },
    {
        "id": "bbbbbbbb-2222-2222-2222-222222222222",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "day": "14",
        "weekday": "WED",
        "time": "16:20",
        "mood": 4,
        "mood_label": "欣喜",
        "title": "雨天里的专注力",
        "content": "窗外下着绵密的雨，反倒让今天的专注力稳定很多。上午把 backlog 里的杂事都清完，下午留了两个小时学习新的动画实现方式。",
        "tags": ["学习", "雨天"],
        "insight": "当环境帮你进入静谧时，趁势排程下周的深度工作时段。",
        "has_viewed_insight": True,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=16, minute=20).isoformat()
    },
    {
        "id": "cccccccc-3333-3333-3333-333333333333",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "day": "13",
        "weekday": "TUE",
        "time": "18:45",
        "mood": 3,
        "mood_label": "平稳",
        "title": "慢跑的呼吸节奏",
        "content": "傍晚去河边慢跑，刚开始胸口有点闷，调整到 4:4 的呼吸后慢慢顺畅。跑完坐在河堤上吹风，脑袋里突然冒出几个产品点子。",
        "tags": ["运动", "灵感"],
        "insight": "记录下跑步带来的灵感，把它们拆成明天可以着手的小动作。",
        "has_viewed_insight": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).replace(hour=18, minute=45).isoformat()
    }
]

# 初始化 Supabase 客户端
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) # This line is removed as per the edit hint

@router.post("", response_model=DiaryPublic, status_code=status.HTTP_201_CREATED)
async def create_diary(
    diary: DiaryCreate,
    current_user: User = Depends(get_current_user),
    use_mock: bool = Query(False, description="使用 Mock 数据")
):
    """
    为当前登录的用户创建一篇新日记。
    同时，根据已存储的当日运势，生成一段即时反馈。
    """
    logging.info(f"📝 Diary creation request received - User: {current_user.id}, use_mock: {use_mock}, content_length: {len(diary.content)} chars")
    
    if use_mock or USE_MOCK:
        # 从 emotion_tags 提取 mood 值 (前端格式: ["mood_5"])
        emotion_tags = diary.emotion_tags or []
        mood = 3  # 默认值
        for tag in emotion_tags:
            if tag.startswith('mood_'):
                try:
                    mood = int(tag.split('_')[1])
                    break
                except:
                    pass
        
        mood_labels = {1: "很糟糕", 2: "不太好", 3: "一般", 4: "不错", 5: "很棒"}
        
        # 生成基于 mood 的 mock insight
        mood_insights = {
            1: "看到你今天的心情不太好，抱抱你。记得这只是暂时的，明天会更好。",
            2: "今天似乎有些不顺心，但你已经很棒了，勇敢面对每一天就是最大的成就。",
            3: "今天是平静的一天，这样的日子也很珍贵，让心沉淀下来。",
            4: "能感受到你今天的好心情！继续保持这份愉悦，给自己一个小奖励吧。",
            5: "哇！今天的你充满活力和快乐！记录下这份美好，以后回看会更开心。"
        }
        
        # 计算当前时间
        now = datetime.now(timezone.utc)
        
        mock_diary = {
            "id": str(uuid.uuid4()),
            "user_id": str(current_user.id),
            "day": str(now.day),
            "weekday": now.strftime("%a").upper(),
            "time": now.strftime("%H:%M"),
            "mood": mood,  # Int 格式 1-5
            "mood_label": mood_labels.get(mood, "一般"),
            "title": diary.content[:20] + "..." if len(diary.content) > 20 else diary.content,
            "content": diary.content,
            "tags": [tag for tag in emotion_tags if not tag.startswith('mood_')],  # 移除 mood_ 标签
            "insight": mood_insights.get(mood, "感谢分享你的心情！"),
            "has_viewed_insight": False,
            "created_at": now.isoformat()
        }
        MOCK_DIARIES.insert(0, mock_diary)
        return mock_diary
    
    today = date.today()
    user_id = str(current_user.id)
    
    # 1. 尝试获取已存储的当日电池运势
    battery_fortune = None
    try:
        response = supabase.table("daily_fortune_details").select("battery_fortune").eq("user_id", user_id).eq("fortune_date", today.isoformat()).single().execute()
        if response.data:
            battery_fortune = response.data.get("battery_fortune")
    except Exception as e:
        # 如果没有今日运势，继续处理，但不包含运势信息
        logging.info(f"No battery fortune found for user {user_id} on {today}, proceeding without fortune context: {e}")

    # 2. 构建即时反馈的Prompt
    if battery_fortune:
        # 有运势数据时，使用生成好的电池运势文案
        overall = battery_fortune.get("overall", {})

        daily_management = overall.get("daily_management", "")
        today_actions = overall.get("today_actions", "")
        power_drain = overall.get("power_drain", "")
        surge_protection = overall.get("surge_protection", "")

        feedback_prompt = f"""
    作为一位充满智慧和同理心的朋友，请阅读以下内容并给出来自你的温暖反馈。

    【朋友今天的日记】
    {diary.content}

    【今日运势参考】
    今日整体: {daily_management}
    顺手的事: {today_actions}
    可能卡的地方: {power_drain}
    卡住了怎么办: {surge_protection}

    请结合日记内容和运势信息，给出50-100字的温暖、鼓励的反馈。语调要亲切自然，就像真正的朋友在聊天。
    """
    else:
        # 没有运势数据时，纯粹基于日记内容生成反馈
        feedback_prompt = f"""
    作为一位充满智慧和同理心的朋友，请阅读以下日记内容并给出来自你的温暖反馈。

    【朋友今天的日记】
    {diary.content}

    请基于日记内容，给出50-100字的温暖、鼓励的反馈。语调要亲切自然，就像真正的朋友在聊天。
    如果感受到积极情绪，给予肯定和鼓励；如果察觉到困扰，给予理解和支持。
    """

    # 3. 调用AI生成反馈 (使用知识库增强)
    try:
        instant_feedback = await genai_service.generate_text(feedback_prompt)
    except Exception as e:
        instant_feedback = f"AI反馈生成失败: {e}" # 在反馈生成失败时返回错误信息，而不是None

    # 4. 生成向量（同步，确保成功）
    try:
        embedding = await genai_service.generate_embedding(diary.content)
        logging.info(f"✅ Vector generated successfully, dimension: {len(embedding)}")
    except Exception as ve:
        logging.error(f"❌ Vector generation failed: {ve}")
        embedding = None  # 向量生成失败时仍然保存日记，但 embedding 为 null

    # 5. 创建日记条目并存储（包含向量）
    diary_data = diary.dict()
    diary_data['user_id'] = user_id
    diary_data['instant_feedback'] = instant_feedback
    diary_data['embedding'] = embedding  # 直接存入 diary_entries 表

    logging.info(f"Creating diary entry with data (embedding: {len(embedding) if embedding else 'None'})")
    print(f"💾 Attempting to save diary to database - User: {user_id}, Content length: {len(diary.content)} chars")

    try:
        response = supabase.table("diary_entries").insert(diary_data).execute()
        logging.info(f"Database response: {response}")

        if not response.data:
            logging.error("❌ No data returned from database insert")
            print(f"❌ DATABASE ERROR: No data returned after insert for user {user_id}")
            raise HTTPException(status_code=500, detail="No data returned from database insert")

        created_entry = response.data[0]

        # 打印成功日志
        logging.info(f"✅ SUCCESS: Diary created successfully! ID: {created_entry['id']}, User: {user_id}, Content length: {len(created_entry['content'])} chars, Embedding: {'Yes' if embedding else 'No'}")
        print(f"✅ CREATE DIARY SUCCESS: ID={created_entry['id']}, User={user_id}, Content={len(created_entry['content'])} chars, Embedding={'✅' if embedding else '❌'}")

        # 6. 存储到 Letta 用户画像系统（后台异步操作，不阻塞响应）
        try:
            from ..services.letta_service import letta_service
            import asyncio

            # 提取日期（格式：YYYY-MM-DD）
            diary_date = created_entry['created_at'][:10] if created_entry.get('created_at') else None

            # 使用 asyncio.create_task 在后台执行，不阻塞主流程
            async def ingest_to_letta():
                try:
                    await letta_service.ingest_diary(
                        user_id=user_id,
                        diary_text=diary.content,
                        diary_date=diary_date
                    )
                    logging.info(f"✅ Letta 画像更新成功 - Diary ID: {created_entry['id']}, Date: {diary_date}")
                except Exception as e:
                    logging.warning(f"⚠️ Letta 画像更新失败（不影响日记创建）: {e}")

            asyncio.create_task(ingest_to_letta())
        except Exception as letta_error:
            logging.warning(f"⚠️ Letta 后台任务启动失败（不影响日记创建）: {letta_error}")

        # 原 Mem0 代码已注释（使用 Letta 替代）
        # try:
        #     await mem0_service.add_diary_memory(
        #         diary_content=diary.content,
        #         user_id=user_id,
        #         diary_id=str(created_entry['id'])
        #     )
        #     logging.info(f"✅ Mem0 记忆存储成功 - Diary ID: {created_entry['id']}")
        # except Exception as mem_error:
        #     logging.warning(f"⚠️ Mem0 记忆存储失败（不影响日记创建）: {mem_error}")

        return created_entry
    except Exception as e:
        logging.error(f"❌ Database operation failed: {e}")
        print(f"❌ DATABASE ERROR: Failed to create diary for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")

def _convert_to_frontend_format(db_entry: dict) -> dict:
    """将数据库格式转换为前端 MockDiaryDTO 格式"""
    created_at = datetime.fromisoformat(db_entry['created_at'].replace('Z', '+00:00')) if isinstance(db_entry['created_at'], str) else db_entry['created_at']
    
    # 从 emotion_tags 提取 mood 值（优先）
    emotion_tags = db_entry.get('emotion_tags', []) or []
    mood = 3  # 默认值
    for tag in emotion_tags:
        if isinstance(tag, str) and tag.startswith('mood_'):
            try:
                mood = int(tag.split('_')[1])
                break
            except:
                pass
    
    # 如果没有 mood_ 标签，使用 mood_score 转换
    if mood == 3 and 'mood_score' in db_entry:
        mood_score = db_entry.get('mood_score', 0) or 0  # 数据库: -100到100
        mood = max(1, min(5, int((mood_score + 100) / 40) + 1))  # 转换为1-5
    
    mood_labels = {1: "很糟糕", 2: "不太好", 3: "一般", 4: "不错", 5: "很棒"}
    
    content = db_entry.get('content', '')
    title = content[:20] + "..." if len(content) > 20 else content  # 从内容生成标题
    
    return {
        "id": str(db_entry['id']),
        "user_id": str(db_entry['user_id']),
        "day": str(created_at.day),
        "weekday": created_at.strftime("%a").upper(),
        "time": created_at.strftime("%H:%M"),
        "mood": mood,  # Int 格式 1-5
        "mood_label": mood_labels[mood],
        "title": title,
        "content": content,
        "tags": [tag for tag in emotion_tags if not (isinstance(tag, str) and tag.startswith('mood_'))],  # 移除 mood_ 标签
        "insight": db_entry.get('instant_feedback', '') or db_entry.get('ai_comment', '') or '',
        "has_viewed_insight": False,
        "created_at": db_entry['created_at']
    }

@router.get("/search")
async def search_diaries(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量"),
    current_user: User = Depends(get_current_user),
    use_mock: bool = Query(False, description="使用 Mock 数据")
):
    """
    语义搜索用户日记（纯向量搜索）
    - 使用向量相似度进行语义匹配
    - 支持中文语义理解（如「开心」匹配「快乐」）
    - 按相似度排序返回结果
    """
    logging.info(f"🔍 搜索请求 - User: {current_user.id}, keyword: {keyword}, limit: {limit}")

    if use_mock or USE_MOCK:
        # Mock 模式：简单文本匹配
        mock_results = [
            d for d in MOCK_DIARIES
            if d["user_id"] == str(current_user.id) and (
                keyword.lower() in d["content"].lower() or
                keyword.lower() in d["title"].lower() or
                any(keyword.lower() in tag.lower() for tag in d["tags"])
            )
        ]
        logging.info(f"✅ Mock 搜索返回 {len(mock_results)} 条结果")
        return mock_results[:limit]

    try:
        user_id = str(current_user.id)

        # 向量语义搜索
        vector_results = await vector_service.search_similar_diaries(
            user_id=user_id,
            query=keyword,
            threshold=0.0,  # 不过滤，返回所有结果按相似度排序
            max_results=limit
        )

        if not vector_results:
            logging.info(f"✅ 搜索无结果 - User: {user_id}, keyword: {keyword}")
            return []

        # 获取完整日记详情
        diary_ids = [r['diary_id'] for r in vector_results]
        diaries_response = supabase.table("diary_entries")\
            .select("*")\
            .in_("id", diary_ids)\
            .execute()

        if not diaries_response.data:
            logging.warning(f"⚠️ 日记详情查询失败 - diary_ids: {diary_ids}")
            return []

        # 转换为前端格式
        frontend_results = [_convert_to_frontend_format(diary) for diary in diaries_response.data]

        logging.info(f"✅ 搜索完成 - 返回 {len(frontend_results)} 条结果")
        return frontend_results

    except Exception as e:
        logging.error(f"❌ 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {e}")

@router.get("")
def get_diaries(
    current_user: User = Depends(get_current_user),
    use_mock: bool = Query(False, description="使用 Mock 数据")
):
    """
    获取当前登录用户的所有日记条目。
    """
    logging.info(f"📖 GET diaries request - User: {current_user.id}, use_mock: {use_mock}")
    print(f"📖 GET DIARIES REQUEST: User={current_user.id}, use_mock={use_mock}")
    
    if use_mock or USE_MOCK:
        mock_result = [d for d in MOCK_DIARIES if d["user_id"] == str(current_user.id)]
        logging.info(f"✅ Returning {len(mock_result)} mock diaries")
        print(f"✅ MOCK MODE: Returning {len(mock_result)} mock diaries")
        return mock_result
    
    try:
        logging.info(f"🔍 Querying database for user: {current_user.id}")
        print(f"🔍 QUERY DB: Fetching diaries for user {current_user.id}")
        response = supabase.table("diary_entries").select("*").eq("user_id", str(current_user.id)).order("created_at", desc=True).execute()
        
        if response.data is None:
            logging.warning(f"⚠️ No diary data returned from database for user {current_user.id}")
            print(f"⚠️ NO DATA: Empty result for user {current_user.id}")
            return []
        
        logging.info(f"✅ Retrieved {len(response.data)} raw entries from database")
        print(f"💾 RAW DATA: Retrieved {len(response.data)} entries from DB")
        
        # 转换为前端格式
        frontend_data = [_convert_to_frontend_format(entry) for entry in response.data]
        logging.info(f"✅ Converted to frontend format: {len(frontend_data)} diaries")
        print(f"✅ GET DIARIES SUCCESS: Returning {len(frontend_data)} formatted entries for user {current_user.id}")
        return frontend_data
    except Exception as e:
        logging.error(f"❌ Database query failed for user {current_user.id}: {e}")
        print(f"❌ DATABASE ERROR: Failed to retrieve diaries for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve diaries: {e}")

@router.put("/{diary_id}", response_model=DiaryPublic)
def update_diary(
    diary_id: UUID,
    diary_update: DiaryUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    更新一篇属于当前用户的日记。
    """
    logging.info(f"📝 UPDATE diary request - Diary ID: {diary_id}, User: {current_user.id}")
    print(f"📝 UPDATE DIARY REQUEST: ID={diary_id}, User={current_user.id}")
    
    # 检查日记是否存在且属于当前用户
    try:
        response = supabase.table("diary_entries").select("id, user_id").eq("id", str(diary_id)).single().execute()
        if not response.data or response.data['user_id'] != str(current_user.id):
            logging.warning(f"⚠️ Diary {diary_id} not found or access denied for user {current_user.id}")
            print(f"⚠️ ACCESS DENIED: User {current_user.id} cannot access diary {diary_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary not found or access denied.")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Failed to check diary ownership: {e}")
        print(f"❌ DATABASE ERROR: Failed to check diary {diary_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    update_data = diary_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    try:
        response = supabase.table("diary_entries").update(update_data).eq("id", str(diary_id)).execute()
        if not response.data:
            logging.error(f"❌ No data returned after update for diary {diary_id}")
            print(f"❌ DATABASE ERROR: No data returned after updating diary {diary_id}")
            raise HTTPException(status_code=500, detail="Failed to update diary.")
        
        logging.info(f"✅ Diary {diary_id} updated successfully")
        print(f"✅ UPDATE DIARY SUCCESS: ID={diary_id}, User={current_user.id}")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Database update failed for diary {diary_id}: {e}")
        print(f"❌ DATABASE ERROR: Failed to update diary {diary_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")

@router.delete("/{diary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary(
    diary_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    删除一篇属于当前用户的日记。
    """
    logging.info(f"🗑️ DELETE diary request - Diary ID: {diary_id}, User: {current_user.id}")
    print(f"🗑️ DELETE DIARY REQUEST: ID={diary_id}, User={current_user.id}")
    
    # 检查日记是否存在且属于当前用户
    try:
        response = supabase.table("diary_entries").select("id, user_id").eq("id", str(diary_id)).single().execute()
        if not response.data or response.data['user_id'] != str(current_user.id):
            logging.warning(f"⚠️ Diary {diary_id} not found or access denied for user {current_user.id}")
            print(f"⚠️ ACCESS DENIED: User {current_user.id} cannot delete diary {diary_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary not found or access denied.")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Failed to check diary ownership: {e}")
        print(f"❌ DATABASE ERROR: Failed to check diary {diary_id} before deletion: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    try:
        supabase.table("diary_entries").delete().eq("id", str(diary_id)).execute()
        logging.info(f"✅ Diary {diary_id} deleted successfully")
        print(f"✅ DELETE DIARY SUCCESS: ID={diary_id}, User={current_user.id}")
    except Exception as e:
        logging.error(f"❌ Database deletion failed for diary {diary_id}: {e}")
        print(f"❌ DATABASE ERROR: Failed to delete diary {diary_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database deletion failed: {e}")
    
    return None


# Begin Journal 风格系统配置
STYLE_PROMPTS = {
    "poetic": {  # 诗意风格（对应 Cinema Voiceover）
        "name": "电影旁白风",
        "prompt": """【风格要求：电影旁白风】
- 像描绘一段情绪镜头，以"光影、雾、回声"等抽象意象表达心境。
- 可以使用隐喻（仅情绪），但不能构成真实场景。
- 句式短，有剪辑感与呼吸感。
- 氛围感强，但克制，不夸张。
- 不出现真实环境、地点、行为描写（如走路、坐下、打开门）。"""
    },
    "concise": {  # 简洁风格（对应 Mini Fiction）
        "name": "微小说风",
        "prompt": """【风格要求：微小说风】
- 像一个小段落的文学短篇，但不能创造情节。
- 可以调整语序、制造轻微节奏起伏。
- 核心是让内容读起来像一个内心小故事。
- 不新增人物、事件、对话。
- 不添加背景设定、冲突或结局。"""
    },
    "detailed": {  # 详细风格（对应 Drifting Realism）
        "name": "轻纪实漫游风",
        "prompt": """【风格要求：轻纪实漫游风】
- 轻松、松弛、有"自然游走感"的内心叙述。
- 温度真实、不冷漠、不戏剧化。
- 使用缓慢流动的句式。
- 不添加场景、行动或新的事实细节。"""
    },
    "emotional": {  # 情感风格（对应 Romantic Lyric）
        "name": "文艺浪漫风",
        "prompt": """【风格要求：文艺浪漫风】
- 柔软、浪漫、细腻、适合分享。
- 可使用比喻与自然意象（如光、风、影、色）。
- 意象只能作为情绪隐喻，不是现实发生的场景。
- 不添加任何外部环境或行为描写。"""
    },
    "philosophical": {  # 哲思风格（对应 Light Philosophy）
        "name": "哲学轻思考风",
        "prompt": """【风格要求：哲学轻思考风】
- 凝练、有思辨味道，但不晦涩。
- 从用户的内容提炼一个内在理解或反思。
- 不加入人生大道理、不做说教。
- 不推断用户未写出的问题原因。
- 文体克制、深度适中。"""
    },
    "witty": {  # 网络幽默风（对应 Witty Casual）
        "name": "网络幽默风",
        "prompt": """【风格要求：网络幽默风】
- 有梗、轻松、带一点自嘲。
- 像一条真实、有趣、可发到社交媒体的内容。
- 不夸张事件，不戏剧化。
- 语言口语化但不低俗。"""
    }
}

SYSTEM_PROMPT_BASE = """你是 Begin Journal 的文风重写 AI，引擎的核心任务是：
在不改变用户所写内容事实的前提下，将用户的日记内容转换为指定的文学风格表达。

你必须严格遵守以下三大规则：

----------------------------------------------------
【A. 第一人称视角规范（必须遵守）】
1. 输出必须使用第一人称"我"作为叙述视角。
2. 用户文本中提到的朋友、家人、同事等人物必须保留，不可修改或合并。
3. 不得将其他人物替换成"我"。
4. 除非用户明确描述，否则禁止创造任何第三人称视角的叙述角度。
5. 涉及他人的行为与话语必须与用户输入一致，不能推断其动机、背景或心理。

----------------------------------------------------
【B. 内容保真规范（必须遵守）】
1. 不得新增事件、人物、地点、行为、对话。
2. 不得虚构用户未提及的经历、行动、背景或情节。
3. 不得增加或夸大用户未表达的情绪强度。
4. 不得推断用户未写出的原因、动机或心理变化。
5. 不得使用真实场景描写或行动描写来"补足画面"。
   （例：不可加"我走在街上""光从窗户照进来"等具体场景）
6. 必须保留用户所有信息，包括事件、感受、关系、想法。
7. 仅允许进行：
   - 语言润色与重写
   - 表达方式的改变
   - 文学风格化
   - 节奏优化
   - 隐喻表达（仅可用于情绪，不代表真实事件）
8. 重写后的文本必须「内容一致」「情绪一致」「事实一致」。

----------------------------------------------------
【C. 输出格式规范】
1. 输出只有正文，不要解释、不反思、不分析风格。
2. 不出现作家、文体、博主、名人引用。
3. 不加入风格标签或风格解释。
4. 文本必须自然、流畅，适合用户阅读与分享。"""


@router.post("/voice-diary/style-transform")
async def transform_voice_diary_style(
    request: VoiceDiaryStyleRequest,
    current_user: User = Depends(get_current_user)
):
    """语音日记风格转换API - 根据用户选择的风格重写转录文本"""
    try:
        raw_text = request.raw_text
        style = request.style
        
        if not raw_text:
            raise HTTPException(status_code=400, detail="原始文本不能为空")
        
        if style not in STYLE_PROMPTS:
            raise HTTPException(status_code=400, detail=f"不支持的风格类型: {style}")
        
        # 构建完整的系统提示词
        style_config = STYLE_PROMPTS[style]
        full_system_prompt = f"""{SYSTEM_PROMPT_BASE}

{style_config['prompt']}

----------------------------------------------------

现在请将以下用户原文按照上述风格要求进行重写：

用户原文：
{raw_text}

请直接输出重写后的文本，不要任何解释或标签："""
        
        logging.info(f"🎨 用户 {current_user.id} 请求风格转换: {style_config['name']}")
        
        # 使用 enhanced_genai_service 生成风格化文本
        styled_text = await genai_service.generate_text(full_system_prompt)
        
        logging.info(f"✅ 风格转换成功，原文长度: {len(raw_text)}, 转换后长度: {len(styled_text)}")
        
        return {
            "styled_text": styled_text,
            "style": style,
            "style_name": style_config['name']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 风格转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"风格转换失败: {str(e)}")
