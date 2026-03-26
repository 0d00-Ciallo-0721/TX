# 添加导入
from src.api.routes import auth, profile, agent, agent_chat, forum 

def get_application() -> FastAPI:
    # ... 原有代码保持不变 ...

    # [新增] 注册广场与社区路由
    application.include_router(
        forum.router,
        prefix=f"{settings.API_V1_STR}/forum",
        tags=["5. 社区广场 (Forum)"]
    )
    
    # ... 原有代码保持不变 ...