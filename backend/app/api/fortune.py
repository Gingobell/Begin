import os
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
from datetime import date, datetime, timedelta
import logging
from supabase import create_client, Client
from uuid import UUID

# 导入我们的核心服务
from ..services.bazi_service import bazi_service
from ..services.tarot_service import tarot_service
from ..core.genai_service import genai_service

# Optional services — endpoints that need them fail gracefully at runtime
try:
    from ..services.memory_service import get_memory, extract_recent_context, get_contextual_memory
except ImportError:
    async def get_memory(uid): return {}
    def extract_recent_context(m): return {"recent_concerns":[], "future_events":[], "personality":"", "goals":[]}
    async def get_contextual_memory(uid, q): return {"has_relevant_context": False, "relevant_diary_events": []}

try:
    from ..services.structured_fortune_service import structured_fortune_service
except ImportError:
    structured_fortune_service = None
from ..models.user import User # 导入我们自己的用户模型
from .auth import get_current_user # 导入新的认证函数

# 用于可选认证
security = HTTPBearer(auto_error=False)

router = APIRouter()
logging.basicConfig(level=logging.INFO)

# 初始化 Supabase 客户端
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 运势缓存 (user_id+date -> fortune_data)
_fortune_cache = {}
_fortune_cache_ttl = 3600  # 运势缓存1小时（运势变化较慢）

def get_user_language(
    user_id: Optional[str] = None,
    accept_language: Optional[str] = None
) -> str:
    """
    获取用户语言偏好
    优先级：1. Accept-Language header  2. 数据库用户偏好  3. 默认zh-CN
    """
    # 1. 优先使用 Accept-Language header
    if accept_language:
        lang = accept_language.split(",")[0].strip()  # 取第一个语言
        logging.info(f"🌐 使用 Accept-Language header: {lang}")
        return lang

    # 2. 从数据库获取用户偏好
    if user_id:
        try:
            pref_response = supabase.table("user_preferences").select("preferred_language").eq("user_id", user_id).single().execute()
            if pref_response.data:
                lang = pref_response.data.get("preferred_language", "zh-CN")
                logging.info(f"🌐 使用数据库用户偏好: {lang}")
                return lang
        except Exception as e:
            logging.warning(f"⚠️ 获取用户语言偏好失败: {e}")

    # 3. 默认中文
    logging.info("🌐 使用默认语言: zh-CN")
    return "zh-CN"


def get_user_gender(user_id: str) -> str:
    """
    获取用户性别。数据库保存英文小写(male/female/other)，引擎需要 'Male'/'Female'。
    默认返回 'Male' 以保持兼容。
    """
    default_gender = "Male"
    try:
        resp = supabase.table("profiles").select("gender").eq("id", user_id).single().execute()
        raw_gender = (resp.data or {}).get("gender") if resp else None
        if not raw_gender:
            return default_gender
        gender_norm = str(raw_gender).lower()
        if gender_norm.startswith("f"):
            return "Female"
        if gender_norm.startswith("m"):
            return "Male"
        return default_gender
    except Exception as e:
        logging.warning(f"⚠️ 获取用户性别失败: {e}")
        return default_gender

