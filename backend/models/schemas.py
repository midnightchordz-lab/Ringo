"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict


# ==================== AUTH MODELS ====================
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: str


# ==================== VIDEO MODELS ====================
class VideoMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    channel: str
    thumbnail: str
    duration: int
    views: int
    likes: int
    comments: int
    viral_score: float
    upload_date: str
    license: str


class ClipRequest(BaseModel):
    video_id: str
    start_time: int = 0
    duration: int = 45
    use_ai_analysis: bool = True


class PostRequest(BaseModel):
    clip_id: str
    caption: str
    platforms: List[str]
    hashtags: Optional[str] = ""


class APIKeysModel(BaseModel):
    youtube_api_key: Optional[str] = None
    instagram_access_token: Optional[str] = None


# ==================== IMAGE MODELS ====================
class ImageFavorite(BaseModel):
    image_id: str
    image_data: Dict


# ==================== CONTENT LIBRARY MODELS ====================
class ContentFavorite(BaseModel):
    resource_id: str
    name: str
    description: Optional[str] = ""
    url: str
    logo: Optional[str] = ""
    categories: List[str] = []
    levels: List[str] = []
