from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, Dict, Any
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