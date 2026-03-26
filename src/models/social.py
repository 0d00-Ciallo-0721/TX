import uuid
from sqlalchemy import String, ForeignKey, Boolean, Text, Index
from sqlalchemy import text as sa_text  # [修复] 起个别名，避免与下方字段名冲突
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from src.models.base import Base, TimestampMixin, UUIDMixin

class Follow(Base, TimestampMixin):
    __tablename__ = "follows"

    follower_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)

class DirectMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "direct_messages"

    from_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    to_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)  # 这里是字段名 text
    is_read: Mapped[bool] = mapped_column(Boolean, server_default='false')

    __table_args__ = (
        # [修复] 使用别名 sa_text 调用 SQLAlchemy 的函数
        Index('idx_dm_thread', 'from_user_id', 'to_user_id', sa_text('created_at DESC')),
    )

# ==========================================
# 新增: 搭子申请表 (阶段四)
# ==========================================
class BuddyRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "buddy_requests"

    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    receiver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default='PENDING') # 状态: PENDING, ACCEPTED, REJECTED

    __table_args__ = (
        # 加速接收方查询待处理申请的索引
        Index('idx_buddy_req_receiver', 'receiver_id', 'status'),
    )