from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List
from uuid import UUID
from src.schemas.agent import AgentTuningBase

class ProfileBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    nickname: str = Field(..., max_length=100)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    city_or_region: Optional[str] = None
    
    preferred_games: List[str] = Field(default_factory=list)
    rank: Optional[str] = None
    active_time: List[str] = Field(default_factory=list)
    main_roles: List[str] = Field(default_factory=list)
    play_style: Optional[str] = None
    target: Optional[str] = None
    voice_pref: Optional[str] = None
    no_gos: List[str] = Field(default_factory=list)

class ProfileUpdate(ProfileBase):
    pass

class BuddyCardBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID = Field(alias="cardId")
    tags: List[str] = Field(default_factory=list)
    declaration: Optional[str] = None
    rules: List[str] = Field(default_factory=list)
    pro_persona_label: Optional[str] = None
    favorite_esports_hint: Optional[str] = None
    base_match_score: int = 0

class AggregatedProfileData(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    profile: Optional[ProfileBase] = None
    buddy_card: Optional[BuddyCardBase] = None
    agent_tuning: Optional[AgentTuningBase] = None

class ProfileAggregateResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AggregatedProfileData

# 兼容保留原有的简单返回，供 PUT /me 使用
class ProfileResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[ProfileBase] = None