from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.routes import auth, profile

# TODO: 引入其他模块的路由 (Agent, Feed, Social)

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        description="同频搭 (TX_ku) 生产级后端 API"
    )

    # CORS 配置 (允许 Android 客户端和 Web 调试)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # 生产环境建议替换为具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    application.include_router(
        auth.router, 
        prefix=f"{settings.API_V1_STR}/auth", 
        tags=["1. 通行证与账号 (Auth)"]
    )
    
    # [新增] 注册 Profile 画像路由
    application.include_router(
        profile.router,
        prefix=f"{settings.API_V1_STR}/profiles",
        tags=["2. 用户画像与同步 (Profile)"]
    )
    
    # 健康检查
    @application.get("/health", tags=["System"])
    async def health_check():
        return {"status": "ok", "message": "TX_ku backend is running."}

    return application

app = get_application()