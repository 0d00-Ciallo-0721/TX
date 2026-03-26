from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.models.user import User
from src.core.security import get_password_hash, verify_password, create_access_token

router = APIRouter()

# --- Schemas (验证模型保持不变) ---
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
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册接口"""
    # 1. 检查邮箱是否已被注册
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )
    
    # 2. 创建新用户，哈希密码入库
    new_user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        reg_nickname=request.nickname
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 3. 签发 Token 并返回
    access_token = create_access_token(subject=new_user.id)
    return AuthResponse(
        accessToken=access_token,
        user=UserSummary(
            id=str(new_user.id),
            email=new_user.email,
            regNickname=new_user.reg_nickname,
            avatarUrl=None # 注册时默认为空，后续在 Profile 中完善
        )
    )

@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录接口"""
    # 1. 查询用户
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    # 2. 验证用户存在且密码正确
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. 签发 Token
    access_token = create_access_token(subject=user.id)
    return AuthResponse(
        accessToken=access_token,
        user=UserSummary(
            id=str(user.id),
            email=user.email,
            regNickname=user.reg_nickname,
            avatarUrl=None
        )
    )