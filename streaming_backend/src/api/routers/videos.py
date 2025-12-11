from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.services.video_service import get_video, list_videos
from src.db.schemas import Video as VideoSchema
from src.db.session import get_db

router = APIRouter()


# PUBLIC_INTERFACE
@router.get(
    "/",
    response_model=List[VideoSchema],
    summary="List videos",
    description=(
        "List videos with optional full-text search on title and category filtering. "
        "Supports `category_id` (preferred) and `category` (alias) for compatibility."
    ),
    tags=["videos"],
)
def list_all_videos(
    q: Optional[str] = Query(
        default=None,
        description="Search term applied to video title (case-insensitive contains).",
    ),
    category_id: Optional[int] = Query(
        default=None,
        description="Numeric category ID to filter videos.",
    ),
    category: Optional[Union[int, str]] = Query(
        default=None,
        description=(
            "Alias for category filtering. If an integer-like value is provided, it will "
            "be interpreted as `category_id` for backwards compatibility."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    List videos with optional search and category filter.

    Query Parameters:
        q: Search term applied to the video title.
        category_id: Category ID filter (preferred).
        category: Compatibility alias, treated as `category_id` when it is an integer.
    """
    # For compatibility, if `category_id` is not provided but `category` is an int-like
    # value, use it as `category_id`.
    if category_id is None and category is not None:
        try:
            category_id = int(category)
        except (TypeError, ValueError):
            # If not int-like, ignore and just rely on q or no filter.
            category_id = None

    vids = list_videos(db, q=q, category_id=category_id)
    return vids


# PUBLIC_INTERFACE
@router.get("/{video_id}", response_model=VideoSchema, summary="Get video by ID", tags=["videos"])
def get_video_by_id(video_id: int, db: Session = Depends(get_db)):
    """
    Get video metadata by ID.
    """
    vid = get_video(db, video_id)
    if not vid:
        raise HTTPException(status_code=404, detail="Video not found")
    return vid
