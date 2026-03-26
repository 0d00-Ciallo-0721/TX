from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List

class ProfileBase(BaseModel):
    # 核心魔法：自动将 Python 的 snake_case 映射为 JSON 的 camelCase
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    nickname: str = Field(..., max_length=100)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    city_or_region: Optional[str] = None
    
    # 复杂数组类型，直接映射为 PostgreSQL 的 JSONB
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

class ProfileResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[ProfileBase] = None