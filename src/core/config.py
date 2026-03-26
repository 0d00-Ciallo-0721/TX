from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "TX_ku (同频搭) API"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    # 已修正密码为 a52651794，并添加了 ssl=disable 以增强 Windows 环境下的稳定性
    DATABASE_URL: str = "postgresql+asyncpg://postgres:a52651794@127.0.0.1:5432/tx_ku?ssl=disable"
    
    # Security
    SECRET_KEY: str = "a52651794"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    class Config:
        env_file = ".env"

settings = Settings()