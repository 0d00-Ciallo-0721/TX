from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from src.core.database import get_db
from src.api.dependencies import get_current_user
from src.models.user import User, Profile, BuddyCard
from src.schemas.ai_tools import (
    BuddyCardGenerationResponse, 
    PostDraftRequest, PostDraftResponse, 
    ConsensusCardRequest, ConsensusCardResponse
)
from src.core.ai_engine import generate_buddy_card, generate_post_draft, generate_consensus_card

router = APIRouter()

@router.post("/buddy-card", response_model=dict)
async def create_or_refresh_buddy_card(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """根据建档画像，AI自动生成搭子名片并固化到数据库"""
    # 1. 取出当前画像
    profile = (await db.execute(select(Profile).where(Profile.user_id == current_user.id))).scalars().first()
    if not profile:
        raise HTTPException(status_code=400, detail="请先完成基础建档 (Profile) 后再生成名片")
        
    # 2. 调用大模型生成结构化名片数据
    try:
        card_data = await generate_buddy_card(profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 名片生成失败: {str(e)}")

    # 3. 查出现有 BuddyCard，执行 Upsert
    existing_card = (await db.execute(select(BuddyCard).where(BuddyCard.user_id == current_user.id))).scalars().first()
    
    if existing_card:
        existing_card.tags = card_data.get("tags", [])
        existing_card.declaration = card_data.get("declaration", "")
        existing_card.rules = card_data.get("rules", [])
        existing_card.pro_persona_label = card_data.get("pro_persona_label", "")
    else:
        new_card = BuddyCard(
            user_id=current_user.id,
            tags=card_data.get("tags", []),
            declaration=card_data.get("declaration", ""),
            rules=card_data.get("rules", []),
            pro_persona_label=card_data.get("pro_persona_label", "")
        )
        db.add(new_card)
        
    await db.commit()
    
    return {"code": 200, "message": "success", "data": card_data}

@router.post("/posts", response_model=dict)
async def generate_post_draft_api(
    request: PostDraftRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI 智能扩写帖子草稿 (不直接落库，返回给客户端编辑器二次确认)"""
    profile = (await db.execute(select(Profile).where(Profile.user_id == current_user.id))).scalars().first()
    
    try:
        draft_data = await generate_post_draft(request.intent, profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 生成草稿失败: {str(e)}")
        
    return {"code": 200, "message": "success", "data": draft_data}

@router.post("/consensus-card", response_model=dict)
async def create_consensus_card(
    request: ConsensusCardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """基于双边画像比对的破冰共识卡分析"""
    my_profile = (await db.execute(select(Profile).where(Profile.user_id == current_user.id))).scalars().first()
    target_profile = (await db.execute(select(Profile).where(Profile.user_id == request.target_user_id))).scalars().first()
    
    if not my_profile or not target_profile:
        raise HTTPException(status_code=404, detail="一方或双方画像不完整，无法分析契合度")
        
    try:
        consensus_data = await generate_consensus_card(my_profile, target_profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 共识卡分析失败: {str(e)}")
        
    return {"code": 200, "message": "success", "data": consensus_data}