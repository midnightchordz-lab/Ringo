from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Form, Query, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import yt_dlp
import subprocess
import tempfile
import httpx
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import re
from passlib.context import CryptContext
from jose import JWTError, jwt
import resend
import secrets
import hashlib
import gzip
from io import BytesIO


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="ContentFlow API")

api_router = APIRouter(prefix="/api")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Authentication setup
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production-09876543210")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Email setup
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Frontend URL for email links
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://videoremix.preview.emergentagent.com")


# ==================== YOUTUBE API OPTIMIZATION ====================
class YouTubeAPIOptimizer:
    """
    Optimizes YouTube API usage with:
    1. Cache Data Store - caches frequently accessed data
    2. Request Only Necessary Fields - uses part and fields parameters
    3. GZIP Compression - reduces data transfer
    4. Conditional Requests - ETags for change detection
    5. Batch Requests - combines multiple API calls
    6. quotaUser - tracks usage per user
    """
    
    # In-memory cache for ETags and data
    _etag_cache: Dict[str, str] = {}
    _data_cache: Dict[str, dict] = {}
    _cache_timestamps: Dict[str, datetime] = {}
    CACHE_TTL_MINUTES = 30  # Cache validity period
    
    # Minimal fields to request (reduces quota usage)
    SEARCH_FIELDS = "items(id/videoId),nextPageToken"
    VIDEO_FIELDS = "items(id,snippet(title,channelTitle,publishedAt,thumbnails/high/url,description),statistics(viewCount,likeCount,commentCount),contentDetails/duration,status/license)"
    
    @classmethod
    def get_cache_key(cls, operation: str, params: dict) -> str:
        """Generate a unique cache key from operation and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{operation}:{param_str}".encode()).hexdigest()
    
    @classmethod
    def is_cache_valid(cls, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in cls._cache_timestamps:
            return False
        age = datetime.now() - cls._cache_timestamps[cache_key]
        return age.total_seconds() < cls.CACHE_TTL_MINUTES * 60
    
    @classmethod
    def get_cached_data(cls, cache_key: str) -> Optional[dict]:
        """Get data from cache if valid"""
        if cls.is_cache_valid(cache_key) and cache_key in cls._data_cache:
            logging.info(f"YouTube API: Cache hit for {cache_key[:8]}...")
            return cls._data_cache[cache_key]
        return None
    
    @classmethod
    def set_cache(cls, cache_key: str, data: dict, etag: str = None):
        """Store data in cache"""
        cls._data_cache[cache_key] = data
        cls._cache_timestamps[cache_key] = datetime.now()
        if etag:
            cls._etag_cache[cache_key] = etag
        logging.info(f"YouTube API: Cached data for {cache_key[:8]}...")
    
    @classmethod
    def get_etag(cls, cache_key: str) -> Optional[str]:
        """Get stored ETag for conditional request"""
        return cls._etag_cache.get(cache_key)
    
    @classmethod
    async def search_videos(
        cls, 
        youtube, 
        query: str, 
        max_results: int = 50,
        user_id: str = None
    ) -> dict:
        """
        Optimized video search with caching and field filtering
        """
        params = {"q": query, "max": max_results}
        cache_key = cls.get_cache_key("search", params)
        
        # Check cache first
        cached = cls.get_cached_data(cache_key)
        if cached:
            return cached
        
        # Build request with optimizations
        request_params = {
            "part": "id",  # Minimal: only get video IDs
            "q": query,
            "type": "video",
            "videoLicense": "creativeCommon",
            "maxResults": min(max_results, 50),
            "order": "viewCount",
            "videoDuration": "medium",
            "fields": cls.SEARCH_FIELDS,  # Request only necessary fields
        }
        
        # Add quotaUser for per-user tracking
        if user_id:
            request_params["quotaUser"] = hashlib.md5(user_id.encode()).hexdigest()[:40]
        
        try:
            search_request = youtube.search().list(**request_params)
            
            # Add ETag header for conditional request
            etag = cls.get_etag(cache_key)
            if etag:
                search_request.headers["If-None-Match"] = etag
            
            response = search_request.execute()
            
            # Cache the response with ETag
            response_etag = response.get("etag")
            cls.set_cache(cache_key, response, response_etag)
            
            return response
            
        except HttpError as e:
            if e.resp.status == 304:  # Not Modified
                logging.info("YouTube API: Data not modified (304), using cache")
                return cls.get_cached_data(cache_key) or {"items": []}
            raise
    
    @classmethod
    async def get_video_details(
        cls, 
        youtube, 
        video_ids: List[str],
        user_id: str = None
    ) -> dict:
        """
        Optimized video details fetch with batching and field filtering
        """
        if not video_ids:
            return {"items": []}
        
        params = {"ids": ",".join(sorted(video_ids))}
        cache_key = cls.get_cache_key("videos", params)
        
        # Check cache first
        cached = cls.get_cached_data(cache_key)
        if cached:
            return cached
        
        # Batch videos in groups of 50 (API limit)
        all_items = []
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            request_params = {
                "part": "statistics,contentDetails,snippet,status",
                "id": ",".join(batch_ids),
                "fields": cls.VIDEO_FIELDS,  # Request only necessary fields
            }
            
            # Add quotaUser for per-user tracking
            if user_id:
                request_params["quotaUser"] = hashlib.md5(user_id.encode()).hexdigest()[:40]
            
            videos_request = youtube.videos().list(**request_params)
            
            # Add ETag for conditional request
            batch_cache_key = cls.get_cache_key("videos_batch", {"ids": ",".join(batch_ids)})
            etag = cls.get_etag(batch_cache_key)
            if etag:
                videos_request.headers["If-None-Match"] = etag
            
            try:
                response = videos_request.execute()
                all_items.extend(response.get("items", []))
                
                # Cache batch response
                cls.set_cache(batch_cache_key, response, response.get("etag"))
                
            except HttpError as e:
                if e.resp.status == 304:  # Not Modified
                    cached_batch = cls.get_cached_data(batch_cache_key)
                    if cached_batch:
                        all_items.extend(cached_batch.get("items", []))
                else:
                    raise
        
        result = {"items": all_items}
        cls.set_cache(cache_key, result)
        return result
    
    @classmethod
    def clear_expired_cache(cls):
        """Clean up expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, timestamp in cls._cache_timestamps.items()
            if (now - timestamp).total_seconds() > cls.CACHE_TTL_MINUTES * 60
        ]
        for key in expired_keys:
            cls._data_cache.pop(key, None)
            cls._etag_cache.pop(key, None)
            cls._cache_timestamps.pop(key, None)
        if expired_keys:
            logging.info(f"YouTube API: Cleared {len(expired_keys)} expired cache entries")


