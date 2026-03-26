from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from fastapi.logger import logger

from src.core.config import settings

# 工业级异步引擎配置
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 生产环境务必保持为 False
    future=True,
    # --- 工业级连接池强化 ---
    pool_size=20,          # 核心连接数（根据你的 Postgres max_connections 调整）
    max_overflow=10,       # 流量突发时允许额外创建的连接数
    pool_timeout=30,       # 获取连接的最长等待时间(秒)
    pool_recycle=1800,     # 30分钟回收一次连接，防止数据库端掐断长连接导致 MySQL/PG "gone away"
    pool_pre_ping=True,    # 每次从池中拿连接前 ping 一下，确保网络没断
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ORM 基类
Base = declarative_base()

# 数据库依赖注入 (带严格事务回滚)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # 注意: 这里不主动 commit，因为业务端可能有更细粒度的事务控制需求
        except SQLAlchemyError as e:
            # 捕获所有 DB 层面错误，确保发生异常时彻底回滚脏事务
            await session.rollback()
            logger.error(f"Database session rollback due to error: {e}")
            raise
        finally:
            # 确保连接归还给连接池
            await session.close()