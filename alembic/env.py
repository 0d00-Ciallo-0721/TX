import sys
import os
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# 动态将项目根目录加入 Python 搜索路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Base
from src.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True  # 开启自动比对类型变化
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """异步模式迁移逻辑"""
    # 拦截并强制覆盖 sqlalchemy.url
    ini_section = config.get_section(config.config_ini_section, {})
    ini_section["sqlalchemy.url"] = settings.DATABASE_URL
    
    connectable = async_engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, 
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """在线模式迁移入口"""
    asyncio.run(run_async_migrations())

def run_migrations_offline() -> None:
    """离线模式迁移逻辑"""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()