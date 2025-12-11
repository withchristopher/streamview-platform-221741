from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., description="Display name of the category")


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int = Field(..., description="Unique category ID")

    class Config:
        from_attributes = True


# Video Schemas
class VideoBase(BaseModel):
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail URL")
    video_url: str = Field(..., description="Public or internal URL to the video file")


class VideoCreate(VideoBase):
    category_ids: Optional[List[int]] = Field(default=None, description="List of category IDs")


class Video(VideoBase):
    id: int = Field(..., description="Unique video ID")
    categories: List[Category] = Field(default_factory=list, description="Categories assigned to the video")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="Full display name")


class UserCreate(UserBase):
    password: str = Field(..., description="Plaintext password for creation (will be hashed)")


class User(UserBase):
    id: int = Field(..., description="Unique user ID")
    created_at: datetime = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True


# Auth payloads (minimal, for later expansion)
class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (usually 'bearer')")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
