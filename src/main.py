from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.routes import auth, ai_tools, upload, profile, agent, agent_chat, forum, social, feed


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

    application.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["1. 通行证与账号 (Auth)"])
    application.include_router(profile.router, prefix=f"{settings.API_V1_STR}/profiles", tags=["2. 用户画像与同步 (Profile)"])
    application.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["3. 智能体配置 (Agent Config)"])
    
    # [新增] 注册智能体对话流路由
    application.include_router(
        agent_chat.router,
        prefix=f"{settings.API_V1_STR}/ai/agent",
        tags=["4. AI 对话引擎 (Agent Chat)"]
    )
    
    application.include_router(
        forum.router,
        prefix=f"{settings.API_V1_STR}/forum",
        tags=["5. 社区广场 (Forum)"]
    )

    application.include_router(
        social.router,
        prefix=f"{settings.API_V1_STR}",
        tags=["6. 社交与私信 (Social & DM)"]
    )

    application.include_router(
        feed.router,
        prefix=f"{settings.API_V1_STR}",
        tags=["7. 发现与推荐 (Feed & Recommendation)"]
    )

    application.include_router(
        ai_tools.router,
        prefix=f"{settings.API_V1_STR}/ai/tools",
        tags=["8. AI 工具引擎 (AI Tools)"]
    )

    application.include_router(
        upload.router,
        prefix=f"{settings.API_V1_STR}/uploads",
        tags=["9. 媒体与存储 (Uploads & Media)"]
    )

    @application.get("/health", tags=["System"])
    async def health_check():
        return {"status": "ok", "message": "TX_ku backend is running."}


    return application

app = get_application()