from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
import logging

from ..models.diary import DiaryCreate, DiaryPublic, DiaryUpdate
from ..models.user import User
from .auth import get_current_user
from ..core.db import supabase
from ..services.vector_service import vector_service
from ..core.genai_service import genai_service
from datetime import date, datetime

router = APIRouter()

@router.post("", response_model=DiaryPublic, status_code=status.HTTP_201_CREATED)
async def create_diary(
    diary: DiaryCreate,
    current_user: User = Depends(get_current_user),
):
    """
    为当前登录的用户创建一篇新日记。
    同时，根据已存储的当日运势，生成一段即时反馈。
    """
    logging.info(f"Diary creation request received - User: {current_user.id}, content_length: {len(diary.content)} chars")

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
            logging.warning(f"Letta background task failed to start (diary still saved): {letta_error}")

        return created_entry
    except Exception as e:
        logging.error(f"❌ Database operation failed: {e}")
        print(f"❌ DATABASE ERROR: Failed to create diary for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")

def _convert_to_frontend_format(db_entry: dict) -> dict:
    """将数据库格式转换为前端展示格式"""
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
):
    """
    语义搜索用户日记（纯向量搜索）
    """
    logging.info(f"搜索请求 - User: {current_user.id}, keyword: {keyword}, limit: {limit}")

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
):
    """
    获取当前登录用户的所有日记条目。
    """
    logging.info(f"GET diaries request - User: {current_user.id}")

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

