from typing import List, Tuple

from passlib.hash import pbkdf2_sha256
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Category, User, Video
from .session import Base, engine


def _get_or_create_category(db: Session, name: str) -> Category:
    existing = db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
    if existing:
        return existing
    cat = Category(name=name)
    db.add(cat)
    db.flush()
    return cat


def _get_or_create_user(db: Session, email: str, password_plain: str, full_name: str) -> User:
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        email=email,
        password_hash=pbkdf2_sha256.hash(password_plain),
        full_name=full_name,
    )
    db.add(user)
    db.flush()
    return user


def _get_or_create_video(
    db: Session,
    title: str,
    description: str,
    thumbnail_url: str,
    video_url: str,
    categories: List[Category],
) -> Video:
    existing = db.execute(select(Video).where(Video.title == title)).scalar_one_or_none()
    if existing:
        # ensure categories linked
        for c in categories:
            if c not in existing.categories:
                existing.categories.append(c)
        return existing
    vid = Video(
        title=title,
        description=description,
        thumbnail_url=thumbnail_url,
        video_url=video_url,
        categories=categories,
    )
    db.add(vid)
    db.flush()
    return vid


# PUBLIC_INTERFACE
def init_db_and_seed(db: Session) -> Tuple[int, int, int]:
    """
    Initialize database (create tables) and seed minimal data.

    Args:
        db: SQLAlchemy session

    Returns:
        tuple: (users_count_added_or_existing, categories_count, videos_count)
    """
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)

    # Seed a default user
    user = _get_or_create_user(
        db=db,
        email="demo@streamview.local",
        password_plain="demopassword",
        full_name="Demo User",
    )

    # Seed categories
    category_names = ["Action", "Drama", "Documentary"]
    categories = [ _get_or_create_category(db, name) for name in category_names ]

    # Public small MP4 sample URLs (commonly used sample videos)
    samples = [
        (
            "Big Buck Bunny - Short Clip",
            "A short open movie clip for testing playback.",
            "https://peach.blender.org/wp-content/uploads/title_anouncement.jpg?x11217",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            ["Action"],
        ),
        (
            "Sintel Trailer",
            "Trailer of Blender Foundation's Sintel.",
            "https://download.blender.org/durian/trailer/sintel_trailer-720p.jpg",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
            ["Drama"],
        ),
        (
            "Tears of Steel - Short",
            "Open movie by Blender Institute.",
            "https://mango.blender.org/wp-content/uploads/2013/05/Tears-of-Steel.jpg?x11217",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
            ["Action", "Documentary"],
        ),
        (
            "For Bigger Joyrides",
            "Sample video from Google.",
            "https://i.ytimg.com/vi/7QUtEmBT_-w/maxresdefault.jpg",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
            ["Documentary"],
        ),
        (
            "For Bigger Meltdowns",
            "Another sample video from Google.",
            "https://i.ytimg.com/vi/68d7dS5-0Iw/maxresdefault.jpg",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
            ["Action", "Drama"],
        ),
    ]

    # Map category names to Category objects
    cat_map = {c.name: c for c in categories}

    for title, desc, thumb, url, cat_names in samples:
        cats = [cat_map[name] for name in cat_names if name in cat_map]
        _get_or_create_video(db, title, desc, thumb, url, cats)

    # Return counts
    users_count = 1 if user else 0
    return users_count, len(categories), len(samples)
