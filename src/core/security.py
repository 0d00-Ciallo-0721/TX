from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from src.core.config import settings

# 使用 bcrypt 算法进行密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

# [修复] 参数改为 data: dict，对齐 auth.py 的调用逻辑
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """签发 JWT Access Token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 将过期时间合并到 payload (data) 中
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码是否与哈希密码匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """将明文密码转化为哈希值"""
    return pwd_context.hash(password)

async def verify_token(token: str) -> Optional[dict]:
    """
    异步解密并校验 JWT Token。
    验证通过返回 payload 字典 (如 {"sub": "user_id", "exp": 12345678})
    验证失败 (过期/篡改) 返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None