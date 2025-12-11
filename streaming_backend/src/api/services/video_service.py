from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.db.models import Category, Video


def list_videos(db: Session, q: Optional[str] = None, category_id: Optional[int] = None) -> List[Video]:
    """
    List videos optionally filtering by search query and/or category.
    """
    stmt = select(Video).options(joinedload(Video.categories)).order_by(Video.created_at.desc())
    if q:
        # naive filtering by title contains
        stmt = stmt.where(Video.title.ilike(f"%{q}%"))
    if category_id:
        stmt = stmt.join(Video.categories).where(Category.id == category_id)
    return list(db.execute(stmt).scalars().all())


def get_video(db: Session, video_id: int) -> Optional[Video]:
    """
    Fetch a single video by ID, including categories.
    """
    stmt = select(Video).options(joinedload(Video.categories)).where(Video.id == video_id)
    return db.execute(stmt).scalar_one_or_none()


def list_categories(db: Session) -> List[Category]:
    """
    Return all categories ordered by name.
    """
    stmt = select(Category).order_by(Category.name.asc())
    return list(db.execute(stmt).scalars().all())
