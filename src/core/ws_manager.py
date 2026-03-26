import asyncio
import json
from typing import Dict, List
from uuid import UUID
from fastapi import WebSocket
import redis.asyncio as redis

from src.core.config import settings
from src.schemas.social import WSOutgoingEvent, WSPushedMessage, WSErrorData

class ConnectionManager:
    def __init__(self):
        # 维护本地实例的 WebSocket 连接字典: {user_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[UUID, List[WebSocket]] = {}
        # 共享的 Redis 客户端
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        self.listener_task = None

    async def connect(self, websocket: WebSocket, user_id: UUID):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
            # 首次连接时，订阅该用户的专属 Redis 频道
            await self.pubsub.subscribe(f"user:{user_id}:dm")
            
            # 启动后台监听任务 (单例)
            if self.listener_task is None:
                self.listener_task = asyncio.create_task(self._listen_to_redis())
                
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: UUID):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # 生产环境可选：取消订阅以节省资源，但需结合 asyncio.gather 异步处理
                # asyncio.create_task(self.pubsub.unsubscribe(f"user:{user_id}:dm"))

    async def send_error(self, websocket: WebSocket, code: int, message: str):
        """下发阻断错误信息 (如未互关拦截)"""
        error_event = WSOutgoingEvent(event="error", data=WSErrorData(code=code, message=message))
        await websocket.send_text(error_event.model_dump_json())

    async def route_message(self, target_user_id: UUID, message_data: WSPushedMessage):
        """核心路由：将消息推入 Redis，由全网实例接收"""
        event = WSOutgoingEvent(event="new_message", data=message_data)
        await self.redis_client.publish(f"user:{target_user_id}:dm", event.model_dump_json(by_alias=True))

    async def _listen_to_redis(self):
        """后台常驻任务：监听 Redis Pub/Sub，并将消息分发给本地连接的对应 WebSocket"""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                data = message["data"]
                
                # 从频道名 user:{user_id}:dm 提取 user_id
                target_user_id_str = channel.split(":")[1]
                target_user_id = UUID(target_user_id_str)
                
                # 如果这个用户正好连在当前服务器实例上，则发送给他
                if target_user_id in self.active_connections:
                    dead_sockets = []
                    for ws in self.active_connections[target_user_id]:
                        try:
                            await ws.send_text(data)
                        except Exception:
                            dead_sockets.append(ws)
                    
                    # 清理死连接
                    for ws in dead_sockets:
                        self.disconnect(ws, target_user_id)

ws_manager = ConnectionManager()