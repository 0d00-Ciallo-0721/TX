from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户的最新输入消息")
    
class ChatStreamResponse(BaseModel):
    content: Optional[str] = None
    tool_call: Optional[str] = None
    done: bool = False