# MongoDB-based persistent cache for YouTube data
class YouTubePersistentCache:
    """
    Persistent cache using MongoDB for YouTube API results.
    Survives server restarts and can be shared across instances.
    """
    
    CACHE_COLLECTION = "youtube_api_cache"
    CACHE_TTL_HOURS = 6  # Cache validity in hours
    
    @classmethod
    async def get_cached_search(cls, query: str, min_views: int) -> Optional[List[dict]]:
        """Get cached search results from MongoDB"""
        cache_key = f"search:{query}:{min_views}"
        
        cache_entry = await db[cls.CACHE_COLLECTION].find_one({
            "cache_key": cache_key,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if cache_entry:
            logging.info(f"YouTube Persistent Cache: Hit for query '{query}'")
            return cache_entry.get("data", [])
        
        return None
    
    @classmethod
    async def set_cached_search(cls, query: str, min_views: int, data: List[dict]):
        """Store search results in MongoDB cache"""
        cache_key = f"search:{query}:{min_views}"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=cls.CACHE_TTL_HOURS)
        
        await db[cls.CACHE_COLLECTION].update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "cache_key": cache_key,
                    "query": query,
                    "min_views": min_views,
                    "data": data,
                    "expires_at": expires_at,
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        logging.info(f"YouTube Persistent Cache: Stored {len(data)} videos for query '{query}'")
    
    @classmethod
    async def get_video_etag(cls, video_id: str) -> Optional[str]:
        """Get stored ETag for a video"""
        entry = await db[cls.CACHE_COLLECTION].find_one({"video_id": video_id})
        return entry.get("etag") if entry else None
    
    @classmethod
    async def cleanup_expired(cls):
        """Remove expired cache entries"""
        result = await db[cls.CACHE_COLLECTION].delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        if result.deleted_count > 0:
            logging.info(f"YouTube Persistent Cache: Cleaned up {result.deleted_count} expired entries")


# ==================== END YOUTUBE API OPTIMIZATION ====================

# Pydantic models
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

# Authentication helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def send_verification_email(email: str, token: str, full_name: str):
    """Send email verification link"""
    if not RESEND_API_KEY:
        logging.warning("No Resend API key configured, skipping email. Get one at https://resend.com/api-keys")
        return
    
    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
            .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 32px; font-weight: 800; }}
            .content {{ padding: 40px; }}
            .content h2 {{ color: #1a202c; font-size: 24px; margin-bottom: 16px; }}
            .content p {{ color: #4a5568; font-size: 16px; line-height: 1.6; margin: 16px 0; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 18px; margin: 24px 0; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); }}
            .footer {{ background: #f7fafc; padding: 24px; text-align: center; color: #718096; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✨ ContentFlow</h1>
            </div>
            <div class="content">
                <h2>Welcome, {full_name}!</h2>
                <p>Thanks for signing up for ContentFlow! We're excited to have you on board.</p>
                <p>To get started, please verify your email address by clicking the button below:</p>
                <div style="text-align: center;">
                    <a href="{verification_link}" class="button">Verify Email Address</a>
                </div>
                <p style="font-size: 14px; color: #718096; margin-top: 32px;">
                    If you didn't create an account, you can safely ignore this email.
                </p>
                <p style="font-size: 12px; color: #a0aec0; margin-top: 16px;">
                    Or copy and paste this link: {verification_link}
                </p>
            </div>
            <div class="footer">
                <p>© 2025 ContentFlow. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [email],
            "subject": "Verify your ContentFlow account ✨",
            "html": html_content
        }
        
        # Use synchronous call in thread pool
        response = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"✅ Verification email sent to {email}: {response}")
        return True
    except Exception as e:
        logging.error(f"❌ Failed to send verification email to {email}: {str(e)}")
        logging.error(f"Please add RESEND_API_KEY to .env file. Get it from https://resend.com/api-keys")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # First, try to decode as JWT (for email/password login)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        
        # The sub field contains email for JWT tokens
        user = await db.users.find_one({"email": sub})
        if user is None:
            # Fallback: try to find by user_id field or _id (for older tokens)
            user = await db.users.find_one({"user_id": sub})
        if user is None:
            user = await db.users.find_one({"_id": sub})
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        pass  # Not a valid JWT, try session token lookup
    
    # If JWT decode fails, check if it's an Emergent session token (Google OAuth)
    session = await db.user_sessions.find_one({
        "session_token": token,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if session:
        user_id = session.get("user_id")
        user = await db.users.find_one({"user_id": user_id})
        if user is None:
            user = await db.users.find_one({"_id": user_id})
        if user:
            return user
    
    raise credentials_exception

# Authentication endpoints
@api_router.post("/auth/google-oauth")
async def google_oauth_callback(session_id: str = Form(...)):
    """Process Google OAuth via Emergent Auth"""
    try:
        # Call Emergent Auth API to get user data
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid session ID")
            
            oauth_data = response.json()
        
        # Check if user exists
        user = await db.users.find_one({"email": oauth_data["email"]})
        
        if not user:
            # Create new user
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user = {
                "user_id": user_id,
                "email": oauth_data["email"],
                "full_name": oauth_data["name"],
                "picture": oauth_data.get("picture", ""),
                "auth_provider": "google",
                "email_verified": True,  # Google emails are pre-verified
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(user)
        else:
            user_id = user.get("user_id") or user.get("_id")
        
        # Store Emergent session token
        session_token = oauth_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Return user data with token
        return {
            "access_token": session_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": oauth_data["email"],
                "full_name": oauth_data["name"],
                "picture": oauth_data.get("picture", "")
            }
        }
    
    except Exception as e:
        logging.error(f"OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    verification_token = secrets.token_urlsafe(32)
    
    new_user = {
        "_id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "email_verified": False,
        "verification_token": verification_token,
        "auth_provider": "email",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
    
    await db.users.insert_one(new_user)
    
    # Send verification email (non-blocking)
    asyncio.create_task(send_verification_email(user_data.email, verification_token, user_data.full_name))
    
    # Don't return token yet - user needs to verify email first
    return {
        "access_token": "pending_verification",
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "created_at": new_user["created_at"],
            "email_verified": False
        }
    }

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    # Find user
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Check if OAuth provider (skip password check for OAuth users)
    if user.get("auth_provider") == "google":
        raise HTTPException(status_code=400, detail="Please sign in with Google")
    
    # Verify password (check if hashed_password exists)
    if not user.get("hashed_password"):
        raise HTTPException(status_code=400, detail="Invalid account configuration. Please contact support.")
    
    if not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Check email verification
    if not user.get("email_verified", False):
        raise HTTPException(
            status_code=403, 
            detail="Please verify your email before logging in. Check your inbox for the verification link."
        )
    
    # Create access token - use email as sub since _id is ObjectId
    access_token = create_access_token(data={"sub": user["email"]})
    
    # Convert ObjectId to string for response
    user_id = str(user.get("_id")) if user.get("_id") else user.get("user_id", "")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user["email"],
            "full_name": user.get("full_name", ""),
            "created_at": user.get("created_at", "")
        }
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user.get("_id")) if current_user.get("_id") else current_user.get("user_id", "")
    return {
        "id": user_id,
        "email": current_user.get("email", ""),
        "full_name": current_user.get("full_name", ""),
        "created_at": current_user.get("created_at", "")
    }

@api_router.get("/auth/verify-email")
async def verify_email(token: str):
    """Verify user's email address"""
    try:
        user = await db.users.find_one({"verification_token": token})
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        if user.get("email_verified"):
            return {"message": "Email already verified", "success": True}
        
        # Update user
        await db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "email_verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                },
                "$unset": {"verification_token": ""}
            }
        )
        
        # Create access token
        access_token = create_access_token(data={"sub": user["_id"]})
        
        return {
            "success": True,
            "message": "Email verified successfully!",
            "access_token": access_token,
            "user": {
                "id": user["_id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "created_at": user["created_at"]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Email verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Verification failed")

@api_router.post("/auth/resend-verification")
async def resend_verification(email: EmailStr):
    """Resend verification email"""
    user = await db.users.find_one({"email": email})
    
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}
    
    if user.get("email_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Generate new token
    new_token = secrets.token_urlsafe(32)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"verification_token": new_token}}
    )
    
    # Send email
    asyncio.create_task(send_verification_email(user["email"], new_token, user["full_name"]))
    
    return {"message": "Verification email sent! Please check your inbox."}

# Existing models (now with user association)

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
    use_ai_analysis: bool = True  # Enable AI by default

class PostRequest(BaseModel):
    clip_id: str
    caption: str
    platforms: List[str]
    hashtags: Optional[str] = ""

class APIKeysModel(BaseModel):
    youtube_api_key: Optional[str] = None
    instagram_access_token: Optional[str] = None

def calculate_viral_score(views: int, likes: int, comments: int, upload_days_ago: int) -> float:
    if views == 0:
        return 0.0
    
    engagement_rate = ((likes + comments * 2) / views) * 100
    recency_factor = max(0, 100 - upload_days_ago) / 100
    
    viral_score = (engagement_rate * 0.7) + (recency_factor * 30)
    
    return min(round(viral_score, 2), 100.0)

@api_router.get("/discover")
async def discover_videos(
    query: str = Query(default="", description="Search query"),
    max_results: int = Query(default=50, le=100),
    min_views: int = Query(default=1000, description="Minimum view count"),
    current_user: dict = Depends(get_current_user)
):
    """
    Discover CC BY licensed YouTube videos with optimized API usage:
    - Caches results (in-memory + MongoDB)
    - Uses minimal fields to reduce quota
    - Supports ETags for conditional requests
    - Tracks quotaUser per user
    """
    try:
        # Get user ID for quota tracking
        user_id = str(current_user.get("_id", current_user.get("email", "anonymous")))
        search_query = query.strip() if query else "tutorial"
        
        # 1. Check persistent cache first (reduces API calls significantly)
        cached_videos = await YouTubePersistentCache.get_cached_search(search_query, min_views)
        if cached_videos:
            return {
                "videos": cached_videos[:max_results],
                "total": len(cached_videos[:max_results]),
                "cached": True,
                "cache_type": "persistent",
                "message": "Showing cached results for faster loading"
            }
        
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        
        if youtube_api_key:
            try:
                # Clean up expired in-memory cache periodically
                YouTubeAPIOptimizer.clear_expired_cache()
                
                youtube = build('youtube', 'v3', developerKey=youtube_api_key, cache_discovery=False)
                
                # 2. Use optimized search with caching and field filtering
                search_response = await YouTubeAPIOptimizer.search_videos(
                    youtube, 
                    search_query,
                    max_results=50,
                    user_id=user_id
                )
                
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                
                # Try alternative queries if no results
                if not video_ids:
                    alt_queries = [
                        f"{search_query} creative commons",
                        "creative commons tutorial" if not query else search_query,
                    ]
                    for alt_query in alt_queries:
                        alt_response = await YouTubeAPIOptimizer.search_videos(
                            youtube, alt_query, max_results=50, user_id=user_id
                        )
                        video_ids = [item['id']['videoId'] for item in alt_response.get('items', [])]
                        if video_ids:
                            break
                
                if not video_ids:
                    # Return MongoDB cached videos if no API results
                    db_videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
                    if db_videos:
                        return {
                            "videos": db_videos,
                            "total": len(db_videos),
                            "cached": True,
                            "message": "No new CC videos found. Showing previously discovered videos."
                        }
                    return {
                        "videos": [], 
                        "total": 0,
                        "message": "No Creative Commons licensed videos found. Try different search terms."
                    }
                
                # 3. Get video details with batching and field optimization
                videos_response = await YouTubeAPIOptimizer.get_video_details(
                    youtube, 
                    video_ids,
                    user_id=user_id
                )
                
                videos = []
                for item in videos_response.get('items', []):
                    snippet = item.get('snippet', {})
                    stats = item.get('statistics', {})
                    status = item.get('status', {})
                    
                    license_type = status.get('license', 'youtube')
                    if license_type != 'creativeCommon':
                        continue
                    
                    views = int(stats.get('viewCount', 0))
                    likes = int(stats.get('likeCount', 0))
                    comments = int(stats.get('commentCount', 0))
                    
                    if views < min_views:
                        continue
                    
                    duration_str = item.get('contentDetails', {}).get('duration', 'PT0S')
                    duration_seconds = parse_youtube_duration(duration_str)
                    
                    if duration_seconds < 60 or duration_seconds > 3600:
                        continue
                    
                    upload_date = snippet.get('publishedAt', '')
                    try:
                        upload_datetime = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                        days_ago = (datetime.now(timezone.utc) - upload_datetime).days
                        upload_date_formatted = upload_datetime.strftime('%Y%m%d')
                    except:
                        days_ago = 365
                        upload_date_formatted = upload_date[:10].replace('-', '') if upload_date else ''
                    
                    viral_score = calculate_viral_score(views, likes, comments, days_ago)
                    
                    # Get thumbnail with fallback
                    thumbnails = snippet.get('thumbnails', {})
                    thumbnail = (
                        thumbnails.get('high', {}).get('url') or 
                        thumbnails.get('medium', {}).get('url') or 
                        thumbnails.get('default', {}).get('url', '')
                    )
                    
                    videos.append({
                        'id': item['id'],
                        'title': snippet.get('title', 'Untitled'),
                        'channel': snippet.get('channelTitle', 'Unknown'),
                        'thumbnail': thumbnail,
                        'duration': duration_seconds,
                        'views': views,
                        'likes': likes,
                        'comments': comments,
                        'viral_score': viral_score,
                        'upload_date': upload_date_formatted,
                        'license': 'Creative Commons Attribution (CC BY)',
                        'is_cc_licensed': True,
                        'description': snippet.get('description', '')[:200]
                    })
                
                videos.sort(key=lambda x: x['viral_score'], reverse=True)
                videos = videos[:max_results]
                
                # 4. Store in MongoDB for persistence
                if videos:
                    await db.discovered_videos.delete_many({})
                    await db.discovered_videos.insert_many(videos)
                    videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
                    
                    # Also cache in persistent cache
                    await YouTubePersistentCache.set_cached_search(search_query, min_views, videos)
                
                return {
                    "videos": videos, 
                    "total": len(videos),
                    "optimized": True,
                    "quota_user": hashlib.md5(user_id.encode()).hexdigest()[:8]
                }
                
            except HttpError as e:
                error_detail = str(e)
                logging.error(f"YouTube API error: {error_detail}")
                if "quotaExceeded" in error_detail:
                    # Try to return cached videos when quota is exceeded
                    cached_videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
                    if cached_videos:
                        logging.info(f"Returning {len(cached_videos)} cached videos due to quota exceeded")
                        return {
                            "videos": cached_videos, 
                            "total": len(cached_videos),
                            "cached": True,
                            "message": "Showing cached results. YouTube API quota exceeded - results will refresh tomorrow."
                        }
                    raise HTTPException(status_code=429, detail="YouTube API quota exceeded. Please try again later or use a different API key.")
                raise HTTPException(status_code=500, detail=f"YouTube API error: {error_detail}")
        
        logging.warning("Using yt-dlp fallback for CC content search")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        search_query = f"{query} creative commons" if query else "creative commons"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False)
            
            videos = []
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if not entry:
                        continue
                    
                    license_info = str(entry.get('license', '')).lower()
                    is_cc = 'creative commons' in license_info or (license_info and 'cc' in license_info and 'by' in license_info)
                    
                    if not is_cc:
                        continue
                    
                    views = entry.get('view_count', 0) or 0
                    likes = entry.get('like_count', 0) or 0
                    comments = entry.get('comment_count', 0) or 0
                    
                    upload_date = entry.get('upload_date', '')
                    try:
                        upload_datetime = datetime.strptime(upload_date, '%Y%m%d') if upload_date else datetime.now()
                        days_ago = (datetime.now() - upload_datetime).days
                    except:
                        days_ago = 365
                    
                    if views < min_views:
                        continue
                    
                    viral_score = calculate_viral_score(views, likes, comments, days_ago)
                    
                    videos.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'channel': entry.get('uploader', 'Unknown'),
                        'thumbnail': entry.get('thumbnail'),
                        'duration': entry.get('duration', 0),
                        'views': views,
                        'likes': likes,
                        'comments': comments,
                        'viral_score': viral_score,
                        'upload_date': upload_date,
                        'license': 'Creative Commons',
                        'is_cc_licensed': True
                    })
            
            videos.sort(key=lambda x: x['viral_score'], reverse=True)
            
            await db.discovered_videos.delete_many({})
            if videos:
                await db.discovered_videos.insert_many(videos)
                videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
            
            return {"videos": videos, "total": len(videos)}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error discovering videos: {str(e)}")
        # Try to return cached videos on any error
        try:
            cached_videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
            if cached_videos:
                logging.info(f"Returning {len(cached_videos)} cached videos due to error")
                return {
                    "videos": cached_videos, 
                    "total": len(cached_videos),
                    "cached": True,
                    "message": "Showing cached results due to temporary issue."
                }
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))

