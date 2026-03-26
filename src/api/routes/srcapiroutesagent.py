from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.api.dependencies import get_current_user
from src.models.user import User
from src.models.agent import AgentTuning
from src.schemas.agent import AgentTuningUpdate

router = APIRouter()

@router.put("/tuning")
async def update_agent_tuning(
    request: AgentTuningUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新或创建智能体偏好配置 (Upsert)"""
    result = await db.execute(select(AgentTuning).where(AgentTuning.user_id == current_user.id))
    tuning = result.scalars().first()
    
    # by_alias=False 确保获取到的是 is_unlocked 而非 agentChatUnlocked
    update_data = request.model_dump(exclude_unset=True, by_alias=False)
    
    if tuning:
        for key, value in update_data.items():
            setattr(tuning, key, value)
    else:
        tuning = AgentTuning(user_id=current_user.id, **update_data)
        db.add(tuning)
        
    await db.commit()
    
    return {"code": 200, "message": "success", "data": {"success": True}}