from src.models.base import Base
from src.models.user import User, Profile, BuddyCard
from src.models.agent import AgentTuning, AgentChatMessage
from src.models.forum import Post, Comment, PostLike, PostBookmark
from src.models.social import Follow, DirectMessage

# 确保 Alembic 在执行 env.py 时能扫描到这些类的 metadata
__all__ = [
    "Base", "User", "Profile", "BuddyCard", 
    "AgentTuning", "AgentChatMessage",
    "Post", "Comment", "PostLike", "PostBookmark",
    "Follow", "DirectMessage"
]