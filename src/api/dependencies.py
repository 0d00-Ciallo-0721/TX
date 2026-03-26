import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import ValidationError

from src.core.config import settings
from src.core.database import get_db
from src.models.user import User

# 定义 OAuth2 规范的 Token 提取器
# 注意: 这里的 tokenUrl 仅用于 Swagger UI 自动生成鉴权界面的指示
# 我们的真实 /login 接口按 Android 契约接收 JSON 而非 Form Data
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scheme_name="JWT"
)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    核心鉴权依赖项 (供私有 API 路由使用)：
    1. 提取并校验 JWT 令牌
    2. 查询关联的真实数据库用户
    3. 拦截异常与被封禁状态
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证或 Token 已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. 解码 JWT，自动校验有效期 (exp) 和签名
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except (jwt.PyJWTError, ValidationError):
        # 捕获所有 JWT 解析错误（过期、篡改、格式错误）
        raise credentials_exception
        
    # 2. 从数据库获取该用户
    # 使用 uuid 字符串进行匹配，SQLAlchemy 的 PostgreSQL 方言会自动处理类型转换
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    # 3. 拦截非活跃用户 (例如风控封禁系统将 status 改为 'BANNED')
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="账号已被封禁或处于非活跃状态"
        )
        
    return user