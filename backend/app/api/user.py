import os
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import Dict, Any, List
from datetime import date, datetime, timedelta, timezone
import logging
import base64

from ..models.user import User
from ..models.fortune import UserProfileUpdate, UserPreferencesUpdate, ReminderSettingsUpdate, OnboardingData
from .auth import get_current_user
from ..core.db import supabase

router = APIRouter()
logging.basicConfig(level=logging.INFO)

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """获取用户完整档案信息（包含所有数据：基本信息、统计、偏好、提醒设置）"""
    try:
        user_id = str(current_user.id)
        user_email = current_user.email # 直接从current_user获取email
        logging.info(f"\n{'='*80}")
        logging.info(f"[GET_PROFILE] 🔍 开始获取用户档案")
        logging.info(f"[GET_PROFILE] 👤 当前登录用户: ID={user_id}, Email={user_email}")
        
        # 获取用户档案信息（从 profiles 表）
        try:
            profile_response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            profile_data = profile_response.data if profile_response.data else {}
        except Exception as e:
            logging.warning(f"[GET_PROFILE] ⚠️ 用户档案不存在，返回空档案: {e}")
            profile_data = {}
        logging.info(f"[GET_PROFILE] 📋 档案数据: {profile_data}")
        
        # 获取用户偏好设置（从 fortune_categories 字段或 user_preferences 表）
        user_focus_areas = profile_data.get("fortune_categories", ["overall", "career", "love", "wealth", "study", "health"])
        
        # 获取提醒设置和隐私设置
        reminder_settings = {}
        privacy_settings = {}
        try:
            preferences_response = supabase.table("user_preferences").select("*").eq("user_id", user_id).maybe_single().execute()
            if preferences_response and preferences_response.data:
                logging.info(f"[GET_PROFILE] ⚙️ 偏好设置数据: {preferences_response.data}")

                # 注意：不再使用 user_preferences.focus_areas 字段（已废弃）
                # 关注领域统一从 profiles.fortune_categories 读取（第37行）
                # 该字段通过 PUT /api/user/preferences 接口更新到 profiles.fortune_categories
                # 旧版本的 focus_areas 数据可能存在但不再使用，避免数据不一致

                if preferences_response.data.get("reminder_settings"):
                    reminder_settings = preferences_response.data.get("reminder_settings")
                if preferences_response.data.get("privacy_settings"):
                    privacy_settings = preferences_response.data.get("privacy_settings")
        except Exception as e:
            logging.warning(f"[GET_PROFILE] ⚠️ 获取用户偏好设置失败，使用默认值: {e}")
        
        # 如果没有提醒设置，使用默认值
        if not reminder_settings:
            reminder_settings = {
                "fortuneReminder": {"isEnabled": True, "time": "08:00:00", "days": [1,2,3,4,5,6,7]},
                "diaryReminder": {"isEnabled": True, "time": "21:00:00", "days": [1,2,3,4,5,6,7]},
                "summaryReminder": {"isEnabled": True, "time": "20:00:00", "days": [7]}
            }

        # 如果没有隐私设置，使用默认值
        if not privacy_settings:
            privacy_settings = {
                "isProfilePublic": False,
                "allowDataAnalysis": True,
                "shareUsageStats": False
            }
        
        # 获取用户使用统计
        stats = await _calculate_user_stats(user_id)
        logging.info(f"[GET_PROFILE] 📊 使用统计: {stats}")
        
        # 解析出生时间和日期 - 数据库格式: "1996-02-16 10:50:00"
        birth_datetime = profile_data.get("birth_datetime")
        if birth_datetime:
            # 将空格替换为T，转为ISO格式: "1996-02-16T10:50:00"
            birthTime = birth_datetime.replace(" ", "T")
            birthday = birth_datetime.split(" ")[0]  # 提取日期部分
            logging.info(f"[GET_PROFILE] 🎂 生日数据: 原始={birth_datetime}, birthTime={birthTime}, birthday={birthday}")
        else:
            birthTime = None
            birthday = None
        
        # 构建完整的用户档案（直接返回数据库字段名，不做转换）
        logging.info(f"[GET_PROFILE] 🔍 full_name from DB: '{profile_data.get('full_name')}'")
        logging.info(f"[GET_PROFILE] 🔍 avatar_url from DB: '{profile_data.get('avatar_url')}'")

        profile = {
            "id": user_id,
            "email": user_email,
            "username": profile_data.get("username"),
            "full_name": profile_data.get("full_name", ""),
            "avatar_url": profile_data.get("avatar_url"),
            "birth_datetime": profile_data.get("birth_datetime"),
            "birth_location": profile_data.get("birth_location"),
            "birth_timezone": profile_data.get("birth_timezone"),
            "timezone": profile_data.get("timezone", "Asia/Shanghai"),
            "gender": profile_data.get("gender"),
            "fortune_categories": profile_data.get("fortune_categories", ["overall", "career", "love", "wealth", "study", "health"]),
            "custom_voice_id": profile_data.get("custom_voice_id"),
            "is_time_unknown": profile_data.get("is_time_unknown", False),
            "created_at": profile_data.get("created_at"),
            "updated_at": profile_data.get("updated_at"),
            "onboarding_data": profile_data.get("onboarding_data"),
            "usageStats": stats,
            "preferences": {
                "focusAreas": user_focus_areas,
                "reminderSettings": reminder_settings,
                "privacySettings": privacy_settings
            }
        }
        
        logging.info(f"[GET_PROFILE] ✅ 用户档案构建完成")
        logging.info(f"[GET_PROFILE] 📦 返回数据: {profile}")
        logging.info(f"{'='*80}\n")
        return profile
        
    except Exception as e:
        logging.error(f"[GET_PROFILE] ❌ 获取用户档案失败: user_id={user_id}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取用户档案失败: {str(e)}")

