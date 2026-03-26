import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from src.core.database import get_db, AsyncSessionLocal
from src.api.dependencies import get_current_user
from src.models.user import User
from src.models.forum import Post, PostLike, PostBookmark
from src.schemas.forum import PostCreate, PostResponse

router = APIRouter()

async def async_moderation_task(post_id: UUID):
    """
    [后台任务] 模拟异步内容审核 (风控系统)
    实际生产中可替换为 Celery Task，调用阿里云/腾讯云内容安全 API
    """
    await asyncio.sleep(3)  # 模拟 API 网络延迟与机器审核耗时
    
    # 注意：后台任务必须开启独立的数据库会话
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalars().first()
        if post:
            # 假设机审全部通过
            post.moderation_status = 'APPROVED'
            await db.commit()

@router.post("/posts", response_model=dict)
async def create_post(
    request: PostCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发布新帖 (自动进入审核队列)"""
    new_post = Post(
        author_id=current_user.id,
        **request.model_dump(by_alias=False)
    )
    # 数据库模型默认 moderation_status 就是 'PENDING_REVIEW'
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

    # 将帖子 ID 丢入后台验证队列，立刻向前端返回结果 (不阻塞)
    background_tasks.add_task(async_moderation_task, new_post.id)

    return {
        "code": 200, 
        "message": "success", 
        "data": PostResponse.model_validate(new_post).model_dump(by_alias=True)
    }

@router.get("/posts")
async def get_posts(
    category_id: str = Query(None, description="按分区筛选"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取广场帖子列表 (仅展示已过审内容)"""
    stmt = select(Post).where(Post.moderation_status == 'APPROVED')
    
    if category_id:
        stmt = stmt.where(Post.category_id == category_id)

    # 查多一条用于判断是否有下一页
    stmt = stmt.order_by(desc(Post.created_at)).offset((page - 1) * size).limit(size + 1)
    
    result = await db.execute(stmt)
    posts = result.scalars().all()

    has_more = len(posts) > size
    posts_to_return = posts[:size]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "list": [PostResponse.model_validate(p).model_dump(by_alias=True) for p in posts_to_return],
            "hasMore": has_more
        }
    }

@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: UUID, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """帖子点赞 (带联合主键防重复点赞拦截)"""
    # 1. 查重防刷
    existing = await db.execute(select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == current_user.id))
    if existing.scalars().first():
        return {"code": 400, "message": "已经点过赞了"}
    
    # 2. 插入点赞记录
    new_like = PostLike(post_id=post_id, user_id=current_user.id)
    db.add(new_like)
    
    # 3. 更新冗余计数字段 (生产环境如果极高并发，这里应改为 Redis 计数后异步刷盘)
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
        
    post.like_count += 1
    await db.commit()
    
    return {"code": 200, "message": "success", "data": {"likeCount": post.like_count}}