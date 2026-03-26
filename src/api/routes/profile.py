from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.api.dependencies import get_current_user
from src.models.user import User, Profile
from src.schemas.profile import ProfileUpdate, ProfileResponse, ProfileBase

router = APIRouter()

@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """获取当前登录用户的 Profile"""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalars().first()
    
    # 如果找到了，Pydantic 的 from_attributes=True 会自动将 ORM 模型转为 JSON
    return ProfileResponse(data=profile)

@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    request: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新或创建用户画像 (Upsert 逻辑)"""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalars().first()
    
    # 获取需要更新的数据字典 (排除未设置的字段)
    update_data = request.model_dump(exclude_unset=True)
    
    if profile:
        # 存在则更新
        for key, value in update_data.items():
            setattr(profile, key, value)
    else:
        # 不存在则新建
        profile = Profile(user_id=current_user.id, **update_data)
        db.add(profile)
        
    await db.commit()
    await db.refresh(profile)
    
    return ProfileResponse(data=profile)