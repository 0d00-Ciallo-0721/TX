import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from src.core.database import get_db, AsyncSessionLocal
from src.api.dependencies import get_current_user
from src.models.user import User, Profile
from src.models.forum import Post, PostLike, PostBookmark, Comment
from src.schemas.forum import PostCreate, PostResponse, PostDetailResponse, CommentCreate, CommentResponse

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
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post)

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

@router.get("/posts/{post_id}")
async def get_post_detail(
    post_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """[新增] 获取帖子详情（聚合作者信息与前置评论）"""
    # 1. 查帖
    stmt = select(Post).where(Post.id == post_id, Post.moderation_status == 'APPROVED')
    post = (await db.execute(stmt)).scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在或还在审核中")

    # 2. 查作者画像
    profile = (await db.execute(select(Profile).where(Profile.user_id == post.author_id))).scalars().first()
    
    # 3. 查前置热评 (限3条)
    comment_stmt = select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc()).limit(3)
    comments = (await db.execute(comment_stmt)).scalars().all()
    
    # 提取评论者画像
    comment_responses = []
    if comments:
        c_author_ids = [c.author_id for c in comments]
        c_profiles = (await db.execute(select(Profile).where(Profile.user_id.in_(c_author_ids)))).scalars().all()
        p_map = {p.user_id: p for p in c_profiles}
        
        for c in comments:
            cp = p_map.get(c.author_id)
            comment_responses.append({
                "id": c.id, "post_id": c.post_id, "author_id": c.author_id,
                "author_name": cp.nickname if cp else "未知搭子",
                "author_avatar": cp.avatar_url if cp else None,
                "content": c.content, "created_at": c.created_at
            })

    # 4. 组装响应
    post_dict = PostResponse.model_validate(post).model_dump(by_alias=True)
    post_dict["authorName"] = profile.nickname if profile else "未知搭子"
    post_dict["authorAvatar"] = profile.avatar_url if profile else None
    post_dict["comments"] = [CommentResponse(**cr).model_dump(by_alias=True) for cr in comment_responses]

    return {"code": 200, "message": "success", "data": post_dict}

@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: UUID, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """帖子点赞 (带联合主键防重)"""
    existing = await db.execute(select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == current_user.id))
    if existing.scalars().first():
        return {"code": 400, "message": "已经点过赞了"}
    
    db.add(PostLike(post_id=post_id, user_id=current_user.id))
    
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
        
    post.like_count += 1
    await db.commit()
    
    return {"code": 200, "message": "success", "data": {"likeCount": post.like_count}}

@router.post("/posts/{post_id}/bookmark")
async def toggle_bookmark_post(
    post_id: UUID, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """[新增] 帖子收藏 (Toggle: 已藏则取消，未藏则收藏)"""
    existing = await db.execute(select(PostBookmark).where(PostBookmark.post_id == post_id, PostBookmark.user_id == current_user.id))
    bookmark = existing.scalars().first()
    
    if bookmark:
        await db.delete(bookmark)
        action = "unbookmarked"
    else:
        # 校验帖子是否存在
        post = (await db.execute(select(Post).where(Post.id == post_id))).scalars().first()
        if not post:
            raise HTTPException(status_code=404, detail="帖子不存在")
        db.add(PostBookmark(post_id=post_id, user_id=current_user.id))
        action = "bookmarked"
        
    await db.commit()
    return {"code": 200, "message": "success", "data": {"action": action}}

@router.get("/posts/{post_id}/comments")
async def get_post_comments(
    post_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """[新增] 获取帖子评论列表 (带游标分页)"""
    stmt = select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc()).offset((page - 1) * size).limit(size + 1)
    comments = (await db.execute(stmt)).scalars().all()
    
    has_more = len(comments) > size
    comments_to_return = comments[:size]
    
    # 批量拉取头像与昵称
    author_ids = [c.author_id for c in comments_to_return]
    profiles = (await db.execute(select(Profile).where(Profile.user_id.in_(author_ids)))).scalars().all()
    p_map = {p.user_id: p for p in profiles}

    comment_responses = []
    for c in comments_to_return:
        cp = p_map.get(c.author_id)
        comment_responses.append({
            "id": c.id, "post_id": c.post_id, "author_id": c.author_id,
            "author_name": cp.nickname if cp else "未知搭子",
            "author_avatar": cp.avatar_url if cp else None,
            "content": c.content, "created_at": c.created_at
        })

    return {
        "code": 200, 
        "message": "success", 
        "data": {
            "list": [CommentResponse(**cr).model_dump(by_alias=True) for cr in comment_responses],
            "hasMore": has_more
        }
    }

@router.post("/posts/{post_id}/comments")
async def create_comment(
    post_id: UUID,
    request: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """[新增] 发布评论 (自动递增冗余统计 count)"""
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalars().first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
        
    new_comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        content=request.content
    )
    db.add(new_comment)
    
    # 事务内自增回复数
    post.reply_count += 1
    await db.commit()
    
    return {"code": 200, "message": "success", "data": {"success": True}}