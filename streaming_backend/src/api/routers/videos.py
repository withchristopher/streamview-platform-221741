from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.services.video_service import get_video, list_videos
from src.db.schemas import Video as VideoSchema
from src.db.session import get_db

router = APIRouter()


# PUBLIC_INTERFACE
@router.get("/", response_model=List[VideoSchema], summary="List videos", tags=["videos"])
def list_all_videos(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List videos with optional search and category filter.

    Query Parameters:
        q: search term (on title)
        category_id: category filter
    """
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
