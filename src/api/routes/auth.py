from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.security import get_password_hash, verify_password, create_access_token
from src.models.user import User
from src.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, AuthResponseData, UserBase

router = APIRouter()

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """工业级注册接口：防冲突校验 + 密码安全哈希"""
    # 1. 校验邮箱是否已存在
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 2. 创建新用户
    new_user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        reg_nickname=request.nickname
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # 3. 签发 JWT
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return AuthResponse(
        data=AuthResponseData(
            accessToken=access_token,
            user=UserBase(
                id=new_user.id,
                email=new_user.email,
                reg_nickname=new_user.reg_nickname
            )
        )
    )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """工业级登录接口：防时序攻击与状态拦截"""
    # 1. 查库
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    # 2. 校验账号与密码 (模糊错误提示，防止被遍历探号)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
        
    # 3. 校验状态
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号不可用"
        )
        
    # 4. 签发 JWT
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return AuthResponse(
        data=AuthResponseData(
            accessToken=access_token,
            user=UserBase(
                id=user.id,
                email=user.email,
                reg_nickname=user.reg_nickname
            )
        )
    )