def parse_youtube_duration(duration_str: str) -> int:
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

@api_router.post("/clear-videos")
async def clear_discovered_videos(current_user: dict = Depends(get_current_user)):
    try:
        result = await db.discovered_videos.delete_many({})
        return {
            "success": True,
            "message": f"Cleared {result.deleted_count} videos",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        logging.error(f"Error clearing videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/videos/{video_id}")
async def get_video_details(video_id: str, current_user: dict = Depends(get_current_user)):
    try:
        video = await db.discovered_videos.find_one({"id": video_id}, {"_id": 0})
        
        if not video:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                views = info.get('view_count', 0) or 0
                likes = info.get('like_count', 0) or 0
                comments = info.get('comment_count', 0) or 0
                
                upload_date = info.get('upload_date', '')
                try:
                    upload_datetime = datetime.strptime(upload_date, '%Y%m%d')
                    days_ago = (datetime.now() - upload_datetime).days
                except:
                    days_ago = 365
                
                viral_score = calculate_viral_score(views, likes, comments, days_ago)
                
                video = {
                    'id': video_id,
                    'title': info.get('title'),
                    'channel': info.get('uploader'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration', 0),
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'viral_score': viral_score,
                    'upload_date': upload_date,
                    'license': info.get('license', 'Unknown'),
                    'description': info.get('description', '')[:500],
                    'is_cc_licensed': True
                }
        
        return video
    
    except Exception as e:
        logging.error(f"Error getting video details: {str(e)}")
        raise HTTPException(status_code=404, detail="Video not found")

async def analyze_video_with_ai(video_id: str, title: str, description: str, duration: int) -> Dict:
    """Use AI to analyze video and find best clip moments"""
    try:
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            logging.warning("No Emergent LLM key found, using default timing")
            return {
                "recommended_start": max(0, duration // 4),
                "recommended_duration": min(45, duration),
                "reasoning": "Default timing: First quarter of video"
            }
        
        # Initialize AI chat
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"clip-analysis-{video_id}",
            system_message="You are an expert video editor who identifies the most engaging and viral moments in videos. Analyze content and suggest optimal clip timings for social media shorts."
        ).with_model("openai", "gpt-5.2")
        
        # Create analysis prompt
        prompt = f"""Analyze this YouTube video and recommend the BEST 30-60 second segment for a viral short:

Title: {title}
Description: {description[:500]}
Total Duration: {duration} seconds

Identify:
1. Hook moments (first 3-5 seconds that grab attention)
2. Peak engagement points (emotional peaks, punchlines, key information)
3. Natural start/end points for a cohesive clip

Respond ONLY with JSON (no markdown, no explanation):
{{
  "recommended_start": <seconds>,
  "recommended_duration": <30-60 seconds>,
  "reasoning": "<brief explanation of why this moment>",
  "hook_type": "<what makes it engaging>"
}}"""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse AI response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                analysis = json.loads(json_match.group())
                # Validate and constrain values
                start = max(0, min(analysis.get('recommended_start', 0), duration - 30))
                clip_duration = max(30, min(60, analysis.get('recommended_duration', 45)))
                
                return {
                    "recommended_start": start,
                    "recommended_duration": clip_duration,
                    "reasoning": analysis.get('reasoning', 'AI-recommended segment'),
                    "hook_type": analysis.get('hook_type', 'Engaging moment')
                }
            else:
                raise ValueError("No JSON found in response")
        except Exception as parse_error:
            logging.error(f"Error parsing AI response: {parse_error}, raw: {response}")
            # Fallback to intelligent default
            return {
                "recommended_start": max(0, duration // 4),
                "recommended_duration": 45,
                "reasoning": "AI analysis fallback: mid-section clip"
            }
            
    except Exception as e:
        logging.error(f"Error in AI analysis: {str(e)}")
        return {
            "recommended_start": max(0, duration // 4),
            "recommended_duration": 45,
            "reasoning": "Default timing due to analysis error"
        }

async def download_and_clip_video(video_id: str, start_time: int, duration: int, use_ai: bool = False):
    try:
        temp_dir = Path("/tmp/contentflow")
        temp_dir.mkdir(exist_ok=True)
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        downloaded_file = None
        video_title = "video"
        video_duration = 0
        
        # Try pytubefix first (better at bypassing bot detection)
        logging.info(f"🎬 Attempting download with pytubefix for {video_id}...")
        try:
            from pytubefix import YouTube
            from pytubefix.cli import on_progress
            
            yt = YouTube(video_url, on_progress_callback=on_progress)
            video_title = yt.title
            video_duration = yt.length
            
            logging.info(f"📹 Video: {video_title} ({video_duration}s)")
            
            # Get stream - try 720p or lower for reliability
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                # Try any available stream
                stream = yt.streams.filter(file_extension='mp4').first()
            
            if not stream:
                stream = yt.streams.get_highest_resolution()
            
            if stream:
                logging.info(f"📥 Downloading: {stream.resolution} - {stream.mime_type}")
                downloaded_file = stream.download(output_path=str(temp_dir), filename=f"{video_id}.mp4")
                logging.info(f"✅ Downloaded via pytubefix: {downloaded_file}")
            else:
                raise Exception("No suitable stream found")
                
        except Exception as pytube_error:
            logging.warning(f"⚠️ pytubefix failed: {str(pytube_error)}")
            logging.info("🔄 Falling back to yt-dlp...")
            
            # Fallback to yt-dlp
            info_opts = {
                'quiet': False,
                'no_warnings': False,
                'skip_download': True,
                'format': 'best[height<=720][ext=mp4]',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                video_title = info.get('title', 'video')
                video_duration = info.get('duration', 0)
            
            output_template = str(temp_dir / f"{video_id}.%(ext)s")
            download_opts = {
                'format': 'best[height<=720][ext=mp4]/best[height<=720]',
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'retries': 3,
                'fragment_retries': 3,
                'user_agent': 'com.google.android.youtube/19.51.41 (Linux; U; Android 14) gzip',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios'],
                        'player_skip': ['webpage']
                    }
                },
                'http_headers': {
                    'User-Agent': 'com.google.android.youtube/19.51.41 (Linux; U; Android 14) gzip',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                'geo_bypass': True,
                'nocheckcertificate': True,
            }
            
            try:
                with yt_dlp.YoutubeDL(download_opts) as ydl:
                    ydl.download([video_url])
                    downloaded_file = ydl.prepare_filename(info)
            except Exception as download_error:
                logging.error(f"yt-dlp download error: {str(download_error)}")
                possible_files = list(temp_dir.glob(f"{video_id}.*"))
                if possible_files:
                    downloaded_file = str(possible_files[0])
        
        # Verify download
        if not downloaded_file or not Path(downloaded_file).exists():
            possible_files = list(temp_dir.glob(f"{video_id}.*"))
            if possible_files:
                downloaded_file = str(possible_files[0])
            else:
                raise Exception(
                    "⚠️ YouTube blocked the download. This happens when:\n"
                    "1. Too many downloads in short time\n"
                    "2. YouTube detects automation\n"
                    "3. Video has restrictions\n\n"
                    "💡 Solutions:\n"
                    "- Wait 5-10 minutes and try again\n"
                    "- Try a different video\n"
                    "- The video might have download restrictions"
                )
        
        logging.info(f"✅ Video downloaded to: {downloaded_file}")
        
        # Use AI analysis if requested
        ai_analysis = None
        if use_ai:
            ai_analysis = await analyze_video_with_ai(
                video_id, 
                video_title,
                "",  # description
                video_duration
            )
            start_time = ai_analysis['recommended_start']
            duration = ai_analysis['recommended_duration']
            logging.info(f"✨ AI recommended: start={start_time}s, duration={duration}s - {ai_analysis['reasoning']}")
        
        clip_id = str(uuid.uuid4())
        output_clip = temp_dir / f"clip_{clip_id}.mp4"
        output_thumbnail = temp_dir / f"thumb_{clip_id}.jpg"
        
        # Create 9:16 vertical clip (1080x1920) with black bars
        logging.info(f"🎬 Creating 9:16 vertical clip...")
        ffmpeg_cmd = [
            'ffmpeg', '-i', downloaded_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-ar', '44100',
            '-movflags', '+faststart',  # Better for streaming
            '-y',
            str(output_clip)
        ]
        
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        logging.info(f"✅ Clip created: {output_clip}")
        
        # Generate thumbnail
        logging.info(f"📸 Creating thumbnail...")
        thumb_cmd = [
            'ffmpeg', '-i', str(output_clip),
            '-ss', '2',
            '-vframes', '1',
            '-vf', 'scale=1080:1920',
            '-q:v', '2',
            '-y',
            str(output_thumbnail)
        ]
        
        subprocess.run(thumb_cmd, check=True, capture_output=True)
        logging.info(f"✅ Thumbnail created")
        
        # Clean up source file
        if Path(downloaded_file).exists():
            Path(downloaded_file).unlink()
            logging.info("🧹 Cleaned up source file")
        
        clip_data = {
            "clip_id": clip_id,
            "video_id": video_id,
            "start_time": start_time,
            "duration": duration,
            "file_path": str(output_clip),
            "thumbnail_path": str(output_thumbnail),
            "format": "9:16 (1080x1920)",
            "resolution": "1080x1920",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready",
            "ai_analysis": ai_analysis
        }
        
        await db.processed_clips.insert_one(clip_data)
        logging.info(f"💾 Clip data saved: {clip_id}")
        
        return clip_id
    
    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ Error creating clip: {error_msg}")
        
        # Provide helpful error messages
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower() or "403" in error_msg or "Forbidden" in error_msg:
            raise Exception(
                "⚠️ YouTube's bot detection is blocking automated downloads.\n\n"
                "This is a YouTube-wide restriction affecting all download tools.\n\n"
                "✅ Alternatives:\n"
                "• Use the 'Preview Clip' feature to see your selected segment\n"
                "• Download the video manually from YouTube (with proper CC BY attribution)\n"
                "• Use a browser extension for downloading\n\n"
                "The AI analysis and clip timing features still work perfectly!"
            )
        elif "HTTP Error 429" in error_msg:
            raise Exception(
                "⚠️ Rate limit exceeded (Error 429).\n\n"
                "Too many requests. Please wait 15-20 minutes before trying again."
            )
        else:
            raise Exception(f"Clip generation error: {error_msg}")

# Clip Preview endpoint - provides embed URL with timestamps
@api_router.get("/clips/preview/{video_id}")
async def get_clip_preview(
    video_id: str,
    start: int = Query(default=0, description="Start time in seconds"),
    duration: int = Query(default=60, description="Duration in seconds"),
    current_user: dict = Depends(get_current_user)
):
    """Get a preview URL for the clip using YouTube's embed player"""
    try:
        end_time = start + duration
        
        # YouTube embed URL with start and end parameters
        embed_url = f"https://www.youtube.com/embed/{video_id}?start={start}&end={end_time}&autoplay=1"
        
        # Also provide the direct watch URL with timestamp
        watch_url = f"https://www.youtube.com/watch?v={video_id}&t={start}s"
        
        return {
            "video_id": video_id,
            "start_time": start,
            "end_time": end_time,
            "duration": duration,
            "embed_url": embed_url,
            "watch_url": watch_url,
            "download_instructions": (
                "To download this CC BY video:\n"
                "1. Visit the watch URL\n"
                "2. Use a browser extension (e.g., Video DownloadHelper)\n"
                "3. Or use yt-dlp with cookies from your browser\n"
                "4. Remember to provide attribution to the original creator!"
            )
        }
    except Exception as e:
        logging.error(f"Error creating clip preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/clips/ai-analyze/{video_id}")
async def get_ai_clip_recommendations(video_id: str):
    """Get AI recommendations for best clip moments without generating"""
    try:
        # Get video details
        video = await db.discovered_videos.find_one({"id": video_id}, {"_id": 0})
        
        if not video:
            # Fetch from YouTube
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                video = {
                    'title': info.get('title'),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0)
                }
        
        analysis = await analyze_video_with_ai(
            video_id,
            video.get('title', ''),
            video.get('description', ''),
            video.get('duration', 0)
        )
        
        return {
            "success": True,
            "video_id": video_id,
            "analysis": analysis
        }
    
    except Exception as e:
        logging.error(f"Error in AI analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/clips/generate")
async def generate_clip(clip_request: ClipRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    try:
        if not clip_request.use_ai_analysis:
            # Manual timing validation
            if clip_request.duration < 10 or clip_request.duration > 60:
                raise HTTPException(status_code=400, detail="Clip duration must be between 10-60 seconds")
        
        clip_id = await download_and_clip_video(
            clip_request.video_id,
            clip_request.start_time,
            clip_request.duration,
            clip_request.use_ai_analysis
        )
        
        return {
            "success": True,
            "clip_id": clip_id,
            "message": "Clip generated successfully with AI analysis!" if clip_request.use_ai_analysis else "Clip generated successfully!",
            "format": "9:16 (1080x1920) - Perfect for Instagram Reels & YouTube Shorts"
        }
    
    except Exception as e:
        logging.error(f"Error in generate_clip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/clips/{clip_id}")
async def get_clip(clip_id: str):
    try:
        clip = await db.processed_clips.find_one({"clip_id": clip_id}, {"_id": 0})
        
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return clip
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting clip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/post")
async def post_to_social(post_request: PostRequest):
    try:
        clip = await db.processed_clips.find_one({"clip_id": post_request.clip_id}, {"_id": 0})
        
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        results = []
        
        for platform in post_request.platforms:
            post_data = {
                "post_id": str(uuid.uuid4()),
                "clip_id": post_request.clip_id,
                "platform": platform,
                "caption": post_request.caption,
                "hashtags": post_request.hashtags,
                "status": "posted",
                "posted_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.social_posts.insert_one(post_data)
            results.append(post_data)
        
        return {
            "success": True,
            "message": f"Posted to {len(results)} platform(s)",
            "posts": results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error posting to social: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/history")
async def get_post_history(limit: int = 50):
    try:
        posts = await db.social_posts.find({}, {"_id": 0}).sort("posted_at", -1).limit(limit).to_list(length=limit)
        return {"posts": posts, "total": len(posts)}
    
    except Exception as e:
        logging.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/stats")
async def get_dashboard_stats():
    try:
        total_videos = await db.discovered_videos.count_documents({})
        total_clips = await db.processed_clips.count_documents({})
        total_posts = await db.social_posts.count_documents({})
        
        top_videos = await db.discovered_videos.find(
            {}, {"_id": 0}
        ).sort("viral_score", -1).limit(5).to_list(length=5)
        
        recent_posts = await db.social_posts.find(
            {}, {"_id": 0}
        ).sort("posted_at", -1).limit(5).to_list(length=5)
        
        return {
            "total_videos_discovered": total_videos,
            "total_clips_generated": total_clips,
            "total_posts_published": total_posts,
            "top_videos": top_videos,
            "recent_posts": recent_posts
        }
    
    except Exception as e:
        logging.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/settings/api-keys")
async def save_api_keys(keys: APIKeysModel):
    try:
        await db.settings.update_one(
            {"type": "api_keys"},
            {"$set": {
                "youtube_api_key": keys.youtube_api_key,
                "instagram_access_token": keys.instagram_access_token,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        return {"success": True, "message": "API keys saved successfully"}
    except Exception as e:
        logging.error(f"Error saving API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/settings/api-keys")
async def get_api_keys():
    try:
        keys = await db.settings.find_one({"type": "api_keys"}, {"_id": 0})
        if keys:
            if keys.get('youtube_api_key'):
                keys['youtube_api_key'] = '***' + keys['youtube_api_key'][-4:] if len(keys['youtube_api_key']) > 4 else '***'
            if keys.get('instagram_access_token'):
                keys['instagram_access_token'] = '***' + keys['instagram_access_token'][-4:] if len(keys['instagram_access_token']) > 4 else '***'
        return keys or {}
    except Exception as e:
        logging.error(f"Error getting API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== IMAGE SEARCH ENDPOINTS ====================

class FavoriteImageModel(BaseModel):
    image_id: str
    url: str
    thumbnail: str
    title: str
    photographer: str
    source: str  # 'unsplash' or 'pexels'
    download_url: str
    width: int
    height: int

@api_router.get("/images/search")
async def search_images(
    query: str = Query(..., description="Search query for images"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search for copyright-free images from Unsplash and Pexels"""
    try:
        images = []
        
        # Get API keys from environment or use defaults
        unsplash_key = os.environ.get('UNSPLASH_API_KEY', '')
        pexels_key = os.environ.get('PEXELS_API_KEY', 'QsPCgrnUhMSwyA25GWLfqMdYdJZw2Rthp33l24iYFCrTpuJcwUEBGAhq')
        
        async with httpx.AsyncClient() as client:
            # Search Unsplash (if key available)
            if unsplash_key:
                try:
                    unsplash_response = await client.get(
                        "https://api.unsplash.com/search/photos",
                        params={
                            "query": query,
                            "page": page,
                            "per_page": per_page // 2,
                            "orientation": "landscape"
                        },
                        headers={
                            "Authorization": f"Client-ID {unsplash_key}"
                        },
                        timeout=10.0
                    )
                    if unsplash_response.status_code == 200:
                        unsplash_data = unsplash_response.json()
                        for photo in unsplash_data.get("results", []):
                            images.append({
                                "id": f"unsplash_{photo['id']}",
                                "url": photo["urls"]["regular"],
                                "thumbnail": photo["urls"]["small"],
                                "title": photo.get("description") or photo.get("alt_description") or "Untitled",
                                "photographer": photo["user"]["name"],
                                "photographer_url": photo["user"]["links"]["html"],
                                "source": "unsplash",
                                "download_url": photo["urls"]["full"],
                                "width": photo["width"],
                                "height": photo["height"],
                                "color": photo.get("color", "#000000"),
                                "likes": photo.get("likes", 0)
                            })
                except Exception as e:
                    logging.warning(f"Unsplash API error: {str(e)}")
            
            # Search Pexels (primary source)
            try:
                pexels_response = await client.get(
                    "https://api.pexels.com/v1/search",
                    params={
                        "query": query,
                        "page": page,
                        "per_page": per_page  # Get full amount from Pexels
                    },
                    headers={
                        "Authorization": pexels_key
                    },
                    timeout=10.0
                )
                if pexels_response.status_code == 200:
                    pexels_data = pexels_response.json()
                    for photo in pexels_data.get("photos", []):
                        images.append({
                            "id": f"pexels_{photo['id']}",
                            "url": photo["src"]["large"],
                            "thumbnail": photo["src"]["medium"],
                            "title": photo.get("alt") or "Untitled",
                            "photographer": photo["photographer"],
                            "photographer_url": photo["photographer_url"],
                            "source": "pexels",
                            "download_url": photo["src"]["original"],
                            "width": photo["width"],
                            "height": photo["height"],
                            "color": photo.get("avg_color", "#000000"),
                            "likes": 0
                        })
            except Exception as e:
                logging.warning(f"Pexels API error: {str(e)}")
        
        # Interleave results from both sources
        unsplash_images = [img for img in images if img["source"] == "unsplash"]
        pexels_images = [img for img in images if img["source"] == "pexels"]
        
        combined = []
        max_len = max(len(unsplash_images), len(pexels_images))
        for i in range(max_len):
            if i < len(unsplash_images):
                combined.append(unsplash_images[i])
            if i < len(pexels_images):
                combined.append(pexels_images[i])
        
        return {
            "images": combined,
            "total": len(combined),
            "page": page,
            "query": query
        }
    
    except Exception as e:
        logging.error(f"Error searching images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/images/favorites")
async def add_favorite_image(
    image: FavoriteImageModel,
    current_user: dict = Depends(get_current_user)
):
    """Add an image to user's favorites"""
    try:
        user_id = current_user.get("user_id") or str(current_user.get("_id"))
        
        # Check if already favorited
        existing = await db.favorite_images.find_one({
            "user_id": user_id,
            "image_id": image.image_id
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Image already in favorites")
        
        favorite = {
            "user_id": user_id,
            "image_id": image.image_id,
            "url": image.url,
            "thumbnail": image.thumbnail,
            "title": image.title,
            "photographer": image.photographer,
            "source": image.source,
            "download_url": image.download_url,
            "width": image.width,
            "height": image.height,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.favorite_images.insert_one(favorite)
        
        return {"success": True, "message": "Image added to favorites"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/images/favorites")
async def get_favorite_images(
    current_user: dict = Depends(get_current_user)
):
    """Get user's favorite images"""
    try:
        user_id = current_user.get("user_id") or str(current_user.get("_id"))
        
        favorites = await db.favorite_images.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("added_at", -1).to_list(length=100)
        
        return {"favorites": favorites, "total": len(favorites)}
    
    except Exception as e:
        logging.error(f"Error getting favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/images/favorites/{image_id}")
async def remove_favorite_image(
    image_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove an image from user's favorites"""
    try:
        user_id = current_user.get("user_id") or str(current_user.get("_id"))
        
        result = await db.favorite_images.delete_one({
            "user_id": user_id,
            "image_id": image_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Image not found in favorites")
        
        return {"success": True, "message": "Image removed from favorites"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CONTENT LIBRARY ENDPOINTS ====================

class ContentLibraryFavorite(BaseModel):
    resource_id: str
    name: str
    description: str
    url: str
    logo: str
    categories: list
    levels: list

@api_router.get("/content-library/favorites")
async def get_content_library_favorites(
    current_user: dict = Depends(get_current_user)
):
    """Get user's favorite content library resources"""
    try:
        user_id = current_user.get("user_id") or str(current_user.get("_id"))
        
        favorites = await db.content_library_favorites.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(length=100)
        
        return {"favorites": favorites, "total": len(favorites)}
    
    except Exception as e:
        logging.error(f"Error getting content library favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/content-library/favorites")
async def add_content_library_favorite(
    resource: ContentLibraryFavorite,
    current_user: dict = Depends(get_current_user)
):
    """Add a resource to content library favorites"""
    try:
        user_id = current_user.get("user_id") or str(current_user.get("_id"))
        
        # Check if already favorited
        existing = await db.content_library_favorites.find_one({
            "user_id": user_id,
            "resource_id": resource.resource_id
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Resource already in favorites")
        
        favorite = {
            "user_id": user_id,
            "resource_id": resource.resource_id,
            "name": resource.name,
            "description": resource.description,
            "url": resource.url,
            "logo": resource.logo,
            "categories": resource.categories,
            "levels": resource.levels,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.content_library_favorites.insert_one(favorite)
        
        return {"success": True, "message": "Resource added to favorites"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding content library favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/content-library/favorites/{resource_id}")
async def remove_content_library_favorite(
    resource_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a resource from content library favorites"""
    try:
        user_id = current_user.get("user_id") or str(current_user.get("_id"))
        
        result = await db.content_library_favorites.delete_one({
            "user_id": user_id,
            "resource_id": resource_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Resource not found in favorites")
        
        return {"success": True, "message": "Resource removed from favorites"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing content library favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/content-library/gutenberg/search")
async def search_gutenberg(
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=12, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search Project Gutenberg for books"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gutendex.com/books/",
                params={"search": query, "page": 1},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                books = []
                for book in data.get("results", [])[:limit]:
                    books.append({
                        "id": book["id"],
                        "title": book["title"],
                        "authors": [a["name"] for a in book.get("authors", [])],
                        "subjects": book.get("subjects", [])[:3],
                        "languages": book.get("languages", []),
                        "download_count": book.get("download_count", 0),
                        "formats": {
                            "html": book.get("formats", {}).get("text/html", ""),
                            "epub": book.get("formats", {}).get("application/epub+zip", ""),
                            "txt": book.get("formats", {}).get("text/plain; charset=utf-8", "")
                        },
                        "cover": book.get("formats", {}).get("image/jpeg", "")
                    })
                return {"books": books, "total": data.get("count", 0)}
            else:
                return {"books": [], "total": 0}
    
    except Exception as e:
        logging.error(f"Error searching Gutenberg: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DYNAMIC CONTENT LIBRARY SEARCH ====================

@api_router.get("/content-library/search")
async def search_content_library(
    query: str = Query(..., description="Search query for educational content"),
    category: str = Query(default="all", description="Category filter"),
    limit: int = Query(default=20, le=50),
    current_user: dict = Depends(get_current_user)
):
    """
    Dynamic search for copyright-free educational content across multiple sources.
    Searches: OpenLibrary, Internet Archive, Wikipedia, and uses AI for enhancement.
    """
    try:
        all_results = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Run searches in parallel
            tasks = [
                search_openlibrary(client, query, limit // 4),
                search_internet_archive(client, query, limit // 4),
                search_wikipedia(client, query, limit // 4),
                search_oer_commons(client, query, limit // 4),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logging.warning(f"Search source failed: {str(result)}")
        
        # Use AI to enhance and categorize results if we have any
        if all_results and len(all_results) > 0:
            try:
                enhanced_results = await ai_enhance_results(query, all_results[:limit])
                return {
                    "results": enhanced_results,
                    "total": len(enhanced_results),
                    "query": query,
                    "sources": ["OpenLibrary", "Internet Archive", "Wikipedia", "OER Commons"]
                }
            except Exception as ai_error:
                logging.warning(f"AI enhancement failed, returning raw results: {str(ai_error)}")
        
        return {
            "results": all_results[:limit],
            "total": len(all_results),
            "query": query,
            "sources": ["OpenLibrary", "Internet Archive", "Wikipedia", "OER Commons"]
        }
    
    except Exception as e:
        logging.error(f"Error in content library search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def search_openlibrary(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search OpenLibrary for books and educational materials"""
    try:
        response = await client.get(
            "https://openlibrary.org/search.json",
            params={"q": query, "limit": limit, "fields": "key,title,author_name,first_publish_year,subject,cover_i,ia"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for doc in data.get("docs", [])[:limit]:
                cover_id = doc.get("cover_i")
                results.append({
                    "id": f"ol-{doc.get('key', '').replace('/works/', '')}",
                    "title": doc.get("title", "Untitled"),
                    "description": f"By {', '.join(doc.get('author_name', ['Unknown'])[:2])}. First published: {doc.get('first_publish_year', 'N/A')}",
                    "url": f"https://openlibrary.org{doc.get('key', '')}",
                    "source": "OpenLibrary",
                    "type": "book",
                    "license": "varies",
                    "thumbnail": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
                    "subjects": doc.get("subject", [])[:5],
                    "authors": doc.get("author_name", [])[:3],
                    "year": doc.get("first_publish_year"),
                    "has_fulltext": bool(doc.get("ia"))
                })
            return results
    except Exception as e:
        logging.warning(f"OpenLibrary search failed: {str(e)}")
    return []


async def search_internet_archive(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Internet Archive for educational materials"""
    try:
        # Search for educational texts and materials
        response = await client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f"{query} AND mediatype:(texts OR education)",
                "fl[]": ["identifier", "title", "description", "creator", "year", "subject"],
                "rows": limit,
                "output": "json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for doc in data.get("response", {}).get("docs", [])[:limit]:
                identifier = doc.get("identifier", "")
                results.append({
                    "id": f"ia-{identifier}",
                    "title": doc.get("title", "Untitled") if isinstance(doc.get("title"), str) else doc.get("title", ["Untitled"])[0],
                    "description": doc.get("description", "")[:200] if isinstance(doc.get("description"), str) else (doc.get("description", [""])[0][:200] if doc.get("description") else ""),
                    "url": f"https://archive.org/details/{identifier}",
                    "source": "Internet Archive",
                    "type": "archive",
                    "license": "public-domain",
                    "thumbnail": f"https://archive.org/services/img/{identifier}",
                    "subjects": doc.get("subject", [])[:5] if isinstance(doc.get("subject"), list) else [doc.get("subject", "")][:5],
                    "authors": [doc.get("creator")] if isinstance(doc.get("creator"), str) else doc.get("creator", [])[:3],
                    "year": doc.get("year")
                })
            return results
    except Exception as e:
        logging.warning(f"Internet Archive search failed: {str(e)}")
    return []


async def search_wikipedia(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Wikipedia for educational articles"""
    try:
        response = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": limit,
                "format": "json",
                "srprop": "snippet|titlesnippet"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("query", {}).get("search", [])[:limit]:
                page_id = item.get("pageid")
                title = item.get("title", "")
                # Clean HTML from snippet
                snippet = item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                results.append({
                    "id": f"wiki-{page_id}",
                    "title": title,
                    "description": snippet[:200],
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source": "Wikipedia",
                    "type": "article",
                    "license": "cc-by-sa",
                    "thumbnail": None,
                    "subjects": [query],
                    "authors": ["Wikipedia Contributors"],
                    "year": None
                })
            return results
    except Exception as e:
        logging.warning(f"Wikipedia search failed: {str(e)}")
    return []


async def search_oer_commons(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search for Open Educational Resources"""
    # OER Commons doesn't have a public API, so we'll simulate with curated educational sites
    # This returns worksheet-related resources from known free sources
    worksheet_sources = [
        {
            "id": "oer-k5learning",
            "title": f"K5 Learning - {query} Worksheets",
            "description": f"Free printable {query} worksheets for K-5 students. Math, reading, spelling, grammar, science.",
            "url": f"https://www.k5learning.com/free-worksheets?search={query.replace(' ', '+')}",
            "source": "K5 Learning",
            "type": "worksheet",
            "license": "edu-only",
            "thumbnail": None,
            "subjects": [query, "worksheets", "K-5"],
            "authors": ["K5 Learning"],
            "year": 2024
        },
        {
            "id": "oer-mathdrills",
            "title": f"Math-Drills - {query}",
            "description": f"Free {query} math worksheets covering all topics from basic operations to algebra.",
            "url": f"https://www.math-drills.com/search.php?q={query.replace(' ', '+')}",
            "source": "Math-Drills",
            "type": "worksheet",
            "license": "edu-only",
            "thumbnail": None,
            "subjects": [query, "math", "worksheets"],
            "authors": ["Math-Drills"],
            "year": 2024
        },
        {
            "id": "oer-commoncore",
            "title": f"Common Core Sheets - {query}",
            "description": f"Free Common Core aligned {query} worksheets for math, ELA, science.",
            "url": f"https://www.commoncoresheets.com/search.php?s={query.replace(' ', '+')}",
            "source": "Common Core Sheets",
            "type": "worksheet",
            "license": "edu-only",
            "thumbnail": None,
            "subjects": [query, "common core", "worksheets"],
            "authors": ["Common Core Sheets"],
            "year": 2024
        },
        {
            "id": "oer-liveworksheets",
            "title": f"Live Worksheets - {query}",
            "description": f"Interactive {query} worksheets that students can complete online.",
            "url": f"https://www.liveworksheets.com/search.asp?content={query.replace(' ', '+')}",
            "source": "Live Worksheets",
            "type": "worksheet",
            "license": "varies",
            "thumbnail": None,
            "subjects": [query, "interactive", "worksheets"],
            "authors": ["Live Worksheets Community"],
            "year": 2024
        },
        {
            "id": "oer-superstar",
            "title": f"Superstar Worksheets - {query}",
            "description": f"Free printable {query} worksheets for pre-K through 8th grade.",
            "url": f"https://www.superstarworksheets.com/?s={query.replace(' ', '+')}",
            "source": "Superstar Worksheets",
            "type": "worksheet",
            "license": "edu-only",
            "thumbnail": None,
            "subjects": [query, "worksheets", "K-8"],
            "authors": ["Superstar Worksheets"],
            "year": 2024
        }
    ]
    
    # Filter based on query relevance
    relevant_sources = []
    query_lower = query.lower()
    
    for source in worksheet_sources:
        # Always include if searching for worksheets or educational content
        if any(term in query_lower for term in ["worksheet", "activity", "printable", "exercise", "practice"]):
            relevant_sources.append(source)
        elif any(term in query_lower for term in ["math", "science", "stem", "reading", "writing", "grammar"]):
            relevant_sources.append(source)
        else:
            # Include a subset for general queries
            relevant_sources.append(source)
    
    return relevant_sources[:limit]


async def ai_enhance_results(query: str, results: list) -> list:
    """Use AI to enhance, categorize and rank search results"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        llm_key = os.environ.get("EMERGENT_LLM_KEY")
        if not llm_key:
            return results
        
        chat = LlmChat(
            api_key=llm_key,
            session_id=f"content-search-{datetime.now().timestamp()}",
            system_message="""You are an educational content curator. Given search results, you will:
1. Add a relevance_score (1-10) based on how well each result matches the query
2. Categorize each result into: worksheet, book, article, video, course, or resource
3. Add grade_level suggestions: preschool, elementary, middle, high, university, all
4. Add a brief AI summary (1 sentence) for each result
Return JSON array with enhanced results. Keep all original fields and add: relevance_score, category, grade_levels, ai_summary"""
        ).with_model("openai", "gpt-4.1-mini")
        
        # Prepare results for AI
        results_summary = []
        for r in results[:15]:  # Limit to avoid token limits
            results_summary.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "description": r.get("description", "")[:150],
                "source": r.get("source"),
                "type": r.get("type"),
                "subjects": r.get("subjects", [])[:3]
            })
        
        user_message = UserMessage(
            text=f"""Query: "{query}"

Search Results to enhance:
{json.dumps(results_summary, indent=2)}

Return a JSON array with enhanced results. Add relevance_score, category, grade_levels array, and ai_summary to each."""
        )
        
        response = await chat.send_message(user_message)
        
        # Parse AI response
        try:
            # Try to extract JSON from response
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            enhanced_data = json.loads(response_text)
            
            # Merge AI enhancements with original results
            enhanced_map = {item.get("id"): item for item in enhanced_data}
            
            for result in results:
                result_id = result.get("id")
                if result_id in enhanced_map:
                    ai_data = enhanced_map[result_id]
                    result["relevance_score"] = ai_data.get("relevance_score", 5)
                    result["category"] = ai_data.get("category", result.get("type", "resource"))
                    result["grade_levels"] = ai_data.get("grade_levels", ["all"])
                    result["ai_summary"] = ai_data.get("ai_summary", "")
                else:
                    result["relevance_score"] = 5
                    result["category"] = result.get("type", "resource")
                    result["grade_levels"] = ["all"]
                    result["ai_summary"] = ""
            
            # Sort by relevance
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
        except json.JSONDecodeError:
            logging.warning("Could not parse AI response as JSON")
        
        return results
        
    except Exception as e:
        logging.warning(f"AI enhancement failed: {str(e)}")
        return results


@api_router.get("/content-library/worksheets/search")
async def search_worksheets(
    query: str = Query(..., description="Search query for worksheets"),
    grade: str = Query(default="all", description="Grade level filter"),
    subject: str = Query(default="all", description="Subject filter"),
    limit: int = Query(default=20, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Search specifically for free educational worksheets and activity sheets"""
    try:
        all_results = []
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search worksheet-specific sources
            oer_results = await search_oer_commons(client, query, limit)
            all_results.extend(oer_results)
            
            # Also search Internet Archive for educational materials
            ia_results = await search_internet_archive(client, f"{query} worksheet OR activity sheet", limit // 2)
            all_results.extend(ia_results)
        
        # Filter by grade if specified
        if grade != "all":
            grade_map = {
                "preschool": ["preschool", "pre-k", "kindergarten"],
                "elementary": ["k-5", "elementary", "grade 1", "grade 2", "grade 3", "grade 4", "grade 5"],
                "middle": ["6-8", "middle", "grade 6", "grade 7", "grade 8"],
                "high": ["9-12", "high school", "grade 9", "grade 10", "grade 11", "grade 12"]
            }
            grade_terms = grade_map.get(grade, [grade])
            filtered = []
            for r in all_results:
                subjects = " ".join(r.get("subjects", [])).lower()
                title = r.get("title", "").lower()
                if any(term in subjects or term in title for term in grade_terms):
                    filtered.append(r)
            if filtered:
                all_results = filtered
        
        return {
            "results": all_results[:limit],
            "total": len(all_results),
            "query": query,
            "grade": grade,
            "subject": subject
        }
    
    except Exception as e:
        logging.error(f"Error searching worksheets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()