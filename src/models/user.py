import uuid
from sqlalchemy import String, ForeignKey
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

    # 关联
    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    buddy_card: Mapped["BuddyCard"] = relationship("BuddyCard", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String)
    bio: Mapped[str | None] = mapped_column(String)
    city_or_region: Mapped[str | None] = mapped_column(String(100))
    
    # 动态标签与偏好 (JSONB)
    preferred_games: Mapped[dict | list] = mapped_column(JSONB, server_default='[]')
    rank: Mapped[str | None] = mapped_column(String(50))
    active_time: Mapped[dict | list] = mapped_column(JSONB, server_default='[]')
    main_roles: Mapped[dict | list] = mapped_column(JSONB, server_default='[]')
    play_style: Mapped[str | None] = mapped_column(String(50))
    target: Mapped[str | None] = mapped_column(String(50))
    voice_pref: Mapped[str | None] = mapped_column(String(50))
    no_gos: Mapped[dict | list] = mapped_column(JSONB, server_default='[]')
    
    # 智能体基底
    personality_archetype: Mapped[str | None] = mapped_column(String(50))
    agent_voice_pref: Mapped[str | None] = mapped_column(String(50))
    agent_visual_theme: Mapped[str | None] = mapped_column(String(100))
    favorite_esports_hint: Mapped[str | None] = mapped_column(String)
    pro_persona_style: Mapped[str | None] = mapped_column(String(100))
    
    # AI 向量检索特征
    profile_embedding = mapped_column(Vector(1536))

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="profile")

class BuddyCard(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "buddy_cards"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    tags: Mapped[dict | list] = mapped_column(JSONB, server_default='[]')
    declaration: Mapped[str | None] = mapped_column(String)
    rules: Mapped[dict | list] = mapped_column(JSONB, server_default='[]')
    pro_persona_label: Mapped[str | None] = mapped_column(String(100))
    favorite_esports_hint: Mapped[str | None] = mapped_column(String)
    base_match_score: Mapped[int] = mapped_column(server_default='0')

    user: Mapped["User"] = relationship("User", back_populates="buddy_card")