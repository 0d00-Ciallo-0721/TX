import uuid
from sqlalchemy import String, ForeignKey, Boolean, Integer, Index, Text
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
        Index('idx_chat_embedding', 'embedding',
              postgresql_using='hnsw',
              postgresql_with={'m': 16, 'ef_construction': 64},
              postgresql_ops={'embedding': 'vector_cosine_ops'}),
        Index('idx_agent_chat_user_time', 'user_id', 'created_at'),
    )


class GameKnowledgeBase(Base, UUIDMixin, TimestampMixin):
    """全局游戏知识库 (用于原生 RAG)"""
    __tablename__ = "game_knowledge_base"

    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True) # 如: 'apex_guide', 'lol_meta'
    embedding = mapped_column(Vector(1536)) # 文档向量化

    __table_args__ = (
        Index('idx_kb_embedding', 'embedding',
              postgresql_using='hnsw',
              postgresql_with={'m': 16, 'ef_construction': 64},
              postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )


class UserMemoryInsight(Base, UUIDMixin, TimestampMixin):
    """AI 总结提炼的用户长期高价值记忆"""
    __tablename__ = "user_memory_insights"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    insight_text: Mapped[str] = mapped_column(Text) # 例如: "用户习惯在深夜打排位，主玩软辅"
    embedding = mapped_column(Vector(1536))

    __table_args__ = (
        Index('idx_memory_insight_embedding', 'embedding',
              postgresql_using='hnsw',
              postgresql_with={'m': 16, 'ef_construction': 64},
              postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )