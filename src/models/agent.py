import uuid
from sqlalchemy import String, ForeignKey, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from src.models.base import Base, TimestampMixin, UUIDMixin

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


class AgentChatMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_chat_messages"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20)) # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(String)
    
    # 聊天历史向量化片段
    embedding = mapped_column(Vector(1536))
    
    __table_args__ = (
        # [新增] AI 长期记忆的 HNSW 向量索引
        Index('idx_chat_embedding', 'embedding',
              postgresql_using='hnsw',
              postgresql_with={'m': 16, 'ef_construction': 64},
              postgresql_ops={'embedding': 'vector_cosine_ops'}),
        # [新增] 复合索引：加速拉取某个用户最近的 N 条短时记忆
        Index('idx_agent_chat_user_time', 'user_id', 'created_at'),
    )