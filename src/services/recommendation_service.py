import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as redis

from src.core.config import settings
from src.models.user import Profile, BuddyCard
from src.schemas.feed import Recommendation
from src.schemas.profile import BuddyCardBase

async def compute_and_cache_recommendations(db: AsyncSession, user_id: UUID):
    """
    [后台异步任务] 为指定用户计算推荐列表并预热 Redis
    实际生产中可由 Celery 定时调度（如每天凌晨或用户修改画像后触发）
    """
    # 1. 获取当前用户画像
    user_profile = (await db.execute(select(Profile).where(Profile.user_id == user_id))).scalars().first()
    if not user_profile or not user_profile.profile_embedding:
        return
        
    user_no_gos = user_profile.no_gos or []

    # 2. 向量检索 (KNN) 获取最相似的 50 个候选人
    # 使用 pgvector 的 cosine_distance 进行余弦距离排序
    stmt = (
        select(Profile)
        .where(Profile.user_id != user_id)
        .order_by(Profile.profile_embedding.cosine_distance(user_profile.profile_embedding))
        .limit(50)
    )
    candidates = (await db.execute(stmt)).scalars().all()

    recommendations = []
    for candidate in candidates:
        # 3. 规则过滤 (硬排斥机制)
        # 假设：如果候选人的标签触碰了当前用户的雷区，则直接 Pass
        candidate_tags = candidate.preferred_games + candidate.main_roles + (candidate.play_style.split() if candidate.play_style else [])
        if any(no_go in candidate_tags for no_go in user_no_gos):
            continue  # 触碰雷区，硬过滤
            
        # 4. 组装展示数据
        # 查询候选人的搭子名片
        card = (await db.execute(select(BuddyCard).where(BuddyCard.user_id == candidate.user_id))).scalars().first()
        
        # 简单模拟打分逻辑（余弦距离越小，分数越高）
        # 实际生产中这里会有一个打分微服务或更复杂的权重公式
        distance = 0.1 # 模拟从数据库获取的距离
        score = max(60, int(100 - (distance * 100))) 
        
        reasons = []
        if set(user_profile.preferred_games) & set(candidate.preferred_games):
            reasons.append("常玩游戏高度重合")
        if user_profile.active_time == candidate.active_time:
            reasons.append("作息神同步")
            
        if not reasons:
            reasons.append("AI 语义深度匹配")

        rec = Recommendation(
            user_id=candidate.user_id,
            nickname=candidate.nickname,
            avatar_url=candidate.avatar_url,
            match_score=score,
            match_reasons=reasons,
            conflict=None,
            advice="你们都很看重配合，建议先打两把匹配磨合一下",
            card=BuddyCardBase.model_validate(card) if card else None
        )
        recommendations.append(rec.model_dump(by_alias=True, mode='json'))

    # 5. 写入 Redis 缓存 (覆盖旧推荐数据，过期时间 24 小时)
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_key = f"feed:recommend:{user_id}"
    await redis_client.setex(redis_key, 86400, json.dumps(recommendations))
    await redis_client.close()