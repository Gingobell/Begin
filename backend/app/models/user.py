from pydantic import BaseModel
from typing import Optional
from datetime import date


class User(BaseModel):
    id: str
    email: Optional[str] = None
    birth_date: Optional[date] = None
