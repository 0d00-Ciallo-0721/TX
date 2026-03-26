import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from uuid import UUID
from datetime import datetime, timezone

from src.core.database import get_db, AsyncSessionLocal
from src.core.security import verify_token
from src.api.dependencies import get_current_user
from src.models.user import User, Profile
from src.models.social import Follow, DirectMessage
from src.schemas.social import (
    FollowRequest, WSIncomingAction, WSPushedMessage,
    PublicUserSummary, UserListResponse,
    DMMessage, DMHistoryResponse,
    DMThreadSummary, DMThreadResponse
)
from src.core.ws_manager import ws_manager

router = APIRouter()

# ==========================================
# 1. 社交网络与用户检索
# ==========================================

@router.get("/users", response_model=UserListResponse)
async def search_users(
    q: str = Query(..., min_length=1, description="搜索昵称"),
    db: AsyncSession = Depends(get_db)
):
    """基于昵称模糊搜索用户，供添加搭子使用"""
    stmt = select(Profile).where(Profile.nickname.ilike(f"%{q}%")).limit(20)
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    
    users = [PublicUserSummary(id=p.user_id, nickname=p.nickname, avatar_url=p.avatar_url, bio=p.bio) for p in profiles]
    return UserListResponse(data=users)

@router.get("/users/me/following", response_model=UserListResponse)
async def get_following(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我关注的人的列表"""
    stmt = select(Profile).join(Follow, Follow.following_id == Profile.user_id).where(Follow.follower_id == current_user.id)
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    
    users = [PublicUserSummary(id=p.user_id, nickname=p.nickname, avatar_url=p.avatar_url, bio=p.bio) for p in profiles]
    return UserListResponse(data=users)

@router.post("/follows")
async def follow_user(
    request: FollowRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """关注用户"""
    if current_user.id == request.target_user_id:
        return {"code": 400, "message": "不能关注自己"}
        
    existing = await db.execute(select(Follow).where(
        Follow.follower_id == current_user.id, Follow.following_id == request.target_user_id))
    if not existing.scalars().first():
        db.add(Follow(follower_id=current_user.id, following_id=request.target_user_id))
        await db.commit()
    return {"code": 200, "message": "success", "data": {"success": True}}

@router.delete("/follows/{target_user_id}")
async def unfollow_user(
    target_user_id: UUID, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """取消关注"""
    stmt = select(Follow).where(
        Follow.follower_id == current_user.id, Follow.following_id == target_user_id)
    follow_record = (await db.execute(stmt)).scalars().first()
    if follow_record:
        await db.delete(follow_record)
        await db.commit()
    return {"code": 200, "message": "success", "data": {"success": True}}

# ==========================================
# 2. 离线私信拉取 (持久化)
# ==========================================

@router.get("/dm/threads", response_model=DMThreadResponse)
async def get_dm_threads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """拉取最近的私信会话列表 (聚合联系人与最后一条消息)"""
    # 抽取最近涉及我的 200 条消息，在内存中按 peer_id 聚合以找到最新记录和未读数
    stmt = select(DirectMessage).where(
        or_(DirectMessage.from_user_id == current_user.id, DirectMessage.to_user_id == current_user.id)
    ).order_by(DirectMessage.created_at.desc()).limit(200)
    
    result = await db.execute(stmt)
    recent_msgs = result.scalars().all()
    
    threads = {}
    for msg in recent_msgs:
        peer_id = msg.to_user_id if msg.from_user_id == current_user.id else msg.from_user_id
        
        if peer_id not in threads:
            threads[peer_id] = {
                "peer_user_id": peer_id,
                "last_message_text": msg.text,
                "last_message_at": msg.created_at,
                "unread_count": 0
            }
        
        # 统计发送给我的未读消息
        if msg.to_user_id == current_user.id and not msg.is_read:
            threads[peer_id]["unread_count"] += 1
            
    if not threads:
        return DMThreadResponse(data=[])
        
    # 批量拉取联系人的画像
    peer_ids = list(threads.keys())
    profiles_stmt = select(Profile).where(Profile.user_id.in_(peer_ids))
    profiles_result = await db.execute(profiles_stmt)
    profiles = profiles_result.scalars().all()
    profile_map = {p.user_id: p for p in profiles}
    
    response_data = []
    for peer_id, t_data in threads.items():
        p = profile_map.get(peer_id)
        t_data["peer_nickname"] = p.nickname if p else "未知搭子"
        t_data["peer_avatar"] = p.avatar_url if p else None
        response_data.append(DMThreadSummary(**t_data))
        
    # 按最后发信时间降序排序
    response_data.sort(key=lambda x: x.last_message_at, reverse=True)
    
    return DMThreadResponse(data=response_data)

@router.get("/dm/{peer_user_id}/messages", response_model=DMHistoryResponse)
async def get_dm_history(
    peer_user_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """按时间倒序拉取与某人的聊天记录，并顺带标记为已读"""
    stmt = select(DirectMessage).where(
        or_(
            and_(DirectMessage.from_user_id == current_user.id, DirectMessage.to_user_id == peer_user_id),
            and_(DirectMessage.from_user_id == peer_user_id, DirectMessage.to_user_id == current_user.id)
        )
    ).order_by(DirectMessage.created_at.desc()).offset((page-1)*size).limit(size+1)
    
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    has_more = len(messages) > size
    msgs_to_return = messages[:size]
    
    # 将接收到的且未读的消息标记为已读
    unread_msgs = [m for m in msgs_to_return if m.to_user_id == current_user.id and not m.is_read]
    if unread_msgs:
        for m in unread_msgs:
            m.is_read = True
        await db.commit()

    return DMHistoryResponse(data={
        "list": [DMMessage.model_validate(m).model_dump(by_alias=True) for m in msgs_to_return],
        "hasMore": has_more
    })

# ==========================================
# 3. 实时私信 WebSocket
# ==========================================

@router.websocket("/ws/dm")
async def websocket_dm(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token 用于鉴权")
):
    # 1. 鉴权：WebSocket 握手阶段手动解析 Token
    user_payload = await verify_token(token) # 需自行在 security.py 提供此解密函数
    if not user_payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    current_user_id = UUID(user_payload.get("sub"))
    await ws_manager.connect(websocket, current_user_id)
    
    # 获取独立 DB Session 用于 WebSocket 生命周期内的查询
    db: AsyncSession = AsyncSessionLocal()

    try:
        while True:
            # 接收客户端发来的数据
            text_data = await websocket.receive_text()
            try:
                action_data = WSIncomingAction.model_validate_json(text_data)
            except Exception:
                await ws_manager.send_error(websocket, 400, "消息格式无效")
                continue

            if action_data.action == "send_message":
                to_user_id = action_data.payload.to_user_id
                
                # --- 风控校验：未互关状态下只能发送 1 条消息 ---
                # A 关注 B
                a_follows_b = await db.execute(select(Follow).where(
                    Follow.follower_id == current_user_id, Follow.following_id == to_user_id))
                # B 关注 A
                b_follows_a = await db.execute(select(Follow).where(
                    Follow.follower_id == to_user_id, Follow.following_id == current_user_id))
                
                is_mutual = a_follows_b.scalars().first() and b_follows_a.scalars().first()
                
                if not is_mutual:
                    msg_count = await db.execute(select(func.count()).select_from(DirectMessage).where(
                        DirectMessage.from_user_id == current_user_id, DirectMessage.to_user_id == to_user_id))
                    if msg_count.scalar() >= 1:
                        await ws_manager.send_error(websocket, 403, "未互关状态下只能发送1条消息")
                        continue

                # --- 消息落库 ---
                new_dm = DirectMessage(
                    from_user_id=current_user_id,
                    to_user_id=to_user_id,
                    text=action_data.payload.text
                )
                db.add(new_dm)
                await db.commit()
                await db.refresh(new_dm)
                
                # --- 组装推送数据并进行全局路由 ---
                push_msg = WSPushedMessage(
                    id=new_dm.id,
                    from_user_id=current_user_id,
                    text=new_dm.text,
                    sent_at=new_dm.created_at.isoformat() + "Z"
                )
                # 推送给接收方 (跨实例)
                await ws_manager.route_message(to_user_id, push_msg)
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, current_user_id)
    finally:
        await db.close()