@router.get("/status", response_model=Dict[str, Any])
async def check_fortune_status(
    use_mock: bool = Query(False, description="使用mock数据（开发模式）"),
    local_date: Optional[str] = Query(None, description="前端本地日期（格式：YYYY-MM-DD）"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    检查今日运势是否已生成
    
    返回格式：
    {
        "is_generated": true/false,  # 运势是否已生成
        "fortune_date": "2025-11-03"  # 运势日期
    }
    """
    if local_date: # 使用前端传递的本地日期
        try:
            today = datetime.strptime(local_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        today = date.today() # 后端服务器日期（fallback）
    
    # Mock模式
    if use_mock:
        logging.info(f"🧪 Mock模式：检查运势生成状态")
        mock_user_id = "11111111-1111-1111-1111-111111111111"
        mock_language = get_user_language(mock_user_id, accept_language)
        
        try:
            # 检查 mock 用户的运势状态
            # 优先匹配语言，避免多语言记录导致 single() 报错
            status_response = supabase.table("daily_fortune_details").select("is_generated").eq("user_id", mock_user_id).eq("fortune_date", today.isoformat()).eq("language", mock_language).limit(1).execute()
            if not status_response.data:
                # 兜底：任意语言有记录即可
                status_response = supabase.table("daily_fortune_details").select("is_generated").eq("user_id", mock_user_id).eq("fortune_date", today.isoformat()).limit(1).execute()

            if status_response.data:
                return {
                    "is_generated": status_response.data[0].get("is_generated", False),
                    "fortune_date": today.isoformat()
                }
        except Exception as e:
            logging.info(f"Mock用户今日运势尚未创建: {e}")
        
        return {
            "is_generated": False,
            "fortune_date": today.isoformat()
        }
    
    # 非Mock模式需要认证
    if not credentials:
        raise HTTPException(status_code=401, detail="需要认证")
    
    current_user = await get_current_user(credentials)
    user_id = str(current_user.id)
    user_language = get_user_language(user_id, accept_language)
    
    # 检查用户今日运势状态
    try:
        # 优先尝试当前语言，避免多语言多条记录导致 single() 报错
        status_response = supabase.table("daily_fortune_details").select("is_generated").eq("user_id", user_id).eq("fortune_date", today.isoformat()).eq("language", user_language).limit(1).execute()
        if not status_response.data:
            # 回退：不区分语言，取任意一条记录判断是否已生成
            status_response = supabase.table("daily_fortune_details").select("is_generated").eq("user_id", user_id).eq("fortune_date", today.isoformat()).limit(1).execute()

        if status_response.data:
            return {
                "is_generated": status_response.data[0].get("is_generated", False),
                "fortune_date": today.isoformat()
            }
    except Exception as e:
        logging.info(f"用户 {user_id} 今日运势尚未创建: {e}")
    
    return {
        "is_generated": False,
        "fortune_date": today.isoformat()
    }

@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_fortune(
    use_mock: bool = Query(False, description="使用mock数据（开发模式）"),
    local_date: Optional[str] = Query(None, description="前端本地日期（格式：YYYY-MM-DD）"),
    tarot_card_id: Optional[int] = Query(None, description="前端抽取的塔罗牌ID"),
    orientation: Optional[str] = Query(None, description="塔罗牌朝向：upright/reversed"),
    force_regenerate: bool = Query(False, description="强制重新生成（语言切换时使用）"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    获取每日综合运势（八字+塔罗+AI记忆增强）

    🆕 使用 v2 增强版本：
    - 情感共鸣+治愈引导风格
    - 术语消歧 + 动态权重 + 知识增强
    - 结构化输出（一次性生成所有分类）

    🎴 前端抽卡模式：
    - 前端传递 tarot_card_id 和 orientation 参数
    - 后端直接使用指定的卡片生成运势

    🔧 开发模式：
    - use_mock=true: 返回简化的mock数据，用于前端开发（无需认证）

    实现逻辑：
    1. 缓存优先：先检查 daily_fortune_details 表是否有今日运势
    2. 如果没有，使用 v2 RAG 增强生成个性化结构化运势
    3. 保存到数据库并返回
    """
    if local_date: # 使用前端传递的本地日期
        try:
            today = datetime.strptime(local_date, "%Y-%m-%d").date()
            logging.info(f"📅 [日期接收] 前端传递日期: {local_date} -> 解析为: {today}")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        today = date.today() # 后端服务器日期（fallback）
        logging.info(f"📅 [日期接收] 未收到前端日期，使用服务器日期: {today}")
    
    logging.info(f"📅 [运势计算] 将使用日期: {today} 进行运势计算")

    # 🧪 Mock模式：从数据库读取mock用户的预备运势（无需认证）
    if use_mock:
        logging.info(f"🧪 Mock模式：从数据库读取mock用户运势（无需认证）")
        mock_user_id = "11111111-1111-1111-1111-111111111111"

        # 获取语言偏好（mock模式也支持语言切换）
        user_language = get_user_language(mock_user_id, accept_language)

        try:
            # 尝试从 daily_fortune_details 表获取 mock 用户的今日运势（包含语言过滤）
            details_response = supabase.table("daily_fortune_details").select("*").eq("user_id", mock_user_id).eq("fortune_date", today.isoformat()).eq("language", user_language).limit(1).execute()
            if details_response.data:
                print(f"\n{'='*80}")
                print(f"✅ 找到 mock 用户的预备运势: {today} (语言: {user_language})")
                data = details_response.data[0]
                
                # 输出数据库返回的原始数据
                print(f"📦 数据库返回的 battery_fortune 字段:")
                print(f"   {data.get('battery_fortune')}")
                print(f"📦 数据库返回的 daily_bazi 字段:")
                print(f"   {data.get('daily_bazi')}")
                print(f"📦 数据库返回的 daily_tarot 字段:")
                print(f"   {data.get('daily_tarot')}")
                
                result = {
                    "bazi_analysis": data.get("daily_bazi"),
                    "tarot_reading": data.get("daily_tarot"),
                    "battery_fortune": data.get("battery_fortune"),
                    "from_cache": True
                }
                
                # 输出最终返回的数据结构
                print(f"📤 返回给前端的数据结构:")
                print(f"   bazi_analysis存在: {result.get('bazi_analysis') is not None}")
                print(f"   tarot_reading存在: {result.get('tarot_reading') is not None}")
                print(f"   battery_fortune键: {list(result.get('battery_fortune', {}).keys()) if result.get('battery_fortune') else 'None'}")
                print(f"{'='*80}\n")
                
                return result
        except Exception as e:
            logging.warning(f"⚠️ Mock模式：未找到预备运势，返回占位数据: {e}")
        
        # 如果没有找到预备运势，返回占位数据（支持多语言）
        placeholder_day_master = "甲"
        placeholder_stem_relation = "比肩"
        placeholder_stem_analysis = "比肩的影响"
        placeholder_branch_relation = "食神"
        placeholder_branch_analysis = "食神的影响"

        return {
            "bazi_analysis": {
                "day_master": placeholder_day_master,
                "stem_influence": {
                    "relation": placeholder_stem_relation,
                    "analysis": placeholder_stem_analysis
                },
                "branch_influence": {
                    "relation": placeholder_branch_relation,
                    "analysis": placeholder_branch_analysis
                },
                "body_strength": "Balanced",
                "energy_phase": "未知"
            },
            "tarot_reading": {
                "card": {
                    "id": 19,
                    "card_id": "19_sun",
                    "card_name": "太阳",
                    "arcana_type": "Major Arcana",
                    "suit": None,
                    "meaning_up": "成功、喜悦、活力、乐观、自信",
                    "meaning_down": "短暂的成功、虚假的快乐、缺乏热情",
                    "keywords": ["成功", "喜悦", "活力", "乐观", "自信", "纯真"],
                    "description": "一个孩子骑在白马上，背景是明亮的太阳。象征着纯真、喜悦和生命的活力。"
                },
                "orientation": "upright"
            },
            "battery_fortune": {
                "overall": {
                    "date_line": f"{today.isoformat()} · Mock ｜ 电量80%",
                    "daily_management": "今天状态平稳，适合按计划推进重要事项。",
                    "fast_charge": "快充：专注一件事 30 分钟，提升掌控感。",
                    "power_saving": "省电：减少刷屏，留出安静时间。",
                    "power_drain": "耗电：无休止的对比和内耗。",
                    "surge_protection": "护电：把待办拆成 3 步，逐个完成。",
                    "recharge": "回电：晒太阳或快走 10 分钟。"
                },
                "career": {
                    "title_line": "事业 ｜ 电量82%",
                    "status": "专注度不错，能推进关键节点。",
                    "charge_action": "整理优先级，先做一件最硬的事。",
                    "drain_warning": "反复切换任务在漏电（信号：心烦意乱）。"
                },
                "wealth": {
                    "title_line": "财富 ｜ 电量75%",
                    "status": "稳定向上，适合复盘支出。",
                    "charge_action": "梳理一笔账，确认现金流。",
                    "drain_warning": "冲动消费在漏电（信号：情绪驱动买）。"
                },
                "love": {
                    "title_line": "感情 ｜ 电量70%",
                    "status": "情绪起伏小，适合轻交流。",
                    "charge_action": "说一次真诚的感谢。",
                    "drain_warning": "翻旧账在漏电（信号：反复提同件事）。"
                },
                "social": {
                    "title_line": "人际 ｜ 电量78%",
                    "status": "关系温和，利于短交流。",
                    "charge_action": "主动问候一位朋友。",
                    "drain_warning": "过度迎合在漏电（信号：敷衍微笑）。"
                },
                "study": {
                    "title_line": "学业 ｜ 电量76%",
                    "status": "吸收力正常，可稳步推进。",
                    "charge_action": "复习 1 个知识点，做 1 题巩固。",
                    "drain_warning": "长时间分心在漏电（信号：频繁切屏）。"
                },
                "low_power_mode": False,
                "scores": {
                    "overall": 80,
                    "career": 82,
                    "wealth": 75,
                    "love": 70,
                    "social": 78,
                    "study": 76
                },
                "fast_charge_domain": "事业",
                "power_drain_domain": "感情"
            },
            "from_cache": False
        }
    
    # 非Mock模式需要认证
    if not credentials:
        raise HTTPException(status_code=401, detail="需要认证")
    
    # 获取当前用户
    current_user = await get_current_user(credentials)
    user_id = str(current_user.id)
    
    logging.info(f"🔄 用户 {user_id} 使用 v2 增强版本生成运势")

    # 获取用户语言偏好（优先使用 Accept-Language header）
    user_language = get_user_language(user_id, accept_language)

    # 检查内存缓存（包含语言）
    cache_key = f"{user_id}:{today.isoformat()}:{user_language}"
    if not force_regenerate and cache_key in _fortune_cache:
        cache_entry = _fortune_cache[cache_key]
        cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
        if cache_age < _fortune_cache_ttl:
            logging.info(f"💾 使用运势缓存: user_id={user_id}, language={user_language}, 已缓存{int(cache_age)}秒")
            return cache_entry['data']

    # 1. 从 daily_fortune_details 表获取今日运势（包含语言过滤）
    if not force_regenerate:
        try:
            details_response = supabase.table("daily_fortune_details").select("*").eq("user_id", user_id).eq("fortune_date", today.isoformat()).eq("language", user_language).limit(1).execute()
            if details_response.data:
                data = details_response.data[0]
                print(f"\n{'='*80}")
                print(f"✅ 找到预备运势 for user {user_id} on {today} (语言: {user_language})")

                # 输出数据库返回的原始数据
                print(f"📦 数据库返回的 battery_fortune 字段:")
                print(f"   {data.get('battery_fortune')}")
                print(f"📦 数据库返回的 daily_bazi 字段:")
                print(f"   {data.get('daily_bazi')}")
                print(f"📦 数据库返回的 daily_tarot 字段:")
                print(f"   {data.get('daily_tarot')}")

                # 补充 image_key 到缓存的 tarot 数据
                tarot_data = data.get("daily_tarot")
                if tarot_data and "image_key" not in tarot_data:
                    card_name = tarot_data.get("card", {}).get("card_name")
                    orientation = tarot_data.get("orientation", "upright")
                    if card_name:
                        tarot_data["image_key"] = tarot_service._generate_image_key(card_name, orientation)

                result = {
                    "bazi_analysis": data.get("daily_bazi"),
                    "tarot_reading": tarot_data,
                    "battery_fortune": data.get("battery_fortune"),
                    "from_cache": True
                }

                # 输出最终返回的数据结构
                print(f"📤 返回给前端的数据结构:")
                print(f"   bazi_analysis存在: {result.get('bazi_analysis') is not None}")
                print(f"   tarot_reading存在: {result.get('tarot_reading') is not None}")
                print(f"   battery_fortune键: {list(result.get('battery_fortune', {}).keys()) if result.get('battery_fortune') else 'None'}")
                print(f"{'='*80}\n")

                # 保存到内存缓存
                _fortune_cache[cache_key] = {
                    'data': result,
                    'timestamp': datetime.now()
                }

                return result
        except Exception as e:
            logging.info(f"未找到预备运势，开始生成新运势...")

    # 2. 如果数据库没有记录，则生成新运势
    logging.info(f"Generating new fortune for user {user_id} on {today}.")
    
    # 获取用户生日
    birth_date = current_user.birth_date

    if not birth_date:
        raise HTTPException(status_code=400, detail="用户生日未设置，请先设置生日信息。")

    # 3. 获取用户记忆
    try:
        user_memory = await get_memory(current_user.id)
        logging.info(f"✅ Retrieved user memory for {user_id}")
    except Exception as e:
        logging.warning(f"⚠️ Failed to get user memory for {user_id}: {e}")
        user_memory = {}

    try: # 4. 获取八字日运分析
        bazi_analysis = bazi_service.analyze_daily_flow(birth_date, target_date=today, language=user_language)
        logging.info(f"✅ BaZi Analysis for {user_id} successful (language: {user_language})")
    except Exception as e:
        logging.error(f"❌ Error in BaZi service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed during BaZi analysis.")

    # 注意：user_language 已在前面获取，这里直接使用

    try:  # 5. 获取塔罗日运分析
        if tarot_card_id is not None and orientation:
            # 前端抽卡模式：使用前端传来的卡片ID和朝向，并落库记录
            logging.info(
                f"🎴 使用前端抽取的塔罗牌并落库: "
                f"card_id={tarot_card_id}, orientation={orientation}"
            )
            tarot_reading = tarot_service.get_card_by_id(
                tarot_card_id,
                orientation,
                user_language,
                user_id=user_id,
                draw_date=today,
                persist=True
            )
            if "error" in tarot_reading:
                raise HTTPException(
                    status_code=400, detail=tarot_reading["error"]
                )
        else:
            # 后端抽卡模式（向后兼容）：使用实时抽卡并存储逻辑
            logging.info("🎲 使用后端抽卡逻辑（向后兼容模式，真实随机+存储）")
            tarot_reading = tarot_service.draw_daily_card(
                user_id, today, user_language
            )
        logging.info(f"✅ Tarot Reading for {user_id} successful")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Error in Tarot service: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed during Tarot card drawing."
        )

    # 6. 获取日记上下文（用于个性化）
    try:
        contextual_memory = await get_contextual_memory(user_id, f"{bazi_analysis['day_master']} {tarot_reading['card']['card_name']}")
        if contextual_memory.get("has_relevant_context", False):
            logging.info(f"✅ Found {len(contextual_memory.get('relevant_diary_events', []))} relevant diary events")
    except Exception as e:
        logging.warning(f"⚠️ Failed to get contextual memory: {e}")
        contextual_memory = {}
    
    # 7. 使用新电池风结构化服务生成运势（先算分再写文案）
    try:
        logging.info("🎯 Generating battery fortune (电池运势)")
        user_gender = get_user_gender(user_id)
        battery_fortune = await structured_fortune_service.generate_battery_fortune(
            bazi_analysis=bazi_analysis,
            tarot_reading=tarot_reading,
            user_memory=user_memory,
            contextual_memory=contextual_memory,
            user_id=user_id,
            language=user_language,
            gender=user_gender
        )
        if not battery_fortune:
            logging.error("❌ battery_fortune is empty or None!")
            raise HTTPException(status_code=500, detail="运势生成返回空结果")
        logging.info("✅ Battery fortune generation completed")
    except Exception as e:
        logging.error(f"❌ Error in battery fortune generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"运势生成失败: {str(e)}")
    
    # 8. 保存电池运势到 daily_fortune_details 表
    try:
        fortune_details_record = {
            "user_id": user_id,
            "fortune_date": today.isoformat(),
            "language": user_language,
            "is_generated": True,
            "daily_bazi": bazi_analysis,
            "daily_tarot": tarot_reading,
            "battery_fortune": battery_fortune
        }

        logging.info(f"📝 准备保存到数据库，记录字段: {list(fortune_details_record.keys())}, 语言: {user_language}")
        insert_response = supabase.table("daily_fortune_details").upsert(fortune_details_record, on_conflict="user_id,fortune_date,language").execute()
        logging.info(f"✅ 数据库保存成功: {insert_response.data}")
    except Exception as e:
        logging.error(f"❌ Failed to save fortune details: {e}", exc_info=True)
        # 不要因为数据库保存失败就中断，继续返回结果
    
    # 9. 返回新格式
    result = {
        "bazi_analysis": bazi_analysis,
        "tarot_reading": tarot_reading,
        "battery_fortune": battery_fortune,
        "from_cache": False
    }
    
    logging.info(
        f"🎉 最终返回数据: bazi={bool(bazi_analysis)}, "
        f"tarot={bool(tarot_reading)}, battery_keys={list(battery_fortune.keys())}"
    )
    
    # 保存到内存缓存
    _fortune_cache[cache_key] = {
        'data': result,
        'timestamp': datetime.now()
    }
    
    return result

@router.get("/categories/{category_type}")
async def get_category_fortune(
    category_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定分类的运势分析
    
    支持的分类类型：
    - overall: 综合运势
    - career: 事业
    - wealth: 财富
    - love: 感情
    - social: 人际
    - study: 学业
    """
    try:
        user_id = str(current_user.id)
        today = date.today()
        
        # 验证分类类型
        valid_categories = ["overall", "career", "wealth", "love", "social", "study"]
        if category_type not in valid_categories:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的分类类型。支持的类型: {', '.join(valid_categories)}"
            )
        
        # 获取用户偏好设置
        try:
            preferences_response = supabase.table("user_preferences").select("focus_areas").eq("user_id", user_id).single().execute()
            user_focus_areas = preferences_response.data.get("focus_areas", []) if preferences_response.data else []
        except Exception as e:
            logging.warning(f"获取用户偏好设置失败: {e}")
            user_focus_areas = ["overall", "career", "wealth", "love", "social", "study"]  # 默认所有领域
        
        # 检查用户是否关注该分类（整体运势总是可用的）
        if category_type != "overall" and category_type not in user_focus_areas:
            return {
                "message": f"您当前未关注{category_type}领域，请在用户设置中开启",
                "category": category_type,
                "is_focused": False,
                "suggestion": "建议在用户偏好设置中开启该领域的关注"
            }
        
        # 获取今日运势（如果存在）
        try:
            fortune_response = supabase.table("fortune_history").select("*").eq("user_id", user_id).eq("fortune_date", today.isoformat()).single().execute()
            if fortune_response.data:
                fortune_data = fortune_response.data
                # 基于今日运势生成分类运势
                category_fortune = await _generate_category_fortune(
                    category_type, 
                    fortune_data, 
                    current_user.id
                )
                return {
                    "category": category_type,
                    "content": category_fortune,
                    "is_focused": True,
                    "based_on_today": True,
                    "generated_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logging.info(f"未找到今日运势，将生成新的分类运势: {e}")
        
        # 如果没有今日运势，生成新的分类运势
        category_fortune = await _generate_new_category_fortune(
            category_type, 
            current_user, 
            user_id
        )
        
        return {
            "category": category_type,
            "content": category_fortune,
            "is_focused": True,
            "based_on_today": False,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取分类运势失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分类运势失败: {str(e)}")

async def _generate_category_fortune(
    category_type: str, 
    fortune_data: dict, 
    user_id: str
) -> str:
    """基于今日运势生成分类运势"""
    
    # 获取运势数据
    bazi_data = fortune_data.get("bazi_data", {})
    tarot_data = fortune_data.get("tarot_data", {})
    final_fortune = fortune_data.get("final_fortune", "")
    
    # 构建分类运势的Prompt
    category_prompts = {
        "overall": "整体运势",
        "career": "事业运势",
        "love": "感情运势", 
        "wealth": "财富运势",
        "study": "学业运势"
    }
    
    # 如果是整体运势，直接返回现有的运势内容
    if category_type == "overall":
        return final_fortune
    
    prompt = f"""
    基于用户的今日运势，请生成一段专门的{category_prompts[category_type]}分析。

    【今日整体运势】
    {final_fortune}

    【八字分析】
    - 日主：{bazi_data.get('day_master', '未知')}
    - 天干影响：{bazi_data.get('stem_influence', {}).get('analysis', '未知')}
    - 地支影响：{bazi_data.get('branch_influence', {}).get('analysis', '未知')}

    【塔罗启示】
    - 牌名：{tarot_data.get('card', {}).get('card_name', '未知')}
    - 正位含义：{tarot_data.get('card', {}).get('meaning_up', '未知')}
    - 逆位含义：{tarot_data.get('card', {}).get('meaning_down', '未知')}

    【任务要求】
    请专门针对{category_prompts[category_type]}，结合上述运势信息，生成一段100-150字的专业分析。
    要求：
    1. 专注于{category_prompts[category_type]}的具体表现
    2. 结合八字和塔罗的启示
    3. 给出实用的建议和指导
    4. 语调要温暖、专业、有指导性
    """
    
    try:
        # 使用知识库增强生成
        fortune_context = f"{category_prompts[category_type]} {category_type} 运势分析"
        category_fortune = await genai_service.generate_text(prompt)
        return category_fortune
    except Exception as e:
        logging.error(f"生成分类运势失败: {e}")
        return f"基于今日运势，{category_prompts[category_type]}分析生成失败，请稍后再试。"

async def _generate_new_category_fortune(
    category_type: str, 
    current_user: User, 
    user_id: str
) -> str:
    """生成新的分类运势（当没有今日运势时）"""
    
    try:
        # 获取用户生日
        birth_date = current_user.birth_date
        if not birth_date:
            return "请先设置生日信息以获取个性化运势分析"

        # 获取八字分析
        today = date.today()

        # 获取用户语言偏好
        try:
            pref_response = supabase.table("user_preferences").select("preferred_language").eq("user_id", user_id).single().execute()
            user_language = pref_response.data.get("preferred_language", "zh-CN") if pref_response.data else "zh-CN"
        except Exception:
            user_language = "zh-CN"

        bazi_analysis = bazi_service.analyze_daily_flow(birth_date, target_date=today, language=user_language)

        # 获取塔罗牌
        tarot_reading = tarot_service.draw_daily_card(user_id, today, user_language)
        
        # 获取用户记忆
        try:
            user_memory = await get_memory(current_user.id)
        except Exception as e:
            logging.warning(f"⚠️ 获取用户记忆失败: {e}")
            user_memory = {}
        
        # 获取日记上下文
        try:
            contextual_memory = await get_contextual_memory(user_id, f"{bazi_analysis['day_master']} {tarot_reading['card']['card_name']}")
        except Exception as e:
            logging.warning(f"⚠️ 获取日记上下文失败: {e}")
            contextual_memory = {}
        
        # 使用电池运势生成，再取对应领域
        logging.info(f"🔄 Generating battery fortune for: {category_type}")
        user_gender = get_user_gender(user_id)
        battery_fortune = await structured_fortune_service.generate_battery_fortune(
            bazi_analysis=bazi_analysis,
            tarot_reading=tarot_reading,
            user_memory=user_memory,
            contextual_memory=contextual_memory,
            user_id=user_id,
            language=user_language,
            gender=user_gender
        )
        
        if category_type == 'overall':
            overall = battery_fortune.get('overall', {})
            return "\n".join([
                overall.get('date_line', ''),
                overall.get('daily_management', ''),
                f"快充：{overall.get('fast_charge', '')}",
                f"省电：{overall.get('power_saving', '')}",
                f"耗电：{overall.get('power_drain', '')}",
                f"护电：{overall.get('surge_protection', '')}",
                f"回电：{overall.get('recharge', '')}"
            ]).strip()

        domain = battery_fortune.get(category_type)
        if not domain:
            logging.error(f"❌ Category {category_type} not found in battery fortune")
            return f"暂无 {category_type} 运势"

        return "\n".join([
            domain.get('title_line', ''),
            f"状态：{domain.get('status', '')}",
            f"充电：{domain.get('charge_action', '')}",
            f"漏电：{domain.get('drain_warning', '')}"
        ]).strip()
    except Exception as e:
        logging.error(f"❌ 生成分类运势失败: {e}")
        return f"生成{category_type}运势时发生错误，请稍后重试"

def _format_fortune_list_response(data: list) -> list: # 格式化运势列表响应
    """将数据库记录转换为前端列表格式（只返回实际存在的类别）"""
    if not data:
        return []
    
    result = []
    for record in data:
        result.append({
            "bazi_analysis": record.get("daily_bazi"),
            "tarot_reading": record.get("daily_tarot"),
            "battery_fortune": record.get("battery_fortune"),
            "fortune_date": record.get("fortune_date"),
            "from_cache": True
        })
    return result

def _build_memory_context(user_memory: dict) -> str:
    """构建用户记忆上下文，使用时间感知的近期事件提取"""
    if not user_memory:
        return ""
    
    # 使用新的时间感知提取方法
    recent_context = extract_recent_context(user_memory)
    recent_concerns = recent_context["recent_concerns"]
    future_events = recent_context["future_events"]
    personality = recent_context["personality"]
    goals = recent_context["goals"]
    
    if recent_concerns or future_events or personality or goals:
        # 添加时间范围说明
        recent_info = f"近期关注(最近30天)" if recent_concerns else "近期关注"
        future_info = f"即将面临(未来60天)" if future_events else "即将面临"
        
        return f"""
    【用户个人情况】
    - 个性特质: {personality if personality else '暂无记录'}
    - {recent_info}: {', '.join(recent_concerns) if recent_concerns else '暂无记录'}
    - {future_info}: {', '.join(future_events) if future_events else '暂无记录'}
    - 目标方向: {', '.join(goals) if goals else '暂无记录'}
    """
    return ""

@router.get("/history")
async def get_fortune_history(
    use_mock: bool = Query(False, description="使用mock数据（开发模式）"),
    limit: int = Query(7, le=30, description="返回记录数量限制"),
    local_date: Optional[str] = Query(None, description="前端本地日期（格式：YYYY-MM-DD）"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """获取用户运势历史记录（最近N天），返回完整运势数据用于列表展示"""
    if local_date: # 使用前端传递的本地日期
        try:
            today = datetime.strptime(local_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    else:
        today = date.today() # 后端服务器日期（fallback）
    
    # Mock模式：返回mock用户的运势历史
    if use_mock:
        logging.info(f"🧪 Mock模式：获取mock用户运势历史")
        mock_user_id = "11111111-1111-1111-1111-111111111111"
        try:
            query = supabase.table("daily_fortune_details").select("*").eq("user_id", mock_user_id).lte("fortune_date", today.isoformat()).order("fortune_date", desc=True).limit(limit)
            response = query.execute()
            return _format_fortune_list_response(response.data)
        except Exception as e:
            logging.warning(f"⚠️ Mock模式获取历史失败: {e}")
            return []
    
    # 非Mock模式需要认证
    if not credentials:
        raise HTTPException(status_code=401, detail="需要认证")
    
    current_user = await get_current_user(credentials)
    user_id = str(current_user.id)
    
    try:
        query = supabase.table("daily_fortune_details").select("*").eq("user_id", user_id).lte("fortune_date", today.isoformat()).order("fortune_date", desc=True).limit(limit)
        response = query.execute()
        return _format_fortune_list_response(response.data)
    except Exception as e:
        logging.error(f"获取运势历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取运势历史失败: {str(e)}")

@router.get("/history/{fortune_id}")
async def get_fortune_detail(
    fortune_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定运势记录的详细信息
    """
    try:
        user_id = str(current_user.id)
        
        # 查询运势记录
        response = supabase.table("fortune_history").select("*").eq("id", str(fortune_id)).eq("user_id", user_id).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="运势记录未找到")
        
        fortune_data = response.data
        
        # 返回完整的运势信息
        return {
            "id": fortune_data.get("id"),
            "fortune_date": fortune_data.get("fortune_date"),
            "bazi_analysis": fortune_data.get("bazi_data"),
            "tarot_reading": fortune_data.get("tarot_data"),
            "final_fortune": fortune_data.get("final_fortune"),
            "enhanced": fortune_data.get("enhanced", False),
            "personalized": fortune_data.get("personalized", False),
            "relevant_events_count": fortune_data.get("relevant_events_count", 0),
            "created_at": fortune_data.get("created_at"),
            "updated_at": fortune_data.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取运势详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取运势详情失败: {str(e)}")

@router.get("/stats")
async def get_fortune_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取用户运势统计信息
    
    包括：
    - 总运势记录数
    - 本月运势记录数
    - 运势类型统计
    - 运势趋势分析
    """
    try:
        user_id = str(current_user.id)
        today = date.today()
        
        # 获取总记录数
        total_response = supabase.table("fortune_history").select("id", count="exact").eq("user_id", user_id).execute()
        total_count = total_response.count if hasattr(total_response, 'count') else 0
        
        # 获取本月记录数
        month_start = date(today.year, today.month, 1)
        month_response = supabase.table("fortune_history").select("id", count="exact").eq("user_id", user_id).gte("fortune_date", month_start.isoformat()).execute()
        month_count = month_response.count if hasattr(month_response, 'count') else 0
        
        # 获取运势类型统计
        enhanced_response = supabase.table("fortune_history").select("id", count="exact").eq("user_id", user_id).eq("enhanced", True).execute()
        enhanced_count = enhanced_response.count if hasattr(enhanced_response, 'count') else 0
        
        personalized_response = supabase.table("fortune_history").select("id", count="exact").eq("user_id", user_id).eq("personalized", True).execute()
        personalized_count = personalized_response.count if hasattr(personalized_response, 'count') else 0
        
        # 计算百分比
        enhanced_percentage = (enhanced_count / total_count * 100) if total_count > 0 else 0
        personalized_percentage = (personalized_count / total_count * 100) if total_count > 0 else 0
        
        # 获取最近7天的运势记录（用于趋势分析）
        week_ago = today - timedelta(days=7)
        recent_response = supabase.table("fortune_history").select("fortune_date, enhanced, personalized").eq("user_id", user_id).gte("fortune_date", week_ago.isoformat()).order("fortune_date", desc=True).execute()
        
        recent_records = recent_response.data if recent_response.data else []
        recent_enhanced = sum(1 for record in recent_records if record.get("enhanced"))
        recent_personalized = sum(1 for record in recent_records if record.get("personalized"))
        
        return {
            "total_records": total_count,
            "monthly_records": month_count,
            "enhanced_count": enhanced_count,
            "enhanced_percentage": round(enhanced_percentage, 1),
            "personalized_count": personalized_count,
            "personalized_percentage": round(personalized_percentage, 1),
            "recent_week": {
                "total": len(recent_records),
                "enhanced": recent_enhanced,
                "personalized": recent_personalized
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"获取运势统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取运势统计失败: {str(e)}")


@router.get("/tarot-cards", response_model=Dict[str, Any])
async def get_tarot_cards(
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    获取所有塔罗牌数据（用于前端抽卡）

    返回格式：
    {
        "cards": [
            {
                "id": 1,
                "card_name": "愚者",
                "arcana_type": "major",
                "suit": null,
                "meaning_up": "...",
                "meaning_down": "...",
                "keywords": [...],
                "description": "..."
            },
            ...
        ],
        "total": 78,
        "language": "zh-CN"
    }
    """
    try:
        # 获取语言偏好
        user_language = get_user_language(None, accept_language)

        # 获取所有塔罗牌
        cards = tarot_service.get_all_cards(language=user_language)

        logging.info(f"✅ 返回 {len(cards)} 张塔罗牌数据，语言: {user_language}")

        return {
            "cards": cards,
            "total": len(cards),
            "language": user_language
        }

    except Exception as e:
        logging.error(f"❌ 获取塔罗牌列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取塔罗牌列表失败: {str(e)}")


@router.get("/tarot/draw-daily", response_model=Dict[str, Any])
async def draw_daily_tarot_card(
    local_date: Optional[str] = Query(None, description="前端本地日期（格式：YYYY-MM-DD）"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    current_user: User = Depends(get_current_user)
):
    """
    抽取每日塔罗牌（后端抽卡）

    返回格式：
    {
        "card": {
            "id": 15,
            "card_name": "恶魔",
            "arcana_type": "major",
            ...
        },
        "orientation": "upright" | "reversed",
        "image_key": "tarot_15_upright"
    }
    """
    try:
        user_id = current_user.id

        # 获取日期
        if local_date:
            try:
                today = datetime.strptime(local_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
        else:
            today = date.today()

        # 获取语言偏好
        user_language = get_user_language(user_id, accept_language)

        # 调用抽卡服务
        tarot_reading = tarot_service.draw_daily_card(user_id, today, user_language)

        logging.info(f"✅ 用户 {user_id} 抽取每日塔罗牌成功: {tarot_reading.get('image_key')}")

        return tarot_reading

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ 抽取每日塔罗牌失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"抽取每日塔罗牌失败: {str(e)}")