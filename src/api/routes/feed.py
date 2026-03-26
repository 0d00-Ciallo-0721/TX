import json
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from src.core.config import settings
from src.core.database import get_db
from src.api.dependencies import get_current_user
from src.models.user import User
from src.models.social import BuddyRequest  # 新增导入
from src.schemas.feed import BuddyRequestCreate
from src.services.recommendation_service import compute_and_cache_recommendations

router = APIRouter()

@router.get("/recommendations")
async def get_recommendations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    极速获取推荐搭子 (从 Redis 缓存获取)
    时间复杂度 O(1)，确保 50ms 内响应
    """
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_key = f"feed:recommend:{current_user.id}"
    
    cached_data = await redis_client.get(redis_key)
    await redis_client.close()
    
    if not cached_data:
        # 如果缓存为空（例如新注册用户），可返回兜底数据或触发异步计算
        return {"code": 200, "message": "正在为你匹配中，请稍后再试", "data": {"list": [], "hasMore": False}}
        
    all_recommendations = json.loads(cached_data)
    
    # 在内存中进行分页切片
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paged_list = all_recommendations[start_idx:end_idx]
    has_more = end_idx < len(all_recommendations)
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": paged_list,
            "hasMore": has_more
        }
    }

@router.post("/recommendations/refresh")
async def manual_refresh_recommendations(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动触发后台匹配算法计算 (供测试或用户主动刷新使用)"""
    background_tasks.add_task(compute_and_cache_recommendations, db, current_user.id)
    return {"code": 200, "message": "后台匹配任务已启动，请稍后刷新发现页"}

@router.post("/buddy-requests")
async def send_buddy_request(
    request: BuddyRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """[更新] 发送搭子申请 (真实校验防重与落库)"""
    if current_user.id == request.target_user_id:
        raise HTTPException(status_code=400, detail="不能向自己发送搭子申请")

    # 1. 检查是否已经存在未处理的申请，防止疯狂点击刷库
    existing_req = await db.execute(
        select(BuddyRequest).where(
            BuddyRequest.sender_id == current_user.id,
            BuddyRequest.receiver_id == request.target_user_id,
            BuddyRequest.status == 'PENDING'
        )
    )
    if existing_req.scalars().first():
        return {"code": 400, "message": "您已发送过申请，请等待对方处理"}
        
    # 2. 真实落库
    new_request = BuddyRequest(
        sender_id=current_user.id,
        receiver_id=request.target_user_id,
        message=request.message
    )
    db.add(new_request)
    await db.commit()
    
    # TODO: 后续可在此处增加向接收方的 WebSocket 推送通知功能
    
    return {"code": 200, "message": "申请已发送", "data": {"success": True}}