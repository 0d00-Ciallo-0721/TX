from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID

# --- 内部 User DTO ---
class UserBase(BaseModel):
    id: UUID
    email: EmailStr
    reg_nickname: Optional[str] = None

# --- 请求 (Requests) ---
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="合法邮箱地址")
    password: str = Field(..., min_length=6, max_length=50, description="密码至少6位")
    nickname: Optional[str] = Field(None, max_length=20, description="初始昵称")
    avatarUrl: Optional[str] = Field(None, description="头像URL")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- 响应 (Responses) ---
# 严格对齐 TX_ku_API接口契约文档.md
class AuthResponseData(BaseModel):
    accessToken: str
    user: UserBase

class AuthResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: AuthResponseData