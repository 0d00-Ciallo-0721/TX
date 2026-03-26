import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from datetime import datetime, timezone

from src.core.database import get_db, AsyncSessionLocal
from src.core.security import verify_token  # 假设你有一个解析 JWT 的函数
from src.api.dependencies import get_current_user
from src.models.user import User
from src.models.social import Follow, DirectMessage
from src.schemas.social import FollowRequest, WSIncomingAction, WSPushedMessage
from src.core.ws_manager import ws_manager

router = APIRouter()

# --- 1. 关注与取关接口 ---

@router.post("/follows")
async def follow_user(
    request: FollowRequest, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
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
    stmt = select(Follow).where(
        Follow.follower_id == current_user.id, Follow.following_id == target_user_id)
    follow_record = (await db.execute(stmt)).scalars().first()
    if follow_record:
        await db.delete(follow_record)
        await db.commit()
    return {"code": 200, "message": "success", "data": {"success": True}}

# --- 2. 实时私信 WebSocket ---

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