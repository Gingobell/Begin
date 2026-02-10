"""应用配置文件 - 统一管理所有配置常量"""
import os
from typing import List

# Mock用户配置
MOCK_USER_ID = "11111111-1111-1111-1111-111111111111"
MOCK_USER_EMAIL = "mock@fortunediary.com"
MOCK_USER_PASSWORD = "mockpassword123"
MOCK_USER_NAME = "Mock测试用户"

# Demo用户配置
DEMO_USER_EMAIL = "sarah.chen@demo.fortunediary.com"
DEMO_USER_PASSWORD = "demo_sarah_2025"
DEMO_USER_NAME = "Sarah Chen"
DEMO_USER_BIRTH = "1997-08-15T14:30:00"
DEMO_USER_GENDER = "female"
DEMO_USER_TIMEZONE = "America/Los_Angeles"

# Supabase配置
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
SUPABASE_DB_URI = os.environ.get("SUPABASE_DB_URI", "")

# Google AI配置
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID", "")
GOOGLE_LOCATION = os.environ.get("GOOGLE_LOCATION", "us-central1")

# AI模型配置
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_CHAT_MODEL = "gemini-3-flash-preview"
THINKING_ENABLED = os.environ.get("THINKING_ENABLED", "true").lower() == "true"
THINKING_LEVEL = os.environ.get("THINKING_LEVEL", "HIGH")  # LOW | MEDIUM | HIGH
THINKING_BUDGET = {"LOW": 1024, "MEDIUM": 4096, "HIGH": 8192}.get(THINKING_LEVEL, 8192)

# Letta配置
LETTA_BASE_URL = os.environ.get("LETTA_BASE_URL", "http://localhost:8283")
LETTA_PG_URI = os.environ.get("LETTA_PG_URI", "")
LETTA_CHAT_MODEL = f"google_ai/{DEFAULT_CHAT_MODEL}"
LETTA_EMBEDDING_MODEL = os.environ.get("LETTA_EMBEDDING_MODEL", f"google_ai/{DEFAULT_EMBEDDING_MODEL}")

# 应用配置
APP_ENV = os.environ.get("APP_ENV", "development")
DEBUG_MODE = os.environ.get("DEBUG_MODE", "true").lower() == "true"

# API配置
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

# RAG配置
RAG_TOP_K = 5
RAG_SIMILARITY_THRESHOLD = 0.7
RAG_MAX_CONTEXT_LENGTH = 4000

# 运势配置
FORTUNE_FOCUS_AREAS = ["career", "love", "wealth", "study"]
FORTUNE_STYLES = ["balanced", "optimistic", "realistic"]

# 语言配置
SUPPORTED_LANGUAGES = ["zh-CN", "en-US"]
DEFAULT_LANGUAGE = "en-US"

# 功能开关
ENABLE_MOCK_MODE = os.environ.get("ENABLE_MOCK_MODE", "false").lower() == "true"
