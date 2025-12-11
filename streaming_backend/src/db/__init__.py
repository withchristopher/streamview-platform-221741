"""
Database package initializer exposing common objects for easier imports.
"""

from .session import Base, engine, SessionLocal, get_db
from .models import User, Video, Category, VideoCategory, WatchHistory  # noqa: F401

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "User",
    "Video",
    "Category",
    "VideoCategory",
    "WatchHistory",
]
