from pydantic import BaseModel


class VoiceDiaryStyleRequest(BaseModel):
    raw_text: str
    style: str
