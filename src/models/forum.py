import uuid
from sqlalchemy import String, ForeignKey, Boolean, Integer, Text, text 
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.models.base import Base, TimestampMixin, UUIDMixin

class Post(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "posts"

    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    
    # 媒体资源：例如 [{"url": "https://oss.../x.jpg", "type": "image"}]
    media_attachments: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    
    # 审核流状态
    moderation_status: Mapped[str] = mapped_column(String(50), server_default='PENDING_REVIEW')
    moderation_hint: Mapped[str | None] = mapped_column(Text)
    
    reply_count: Mapped[int] = mapped_column(Integer, server_default='0')
    like_count: Mapped[int] = mapped_column(Integer, server_default='0')
    is_pinned: Mapped[bool] = mapped_column(Boolean, server_default='false')

    # 关联
    author = relationship("User")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

class Comment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "comments"

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)

    # 关联
    post = relationship("Post", back_populates="comments")
    author = relationship("User")

class PostLike(Base, TimestampMixin):
    """帖子点赞表 (避免重复点赞)"""
    __tablename__ = "post_likes"

    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

class PostBookmark(Base, TimestampMixin):
    """帖子收藏表"""
    __tablename__ = "post_bookmarks"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)