@router.put("/profile")
async def update_user_profile(
    profile_update: UserProfileUpdate, 
    current_user: User = Depends(get_current_user)
):
    """更新用户档案信息 - 更新 profiles 表"""
    try:
        user_id = str(current_user.id)
        logging.info(f"[UPDATE_PROFILE] 更新用户档案: user_id={user_id}")
        logging.debug(f"[UPDATE_PROFILE] 接收到的数据: {profile_update.dict()}")
        
        # 构建更新数据（映射到 profiles 表字段）
        update_data = {}

        if profile_update.full_name is not None:
            update_data["full_name"] = profile_update.full_name
        
        if profile_update.gender is not None:
            # Frontend should send 'male', 'female', or 'other' (English only)
            update_data["gender"] = profile_update.gender
        
        # 处理生日和出生时间 - 合并为 birth_datetime（保留用户输入的原始时间，不进行时区转换）
        if profile_update.birthYear and profile_update.birthMonth and profile_update.birthDay:
            year = profile_update.birthYear
            month = profile_update.birthMonth.zfill(2)
            day = profile_update.birthDay.zfill(2)
            
            if profile_update.isTimeUnknown or not profile_update.birthHour:
                update_data["birth_datetime"] = f"{year}-{month}-{day}T12:00:00" # 时辰不详，使用午时
                update_data["is_time_unknown"] = True
            else:
                hour = profile_update.birthHour.zfill(2)
                minute = (profile_update.birthMinute or "0").zfill(2)
                update_data["birth_datetime"] = f"{year}-{month}-{day}T{hour}:{minute}:00"
                update_data["is_time_unknown"] = False
        
        # 处理出生地点
        if profile_update.birthLocation:
            update_data["birth_location"] = profile_update.birthLocation
        
        # 存储出生地时区名称（用于显示）
        if profile_update.birthTimezone:
            update_data["birth_timezone"] = profile_update.birthTimezone
        
        if profile_update.timezone is not None:
            update_data["timezone"] = profile_update.timezone
        
        # 更新 profiles 表
        if update_data:
            update_data["updated_at"] = datetime.utcnow().isoformat()

            # 首先检查 profile 是否存在并获取旧数据
            check_response = supabase.table("profiles").select("*").eq("id", user_id).execute()

            old_profile_data = check_response.data[0] if check_response.data else {}

            if not check_response.data:
                # Profile 不存在，创建新的
                update_data["id"] = user_id
                response = supabase.table("profiles").insert(update_data).execute()
            else:
                # Profile 存在，更新
                response = supabase.table("profiles").update(update_data).eq("id", user_id).execute()

            if not response.data:
                raise HTTPException(status_code=500, detail="更新档案失败")

            # 记录档案更新
            if old_profile_data:
                from ..services.daily_activity_service import daily_activity_service
                asyncio.create_task(
                    daily_activity_service.record_profile_update(user_id, old_profile_data, update_data)
                )

        logging.info(f"[UPDATE_PROFILE] 用户档案更新成功: user_id={user_id}, fields={list(update_data.keys())}")
        return {"message": "用户档案更新成功", "updated_fields": list(update_data.keys())}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[UPDATE_PROFILE] 更新用户档案失败: user_id={current_user.id if current_user else 'unknown'}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新用户档案失败: {str(e)}")

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """上传用户头像到 Supabase Storage"""
    try:
        user_id = str(current_user.id)
        logging.info(f"[UPLOAD_AVATAR] 开始上传头像: user_id={user_id}, filename={file.filename}")

        # 验证文件类型
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.content_type}。仅支持 JPEG, PNG, WebP"
            )

        # 读取文件内容
        file_content = await file.read()

        # 验证文件大小（最大 5MB）
        max_size = 5 * 1024 * 1024  # 5MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大: {len(file_content)} bytes。最大允许 5MB"
            )

        # 生成文件名（使用用户ID文件夹 + 时间戳文件名，符合RLS策略）
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        storage_filename = f"{user_id}/avatar_{timestamp}.{file_extension}"  # 格式: {user_id}/avatar_{timestamp}.jpg
        storage_path = f"avatars/{storage_filename}"

        logging.info(f"[UPLOAD_AVATAR] 上传到 Storage: {storage_path}")

        # 上传到 Supabase Storage
        try:
            # 删除旧头像（如果存在）
            profile_response = supabase.table("profiles").select("avatar_url").eq("id", user_id).single().execute()
            if profile_response.data and profile_response.data.get("avatar_url"):
                old_avatar_url = profile_response.data["avatar_url"]
                # 从 URL 中提取文件路径（格式: {user_id}/avatar_{timestamp}.jpg）
                if "/object/public/avatars/" in old_avatar_url:
                    # 提取 avatars/ 后面的完整路径
                    old_path = old_avatar_url.split("/object/public/avatars/")[-1].split("?")[0]
                    try:
                        supabase.storage.from_("avatars").remove([old_path])
                        logging.info(f"[UPLOAD_AVATAR] 已删除旧头像: {old_path}")
                    except Exception as e:
                        logging.warning(f"[UPLOAD_AVATAR] 删除旧头像失败（可能不存在）: {e}")

            # 上传新头像
            upload_response = supabase.storage.from_("avatars").upload(
                path=storage_filename,
                file=file_content,
                file_options={"content-type": file.content_type}
            )

            logging.info(f"[UPLOAD_AVATAR] Storage 上传响应: {upload_response}")

            # 获取公开 URL
            public_url = supabase.storage.from_("avatars").get_public_url(storage_filename)
            logging.info(f"[UPLOAD_AVATAR] 公开 URL: {public_url}")

        except Exception as storage_error:
            logging.error(f"[UPLOAD_AVATAR] Storage 上传失败: {storage_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"上传到存储失败: {str(storage_error)}"
            )

        # 更新数据库中的头像 URL
        try:
            update_data = {
                "avatar_url": public_url,
                "updated_at": datetime.utcnow().isoformat()
            }

            # 检查 profile 是否存在
            check_response = supabase.table("profiles").select("id").eq("id", user_id).execute()

            if not check_response.data:
                # Profile 不存在，创建新的
                update_data["id"] = user_id
                db_response = supabase.table("profiles").insert(update_data).execute()
            else:
                # Profile 存在，更新
                db_response = supabase.table("profiles").update(update_data).eq("id", user_id).execute()

            if not db_response.data:
                raise HTTPException(status_code=500, detail="更新数据库失败")

            logging.info(f"[UPLOAD_AVATAR] 数据库更新成功: avatar_url={public_url}")

        except HTTPException:
            raise
        except Exception as db_error:
            logging.error(f"[UPLOAD_AVATAR] 数据库更新失败: {db_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"更新数据库失败: {str(db_error)}"
            )

        logging.info(f"[UPLOAD_AVATAR] ✅ 头像上传成功: user_id={user_id}, url={public_url}")
        return {
            "message": "头像上传成功",
            "avatar_url": public_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[UPLOAD_AVATAR] 上传头像失败: user_id={current_user.id if current_user else 'unknown'}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传头像失败: {str(e)}")


def build_initial_profile_text(
    full_name: str,
    gender: str,
    birth_year: str,
    birth_month: str,
    birth_day: str,
    onboarding_data: dict
) -> str:
    """将 onboarding 数据转换为自然语言，作为 Letta 的初始画像"""

    # 定义映射字典
    gender_map = {"male": "男性", "female": "女性", "other": "其他"}
    region_map = {"china": "中国", "usa": "美国", "canada": "加拿大", "other": "其他地区"}
    work_type_map = {"fulltime": "全职", "parttime": "兼职", "freelance": "自由职业", "startup": "创业中"}
    industry_map = {
        "tech": "科技互联网", "finance": "金融商业", "health": "医疗健康",
        "creative": "创意媒体", "edu": "教育科研", "other": "其他"
    }
    role_map = {
        "engineer": "工程技术", "product": "产品策划", "design": "设计创意",
        "marketing": "营销运营", "sales": "销售商务", "admin": "管理行政", "other": "其他"
    }
    rhythm_map = {"remote": "居家线上", "onsite": "现场线下", "hybrid": "混合模式", "travel": "经常出差"}
    relationship_map = {"single": "单身", "dating": "约会中", "partnered": "稳定关系", "complex": "一言难尽"}
    income_map = {"salary": "固定薪资", "bonus": "奖金提成", "invest": "投资理财", "side": "副业收入", "other": "其他"}
    student_focus_map = {
        "study": "课业学习", "job": "找工作实习", "skill": "技能提升",
        "network": "社交人脉", "balance": "生活平衡", "explore": "探索方向"
    }

    lines = []

    # 基本信息
    if full_name:
        lines.append(f"我叫{full_name}，")
    if gender:
        lines.append(f"性别{gender_map.get(gender, gender)}，")
    if birth_year and birth_month and birth_day:
        lines.append(f"生日是{birth_year}年{birth_month}月{birth_day}日。")

    # 地区
    if "region" in onboarding_data:
        region = onboarding_data["region"]
        lines.append(f"我生活在{region_map.get(region, region)}。")

    # 状态（学生/在职）
    if "status" in onboarding_data:
        status = onboarding_data["status"]
        if status == "student":
            lines.append("我目前是学生。")

            # 学生路径：未来想从事的行业
            if "student_industry" in onboarding_data:
                industries = onboarding_data["student_industry"]
                if isinstance(industries, list) and industries:
                    industry_names = [industry_map.get(ind, ind) for ind in industries]
                    lines.append(f"未来想从事：{', '.join(industry_names)}。")

            # 学生路径：当前关注
            if "student_focus" in onboarding_data:
                focus = onboarding_data["student_focus"]
                if isinstance(focus, list) and focus:
                    focus_names = [student_focus_map.get(f, f) for f in focus]
                    lines.append(f"现在更关注：{', '.join(focus_names)}。")

            # 学生的感情状态
            if "relationship_student" in onboarding_data:
                relationship = onboarding_data["relationship_student"]
                if isinstance(relationship, list) and relationship:
                    rel_names = [relationship_map.get(r, r) for r in relationship]
                    lines.append(f"感情状态：{', '.join(rel_names)}。")

        elif status == "working":
            lines.append("我目前在职。")

            # 在职路径：工作类型
            if "work_type" in onboarding_data:
                work_types = onboarding_data["work_type"]
                if isinstance(work_types, list) and work_types:
                    type_names = [work_type_map.get(wt, wt) for wt in work_types]
                    lines.append(f"工作类型：{', '.join(type_names)}。")

            # 在职路径：所在行业
            if "industry" in onboarding_data:
                industries = onboarding_data["industry"]
                if isinstance(industries, list) and industries:
                    industry_names = [industry_map.get(ind, ind) for ind in industries]
                    lines.append(f"所在行业：{', '.join(industry_names)}。")

            # 在职路径：主要职责
            if "role" in onboarding_data:
                roles = onboarding_data["role"]
                if isinstance(roles, list) and roles:
                    role_names = [role_map.get(r, r) for r in roles]
                    lines.append(f"主要职责：{', '.join(role_names)}。")

            # 在职路径：日常节奏
            if "rhythm" in onboarding_data:
                rhythms = onboarding_data["rhythm"]
                if isinstance(rhythms, list) and rhythms:
                    rhythm_names = [rhythm_map.get(rh, rh) for rh in rhythms]
                    lines.append(f"日常节奏：{', '.join(rhythm_names)}。")

            # 在职的感情状态
            if "relationship_working" in onboarding_data:
                relationship = onboarding_data["relationship_working"]
                if isinstance(relationship, list) and relationship:
                    rel_names = [relationship_map.get(r, r) for r in relationship]
                    lines.append(f"感情状态：{', '.join(rel_names)}。")

            # 在职路径：收入来源
            if "income" in onboarding_data:
                incomes = onboarding_data["income"]
                if isinstance(incomes, list) and incomes:
                    income_names = [income_map.get(inc, inc) for inc in incomes]
                    lines.append(f"收入来源：{', '.join(income_names)}。")

    result = "".join(lines)
    return result if result else "用户完成了基本信息填写。"

@router.post("/onboarding")
async def complete_onboarding(
    onboarding_data: OnboardingData,
    current_user: User = Depends(get_current_user)
):
    """完成用户Onboarding - 一次性保存所有用户信息（最佳实践）"""
    try:
        user_id = str(current_user.id)
        logging.info(f"[ONBOARDING] 开始处理用户Onboarding: user_id={user_id}")
        logging.debug(f"[ONBOARDING] 接收到的数据: {onboarding_data.dict()}")
        
        updated_sections = []
        
        # 1. 更新个人信息到 profiles 表
        profile_data = {}
        if onboarding_data.full_name:
            profile_data["full_name"] = onboarding_data.full_name
        if onboarding_data.gender:
            profile_data["gender"] = onboarding_data.gender
        
        # 处理生日和出生时间
        if onboarding_data.birthYear and onboarding_data.birthMonth and onboarding_data.birthDay:
            year = onboarding_data.birthYear
            month = onboarding_data.birthMonth.zfill(2)
            day = onboarding_data.birthDay.zfill(2)
            
            if onboarding_data.isTimeUnknown or not onboarding_data.birthHour:
                profile_data["birth_datetime"] = f"{year}-{month}-{day}T12:00:00" # 时辰不详，使用午时
                profile_data["is_time_unknown"] = True
            else:
                hour = onboarding_data.birthHour.zfill(2)
                minute = (onboarding_data.birthMinute or "0").zfill(2)
                profile_data["birth_datetime"] = f"{year}-{month}-{day}T{hour}:{minute}:00"
                profile_data["is_time_unknown"] = False
        
        # 处理出生地点
        if onboarding_data.birthLocation:
            profile_data["birth_location"] = onboarding_data.birthLocation
        
        # 存储出生地时区名称
        if onboarding_data.birthTimezone:
            profile_data["birth_timezone"] = onboarding_data.birthTimezone
        
        if onboarding_data.timezone:
            profile_data["timezone"] = onboarding_data.timezone

        # 2. 更新关注领域到 profiles 表
        if onboarding_data.focusAreas:
            valid_categories = ["overall", "career", "love", "wealth", "study", "health"]
            mapped_categories = [cat for cat in onboarding_data.focusAreas if cat in valid_categories]
            if mapped_categories:
                profile_data["fortune_categories"] = mapped_categories

        # 3. 存储额外的问卷数据到 onboarding_data JSONB 字段
        if onboarding_data.onboarding_data:
            profile_data["onboarding_data"] = onboarding_data.onboarding_data
            logging.info(f"[ONBOARDING] 存储额外问卷数据: {list(onboarding_data.onboarding_data.keys())}")

        # 更新 profiles 表
        if profile_data:
            profile_data["updated_at"] = datetime.utcnow().isoformat()
            check_response = supabase.table("profiles").select("*").eq("id", user_id).execute()

            old_profile_data = check_response.data[0] if check_response.data else {}

            if not check_response.data:
                profile_data["id"] = user_id
                supabase.table("profiles").insert(profile_data).execute()
            else:
                supabase.table("profiles").update(profile_data).eq("id", user_id).execute()

            # 记录档案更新
            if old_profile_data:
                from ..services.daily_activity_service import daily_activity_service
                asyncio.create_task(
                    daily_activity_service.record_profile_update(user_id, old_profile_data, profile_data)
                )

            updated_sections.append("profile")
            logging.info(f"[ONBOARDING] 个人信息更新成功: user_id={user_id}")

        # 4. 更新提醒设置到 user_preferences 表
        if onboarding_data.reminderSettings:
            reminder_data = {}
            
            if onboarding_data.reminderSettings.fortuneReminder:
                reminder_data["fortuneReminder"] = onboarding_data.reminderSettings.fortuneReminder.dict()
            if onboarding_data.reminderSettings.diaryReminder:
                reminder_data["diaryReminder"] = onboarding_data.reminderSettings.diaryReminder.dict()
            if onboarding_data.reminderSettings.summaryReminder:
                reminder_data["summaryReminder"] = onboarding_data.reminderSettings.summaryReminder.dict()
            
            if reminder_data:
                pref_check = supabase.table("user_preferences").select("id").eq("user_id", user_id).execute()
                
                if not pref_check.data:
                    supabase.table("user_preferences").insert({
                        "user_id": user_id,
                        "reminder_settings": reminder_data
                    }).execute()
                else:
                    supabase.table("user_preferences").update({
                        "reminder_settings": reminder_data,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("user_id", user_id).execute()
                
                updated_sections.append("reminders")
                logging.info(f"[ONBOARDING] 提醒设置更新成功: user_id={user_id}")

        # 5. 初始化 Letta 用户画像（异步后台任务）
        if onboarding_data.onboarding_data:
            try:
                from ..services.letta_service import letta_service
                import asyncio

                # 构建初始画像文本
                initial_profile = build_initial_profile_text(
                    full_name=onboarding_data.full_name or "",
                    gender=onboarding_data.gender or "",
                    birth_year=onboarding_data.birthYear or "",
                    birth_month=onboarding_data.birthMonth or "",
                    birth_day=onboarding_data.birthDay or "",
                    onboarding_data=onboarding_data.onboarding_data
                )

                logging.info(f"[ONBOARDING] 准备初始化 Letta 画像: user_id={user_id}")
                logging.debug(f"[ONBOARDING] 初始画像文本: {initial_profile}")

                # 后台任务喂入 Letta（不阻塞主流程）
                async def ingest_to_letta():
                    try:
                        await letta_service.ingest_diary(
                            user_id=user_id,
                            diary_text=initial_profile,
                            diary_date=None
                        )
                        logging.info(f"✅ [ONBOARDING] Letta 初始画像已创建: user_id={user_id}")
                    except Exception as e:
                        logging.warning(f"⚠️ [ONBOARDING] Letta 初始化失败（不影响主流程）: {e}")

                asyncio.create_task(ingest_to_letta())
                updated_sections.append("letta_profile")

            except Exception as letta_error:
                logging.warning(f"⚠️ [ONBOARDING] Letta 初始化失败（不影响主流程）: {letta_error}")

        logging.info(f"[ONBOARDING] Onboarding完成: user_id={user_id}, updated_sections={updated_sections}")
        return {
            "message": "Onboarding完成",
            "updated_sections": updated_sections,
            "success": True
        }
        
    except Exception as e:
        logging.error(f"[ONBOARDING] Onboarding处理失败: user_id={current_user.id if current_user else 'unknown'}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Onboarding处理失败: {str(e)}")

@router.get("/stats")
async def get_user_stats(current_user: User = Depends(get_current_user)):
    """获取用户使用统计"""
    try:
        user_id = str(current_user.id)
        stats = await _calculate_user_stats(user_id)
        return stats
        
    except Exception as e:
        logging.error(f"获取用户统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户统计失败: {str(e)}")

@router.put("/preferences")
async def update_user_preferences(
    preferences: UserPreferencesUpdate, 
    current_user: User = Depends(get_current_user)
):
    """更新用户偏好设置 - 更新 profiles 表的 fortune_categories"""
    try:
        user_id = str(current_user.id)
        logging.info(f"[UPDATE_PREFERENCES] 更新用户偏好: user_id={user_id}")
        logging.debug(f"[UPDATE_PREFERENCES] 接收到的数据: {preferences.dict()}")
        
        # 如果有 focusAreas，更新 profiles 表的 fortune_categories
        if preferences.focusAreas:
            # 前端应该直接发送英文: ["career", "wealth", "love", "health", "study"]
            # 过滤有效的类别
            valid_categories = ["overall", "career", "love", "wealth", "study", "health"]
            mapped_categories = [cat for cat in preferences.focusAreas if cat in valid_categories]
            
            # 如果没有有效类别，使用默认值
            if not mapped_categories:
                mapped_categories = ["overall", "career", "love", "wealth", "study", "health"]
            
            # 更新 profiles 表
            update_data = {
                "fortune_categories": mapped_categories,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 检查 profile 是否存在（通常由触发器创建）
            check_response = supabase.table("profiles").select("id").eq("id", user_id).execute()
            
            if not check_response.data:
                # Profile 不存在，创建新的（fallback，正常不应该到这里）
                update_data["id"] = user_id
                response = supabase.table("profiles").insert(update_data).execute()
            else:
                # Profile 存在，更新
                response = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        
        # 如果有 reminderSettings 或 privacySettings，存储到 user_preferences 表
        if preferences.reminderSettings or preferences.privacySettings:
            preferences_data = {
                "user_id": user_id,
                "reminder_settings": preferences.reminderSettings.dict() if preferences.reminderSettings else {},
                "privacy_settings": preferences.privacySettings.dict() if preferences.privacySettings else {},
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # 使用upsert操作，如果不存在则创建，存在则更新
            # 指定 on_conflict 参数来处理 user_id 唯一约束冲突
            supabase.table("user_preferences").upsert(
                preferences_data,
                on_conflict="user_id"
            ).execute()
        
        logging.info(f"[UPDATE_PREFERENCES] 用户偏好更新成功: user_id={user_id}")
        return {"message": "用户偏好设置更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[UPDATE_PREFERENCES] 更新用户偏好失败: user_id={current_user.id if current_user else 'unknown'}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新用户偏好设置失败: {str(e)}")

@router.get("/reminders")
async def get_reminder_settings(current_user: User = Depends(get_current_user)):
    """获取用户提醒设置"""
    try:
        user_id = str(current_user.id)
        
        response = supabase.table("user_preferences").select("reminder_settings").eq("user_id", user_id).single().execute()
        
        if response.data and response.data.get("reminder_settings"):
            return response.data["reminder_settings"]
        else:
            # 返回默认提醒设置
            return {
                "fortuneReminder": {"isEnabled": True, "time": "08:00:00", "days": [1,2,3,4,5,6,7]},
                "diaryReminder": {"isEnabled": True, "time": "21:00:00", "days": [1,2,3,4,5,6,7]},
                "summaryReminder": {"isEnabled": True, "time": "20:00:00", "days": [7]} # 周日
            }
            
    except Exception as e:
        logging.error(f"获取提醒设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取提醒设置失败: {str(e)}")

@router.put("/reminders")
async def update_reminder_settings(
    settings: ReminderSettingsUpdate, 
    current_user: User = Depends(get_current_user)
):
    """更新用户提醒设置"""
    try:
        user_id = str(current_user.id)
        logging.info(f"[UPDATE_REMINDERS] 更新提醒设置: user_id={user_id}")
        
        # 获取现有偏好设置
        response = supabase.table("user_preferences").select("*").eq("user_id", user_id).single().execute()
        
        if response.data:
            # 更新现有设置
            current_settings = response.data.get("reminder_settings", {})
            current_settings.update(settings.dict())
            
            update_data = {
                "reminder_settings": current_settings,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("user_preferences").update(update_data).eq("user_id", user_id).execute()
        else:
            # 创建新的偏好设置
            preferences_data = {
                "user_id": user_id,
                "reminder_settings": settings.dict(),
                "focus_areas": [],
                "privacy_settings": {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("user_preferences").insert(preferences_data).execute()
        
        logging.info(f"[UPDATE_REMINDERS] 提醒设置更新成功: user_id={user_id}")
        return {"message": "提醒设置更新成功"}
        
    except Exception as e:
        logging.error(f"[UPDATE_REMINDERS] 更新提醒设置失败: user_id={user_id}, error={e}")
        raise HTTPException(status_code=500, detail=f"更新提醒设置失败: {str(e)}")

@router.post("/checkin")
async def user_checkin(current_user: User = Depends(get_current_user)):
    """用户每日签到"""
    try:
        user_id = str(current_user.id)
        today = date.today().isoformat()
        
        # 检查今日是否已签到
        checkin_response = supabase.table("user_checkins").select("*").eq("user_id", user_id).eq("checkin_date", today).single().execute()
        
        if checkin_response.data:
            raise HTTPException(status_code=400, detail="今日已签到")
        
        # 记录签到
        checkin_data = {
            "user_id": user_id,
            "checkin_date": today,
            "checkin_time": datetime.utcnow().isoformat()
        }
        
        supabase.table("user_checkins").insert(checkin_data).execute()
        
        # 更新连续签到天数
        await _update_consecutive_checkins(user_id)
        
        return {"message": "签到成功", "checkin_date": today}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"用户签到失败: {e}")
        raise HTTPException(status_code=500, detail=f"签到失败: {str(e)}")

async def _calculate_user_stats(user_id: str) -> Dict[str, Any]:
    """计算用户使用统计"""
    try:
        logging.info(f"[STATS] 📊 开始计算用户统计: user_id={user_id}")
        now_utc = datetime.now(timezone.utc) # 使用 aware datetime
        
        # 获取用户注册时间（从profiles表）
        registration_date = None
        try:
            profile_response = supabase.table("profiles").select("created_at").eq("id", user_id).single().execute()
            registration_date = profile_response.data.get("created_at") if profile_response.data else None
        except Exception as e:
            logging.warning(f"[STATS] ⚠️ 无法获取注册日期: {e}")
        logging.info(f"[STATS] 📅 注册日期: {registration_date}")
        
        # 计算总天数
        total_days = 0
        if registration_date:
            reg_date = datetime.fromisoformat(registration_date.replace('Z', '+00:00'))
            total_days = (now_utc - reg_date).days + 1
        logging.info(f"[STATS] 🔢 总使用天数: {total_days}")
        
        # 获取连续签到天数
        consecutive_checkins = await _get_consecutive_checkins(user_id)
        logging.info(f"[STATS] ✅ 连续签到天数: {consecutive_checkins}")
        
        # 获取日记统计
        diary_response = supabase.table("diary_entries").select("created_at").eq("user_id", user_id).execute()
        total_diaries = len(diary_response.data) if diary_response.data else 0
        logging.info(f"[STATS] 📖 总日记数: {total_diaries}")
        
        # 计算本月日记数
        current_month = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_diaries = 0
        if diary_response.data:
            for diary in diary_response.data:
                diary_date = datetime.fromisoformat(diary["created_at"].replace('Z', '+00:00'))
                if diary_date >= current_month:
                    monthly_diaries += 1
        logging.info(f"[STATS] 📊 本月日记数: {monthly_diaries}")
        
        # 获取对话统计
        chat_response = supabase.table("chat_messages").select("id").eq("user_id", user_id).execute()
        total_conversations = len(chat_response.data) if chat_response.data else 0
        logging.info(f"[STATS] 💬 总对话数: {total_conversations}")
        
        # 获取总字数
        total_words = 0
        if diary_response.data:
            for diary in diary_response.data:
                content = diary.get("content", "")
                total_words += len(content)
        logging.info(f"[STATS] 📝 总字数: {total_words}")
        
        # 获取最后活跃时间
        last_active = None
        if diary_response.data:
            latest_diary = max(diary_response.data, key=lambda x: x["created_at"])
            last_active = latest_diary["created_at"]
        logging.info(f"[STATS] ⏰ 最后活跃: {last_active}")
        
        stats_result = {
            "registrationDate": registration_date,
            "totalDays": total_days,
            "consecutiveCheckins": consecutive_checkins,
            "totalDiaries": total_diaries,
            "monthlyDiaries": monthly_diaries,
            "totalConversations": total_conversations,
            "totalWords": total_words,
            "lastActiveDate": last_active
        }
        logging.info(f"[STATS] ✅ 统计计算完成: {stats_result}")
        return stats_result
        
    except Exception as e:
        logging.error(f"计算用户统计失败: {e}")
        return {
            "registrationDate": None,
            "totalDays": 0,
            "consecutiveCheckins": 0,
            "totalDiaries": 0,
            "monthlyDiaries": 0,
            "totalConversations": 0,
            "totalWords": 0,
            "lastActiveDate": None
        }

async def _get_consecutive_checkins(user_id: str) -> int:
    """获取用户连续签到天数"""
    try:
        now_utc = datetime.now(timezone.utc) # 使用 aware datetime
        
        # 获取最近30天的签到记录
        thirty_days_ago = (now_utc - timedelta(days=30)).date().isoformat()
        
        response = supabase.table("user_checkins").select("checkin_date").eq("user_id", user_id).gte("checkin_date", thirty_days_ago).order("checkin_date", desc=True).execute()
        
        if not response.data:
            return 0
        
        checkin_dates = [datetime.fromisoformat(date_str).date() for date_str in response.data]
        checkin_dates.sort(reverse=True)
        
        # 计算连续签到天数
        consecutive = 0
        current_date = now_utc.date()
        
        for i, checkin_date in enumerate(checkin_dates):
            if i == 0:
                if checkin_date == current_date:
                    consecutive = 1
                else:
                    break
            else:
                expected_date = checkin_dates[i-1] - timedelta(days=1)
                if checkin_date == expected_date:
                    consecutive += 1
                else:
                    break
        
        return consecutive
        
    except Exception as e:
        logging.error(f"获取连续签到天数失败: {e}")
        return 0

async def _update_consecutive_checkins(user_id: str):
    """更新用户连续签到天数"""
    try:
        consecutive_days = await _get_consecutive_checkins(user_id)
        
        # 更新用户偏好表中的统计信息
        update_data = {
            "consecutive_checkins": consecutive_days,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("user_preferences").update(update_data).eq("user_id", user_id).execute()
        
    except Exception as e:
        logging.error(f"更新连续签到天数失败: {e}") 

@router.get("/export")
async def export_user_data(
    format: str = Query("json", description="导出格式: json 或 csv"),
    include_fortunes: bool = Query(True, description="是否包含运势数据"),
    include_diaries: bool = Query(True, description="是否包含日记数据"),
    include_chats: bool = Query(True, description="是否包含对话数据"),
    current_user: User = Depends(get_current_user)
):
    """
    导出用户数据
    
    支持格式：
    - JSON: 完整的数据结构，适合数据迁移
    - CSV: 表格格式，适合数据分析
    
    数据范围：
    - 运势历史记录
    - 日记内容
    - AI对话记录
    - 用户偏好设置
    """
    try:
        user_id = str(current_user.id)
        user_email = current_user.email
        
        # 获取用户基础信息（从profiles表）
        try:
            profile_response = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            user_data = profile_response.data if profile_response.data else {}
        except Exception as e:
            logging.warning(f"获取用户档案失败: {e}")
            user_data = {}
        
        # 补充email信息
        user_data["id"] = user_id
        user_data["email"] = user_email
        
        # 获取用户偏好设置
        try:
            preferences_response = supabase.table("user_preferences").select("*").eq("user_id", user_id).single().execute()
            user_preferences = preferences_response.data if preferences_response.data else {}
        except Exception as e:
            logging.warning(f"获取用户偏好设置失败: {e}")
            user_preferences = {}
        
        # 构建导出数据结构
        export_data = {
            "export_info": {
                "exported_at": datetime.utcnow().isoformat(),
                "format": format,
                "user_id": user_id,
                "data_version": "1.0"
            },
            "user_profile": {
                "id": user_data["id"],
                "email": user_data["email"],
                "full_name": user_data.get("full_name"),
                "birth_datetime": user_data.get("birth_datetime"), # 使用正确的字段名
                "gender": user_data.get("gender"),
                "birth_location": user_data.get("birth_location"), # 使用正确的字段名
                "birth_timezone": user_data.get("birth_timezone"), # 使用正确的字段名
                "timezone": user_data.get("timezone"),
                "created_at": user_data.get("created_at"),
                "updated_at": user_data.get("updated_at")
            },
            "preferences": user_preferences
        }
        
        # 获取运势数据
        if include_fortunes:
            try:
                fortunes_response = supabase.table("fortune_history").select("*").eq("user_id", user_id).order("fortune_date", desc=True).execute()
                export_data["fortunes"] = fortunes_response.data if fortunes_response.data else []
            except Exception as e:
                logging.warning(f"获取运势数据失败: {e}")
                export_data["fortunes"] = []
        
        # 获取日记数据
        if include_diaries:
            try:
                diaries_response = supabase.table("diary_entries").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
                export_data["diaries"] = diaries_response.data if diaries_response.data else []
            except Exception as e:
                logging.warning(f"获取日记数据失败: {e}")
                export_data["diaries"] = []
        
        # 获取对话数据
        if include_chats:
            try:
                chats_response = supabase.table("chat_messages").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
                export_data["chats"] = chats_response.data if chats_response.data else []
            except Exception as e:
                logging.warning(f"获取对话数据失败: {e}")
                export_data["chats"] = []
        
        # 根据格式返回数据
        if format.lower() == "csv":
            return await _generate_csv_export(export_data)
        else:
            return export_data
            
    except Exception as e:
        logging.error(f"导出用户数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出用户数据失败: {str(e)}")

async def _generate_csv_export(export_data: dict) -> Dict[str, Any]:
    """生成CSV格式的导出数据"""
    try:
        import csv
        import io
        
        # 创建CSV数据
        csv_data = {}
        
        # 用户档案CSV
        if "user_profile" in export_data:
            profile_buffer = io.StringIO()
            profile_writer = csv.writer(profile_buffer)
            profile_writer.writerow(["字段", "值"])
            for key, value in export_data["user_profile"].items():
                profile_writer.writerow([key, str(value) if value is not None else ""])
            csv_data["user_profile"] = profile_buffer.getvalue()
            profile_buffer.close()
        
        # 运势数据CSV
        if "fortunes" in export_data and export_data["fortunes"]:
            fortunes_buffer = io.StringIO()
            fortunes_writer = csv.writer(fortunes_buffer)
            
            # 写入表头
            if export_data["fortunes"]:
                headers = list(export_data["fortunes"][0].keys())
                fortunes_writer.writerow(headers)
                
                # 写入数据行
                for fortune in export_data["fortunes"]:
                    row = [str(fortune.get(header, "")) for header in headers]
                    fortunes_writer.writerow(row)
            
            csv_data["fortunes"] = fortunes_buffer.getvalue()
            fortunes_buffer.close()
        
        # 日记数据CSV
        if "diaries" in export_data and export_data["diaries"]:
            diaries_buffer = io.StringIO()
            diaries_writer = csv.writer(diaries_buffer)
            
            if export_data["diaries"]:
                headers = list(export_data["diaries"][0].keys())
                diaries_writer.writerow(headers)
                
                for diary in export_data["diaries"]:
                    row = [str(diary.get(header, "")) for header in headers]
                    diaries_writer.writerow(row)
            
            csv_data["diaries"] = diaries_buffer.getvalue()
            diaries_buffer.close()
        
        # 对话数据CSV
        if "chats" in export_data and export_data["chats"]:
            chats_buffer = io.StringIO()
            chats_writer = csv.writer(chats_buffer)
            
            if export_data["chats"]:
                headers = list(export_data["chats"][0].keys())
                chats_writer.writerow(headers)
                
                for chat in export_data["chats"]:
                    row = [str(chat.get(header, "")) for header in headers]
                    chats_writer.writerow(row)
            
            csv_data["chats"] = chats_buffer.getvalue()
            chats_buffer.close()
        
        return {
            "format": "csv",
            "exported_at": export_data["export_info"]["exported_at"],
            "csv_files": csv_data,
            "note": "CSV数据已生成，每个数据类型对应一个CSV字符串"
        }
        
    except Exception as e:
        logging.error(f"生成CSV导出失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成CSV导出失败: {str(e)}")

@router.delete("/export")
async def delete_exported_data(
    current_user: User = Depends(get_current_user)
):
    """
    删除导出的数据（清理临时文件）
    
    注意：这只是清理操作，不会删除用户的原始数据
    """
    try:
        user_id = str(current_user.id)
        
        # 这里可以添加清理临时导出文件的逻辑
        # 目前返回成功消息
        
        return {
            "message": "导出数据清理完成",
            "user_id": user_id,
            "cleaned_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"清理导出数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理导出数据失败: {str(e)}") 

@router.delete("/account")
async def delete_user_account(current_user: User = Depends(get_current_user)):
    """删除用户账号及所有相关数据（级联删除）"""
    try:
        user_id = str(current_user.id)
        user_email = current_user.email
        logging.info(f"[DELETE_ACCOUNT] 🗑️ 开始删除用户账号: user_id={user_id}, email={user_email}")
        
        # 检查是否配置了 Service Role Key
        import os
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not service_key:
            logging.error(f"[DELETE_ACCOUNT] ❌ 未配置 SUPABASE_SERVICE_KEY，无法删除用户")
            raise HTTPException(
                status_code=500, 
                detail="服务器配置错误：未配置管理员密钥。请联系管理员配置 SUPABASE_SERVICE_KEY。"
            )
        
        # 创建独立的 Admin Client 执行删除操作（避免认证上下文冲突）
        logging.info(f"[DELETE_ACCOUNT] 🔧 创建独立的 Admin Client...")
        from supabase import create_client
        admin_client = create_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_SERVICE_KEY")
        )
        logging.info(f"[DELETE_ACCOUNT] ✅ Admin Client 创建成功")
        
        logging.info(f"[DELETE_ACCOUNT] 🔧 调用 Supabase Admin API 删除用户...")
        
        try:
            # 检查方法是否存在
            if not hasattr(admin_client.auth, 'admin'):
                logging.error(f"[DELETE_ACCOUNT] ❌ admin_client.auth.admin 不存在")
                raise HTTPException(
                    status_code=500,
                    detail="Supabase SDK 不支持 admin 操作，请更新 supabase-py 包"
                )
            
            if not hasattr(admin_client.auth.admin, 'delete_user'):
                available_methods = [m for m in dir(admin_client.auth.admin) if not m.startswith('_')]
                logging.error(f"[DELETE_ACCOUNT] ❌ delete_user 方法不存在，可用方法: {available_methods}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Supabase SDK 缺少 delete_user 方法，可用: {', '.join(available_methods[:5])}"
                )
            
            # 调用删除方法（should_soft_delete=False 表示永久删除）
            logging.info(f"[DELETE_ACCOUNT] 🔧 执行 delete_user({user_id})...")
            result = admin_client.auth.admin.delete_user(user_id, should_soft_delete=False)
            logging.info(f"[DELETE_ACCOUNT] 📋 删除结果: {result}")
            
        except HTTPException:
            raise
        except AttributeError as ae:
            logging.error(f"[DELETE_ACCOUNT] ❌ Supabase SDK AttributeError: {ae}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Supabase SDK 方法调用失败: {str(ae)}"
            )
        except Exception as delete_error:
            logging.error(f"[DELETE_ACCOUNT] ❌ Supabase 删除失败: {delete_error}", exc_info=True)
            logging.error(f"[DELETE_ACCOUNT] ❌ 错误类型: {type(delete_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"删除用户失败: {str(delete_error)}"
            )
        
        # 验证用户是否真的被删除（尝试查询用户）
        try:
            check_user = admin_client.auth.admin.get_user_by_id(user_id)
            if check_user:
                logging.warning(f"[DELETE_ACCOUNT] ⚠️ 用户可能未被完全删除，仍可查询到: {check_user}")
        except:
            logging.info(f"[DELETE_ACCOUNT] ✅ 验证通过：用户已从 auth.users 中删除")
        
        logging.info(f"[DELETE_ACCOUNT] ✅ 用户账号删除成功: user_id={user_id}")
        return {"message": "账号删除成功", "deleted_at": datetime.utcnow().isoformat()}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"[DELETE_ACCOUNT] ❌ 删除账号失败: user_id={current_user.id if current_user else 'unknown'}, error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除账号失败: {str(e)}")
