"""user.py 所需的 Pydantic 请求模型"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    birthYear: Optional[str] = None
    birthMonth: Optional[str] = None
    birthDay: Optional[str] = None
    birthHour: Optional[str] = None
    birthMinute: Optional[str] = None
    isTimeUnknown: Optional[bool] = None
    birthLocation: Optional[str] = None
    birthTimezone: Optional[str] = None
    timezone: Optional[str] = None


class ReminderItem(BaseModel):
    isEnabled: bool = True
    time: str = "08:00:00"
    days: List[int] = [1, 2, 3, 4, 5, 6, 7]


class ReminderSettingsUpdate(BaseModel):
    fortuneReminder: Optional[ReminderItem] = None
    diaryReminder: Optional[ReminderItem] = None
    summaryReminder: Optional[ReminderItem] = None


class PrivacySettings(BaseModel):
    isProfilePublic: Optional[bool] = None
    allowDataAnalysis: Optional[bool] = None
    shareUsageStats: Optional[bool] = None


class UserPreferencesUpdate(BaseModel):
    focusAreas: Optional[List[str]] = None
    reminderSettings: Optional[ReminderSettingsUpdate] = None
    privacySettings: Optional[PrivacySettings] = None


class OnboardingData(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    birthYear: Optional[str] = None
    birthMonth: Optional[str] = None
    birthDay: Optional[str] = None
    birthHour: Optional[str] = None
    birthMinute: Optional[str] = None
    isTimeUnknown: Optional[bool] = None
    birthLocation: Optional[str] = None
    birthTimezone: Optional[str] = None
    timezone: Optional[str] = None
    focusAreas: Optional[List[str]] = None
    reminderSettings: Optional[ReminderSettingsUpdate] = None
    onboarding_data: Optional[Dict[str, Any]] = None
