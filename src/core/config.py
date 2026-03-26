from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "TX_ku (同频搭) API"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    # 默认连接本地 PostgreSQL，实际生产环境需通过环境变量覆盖
    DATABASE_URL: str = "postgresql+asyncpg://postgres:a52651794password@127.0.0.1:5432/tx_ku"
    
    # Security
    SECRET_KEY: str = "a52651794"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        env_file = ".env"

settings = Settings()