import uuid
from sqlalchemy import String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from src.models.base import Base, TimestampMixin, UUIDMixin
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.sql import func

class AgentTuning(Base, TimestampMixin):
    __tablename__ = "agent_tunings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, server_default='false')
    
    intensity: Mapped[int] = mapped_column(Integer, server_default='50')
    reply_length: Mapped[str] = mapped_column(String(20), server_default='MEDIUM')
    focus_scenario: Mapped[str | None] = mapped_column(String(50))
    emotion_tone: Mapped[str | None] = mapped_column(String(50))
    humor_mix: Mapped[str | None] = mapped_column(String(50))
    social_energy: Mapped[str | None] = mapped_column(String(50))
    wit_style: Mapped[str | None] = mapped_column(String(50))
    stance_mode: Mapped[str | None] = mapped_column(String(50))
    initiative_level: Mapped[str | None] = mapped_column(String(50))
    address_style: Mapped[str | None] = mapped_column(String(50))
    
    avatar_style: Mapped[str | None] = mapped_column(String(50))
    avatar_frame: Mapped[str | None] = mapped_column(String(50))
    bubble_style: Mapped[str | None] = mapped_column(String(50))
    voice_mood: Mapped[str | None] = mapped_column(String(50))
    agent_display_name_override: Mapped[str | None] = mapped_column(String(100))
    
    extra_instructions: Mapped[str | None] = mapped_column(String)
    taboo_notes: Mapped[str | None] = mapped_column(String)
    custom_persona_script: Mapped[str | None] = mapped_column(String)
    custom_phrase_1: Mapped[str | None] = mapped_column(String(100))
    custom_phrase_2: Mapped[str | None] = mapped_column(String(100))
    custom_phrase_3: Mapped[str | None] = mapped_column(String(100))

class AgentChatMessage(Base, UUIDMixin):
    __tablename__ = "agent_chat_messages"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20)) # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(String)
    
    # 聊天历史向量化片段
    embedding = mapped_column(Vector(1536))
    
    # 仅需创建时间用于滑动窗口召回
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )