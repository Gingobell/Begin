from pydantic import BaseModel
from typing import Optional, List


class DiaryCreate(BaseModel):
    content: str
    emotion_tags: Optional[List[str]] = None


class DiaryUpdate(BaseModel):
    content: Optional[str] = None
    emotion_tags: Optional[List[str]] = None


class DiaryPublic(BaseModel):
    """Permissive model that accepts any fields from the database."""

    class Config:
        extra = "allow"
