import uuid
# [修复] 确保包含了 text
from sqlalchemy import String, ForeignKey, text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from src.models.base import Base, TimestampMixin, UUIDMixin

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    reg_nickname: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), server_default='ACTIVE')

    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    buddy_card: Mapped["BuddyCard"] = relationship("BuddyCard", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String)
    bio: Mapped[str | None] = mapped_column(String)
    city_or_region: Mapped[str | None] = mapped_column(String(100))
    
    # [修复] JSONB 默认值必须指定 ::jsonb 强转
    preferred_games: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    rank: Mapped[str | None] = mapped_column(String(50))
    active_time: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    main_roles: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    play_style: Mapped[str | None] = mapped_column(String(50))
    target: Mapped[str | None] = mapped_column(String(50))
    voice_pref: Mapped[str | None] = mapped_column(String(50))
    no_gos: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    
    personality_archetype: Mapped[str | None] = mapped_column(String(50))
    agent_voice_pref: Mapped[str | None] = mapped_column(String(50))
    agent_visual_theme: Mapped[str | None] = mapped_column(String(100))
    favorite_esports_hint: Mapped[str | None] = mapped_column(String)
    pro_persona_style: Mapped[str | None] = mapped_column(String(100))
    
    profile_embedding = mapped_column(Vector(1536))

    user: Mapped["User"] = relationship("User", back_populates="profile")

    # [新增] 向量的 HNSW 索引，使用余弦相似度优化
    __table_args__ = (
        Index('idx_profile_embedding', 'profile_embedding',
              postgresql_using='hnsw',
              postgresql_with={'m': 16, 'ef_construction': 64},
              postgresql_ops={'profile_embedding': 'vector_cosine_ops'}),
    )

class BuddyCard(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "buddy_cards"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    # [修复]
    tags: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    declaration: Mapped[str | None] = mapped_column(String)
    rules: Mapped[dict | list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    pro_persona_label: Mapped[str | None] = mapped_column(String(100))
    favorite_esports_hint: Mapped[str | None] = mapped_column(String)
    base_match_score: Mapped[int] = mapped_column(server_default='0')

    user: Mapped["User"] = relationship("User", back_populates="buddy_card")