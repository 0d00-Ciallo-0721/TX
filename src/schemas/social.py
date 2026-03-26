from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

# --- 关注相关 ---
class FollowRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    target_user_id: UUID

# --- WebSocket 消息载荷相关 ---
class WSMessagePayload(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    to_user_id: UUID
    text: str

class WSIncomingAction(BaseModel):
    """客户端发给服务端的指令"""
    action: str  # 比如 "send_message"
    payload: WSMessagePayload

class WSPushedMessage(BaseModel):
    """服务端推给客户端的新消息"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: UUID
    from_user_id: UUID
    text: str
    sent_at: str

class WSErrorData(BaseModel):
    code: int
    message: str

class WSOutgoingEvent(BaseModel):
    """服务端统一下发的事件包装"""
    event: str  # "new_message" 或 "error"
    data: Any   # WSPushedMessage 或 WSErrorData

# ==========================================
# 新增: 用户检索与私信持久化 Schema (阶段二)
# ==========================================

class PublicUserSummary(BaseModel):
    """公开展示的用户信息摘要"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None

class UserListResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: List[PublicUserSummary]

class DMMessage(BaseModel):
    """单条私信消息数据"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: UUID
    from_user_id: UUID
    to_user_id: UUID
    text: str
    created_at: datetime
    is_read: bool

class DMHistoryResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: dict  # 包含 list: List[DMMessage] 和 hasMore: bool

class DMThreadSummary(BaseModel):
    """私信会话列表的单条摘要 (最近联系人)"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    peer_user_id: UUID
    peer_nickname: str
    peer_avatar: Optional[str] = None
    last_message_text: str
    last_message_at: datetime
    unread_count: int = 0

class DMThreadResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: List[DMThreadSummary]