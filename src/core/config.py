from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "TX_ku (同频搭) API"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:a52651794@127.0.0.1:5432/tx_ku?ssl=disable"
    
    # [新增] Redis 配置 (用于 WebSocket Pub/Sub 和推荐系统缓存)
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    
    # Security
    SECRET_KEY: str = "a52651794"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        env_file = ".env"

settings = Settings()