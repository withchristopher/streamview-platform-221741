from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.services.video_service import list_categories
from src.db.schemas import Category as CategorySchema
from src.db.session import get_db

router = APIRouter()


# PUBLIC_INTERFACE
@router.get("/", response_model=List[CategorySchema], summary="List categories", tags=["categories"])
def get_categories(db: Session = Depends(get_db)):
    """
    Return all categories.
    """
    cats = list_categories(db)
    return cats
