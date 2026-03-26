from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.routes import auth, profile, agent  # <-- 新增导入 agent

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="同频搭 (TX_ku) 生产级后端 API"
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(
        auth.router, 
        prefix=f"{settings.API_V1_STR}/auth", 
        tags=["1. 通行证与账号 (Auth)"]
    )
    
    application.include_router(
        profile.router,
        prefix=f"{settings.API_V1_STR}/profiles",
        tags=["2. 用户画像与同步 (Profile)"]
    )
    
    # [新增] 注册智能体路由
    application.include_router(
        agent.router,
        prefix=f"{settings.API_V1_STR}/agent",
        tags=["3. 智能体 (Agent)"]
    )
    
    @application.get("/health", tags=["System"])
    async def health_check():
        return {"status": "ok", "message": "TX_ku backend is running."}

    return application

app = get_application()