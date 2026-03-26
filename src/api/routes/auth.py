from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()

# --- Schemas ---
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    avatarUrl: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserSummary(BaseModel):
    id: str
    email: EmailStr
    regNickname: str
    avatarUrl: Optional[str] = None

class AuthResponse(BaseModel):
    accessToken: str
    user: UserSummary

# --- Routes ---
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def register(request: UserRegisterRequest):
    """
    用户注册接口
    """
    # TODO: 接入真实数据库校验和哈希入库逻辑
    return AuthResponse(
        accessToken="eyJhbG...mock_token_for_registration",
        user=UserSummary(
            id="uuid-string-1234",
            email=request.email,
            regNickname=request.nickname,
            avatarUrl=request.avatarUrl
        )
    )

@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login(request: UserLoginRequest):
    """
    用户登录接口
    """
    # TODO: 接入真实的密码校验与 JWT 签发逻辑
    return AuthResponse(
        accessToken="eyJhbG...mock_token_for_login",
        user=UserSummary(
            id="uuid-string-1234",
            email=request.email,
            regNickname="已登录玩家",
            avatarUrl=None
        )
    )