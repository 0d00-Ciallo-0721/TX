from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import List, Optional
from uuid import UUID

# --- 搭子名片生成 ---
class BuddyCardGenerationResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    tags: List[str] = Field(description="提炼的个性标签")
    declaration: str = Field(description="交友宣言")
    rules: List[str] = Field(description="组队原则/底线")
    pro_persona_label: Optional[str] = Field(None, description="气质总结标签")
    favorite_esports_hint: Optional[str] = None

# --- AI 发帖草稿 ---
class PostDraftRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    intent: str = Field(..., description="用户的发帖意图，如：找周末一起打无畏契约的，别压力")
    category_id: str = Field(default="recruit", description="发帖分区")

class PostDraftResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str = Field(description="吸引人的标题")
    content: str = Field(description="排版良好的正文内容")
    tags: List[str] = Field(description="推荐标签")

# --- 共识卡 (匹配破冰) ---
class ConsensusCardRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    target_user_id: UUID = Field(..., description="目标用户的 ID")

class ConsensusCardResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    match_score: int = Field(description="综合匹配度得分 0-100")
    match_reasons: List[str] = Field(description="匹配理由，例如：作息一致、互补位置")
    advice: str = Field(description="相处建议与潜在风险防范")
    icebreaker_suggestion: str = Field(description="专属的打招呼破冰话术")