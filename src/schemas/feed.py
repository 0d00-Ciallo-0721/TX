from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List
from uuid import UUID
from src.schemas.profile import BuddyCardBase

class Recommendation(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    user_id: UUID
    nickname: str
    avatar_url: Optional[str] = None
    match_score: int = Field(description="匹配度打分 0-100")
    match_reasons: List[str] = Field(description="匹配理由，例如 ['都玩LOL', '时间互补']")
    conflict: Optional[str] = Field(None, description="潜在冲突")
    advice: Optional[str] = Field(None, description="相处建议")
    communication_style_preview: Optional[str] = None
    card: Optional[BuddyCardBase] = None

class BuddyRequestCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    target_user_id: UUID
    message: Optional[str] = None