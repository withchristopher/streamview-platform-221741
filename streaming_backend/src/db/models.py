from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base

# Association table for many-to-many Video <-> Category
VideoCategory = Table(
    "video_category",
    Base.metadata,
    Column("video_id", ForeignKey("videos.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
    UniqueConstraint("video_id", "category_id", name="uq_video_category"),
)


class User(Base):
    """
    Application user model. Minimal fields for seeding and future auth.
    The password is stored as a hash (pbkdf2_sha256).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    watch_history: Mapped[List["WatchHistory"]] = relationship(
        "WatchHistory", back_populates="user", cascade="all, delete-orphan"
    )


class Video(Base):
    """
    Video metadata including URLs and thumbnails.
    """

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Many-to-many with categories
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        secondary=VideoCategory,
        back_populates="videos",
    )

    # Watch history backref
    watch_history: Mapped[List["WatchHistory"]] = relationship(
        "WatchHistory", back_populates="video", cascade="all, delete-orphan"
    )


class Category(Base):
    """
    Video categories (Action, Drama, Documentary, etc).
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    videos: Mapped[List[Video]] = relationship(
        "Video",
        secondary=VideoCategory,
        back_populates="categories",
    )


class WatchHistory(Base):
    """
    Optional watch history model linking users to videos with timestamps and progress.
    """

    __tablename__ = "watch_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    video_id: Mapped[int] = mapped_column(Integer, ForeignKey("videos.id"), index=True, nullable=False)
    watched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    progress_seconds: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User", back_populates="watch_history")
    video: Mapped[Video] = relationship("Video", back_populates="watch_history")

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_user_video_once"),
    )
