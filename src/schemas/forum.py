from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime

class PostBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    category_id: str = Field(..., description="分区ID: recruit, guide, social, event")
    title: str = Field(..., max_length=255)
    content: str = Field(...)
    tags: List[str] = Field(default_factory=list)
    media_attachments: List[dict] = Field(default_factory=list)

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: UUID
    author_id: UUID
    moderation_status: str
    moderation_hint: Optional[str] = None
    reply_count: int
    like_count: int
    is_pinned: bool
    created_at: datetime

class PostListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: dict  # 包含 list 和 hasMore