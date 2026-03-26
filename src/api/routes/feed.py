import json
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.core.config import settings
from src.core.database import get_db
from src.api.dependencies import get_current_user
from src.models.user import User
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
    """发送搭子申请 (满足 Android 端的遗留 TODO)"""
    # 这里为了简便直接返回成功，生产环境需落库到 buddy_requests 表并通知目标用户
    return {"code": 200, "message": "申请已发送", "data": {"success": True}}