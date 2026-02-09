"""
每日活动收集服务
收集用户的日记、对话和档案更新，生成每日活动日志
"""
import logging
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from ..core.db import supabase

logger = logging.getLogger(__name__)


class DailyActivityService:
    """每日活动收集服务"""

    async def collect_daily_diaries(
        self,
        user_id: str,
        target_date: date,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """收集指定日期的日记

        Args:
            user_id: 用户ID
            target_date: 目标日期
            start_time: 开始时间（UTC），如果提供则使用此时间范围
            end_time: 结束时间（UTC），如果提供则使用此时间范围
        """
        try:
            # 如果没有提供时间范围，使用默认的日期范围
            if start_time is None:
                start_time = datetime.combine(target_date, datetime.min.time())
            if end_time is None:
                end_time = datetime.combine(target_date, datetime.max.time())

            response = supabase.table("diary_entries")\
                .select("id, content, emotion_tags, created_at")\
                .eq("user_id", user_id)\
                .gte("created_at", start_time.isoformat())\
                .lte("created_at", end_time.isoformat())\
                .execute()

            diaries = []
            if response.data:
                for diary in response.data:
                    diaries.append({
                        "id": diary["id"],
                        "content": diary["content"],
                        "emotion_tags": diary.get("emotion_tags", []),
                        "created_at": diary["created_at"]
                    })

            logger.info(f"✅ 收集日记: user_id={user_id}, date={target_date}, count={len(diaries)}")
            return diaries

        except Exception as e:
            logger.error(f"❌ 收集日记失败: {e}")
            return []

    async def collect_daily_conversations(
        self,
        user_id: str,
        target_date: date,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """收集指定日期的对话摘要

        Args:
            user_id: 用户ID
            target_date: 目标日期
            start_time: 开始时间（UTC），如果提供则使用此时间范围
            end_time: 结束时间（UTC），如果提供则使用此时间范围
        """
        try:
            # 如果没有提供时间范围，使用默认的日期范围
            if start_time is None:
                start_time = datetime.combine(target_date, datetime.min.time())
            if end_time is None:
                end_time = datetime.combine(target_date, datetime.max.time())

            response = supabase.table("conversations")\
                .select("id, conversation_id, preview, created_at")\
                .eq("user_id", user_id)\
                .gte("created_at", start_time.isoformat())\
                .lte("created_at", end_time.isoformat())\
                .execute()

            conversations = []
            if response.data:
                for conv in response.data:
                    msg_response = supabase.table("chat_messages")\
                        .select("id", count="exact")\
                        .eq("conversation_id", conv["conversation_id"])\
                        .execute()

                    conversations.append({
                        "conversation_id": conv["id"],
                        "summary": conv.get("preview", ""),
                        "message_count": msg_response.count or 0,
                        "started_at": conv["created_at"]
                    })

            logger.info(f"✅ 收集对话: user_id={user_id}, date={target_date}, count={len(conversations)}")
            return conversations

        except Exception as e:
            logger.error(f"❌ 收集对话失败: {e}")
            return []

    async def record_profile_update(
        self,
        user_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        target_date: Optional[date] = None
    ) -> bool:
        """记录档案更新到当天的活动日志"""
        try:
            if target_date is None:
                target_date = date.today()

            # 获取或创建当天的活动日志
            existing = supabase.table("daily_activity_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("activity_date", target_date.isoformat())\
                .execute()

            if existing.data:
                # 已有记录：保留初始状态，只更新最终状态
                activity_data = existing.data[0].get("activity_data", {})
                existing_updates = activity_data.get("profile_updates", {})

                if existing_updates:
                    # 已有初始状态，保留 initial_state，更新 final_state
                    initial_state = existing_updates.get("initial_state", old_data)
                    updates = self._track_profile_changes(initial_state, new_data)
                    updates["initial_state"] = initial_state
                    updates["final_state"] = new_data
                else:
                    # 第一次记录，保存初始和最终状态
                    updates = self._track_profile_changes(old_data, new_data)
                    updates["initial_state"] = old_data
                    updates["final_state"] = new_data

                # 检查是否有变化
                if not any([
                    updates["basic_info"],
                    updates["current_activities"]["added"],
                    updates["current_activities"]["removed"],
                    updates["interests"]["added"],
                    updates["interests"]["removed"]
                ]):
                    logger.info(f"ℹ️ 档案无变化: user_id={user_id}")
                    return True

                updates["updated_at"] = datetime.utcnow().isoformat()
                activity_data["profile_updates"] = updates

                supabase.table("daily_activity_logs")\
                    .update({
                        "activity_data": activity_data,
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("user_id", user_id)\
                    .eq("activity_date", target_date.isoformat())\
                    .execute()
            else:
                # 创建新日志：第一次记录
                updates = self._track_profile_changes(old_data, new_data)

                # 检查是否有变化
                if not any([
                    updates["basic_info"],
                    updates["current_activities"]["added"],
                    updates["current_activities"]["removed"],
                    updates["interests"]["added"],
                    updates["interests"]["removed"]
                ]):
                    logger.info(f"ℹ️ 档案无变化: user_id={user_id}")
                    return True

                updates["initial_state"] = old_data
                updates["final_state"] = new_data
                updates["updated_at"] = datetime.utcnow().isoformat()

                activity_data = {
                    "date": target_date.isoformat(),
                    "user_id": user_id,
                    "diaries": [],
                    "conversations": [],
                    "profile_updates": updates
                }

                supabase.table("daily_activity_logs").insert({
                    "user_id": user_id,
                    "activity_date": target_date.isoformat(),
                    "activity_data": activity_data,
                    "processed": False
                }).execute()

            logger.info(f"✅ 记录档案更新: user_id={user_id}, date={target_date}")
            return True

        except Exception as e:
            logger.error(f"❌ 记录档案更新失败: {e}")
            return False

    def _track_profile_changes(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """追踪档案变化"""
        updates = {
            "basic_info": {},
            "current_activities": {"added": [], "removed": []},
            "interests": {"added": [], "removed": []}
        }

        onboarding_old = old_data.get("onboarding_data", {})
        onboarding_new = new_data.get("onboarding_data", {})

        # 基本信息对比
        for field in ["gender", "region", "status"]:
            old_val = onboarding_old.get(field)
            new_val = onboarding_new.get(field)
            if old_val != new_val and new_val:
                updates["basic_info"][field] = {"from": old_val, "to": new_val}

        # 生日对比
        old_birth = old_data.get("birth_datetime")
        new_birth = new_data.get("birth_datetime")
        if old_birth != new_birth and new_birth:
            updates["basic_info"]["birthday"] = {"from": old_birth, "to": new_birth}

        # 工作/学习活动对比
        activity_fields = ["industry", "role", "work_type", "rhythm", "student_focus", "student_industry"]
        old_activities = set()
        new_activities = set()

        for field in activity_fields:
            old_list = onboarding_old.get(field, [])
            new_list = onboarding_new.get(field, [])
            if isinstance(old_list, list):
                old_activities.update(old_list)
            if isinstance(new_list, list):
                new_activities.update(new_list)

        updates["current_activities"]["added"] = list(new_activities - old_activities)
        updates["current_activities"]["removed"] = list(old_activities - new_activities)

        # 兴趣爱好对比
        old_interests = set(onboarding_old.get("hobbies", [])) | set(onboarding_old.get("lifestyle", []))
        new_interests = set(onboarding_new.get("hobbies", [])) | set(onboarding_new.get("lifestyle", []))

        updates["interests"]["added"] = list(new_interests - old_interests)
        updates["interests"]["removed"] = list(old_interests - new_interests)

        return updates

    async def generate_daily_log(
        self,
        user_id: str,
        target_date: date,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> bool:
        """生成并保存每日活动日志

        Args:
            user_id: 用户ID
            target_date: 目标日期
            start_time: 开始时间（UTC），如果提供则使用此时间范围
            end_time: 结束时间（UTC），如果提供则使用此时间范围
        """
        try:
            diaries = await self.collect_daily_diaries(user_id, target_date, start_time, end_time)
            conversations = await self.collect_daily_conversations(user_id, target_date, start_time, end_time)

            activity_data = {
                "date": target_date.isoformat(),
                "user_id": user_id,
                "diaries": diaries,
                "conversations": conversations
            }

            # 检查是否已存在
            existing = supabase.table("daily_activity_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("activity_date", target_date.isoformat())\
                .execute()

            if existing.data:
                # 保留已有的 profile_updates
                old_activity_data = existing.data[0].get("activity_data", {})
                if "profile_updates" in old_activity_data:
                    activity_data["profile_updates"] = old_activity_data["profile_updates"]

                supabase.table("daily_activity_logs")\
                    .update({
                        "activity_data": activity_data,
                        "updated_at": datetime.utcnow().isoformat()
                    })\
                    .eq("user_id", user_id)\
                    .eq("activity_date", target_date.isoformat())\
                    .execute()
                logger.info(f"✅ 更新每日日志: user_id={user_id}, date={target_date}")
            else:
                supabase.table("daily_activity_logs").insert({
                    "user_id": user_id,
                    "activity_date": target_date.isoformat(),
                    "activity_data": activity_data,
                    "processed": False
                }).execute()
                logger.info(f"✅ 创建每日日志: user_id={user_id}, date={target_date}")

            return True

        except Exception as e:
            logger.error(f"❌ 生成每日日志失败: {e}")
            return False


daily_activity_service = DailyActivityService()
