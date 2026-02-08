"""
core/config.py — re-exports app-level config so that
``from ..core.config import X`` works inside api/ and services/.
"""
import os
from app.config import *  # noqa: F401,F403 – re-export everything

# Extra vars expected by auth.py (OAuth redirects – not actively used
# in the current endpoints but imported at module level).
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
