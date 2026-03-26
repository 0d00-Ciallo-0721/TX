from src.models.base import Base
from src.models.user import User, Profile, BuddyCard
from src.models.agent import AgentTuning, AgentChatMessage

# 确保 Alembic 在执行 env.py 时能扫描到这些类的 metadata
__all__ = ["Base", "User", "Profile", "BuddyCard", "AgentTuning", "AgentChatMessage"]