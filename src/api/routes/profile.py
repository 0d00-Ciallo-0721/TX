import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.api.dependencies import get_current_user
from src.models.user import User, Profile, BuddyCard
from src.models.agent import AgentTuning
from src.schemas.profile import ProfileUpdate, ProfileResponse, ProfileAggregateResponse, AggregatedProfileData

router = APIRouter()

@router.get("/me", response_model=ProfileAggregateResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """获取当前登录用户的冷启动聚合配置 (Profile, BuddyCard, AgentTuning)"""
    # 核心：使用 asyncio.gather 并发三个查库任务，消除 I/O 阻塞等待
    profile_task = db.execute(select(Profile).where(Profile.user_id == current_user.id))
    card_task = db.execute(select(BuddyCard).where(BuddyCard.user_id == current_user.id))
    tuning_task = db.execute(select(AgentTuning).where(AgentTuning.user_id == current_user.id))
    
    results = await asyncio.gather(profile_task, card_task, tuning_task)
    
    profile = results[0].scalars().first()
    card = results[1].scalars().first()
    tuning = results[2].scalars().first()
    
    return ProfileAggregateResponse(
        data=AggregatedProfileData(
            profile=profile,
            buddy_card=card,
            agent_tuning=tuning
        )
    )

@router.put("/me", response_model=ProfileResponse)
async def update_my_profile(
    request: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新或创建用户画像 (Upsert 逻辑)"""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalars().first()
    
    update_data = request.model_dump(exclude_unset=True, by_alias=False)
    
    if profile:
        for key, value in update_data.items():
            setattr(profile, key, value)
    else:
        profile = Profile(user_id=current_user.id, **update_data)
        db.add(profile)
        
    await db.commit()
    await db.refresh(profile)
    
    return ProfileResponse(data=profile)