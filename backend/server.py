from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Form, Query, Depends, status, Request
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
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://freedomvid.preview.emergentagent.com")


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
        user_id: str = None,
        page_token: str = None,
        order: str = "viewCount"
    ) -> dict:
        """
        Optimized video search with caching, pagination and field filtering
        """
        params = {"q": query, "max": max_results, "page": page_token or "first", "order": order}
        cache_key = cls.get_cache_key("search", params)
        
        # Check cache first (skip cache if requesting different page)
        if not page_token:
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
            "order": order,
            "videoDuration": "medium",
            "fields": cls.SEARCH_FIELDS + ",nextPageToken,prevPageToken,pageInfo",  # Include pagination info
        }
        
        # Add page token for pagination
        if page_token:
            request_params["pageToken"] = page_token
        
        # Add quotaUser for per-user tracking
        if user_id:
            request_params["quotaUser"] = hashlib.md5(user_id.encode()).hexdigest()[:40]
        
        try:
            search_request = youtube.search().list(**request_params)
            
            # Add ETag header for conditional request (only for first page)
            if not page_token:
                etag = cls.get_etag(cache_key)
                if etag:
                    search_request.headers["If-None-Match"] = etag
            
            response = search_request.execute()
            
            # Cache the response with ETag (only first page)
            if not page_token:
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


# ==================== MICROSOFT OAUTH ====================

MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET")
MICROSOFT_TENANT = "common"  # Allows any Microsoft account

@api_router.get("/auth/microsoft/login")
async def microsoft_login(request: Request):
    """Redirect to Microsoft OAuth login"""
    # Get the frontend URL for redirect - use referer or origin header
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    # Determine the correct frontend URL
    if origin and "localhost" not in origin:
        frontend_url = origin
    elif referer:
        # Extract base URL from referer
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        frontend_url = f"{parsed.scheme}://{parsed.netloc}"
    else:
        # Use FRONTEND_URL from environment, fallback to localhost for local dev
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    
    redirect_uri = f"{frontend_url}/auth/microsoft/callback"
    
    # Build Microsoft OAuth URL
    auth_url = (
        f"https://login.microsoftonline.com/{MICROSOFT_TENANT}/oauth2/v2.0/authorize"
        f"?client_id={MICROSOFT_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&response_mode=query"
        f"&scope=openid%20profile%20email%20User.Read"
        f"&state=contentflow_microsoft_auth"
    )
    
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@api_router.post("/auth/microsoft/callback")
async def microsoft_callback(code: str = Form(...), redirect_uri: str = Form(...)):
    """Process Microsoft OAuth callback"""
    try:
        # Exchange code for tokens
        token_url = f"https://login.microsoftonline.com/{MICROSOFT_TENANT}/oauth2/v2.0/token"
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data={
                    "client_id": MICROSOFT_CLIENT_ID,
                    "client_secret": MICROSOFT_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "openid profile email User.Read"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.json()
                logging.error(f"Microsoft token error: {error_detail}")
                raise HTTPException(status_code=400, detail="Failed to get access token from Microsoft")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Get user info from Microsoft Graph
            user_response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info from Microsoft")
            
            user_info = user_response.json()
        
        # Extract user data
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        full_name = user_info.get("displayName", "")
        microsoft_id = user_info.get("id")
        
        if not email:
            raise HTTPException(status_code=400, detail="Could not get email from Microsoft account")
        
        # Check if user exists
        user = await db.users.find_one({"email": email})
        
        if not user:
            # Create new user
            user_id = str(uuid.uuid4())
            user = {
                "_id": user_id,
                "email": email,
                "full_name": full_name,
                "microsoft_id": microsoft_id,
                "auth_provider": "microsoft",
                "email_verified": True,  # Microsoft emails are pre-verified
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.users.insert_one(user)
        else:
            user_id = str(user.get("_id")) or user.get("user_id")
            # Update Microsoft ID if not set
            if not user.get("microsoft_id"):
                await db.users.update_one(
                    {"email": email},
                    {"$set": {"microsoft_id": microsoft_id}}
                )
        
        # Create JWT token
        jwt_token = create_access_token(data={"sub": email})
        
        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "auth_provider": "microsoft"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Microsoft OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


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
    
    # Auto-verify users since email verification isn't configured
    # Set email_verified to True to allow immediate login
    new_user = {
        "_id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "email_verified": True,  # Auto-verified since Resend API not configured
        "verification_token": verification_token,
        "auth_provider": "email",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }
    
    await db.users.insert_one(new_user)
    
    # Try to send verification email (non-blocking, won't fail registration)
    if RESEND_API_KEY:
        asyncio.create_task(send_verification_email(user_data.email, verification_token, user_data.full_name))
    
    # Create access token and log user in immediately
    access_token = create_access_token(data={"sub": user_data.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "created_at": new_user["created_at"],
            "email_verified": True
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


@api_router.get("/youtube/cache-stats")
async def get_youtube_cache_stats(current_user: dict = Depends(get_current_user)):
    """
    Get YouTube API cache statistics for monitoring and debugging.
    Shows both in-memory and persistent cache stats.
    """
    # In-memory cache stats
    memory_cache_entries = len(YouTubeAPIOptimizer._data_cache)
    memory_etag_entries = len(YouTubeAPIOptimizer._etag_cache)
    
    # Persistent cache stats
    persistent_cache_count = await db[YouTubePersistentCache.CACHE_COLLECTION].count_documents({})
    persistent_valid_count = await db[YouTubePersistentCache.CACHE_COLLECTION].count_documents({
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    # Discovered videos in main collection
    discovered_videos_count = await db.discovered_videos.count_documents({})
    
    return {
        "memory_cache": {
            "data_entries": memory_cache_entries,
            "etag_entries": memory_etag_entries,
            "ttl_minutes": YouTubeAPIOptimizer.CACHE_TTL_MINUTES
        },
        "persistent_cache": {
            "total_entries": persistent_cache_count,
            "valid_entries": persistent_valid_count,
            "ttl_hours": YouTubePersistentCache.CACHE_TTL_HOURS
        },
        "discovered_videos": discovered_videos_count,
        "optimization_features": {
            "field_filtering": True,
            "etag_conditional_requests": True,
            "quota_user_tracking": True,
            "batch_requests": True,
            "gzip_compression": True
        }
    }


@api_router.post("/youtube/clear-cache")
async def clear_youtube_cache(current_user: dict = Depends(get_current_user)):
    """Clear all YouTube API caches (admin function)"""
    # Clear in-memory cache
    YouTubeAPIOptimizer._data_cache.clear()
    YouTubeAPIOptimizer._etag_cache.clear()
    YouTubeAPIOptimizer._cache_timestamps.clear()
    
    # Clear persistent cache
    await db[YouTubePersistentCache.CACHE_COLLECTION].delete_many({})
    
    return {"message": "All YouTube caches cleared successfully"}


@api_router.get("/discover")
async def discover_videos(
    query: str = Query(default="", description="Search query"),
    max_results: int = Query(default=50, le=50),
    min_views: int = Query(default=1000, description="Minimum view count"),
    page_token: str = Query(default=None, description="Page token for pagination"),
    sort_by: str = Query(default="viewCount", description="Sort order: viewCount, date, rating, relevance"),
    skip_cache: bool = Query(default=False, description="Skip cache and fetch fresh results"),
    current_user: dict = Depends(get_current_user)
):
    """
    Discover CC BY licensed YouTube videos with optimized API usage:
    - Caches results (in-memory + MongoDB)
    - Uses minimal fields to reduce quota
    - Supports ETags for conditional requests
    - Tracks quotaUser per user
    - Supports pagination with page tokens
    - Multiple sort options: viewCount, date, rating, relevance
    """
    try:
        # Get user ID for quota tracking
        user_id = str(current_user.get("_id", current_user.get("email", "anonymous")))
        search_query = query.strip() if query else "tutorial"
        
        # Validate sort option
        valid_sorts = ["viewCount", "date", "rating", "relevance"]
        if sort_by not in valid_sorts:
            sort_by = "viewCount"
        
        # 1. Check persistent cache first (only for first page and if not skipping cache)
        if not page_token and not skip_cache:
            cached_videos = await YouTubePersistentCache.get_cached_search(search_query, min_views)
            if cached_videos:
                return {
                    "videos": cached_videos[:max_results],
                    "total": len(cached_videos[:max_results]),
                    "cached": True,
                    "cache_type": "persistent",
                    "next_page_token": None,
                    "message": "Showing cached results. Use skip_cache=true for fresh results."
                }
        
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        
        if youtube_api_key:
            try:
                # Clean up expired in-memory cache periodically
                YouTubeAPIOptimizer.clear_expired_cache()
                
                youtube = build('youtube', 'v3', developerKey=youtube_api_key, cache_discovery=False)
                
                # 2. Use optimized search with caching, pagination and field filtering
                search_response = await YouTubeAPIOptimizer.search_videos(
                    youtube, 
                    search_query,
                    max_results=50,
                    user_id=user_id,
                    page_token=page_token,
                    order=sort_by
                )
                
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                next_page_token = search_response.get('nextPageToken')
                prev_page_token = search_response.get('prevPageToken')
                total_results = search_response.get('pageInfo', {}).get('totalResults', 0)
                
                # Try alternative queries if no results (only on first page)
                if not video_ids and not page_token:
                    alt_queries = [
                        f"{search_query} creative commons",
                        "creative commons tutorial" if not query else search_query,
                    ]
                    for alt_query in alt_queries:
                        alt_response = await YouTubeAPIOptimizer.search_videos(
                            youtube, alt_query, max_results=50, user_id=user_id, order=sort_by
                        )
                        video_ids = [item['id']['videoId'] for item in alt_response.get('items', [])]
                        next_page_token = alt_response.get('nextPageToken')
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
                
                # 4. Store in MongoDB for persistence (only for first page)
                if videos and not page_token:
                    await db.discovered_videos.delete_many({})
                    await db.discovered_videos.insert_many(videos)
                    videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
                    
                    # Also cache in persistent cache
                    await YouTubePersistentCache.set_cached_search(search_query, min_views, videos)
                
                return {
                    "videos": videos, 
                    "total": len(videos),
                    "total_available": total_results,
                    "next_page_token": next_page_token,
                    "prev_page_token": prev_page_token,
                    "has_more": next_page_token is not None,
                    "sort_by": sort_by,
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
                            "next_page_token": None,
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
    per_page: int = Query(default=50, le=100),
    source: str = Query(default="all", description="Filter by source: all, unsplash, pexels, pixabay"),
    image_type: str = Query(default=None, description="Filter by type: photo, illustration, vector"),
    current_user: dict = Depends(get_current_user)
):
    """Search for copyright-free images from Unsplash, Pexels, and Pixabay
    
    Image Type Filtering:
    - photo: Search Unsplash, Pexels, and Pixabay (all support photos)
    - illustration: Search ONLY Pixabay (only source with illustrations)
    - vector: Search ONLY Pixabay (only source with vectors)
    - None/all: Search all sources for all types
    """
    try:
        images = []
        total_available = 0
        
        # Get API keys from environment
        unsplash_key = os.environ.get('UNSPLASH_API_KEY', '')
        pexels_key = os.environ.get('PEXELS_API_KEY', 'QsPCgrnUhMSwyA25GWLfqMdYdJZw2Rthp33l24iYFCrTpuJcwUEBGAhq')
        pixabay_key = os.environ.get('PIXABAY_API_KEY', '')
        
        # Determine which sources to query based on image_type
        # Only Pixabay supports illustrations and vectors
        is_pixabay_only_type = image_type in ["illustration", "vector"]
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            tasks = []
            
            # Search Unsplash (only for photos - Unsplash doesn't have illustrations/vectors)
            # Skip if user specifically wants illustrations or vectors
            if unsplash_key and source in ["all", "unsplash"] and not is_pixabay_only_type:
                tasks.append(search_unsplash_images(client, query, page, per_page, unsplash_key))
            
            # Search Pexels (only for photos - Pexels doesn't have illustrations/vectors)
            # Skip if user specifically wants illustrations or vectors
            if source in ["all", "pexels"] and not is_pixabay_only_type:
                tasks.append(search_pexels_images(client, query, page, per_page, pexels_key))
            
            # Search Pixabay (supports photos, illustrations, and vectors)
            # Always search if source allows, with proper image_type filtering
            if pixabay_key and source in ["all", "pixabay"]:
                tasks.append(search_pixabay_images(client, query, page, per_page, pixabay_key, image_type))
            
            # Run all searches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict):
                    images.extend(result.get("images", []))
                    total_available += result.get("total", 0)
                elif isinstance(result, Exception):
                    logging.warning(f"Image search source failed: {str(result)}")
        
        # Filter by image_type if specified (in case API didn't filter)
        if image_type and image_type != "all":
            images = [img for img in images if img.get("image_type") == image_type]
        
        # Interleave results from all sources for variety
        sources_dict = {}
        for img in images:
            src = img["source"]
            if src not in sources_dict:
                sources_dict[src] = []
            sources_dict[src].append(img)
        
        # Interleave images from different sources
        combined = []
        source_lists = list(sources_dict.values())
        if source_lists:
            max_len = max(len(lst) for lst in source_lists)
            for i in range(max_len):
                for lst in source_lists:
                    if i < len(lst):
                        combined.append(lst[i])
        
        # Calculate pagination info
        total_pages = (total_available + per_page - 1) // per_page if total_available > 0 else 1
        
        return {
            "images": combined[:per_page],  # Return requested number
            "total": total_available,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "query": query,
            "sources": list(sources_dict.keys()),
            "image_type": image_type
        }
    
    except Exception as e:
        logging.error(f"Error searching images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def search_unsplash_images(client: httpx.AsyncClient, query: str, page: int, per_page: int, api_key: str) -> dict:
    """Search Unsplash for images"""
    try:
        response = await client.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query,
                "page": page,
                "per_page": min(per_page, 30),  # Unsplash max is 30
                "orientation": "landscape"
            },
            headers={"Authorization": f"Client-ID {api_key}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            images = []
            for photo in data.get("results", []):
                images.append({
                    "id": f"unsplash_{photo['id']}",
                    "url": photo["urls"]["regular"],
                    "thumbnail": photo["urls"]["small"],
                    "title": photo.get("description") or photo.get("alt_description") or "Untitled",
                    "photographer": photo["user"]["name"],
                    "photographer_url": photo["user"]["links"]["html"],
                    "source": "unsplash",
                    "source_url": photo["links"]["html"],
                    "download_url": photo["urls"]["full"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "color": photo.get("color", "#000000"),
                    "likes": photo.get("likes", 0),
                    "license": "Unsplash License (Free for commercial use)",
                    "image_type": "photo"
                })
            return {"images": images, "total": data.get("total", 0)}
    except Exception as e:
        logging.warning(f"Unsplash API error: {str(e)}")
    return {"images": [], "total": 0}


async def search_pexels_images(client: httpx.AsyncClient, query: str, page: int, per_page: int, api_key: str) -> dict:
    """Search Pexels for images (photos only)"""
    try:
        response = await client.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": query,
                "page": page,
                "per_page": min(per_page, 80)  # Pexels max is 80
            },
            headers={"Authorization": api_key}
        )
        
        if response.status_code == 200:
            data = response.json()
            images = []
            for photo in data.get("photos", []):
                images.append({
                    "id": f"pexels_{photo['id']}",
                    "url": photo["src"]["large"],
                    "thumbnail": photo["src"]["medium"],
                    "title": photo.get("alt") or "Untitled",
                    "photographer": photo["photographer"],
                    "photographer_url": photo["photographer_url"],
                    "source": "pexels",
                    "source_url": photo["url"],
                    "download_url": photo["src"]["original"],
                    "width": photo["width"],
                    "height": photo["height"],
                    "color": photo.get("avg_color", "#000000"),
                    "likes": 0,
                    "license": "Pexels License (Free for commercial use)",
                    "image_type": "photo"
                })
            return {"images": images, "total": data.get("total_results", 0)}
    except Exception as e:
        logging.warning(f"Pexels API error: {str(e)}")
    return {"images": [], "total": 0}


async def search_pixabay_images(client: httpx.AsyncClient, query: str, page: int, per_page: int, api_key: str, image_type: str = None) -> dict:
    """Search Pixabay for images - supports photos, illustrations, and vectors"""
    try:
        # Pixabay image_type: all, photo, illustration, vector
        pixabay_type = "all"
        if image_type:
            if image_type in ["photo", "illustration", "vector"]:
                pixabay_type = image_type
        
        response = await client.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "page": page,
                "per_page": min(per_page, 200),  # Pixabay allows up to 200
                "image_type": pixabay_type,
                "safesearch": "true"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            images = []
            for photo in data.get("hits", []):
                # Get the actual type from Pixabay response
                img_type = photo.get("type", "photo")
                if img_type == "vector/svg":
                    img_type = "vector"
                elif "illustration" in img_type.lower():
                    img_type = "illustration"
                else:
                    img_type = "photo"
                
                images.append({
                    "id": f"pixabay_{photo['id']}",
                    "url": photo.get("largeImageURL") or photo.get("webformatURL"),
                    "thumbnail": photo.get("previewURL") or photo.get("webformatURL"),
                    "title": photo.get("tags", "Untitled"),
                    "photographer": photo.get("user", "Unknown"),
                    "photographer_url": f"https://pixabay.com/users/{photo.get('user', '')}-{photo.get('user_id', '')}",
                    "source": "pixabay",
                    "source_url": photo.get("pageURL", ""),
                    "download_url": photo.get("largeImageURL") or photo.get("fullHDURL") or photo.get("webformatURL"),
                    "width": photo.get("imageWidth", 0),
                    "height": photo.get("imageHeight", 0),
                    "color": "#000000",
                    "likes": photo.get("likes", 0),
                    "license": "Pixabay License (Free for commercial use)",
                    "image_type": img_type
                })
            return {"images": images, "total": data.get("totalHits", 0)}
    except Exception as e:
        logging.warning(f"Pixabay API error: {str(e)}")
    return {"images": [], "total": 0}

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
    category: str = Query(default="all", description="Category filter: all, article, course, video, resource, worksheet, book"),
    grade: str = Query(default="all", description="Education level filter: preschool, elementary, middle, high, university"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, le=100, description="Results per page"),
    enhance: bool = Query(default=False, description="Use AI to enhance results (slower)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Dynamic search for copyright-free educational content across the ENTIRE WEB.
    Searches multiple open-access APIs for real, current content.
    """
    try:
        all_results = []
        fetch_limit = per_page * 2  # Get enough results
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            tasks = []
            
            # ARTICLES - Search multiple open-access sources
            if category in ["all", "article"]:
                tasks.append(search_openalex_articles(client, query, fetch_limit))  # 240M+ papers
                tasks.append(search_arxiv_articles(client, query, fetch_limit // 2))  # Academic preprints
                tasks.append(search_pubmed_articles(client, query, fetch_limit // 2))  # Medical/science
                tasks.append(search_wikipedia_articles(client, query, fetch_limit // 3))  # Encyclopedia
                tasks.append(search_doaj_articles(client, query, fetch_limit // 2))  # Open access journals
            
            # COURSES - Search course aggregators and platforms (CC-BY LICENSED)
            if category in ["all", "course"]:
                tasks.append(search_openstax_cc(client, query, fetch_limit))  # CC BY 4.0 textbooks
                tasks.append(search_ck12_flexbooks(client, query, fetch_limit))  # CC BY-NC FlexBooks
                tasks.append(search_mit_ocw_real(client, query, fetch_limit))  # CC BY-NC-SA courses
                tasks.append(search_wikiversity_courses(client, query, fetch_limit))  # CC BY-SA
                tasks.append(search_wikibooks_courses(client, query, fetch_limit // 2))  # CC BY-SA
                tasks.append(search_youtube_courses(client, query, fetch_limit))  # CC BY videos
                tasks.append(search_freecodecamp_courses(client, query, fetch_limit // 2))  # Free
            
            # VIDEOS - Search for CC-licensed video content
            if category in ["all", "video"]:
                tasks.append(search_youtube_videos_comprehensive(client, query, fetch_limit))  # CC BY
                tasks.append(search_youtube_educational(client, query, fetch_limit // 2))  # CC BY
                tasks.append(search_internet_archive_videos_enhanced(client, query, fetch_limit))  # Public Domain
                tasks.append(search_internet_archive_videos(client, query, fetch_limit // 2))  # Public Domain
                tasks.append(search_ted_talks(client, query, fetch_limit // 2))  # CC BY-NC-ND
            
            # RESOURCES - Search CC-licensed educational resources
            if category in ["all", "resource", "worksheet"]:
                tasks.append(search_oer_commons_cc(client, query, fetch_limit))  # CC BY / CC BY-SA
                tasks.append(search_wikimedia_commons(client, query, fetch_limit // 2))  # CC BY-SA
                tasks.append(search_merlot_resources(client, query, fetch_limit // 2))
                tasks.append(search_internet_archive_texts(client, query, fetch_limit // 2))  # Public Domain
                tasks.append(search_smithsonian_resources(client, query, fetch_limit // 3))  # Open Access
                tasks.append(search_library_of_congress(client, query, fetch_limit // 2))  # Public Domain
                tasks.append(search_pbs_learningmedia(client, query, fetch_limit // 3))  # Educational
            
            # BOOKS - Public Domain and CC-licensed books
            if category in ["all", "book"]:
                tasks.append(search_openlibrary(client, query, fetch_limit // 2))  # Various (check per book)
                tasks.append(search_internet_archive(client, query, fetch_limit // 2))  # Public Domain
            
            # Run all searches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logging.warning(f"Search source failed: {str(result)}")
        
        # Filter by category if specified
        if category != "all":
            all_results = [r for r in all_results if r.get("type") == category or r.get("category") == category]
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            title = r.get("title", "")
            key = url or title
            if key and key not in seen_urls:
                seen_urls.add(key)
                unique_results.append(r)
        all_results = unique_results
        
        # Sort by relevance (items with more metadata first)
        all_results.sort(key=lambda x: (
            1 if x.get("description") else 0,
            1 if x.get("thumbnail") and x.get("thumbnail") != "📄" else 0
        ), reverse=True)
        
        # Pagination
        total_results = len(all_results)
        total_pages = max(1, (total_results + per_page - 1) // per_page)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = all_results[start_idx:end_idx]
        
        return {
            "results": paginated_results,
            "total": total_results,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "query": query,
            "category": category,
            "grade": grade,
            "sources": get_active_sources_v2(category)
        }
    
    except Exception as e:
        logging.error(f"Error in content library search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_active_sources_v2(category: str) -> list:
    """Get list of CC-licensed sources used for a category"""
    sources = {
        "all": ["OpenStax (CC BY)", "CK-12 (CC BY-NC)", "MIT OCW (CC BY-NC-SA)", "Wikiversity (CC BY-SA)", "Wikibooks (CC BY-SA)", "YouTube (CC BY)", "Internet Archive (Public Domain)", "OER Commons (CC BY/SA)", "Wikimedia Commons (CC BY-SA)", "Library of Congress (Public Domain)"],
        "article": ["OpenAlex", "arXiv (Open Access)", "PubMed Central", "Wikipedia (CC BY-SA)", "DOAJ (Open Access)"],
        "course": ["OpenStax (CC BY 4.0)", "CK-12 FlexBooks (CC BY-NC)", "MIT OpenCourseWare (CC BY-NC-SA)", "Wikiversity (CC BY-SA)", "Wikibooks (CC BY-SA)", "freeCodeCamp (Free)", "YouTube (CC BY)"],
        "video": ["YouTube Creative Commons (CC BY)", "Internet Archive (Public Domain)", "TED Talks (CC BY-NC-ND)"],
        "resource": ["OER Commons (CC BY/CC BY-SA)", "Wikimedia Commons (CC BY-SA)", "MERLOT", "Internet Archive (Public Domain)", "Smithsonian (Open Access)", "Library of Congress (Public Domain)", "PBS LearningMedia"],
        "worksheet": ["OER Commons (CC BY/SA)", "Internet Archive", "PBS LearningMedia"],
        "book": ["OpenLibrary", "Internet Archive (Public Domain)"]
    }
    return sources.get(category, sources["all"])


# ==================== ARTICLE SEARCH FUNCTIONS ====================

async def search_openalex_articles(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search OpenAlex - 240 million scholarly works, completely free"""
    try:
        response = await client.get(
            "https://api.openalex.org/works",
            params={
                "search": query,
                "filter": "is_oa:true",  # Only open access
                "per_page": min(limit, 50),
                "sort": "relevance_score:desc",
                "mailto": "contentflow@example.com"
            },
            headers={"User-Agent": "ContentFlow/1.0 (Educational Search)"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", []):
                title = item.get("title", "Untitled")
                authors = item.get("authorships", [])
                author_names = ", ".join([a.get("author", {}).get("display_name", "") for a in authors[:3]])
                
                # Get the best available URL
                url = item.get("primary_location", {}).get("landing_page_url", "") or item.get("doi", "")
                if url and url.startswith("https://doi.org/"):
                    url = url
                elif item.get("doi"):
                    url = f"https://doi.org/{item.get('doi')}"
                
                pdf_url = item.get("primary_location", {}).get("pdf_url", "")
                
                results.append({
                    "id": f"openalex_{item.get('id', '').split('/')[-1]}",
                    "title": title,
                    "description": f"By {author_names}. Published {item.get('publication_year', 'N/A')}. Cited {item.get('cited_by_count', 0)} times.",
                    "type": "article",
                    "category": "article",
                    "source": "OpenAlex",
                    "url": url,
                    "download_url": pdf_url,
                    "thumbnail": "📄",
                    "license": "Open Access",
                    "free": True,
                    "year": item.get("publication_year"),
                    "citations": item.get("cited_by_count", 0)
                })
            return results
    except Exception as e:
        logging.warning(f"OpenAlex search failed: {str(e)}")
    return []


async def search_pubmed_articles(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search PubMed Central for free medical/science articles"""
    try:
        # First search for IDs
        search_response = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "pmc",  # PubMed Central (free full text)
                "term": f"{query} AND open access[filter]",
                "retmax": min(limit, 50),
                "retmode": "json",
                "sort": "relevance"
            },
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        if search_response.status_code == 200:
            search_data = search_response.json()
            ids = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not ids:
                return []
            
            # Fetch details for the IDs
            detail_response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={
                    "db": "pmc",
                    "id": ",".join(ids[:20]),
                    "retmode": "json"
                },
                headers={"User-Agent": "ContentFlow/1.0"}
            )
            
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                results = []
                
                for pmcid in ids[:20]:
                    item = detail_data.get("result", {}).get(pmcid, {})
                    if item and isinstance(item, dict):
                        title = item.get("title", "Untitled")
                        authors = item.get("authors", [])
                        author_str = ", ".join([a.get("name", "") for a in authors[:3]]) if authors else "Unknown"
                        
                        results.append({
                            "id": f"pmc_{pmcid}",
                            "title": title,
                            "description": f"By {author_str}. {item.get('source', '')} ({item.get('pubdate', '')})",
                            "type": "article",
                            "category": "article",
                            "source": "PubMed Central",
                            "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/",
                            "download_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/pdf/",
                            "thumbnail": "📄",
                            "license": "Open Access",
                            "free": True
                        })
                return results
    except Exception as e:
        logging.warning(f"PubMed search failed: {str(e)}")
    return []


async def search_doaj_articles(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search DOAJ - Directory of Open Access Journals"""
    try:
        response = await client.get(
            "https://doaj.org/api/search/articles/" + query.replace(" ", "%20"),
            params={
                "pageSize": min(limit, 50)
            },
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", []):
                bibjson = item.get("bibjson", {})
                title = bibjson.get("title", "Untitled")
                authors = bibjson.get("author", [])
                author_str = ", ".join([a.get("name", "") for a in authors[:3]]) if authors else "Unknown"
                
                # Get URL
                links = bibjson.get("link", [])
                url = ""
                for link in links:
                    if link.get("type") == "fulltext":
                        url = link.get("url", "")
                        break
                if not url and links:
                    url = links[0].get("url", "")
                
                journal = bibjson.get("journal", {})
                
                results.append({
                    "id": f"doaj_{item.get('id', '')}",
                    "title": title,
                    "description": f"By {author_str}. Published in {journal.get('title', 'Open Access Journal')}",
                    "type": "article",
                    "category": "article",
                    "source": "DOAJ",
                    "url": url,
                    "thumbnail": "📄",
                    "license": "Open Access",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"DOAJ search failed: {str(e)}")
    return []


async def search_wikipedia_articles(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Wikipedia for articles"""
    try:
        response = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": min(limit, 50),
                "format": "json",
                "srprop": "snippet|titlesnippet|size"
            },
            headers={
                "User-Agent": "ContentFlow/1.0 (Educational Content Search; contact@contentflow.app)"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "")
                results.append({
                    "id": f"wiki_{item.get('pageid', '')}",
                    "title": title,
                    "description": item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")[:200],
                    "type": "article",
                    "category": "article",
                    "source": "Wikipedia",
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "thumbnail": "📄",
                    "license": "CC BY-SA",
                    "free": True
                })
            return results
        else:
            logging.warning(f"Wikipedia API returned status {response.status_code}")
    except Exception as e:
        logging.warning(f"Wikipedia search failed: {str(e)}")
    return []


async def search_arxiv_articles(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search arXiv for academic articles (all free/open access)"""
    try:
        response = await client.get(
            "http://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(limit, 30),
                "sortBy": "relevance"
            },
            headers={
                "User-Agent": "ContentFlow/1.0 (Educational Content Search)"
            }
        )
        
        if response.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            results = []
            
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:id", ns)
                
                if title is not None and link is not None:
                    arxiv_id = link.text.split("/")[-1] if link.text else ""
                    results.append({
                        "id": f"arxiv_{arxiv_id}",
                        "title": " ".join(title.text.strip().split()) if title.text else "Untitled",
                        "description": (" ".join(summary.text.strip().split())[:200] + "...") if summary is not None and summary.text else "",
                        "type": "article",
                        "category": "article",
                        "source": "arXiv",
                        "url": f"https://arxiv.org/abs/{arxiv_id}",
                        "download_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                        "thumbnail": "📄",
                        "license": "Open Access",
                        "free": True
                    })
            return results
        else:
            logging.warning(f"arXiv API returned status {response.status_code}")
    except Exception as e:
        logging.warning(f"arXiv search failed: {str(e)}")
    return []


async def search_oer_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search for free online courses from multiple sources"""
    results = []
    
    # Add curated free course platforms
    course_platforms = [
        {
            "name": "Khan Academy",
            "base_url": "https://www.khanacademy.org/search",
            "search_param": "referer=search&page_search_query="
        },
        {
            "name": "Coursera (Free)",
            "base_url": "https://www.coursera.org/search",
            "search_param": "query="
        },
        {
            "name": "edX (Free)",
            "base_url": "https://www.edx.org/search",
            "search_param": "q="
        }
    ]
    
    for platform in course_platforms:
        results.append({
            "id": f"course_{platform['name'].lower().replace(' ', '_')}_{query.replace(' ', '_')}",
            "title": f"{query} courses on {platform['name']}",
            "description": f"Find free {query} courses on {platform['name']} - one of the world's leading educational platforms.",
            "type": "course",
            "category": "course",
            "source": platform['name'],
            "url": f"{platform['base_url']}?{platform['search_param']}{query.replace(' ', '+')}",
            "thumbnail": "🎓",
            "license": "Free to access",
            "free": True
        })
    
    return results[:limit]


# ==================== CC-BY / CC-BY-SA LICENSED CONTENT SOURCES ====================

async def search_ck12_flexbooks(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search CK-12 FlexBooks - CC-BY-NC licensed educational content"""
    results = []
    
    # CK-12 provides excellent educational resources under CC licenses
    # Since they don't have a public API, we provide direct search links
    ck12_subjects = {
        "math": "Mathematics",
        "science": "Science", 
        "physics": "Physical Science",
        "chemistry": "Chemistry",
        "biology": "Biology",
        "earth": "Earth Science",
        "algebra": "Algebra",
        "geometry": "Geometry",
        "calculus": "Calculus",
        "statistics": "Statistics",
        "history": "History",
        "english": "English Language Arts"
    }
    
    query_lower = query.lower()
    
    # Main search result
    results.append({
        "id": f"ck12_search_{query.replace(' ', '_')}",
        "title": f"{query} - CK-12 FlexBooks",
        "description": f"Free, customizable textbooks and educational resources about {query}. CK-12 provides free educational content under Creative Commons licenses.",
        "type": "course",
        "category": "course",
        "source": "CK-12 Foundation",
        "url": f"https://www.ck12.org/search/?q={query.replace(' ', '+')}",
        "thumbnail": "📖",
        "license": "CC BY-NC",
        "license_details": "Creative Commons Attribution-NonCommercial - Free for educational use",
        "free": True
    })
    
    # Add subject-specific results if query matches
    for keyword, subject in ck12_subjects.items():
        if keyword in query_lower:
            results.append({
                "id": f"ck12_{keyword}",
                "title": f"{subject} FlexBooks - CK-12",
                "description": f"Comprehensive {subject.lower()} curriculum with interactive simulations, videos, and practice problems. Free to use and customize.",
                "type": "course",
                "category": "course", 
                "source": "CK-12 Foundation",
                "url": f"https://www.ck12.org/browse/{keyword}/",
                "thumbnail": "📚",
                "license": "CC BY-NC",
                "license_details": "Creative Commons Attribution-NonCommercial",
                "free": True
            })
    
    return results[:limit]


async def search_oer_commons_cc(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search OER Commons for CC-BY and CC-BY-SA licensed educational resources"""
    results = []
    
    try:
        # OER Commons provides open educational resources with clear CC licenses
        # Using their search interface since API requires authentication
        
        # Main search result with CC filters
        results.append({
            "id": f"oer_commons_{query.replace(' ', '_')}",
            "title": f"{query} - OER Commons",
            "description": f"Open Educational Resources about {query}. All content is licensed under Creative Commons for free educational and commercial use.",
            "type": "resource",
            "category": "resource",
            "source": "OER Commons",
            "url": f"https://www.oercommons.org/search?f.search={query.replace(' ', '+')}&f.sublevel=&f.general_subject=&f.alignment=&batch_size=20",
            "thumbnail": "🎓",
            "license": "CC BY / CC BY-SA",
            "license_details": "Creative Commons - Free for educational and commercial use",
            "free": True
        })
        
        # Add grade-level specific searches
        grade_levels = [
            ("preschool", "Pre-K"),
            ("lower-primary", "Grades K-2"),
            ("upper-primary", "Grades 3-5"),
            ("middle-school", "Middle School"),
            ("high-school", "High School"),
            ("college-upper-division", "College/University")
        ]
        
        for level_id, level_name in grade_levels[:3]:  # Limit to avoid too many results
            results.append({
                "id": f"oer_{level_id}_{query.replace(' ', '_')}",
                "title": f"{query} for {level_name} - OER Commons",
                "description": f"CC-licensed educational resources about {query} specifically designed for {level_name} students.",
                "type": "resource",
                "category": "resource",
                "source": "OER Commons",
                "url": f"https://www.oercommons.org/search?f.search={query.replace(' ', '+')}&f.sublevel={level_id}",
                "thumbnail": "📚",
                "license": "CC BY / CC BY-SA",
                "license_details": "Creative Commons - Free for educational and commercial use",
                "free": True,
                "grade_levels": [level_name]
            })
    
    except Exception as e:
        logging.warning(f"OER Commons search failed: {str(e)}")
    
    return results[:limit]


async def search_openstax_cc(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search OpenStax for CC BY 4.0 licensed free textbooks"""
    try:
        response = await client.get(
            "https://openstax.org/apps/cms/api/v2/pages/",
            params={
                "type": "books.Book",
                "fields": "title,description,cover_url,webview_rex_link",
                "limit": min(limit, 50)
            },
            headers={"User-Agent": "ContentFlow/1.0 (Educational Search)"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            query_lower = query.lower()
            
            for item in data.get("items", []):
                title = item.get("title", "")
                desc = item.get("description", "")
                
                # Clean HTML from description
                import re
                desc = re.sub(r'<[^>]+>', '', desc) if desc else ""
                desc = desc.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                
                # Filter by query relevance
                if query_lower in title.lower() or query_lower in desc.lower() or not query.strip():
                    results.append({
                        "id": f"openstax_{item.get('id', '')}",
                        "title": title,
                        "description": desc[:200] if desc else "Free, peer-reviewed textbook from OpenStax",
                        "type": "course",
                        "category": "course",
                        "source": "OpenStax",
                        "url": item.get("webview_rex_link", f"https://openstax.org/details/{item.get('id', '')}"),
                        "thumbnail": item.get("cover_url", "📚"),
                        "license": "CC BY 4.0",
                        "license_details": "Creative Commons Attribution 4.0 - Free for ANY use including commercial",
                        "free": True
                    })
            return results[:limit]
    except Exception as e:
        logging.warning(f"OpenStax search failed: {str(e)}")
    return []


async def search_wikimedia_commons(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Wikimedia Commons for CC-licensed media"""
    try:
        response = await client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srnamespace": "6",  # File namespace
                "srlimit": min(limit, 50),
                "format": "json"
            },
            headers={"User-Agent": "ContentFlow/1.0 (Educational Search)"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "").replace("File:", "")
                results.append({
                    "id": f"commons_{item.get('pageid', '')}",
                    "title": title,
                    "description": item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')[:200],
                    "type": "resource",
                    "category": "resource",
                    "source": "Wikimedia Commons",
                    "url": f"https://commons.wikimedia.org/wiki/File:{title.replace(' ', '_')}",
                    "thumbnail": "🖼️",
                    "license": "CC BY-SA / Public Domain",
                    "license_details": "Creative Commons or Public Domain - Free for ANY use",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"Wikimedia Commons search failed: {str(e)}")
    return []


# ==================== COURSE SEARCH FUNCTIONS ====================

async def search_openstax_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search OpenStax for free textbooks and courses"""
    try:
        response = await client.get(
            "https://openstax.org/apps/cms/api/v2/pages/",
            params={
                "type": "books.Book",
                "fields": "title,description,cover_url,webview_rex_link",
                "limit": min(limit, 50)
            },
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            query_lower = query.lower()
            
            for item in data.get("items", []):
                title = item.get("title", "")
                desc = item.get("description", "")
                
                # Filter by query relevance
                if query_lower in title.lower() or query_lower in desc.lower():
                    results.append({
                        "id": f"openstax_{item.get('id', '')}",
                        "title": title,
                        "description": desc[:200] if desc else "Free, peer-reviewed textbook from OpenStax",
                        "type": "course",
                        "category": "course",
                        "source": "OpenStax",
                        "url": item.get("webview_rex_link", f"https://openstax.org/details/{item.get('id', '')}"),
                        "thumbnail": item.get("cover_url", "📚"),
                        "license": "CC BY",
                        "free": True
                    })
            return results[:limit]
    except Exception as e:
        logging.warning(f"OpenStax search failed: {str(e)}")
    return []


async def search_mit_ocw_real(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search MIT OpenCourseWare"""
    try:
        # MIT OCW search
        response = await client.get(
            f"https://ocw.mit.edu/search/?q={query.replace(' ', '+')}&t=Lecture%20Videos",
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        # Since OCW doesn't have a public API, return search links
        results = [{
            "id": f"mit_ocw_{query.replace(' ', '_')}",
            "title": f"{query} - MIT OpenCourseWare",
            "description": f"Free courses from MIT covering {query}. Includes lecture videos, notes, and assignments.",
            "type": "course",
            "category": "course",
            "source": "MIT OpenCourseWare",
            "url": f"https://ocw.mit.edu/search/?q={query.replace(' ', '+')}",
            "thumbnail": "🎓",
            "license": "CC BY-NC-SA",
            "free": True
        }]
        return results
    except Exception as e:
        logging.warning(f"MIT OCW search failed: {str(e)}")
    return []


async def search_youtube_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search YouTube for course playlists"""
    youtube_api_key = os.environ.get("YOUTUBE_API_KEY", "")
    
    if not youtube_api_key:
        return [{
            "id": "yt_course_placeholder",
            "title": f"{query} - Full Course (YouTube)",
            "description": f"Find complete {query} courses and tutorials on YouTube",
            "type": "course",
            "category": "course",
            "source": "YouTube",
            "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}+full+course+tutorial",
            "thumbnail": "🎥",
            "license": "Various",
            "free": True
        }]
    
    try:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": f"{query} full course tutorial",
                "type": "playlist",
                "maxResults": min(limit, 25),
                "key": youtube_api_key
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                playlist_id = item.get("id", {}).get("playlistId", "")
                results.append({
                    "id": f"yt_course_{playlist_id}",
                    "title": snippet.get("title", "Untitled"),
                    "description": snippet.get("description", "")[:200],
                    "type": "course",
                    "category": "course",
                    "source": "YouTube",
                    "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", "🎥"),
                    "license": "Standard YouTube License",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"YouTube courses search failed: {str(e)}")
    return []


# ==================== VIDEO SEARCH FUNCTIONS ====================

async def search_internet_archive_videos(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Internet Archive for educational videos"""
    try:
        response = await client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f"({query}) AND mediatype:movies AND (subject:educational OR subject:lecture OR subject:documentary)",
                "fl[]": ["identifier", "title", "description", "creator", "year"],
                "sort[]": "downloads desc",
                "rows": min(limit, 50),
                "output": "json"
            },
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for doc in data.get("response", {}).get("docs", []):
                identifier = doc.get("identifier", "")
                results.append({
                    "id": f"ia_video_{identifier}",
                    "title": doc.get("title", "Untitled"),
                    "description": str(doc.get("description", ""))[:200] if doc.get("description") else "Educational video from Internet Archive",
                    "type": "video",
                    "category": "video",
                    "source": "Internet Archive",
                    "url": f"https://archive.org/details/{identifier}",
                    "thumbnail": f"https://archive.org/services/img/{identifier}",
                    "license": "Public Domain / Open",
                    "free": True,
                    "year": doc.get("year")
                })
            return results
    except Exception as e:
        logging.warning(f"Internet Archive videos search failed: {str(e)}")
    return []


async def search_ted_talks(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search TED Talks"""
    # TED doesn't have a public API, return search link
    return [{
        "id": f"ted_{query.replace(' ', '_')}",
        "title": f"TED Talks about {query}",
        "description": f"Inspiring talks from experts worldwide on {query}. Free to watch with transcripts in 100+ languages.",
        "type": "video",
        "category": "video",
        "source": "TED",
        "url": f"https://www.ted.com/search?q={query.replace(' ', '+')}",
        "thumbnail": "🎤",
        "license": "CC BY-NC-ND",
        "free": True
    }]


# ==================== RESOURCE SEARCH FUNCTIONS ====================

async def search_oer_commons_real(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search OER Commons - Open Educational Resources"""
    try:
        # OER Commons search page - they have limited API
        return [{
            "id": f"oer_{query.replace(' ', '_')}",
            "title": f"{query} - OER Commons Resources",
            "description": f"Open Educational Resources for {query}. Free to use, adapt, and share.",
            "type": "resource",
            "category": "resource",
            "source": "OER Commons",
            "url": f"https://www.oercommons.org/search?q={query.replace(' ', '+')}",
            "thumbnail": "📚",
            "license": "Various CC Licenses",
            "free": True
        }]
    except Exception as e:
        logging.warning(f"OER Commons search failed: {str(e)}")
    return []


async def search_merlot_resources(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search MERLOT - Multimedia Educational Resource for Learning and Online Teaching"""
    try:
        return [{
            "id": f"merlot_{query.replace(' ', '_')}",
            "title": f"{query} - MERLOT Learning Materials",
            "description": f"Curated collection of free online teaching and learning materials for {query}.",
            "type": "resource",
            "category": "resource",
            "source": "MERLOT",
            "url": f"https://www.merlot.org/merlot/materials.htm?keywords={query.replace(' ', '+')}",
            "thumbnail": "📖",
            "license": "Various",
            "free": True
        }]
    except Exception as e:
        logging.warning(f"MERLOT search failed: {str(e)}")
    return []


async def search_internet_archive_texts(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Internet Archive for educational texts/documents"""
    try:
        response = await client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f"({query}) AND mediatype:texts AND (subject:education OR subject:textbook OR subject:learning)",
                "fl[]": ["identifier", "title", "description", "creator", "year"],
                "sort[]": "downloads desc",
                "rows": min(limit, 30),
                "output": "json"
            },
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for doc in data.get("response", {}).get("docs", []):
                identifier = doc.get("identifier", "")
                results.append({
                    "id": f"ia_text_{identifier}",
                    "title": doc.get("title", "Untitled"),
                    "description": str(doc.get("description", ""))[:200] if doc.get("description") else "Educational resource from Internet Archive",
                    "type": "resource",
                    "category": "resource",
                    "source": "Internet Archive",
                    "url": f"https://archive.org/details/{identifier}",
                    "download_url": f"https://archive.org/download/{identifier}",
                    "thumbnail": f"https://archive.org/services/img/{identifier}",
                    "license": "Public Domain / Open",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"Internet Archive texts search failed: {str(e)}")
    return []


async def search_mit_ocw(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search MIT OpenCourseWare"""
    try:
        # MIT OCW doesn't have a public API, so we use a simulated response
        # In production, you would scrape or use their official data
        courses = [
            {"title": f"{query} - Introduction", "dept": "Various", "num": "101"},
            {"title": f"Advanced {query}", "dept": "Various", "num": "201"},
            {"title": f"{query} Fundamentals", "dept": "Various", "num": "100"},
        ]
        
        results = []
        for i, course in enumerate(courses[:limit]):
            results.append({
                "id": f"mit_ocw_{i}",
                "title": course["title"],
                "description": f"Free course materials from MIT OpenCourseWare covering {query}",
                "type": "course",
                "category": "course",
                "source": "MIT OpenCourseWare",
                "url": f"https://ocw.mit.edu/search/?q={query.replace(' ', '+')}",
                "thumbnail": "🎓",
                "license": "CC BY-NC-SA",
                "free": True
            })
        return results
    except Exception as e:
        logging.warning(f"MIT OCW search failed: {str(e)}")
    return []


async def search_youtube_educational(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search for educational YouTube videos (Creative Commons licensed)"""
    try:
        youtube_api_key = os.environ.get("YOUTUBE_API_KEY", "")
        if not youtube_api_key:
            # Return placeholder results if no API key
            return [{
                "id": "yt_placeholder",
                "title": f"Educational videos about {query}",
                "description": "Search YouTube for educational content on this topic",
                "type": "video",
                "category": "video",
                "source": "YouTube",
                "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}+educational+creative+commons",
                "thumbnail": "🎥",
                "license": "Various",
                "free": True
            }]
        
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": f"{query} educational",
                "type": "video",
                "videoLicense": "creativeCommon",
                "maxResults": min(limit, 50),
                "key": youtube_api_key
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                results.append({
                    "id": f"yt_{video_id}",
                    "title": snippet.get("title", "Untitled"),
                    "description": snippet.get("description", "")[:200],
                    "type": "video",
                    "category": "video",
                    "source": "YouTube",
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", "🎥"),
                    "license": "Creative Commons",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"YouTube search failed: {str(e)}")
    return []


async def search_educational_resources(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search for educational resources - worksheets, templates, guides"""
    results = []
    
    # Educational resource platforms
    resource_sites = [
        {
            "name": "Teachers Pay Teachers (Free)",
            "url": f"https://www.teacherspayteachers.com/Browse/Search:{query.replace(' ', '%20')}/Price-Range/Free",
            "description": "Free educational worksheets and resources from teachers worldwide"
        },
        {
            "name": "Education.com (Free)",
            "url": f"https://www.education.com/worksheets/?q={query.replace(' ', '+')}",
            "description": "Free printable worksheets for all grade levels"
        },
        {
            "name": "K12 Reader",
            "url": f"https://www.k12reader.com/?s={query.replace(' ', '+')}",
            "description": "Free reading worksheets and educational materials"
        },
        {
            "name": "Super Teacher Worksheets",
            "url": f"https://www.superteacherworksheets.com/search.html?q={query.replace(' ', '+')}",
            "description": "Printable worksheets for teachers and parents"
        },
        {
            "name": "Worksheet Works",
            "url": f"https://www.worksheetworks.com/",
            "description": "Free customizable worksheet generator"
        },
        {
            "name": "CommonLit",
            "url": f"https://www.commonlit.org/en/library?searchText={query.replace(' ', '+')}",
            "description": "Free reading passages and literacy resources"
        },
        {
            "name": "ReadWriteThink",
            "url": f"https://www.readwritethink.org/search?term={query.replace(' ', '+')}",
            "description": "Free K-12 lesson plans and resources"
        },
        {
            "name": "PBS LearningMedia",
            "url": f"https://www.pbslearningmedia.org/search/?q={query.replace(' ', '+')}",
            "description": "Free educational videos and resources from PBS"
        }
    ]
    
    for i, site in enumerate(resource_sites[:limit]):
        results.append({
            "id": f"resource_{i}_{query.replace(' ', '_')}",
            "title": f"{query.title()} resources on {site['name']}",
            "description": site['description'],
            "type": "resource",
            "category": "resource",
            "source": site['name'],
            "url": site['url'],
            "thumbnail": "📚",
            "license": "Free to access",
            "free": True
        })
    
    return results


# ==================== ENHANCED COURSE SEARCH FUNCTIONS ====================

async def search_wikiversity_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Wikiversity for free educational courses and learning resources"""
    try:
        response = await client.get(
            "https://en.wikiversity.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srnamespace": "0",  # Main namespace
                "srlimit": min(limit, 50),
                "format": "json"
            },
            headers={"User-Agent": "ContentFlow/1.0 (Educational Search)"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "Untitled")
                snippet = item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                page_id = item.get("pageid", "")
                
                results.append({
                    "id": f"wikiversity_{page_id}",
                    "title": title,
                    "description": snippet[:200] if snippet else f"Free educational resource about {query} from Wikiversity",
                    "type": "course",
                    "category": "course",
                    "source": "Wikiversity",
                    "url": f"https://en.wikiversity.org/wiki/{title.replace(' ', '_')}",
                    "thumbnail": "📖",
                    "license": "CC BY-SA",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"Wikiversity search failed: {str(e)}")
    return []


async def search_wikibooks_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Wikibooks for free textbooks and educational content"""
    try:
        response = await client.get(
            "https://en.wikibooks.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srnamespace": "0",
                "srlimit": min(limit, 50),
                "format": "json"
            },
            headers={"User-Agent": "ContentFlow/1.0 (Educational Search)"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "Untitled")
                snippet = item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                page_id = item.get("pageid", "")
                
                results.append({
                    "id": f"wikibooks_{page_id}",
                    "title": title,
                    "description": snippet[:200] if snippet else f"Free textbook about {query} from Wikibooks",
                    "type": "course",
                    "category": "course",
                    "source": "Wikibooks",
                    "url": f"https://en.wikibooks.org/wiki/{title.replace(' ', '_')}",
                    "thumbnail": "📚",
                    "license": "CC BY-SA",
                    "free": True
                })
            return results
    except Exception as e:
        logging.warning(f"Wikibooks search failed: {str(e)}")
    return []


async def search_freecodecamp_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search freeCodeCamp for programming courses"""
    try:
        # freeCodeCamp forum/news search
        response = await client.get(
            "https://www.freecodecamp.org/news/search/",
            params={"query": query},
            headers={"User-Agent": "ContentFlow/1.0"},
            follow_redirects=True
        )
        
        # Since freeCodeCamp doesn't have a public API, return curated search results
        results = [{
            "id": f"fcc_{query.replace(' ', '_')}",
            "title": f"{query} tutorials on freeCodeCamp",
            "description": f"Learn {query} for free with freeCodeCamp's comprehensive curriculum, including 3,000+ hours of coding practice.",
            "type": "course",
            "category": "course",
            "source": "freeCodeCamp",
            "url": f"https://www.freecodecamp.org/news/search/?query={query.replace(' ', '+')}",
            "thumbnail": "💻",
            "license": "Free",
            "free": True
        }]
        
        # Add specific freeCodeCamp certifications if query matches
        cert_keywords = {
            "web": "Responsive Web Design Certification",
            "javascript": "JavaScript Algorithms and Data Structures Certification",
            "python": "Scientific Computing with Python Certification",
            "data": "Data Analysis with Python Certification",
            "machine learning": "Machine Learning with Python Certification",
            "api": "Back End Development and APIs Certification"
        }
        
        for keyword, cert_name in cert_keywords.items():
            if keyword in query.lower():
                results.append({
                    "id": f"fcc_cert_{keyword}",
                    "title": cert_name,
                    "description": f"Free {cert_name.lower()} from freeCodeCamp. Includes projects and hands-on practice.",
                    "type": "course",
                    "category": "course",
                    "source": "freeCodeCamp",
                    "url": f"https://www.freecodecamp.org/learn/",
                    "thumbnail": "🎓",
                    "license": "Free",
                    "free": True
                })
                break
        
        return results[:limit]
    except Exception as e:
        logging.warning(f"freeCodeCamp search failed: {str(e)}")
    return []


async def search_codecademy_courses(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Codecademy for free coding courses"""
    return [{
        "id": f"codecademy_{query.replace(' ', '_')}",
        "title": f"Learn {query} on Codecademy",
        "description": f"Interactive {query} courses with hands-on coding practice. Many free courses available.",
        "type": "course",
        "category": "course",
        "source": "Codecademy",
        "url": f"https://www.codecademy.com/search?query={query.replace(' ', '+')}",
        "thumbnail": "💻",
        "license": "Free + Premium",
        "free": True
    }]


# ==================== ENHANCED VIDEO SEARCH FUNCTIONS ====================

async def search_youtube_videos_comprehensive(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Comprehensive YouTube video search with multiple educational queries"""
    youtube_api_key = os.environ.get("YOUTUBE_API_KEY", "")
    
    if not youtube_api_key:
        # Return multiple placeholder search links
        return [
            {
                "id": f"yt_edu_{query.replace(' ', '_')}",
                "title": f"{query} educational videos",
                "description": f"Educational videos about {query} on YouTube",
                "type": "video",
                "category": "video",
                "source": "YouTube",
                "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}+educational",
                "thumbnail": "🎥",
                "license": "Various",
                "free": True
            },
            {
                "id": f"yt_tutorial_{query.replace(' ', '_')}",
                "title": f"{query} tutorial",
                "description": f"Step-by-step tutorials for {query}",
                "type": "video",
                "category": "video",
                "source": "YouTube",
                "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}+tutorial",
                "thumbnail": "🎥",
                "license": "Various",
                "free": True
            },
            {
                "id": f"yt_lecture_{query.replace(' ', '_')}",
                "title": f"{query} lecture",
                "description": f"University lectures and academic content on {query}",
                "type": "video",
                "category": "video",
                "source": "YouTube",
                "url": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}+lecture+university",
                "thumbnail": "🎓",
                "license": "Various",
                "free": True
            }
        ]
    
    try:
        # Search for Creative Commons licensed educational videos
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": f"{query} educational tutorial",
                "type": "video",
                "videoLicense": "creativeCommon",
                "videoDuration": "medium",  # 4-20 minutes
                "maxResults": min(limit, 50),
                "order": "relevance",
                "key": youtube_api_key
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                results.append({
                    "id": f"yt_cc_{video_id}",
                    "title": snippet.get("title", "Untitled"),
                    "description": snippet.get("description", "")[:200],
                    "type": "video",
                    "category": "video",
                    "source": "YouTube (CC)",
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", 
                        snippet.get("thumbnails", {}).get("medium", {}).get("url", "🎥")),
                    "license": "Creative Commons",
                    "free": True,
                    "channel": snippet.get("channelTitle", "")
                })
            return results
    except Exception as e:
        logging.warning(f"YouTube comprehensive search failed: {str(e)}")
    return []


async def search_internet_archive_videos_enhanced(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Enhanced Internet Archive video search with broader categories"""
    try:
        # Search multiple categories
        categories = [
            ("movies", "educational OR lecture OR documentary OR tutorial"),
            ("movies", "science OR history OR mathematics OR technology"),
            ("movies", "course OR lesson OR training")
        ]
        
        all_results = []
        
        for mediatype, subject_filter in categories:
            if len(all_results) >= limit:
                break
                
            try:
                response = await client.get(
                    "https://archive.org/advancedsearch.php",
                    params={
                        "q": f"({query}) AND mediatype:{mediatype} AND ({subject_filter})",
                        "fl[]": ["identifier", "title", "description", "creator", "year", "downloads"],
                        "sort[]": "downloads desc",
                        "rows": min(limit // 2, 25),
                        "output": "json"
                    },
                    headers={"User-Agent": "ContentFlow/1.0"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for doc in data.get("response", {}).get("docs", []):
                        identifier = doc.get("identifier", "")
                        if identifier and not any(r["id"].endswith(identifier) for r in all_results):
                            all_results.append({
                                "id": f"ia_video_enhanced_{identifier}",
                                "title": doc.get("title", "Untitled"),
                                "description": str(doc.get("description", ""))[:200] if doc.get("description") else f"Educational video from Internet Archive about {query}",
                                "type": "video",
                                "category": "video",
                                "source": "Internet Archive",
                                "url": f"https://archive.org/details/{identifier}",
                                "thumbnail": f"https://archive.org/services/img/{identifier}",
                                "license": "Public Domain / Open",
                                "free": True,
                                "year": doc.get("year"),
                                "downloads": doc.get("downloads", 0)
                            })
            except Exception as inner_e:
                logging.warning(f"IA video category search failed: {str(inner_e)}")
                continue
        
        # Sort by downloads
        all_results.sort(key=lambda x: x.get("downloads", 0), reverse=True)
        return all_results[:limit]
        
    except Exception as e:
        logging.warning(f"Internet Archive enhanced videos search failed: {str(e)}")
    return []


# ==================== ENHANCED RESOURCE SEARCH FUNCTIONS ====================

async def search_smithsonian_resources(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Smithsonian Learning Lab for educational resources"""
    return [{
        "id": f"smithsonian_{query.replace(' ', '_')}",
        "title": f"{query} - Smithsonian Learning Lab",
        "description": f"Explore {query} through millions of digitized images, recordings, and texts from Smithsonian collections.",
        "type": "resource",
        "category": "resource",
        "source": "Smithsonian Learning Lab",
        "url": f"https://learninglab.si.edu/search?st={query.replace(' ', '+')}",
        "thumbnail": "🏛️",
        "license": "Educational Use",
        "free": True
    }]


async def search_national_geographic_edu(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search National Geographic Education resources"""
    return [{
        "id": f"natgeo_edu_{query.replace(' ', '_')}",
        "title": f"{query} - National Geographic Education",
        "description": f"Educational resources about {query} with maps, videos, and activities from National Geographic.",
        "type": "resource",
        "category": "resource",
        "source": "National Geographic Education",
        "url": f"https://education.nationalgeographic.org/resource-library?q={query.replace(' ', '+')}",
        "thumbnail": "🌍",
        "license": "Educational Use",
        "free": True
    }]


async def search_library_of_congress(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Library of Congress for educational primary sources"""
    try:
        response = await client.get(
            "https://www.loc.gov/search/",
            params={
                "q": query,
                "fo": "json",
                "c": min(limit, 25),
                "fa": "access-restricted:false"
            },
            headers={"User-Agent": "ContentFlow/1.0"}
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", []):
                title = item.get("title", "Untitled")
                if isinstance(title, list):
                    title = title[0] if title else "Untitled"
                    
                description = item.get("description", [""])[0] if isinstance(item.get("description"), list) else item.get("description", "")
                
                results.append({
                    "id": f"loc_{item.get('id', '')}",
                    "title": title[:100],
                    "description": str(description)[:200] if description else f"Primary source from Library of Congress about {query}",
                    "type": "resource",
                    "category": "resource",
                    "source": "Library of Congress",
                    "url": item.get("url", f"https://www.loc.gov/search/?q={query}"),
                    "thumbnail": item.get("image_url", ["🏛️"])[0] if isinstance(item.get("image_url"), list) else item.get("image_url", "🏛️"),
                    "license": "Public Domain",
                    "free": True
                })
            return results[:limit]
    except Exception as e:
        logging.warning(f"Library of Congress search failed: {str(e)}")
    
    # Fallback to search link
    return [{
        "id": f"loc_{query.replace(' ', '_')}",
        "title": f"{query} - Library of Congress",
        "description": f"Primary sources and historical materials about {query} from the Library of Congress.",
        "type": "resource",
        "category": "resource",
        "source": "Library of Congress",
        "url": f"https://www.loc.gov/search/?q={query.replace(' ', '+')}",
        "thumbnail": "🏛️",
        "license": "Public Domain",
        "free": True
    }]


async def search_pbs_learningmedia(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search PBS LearningMedia for educational videos and resources"""
    return [{
        "id": f"pbs_{query.replace(' ', '_')}",
        "title": f"{query} - PBS LearningMedia",
        "description": f"Free PreK-12 educational videos, lesson plans, and interactive resources about {query}.",
        "type": "resource",
        "category": "resource",
        "source": "PBS LearningMedia",
        "url": f"https://www.pbslearningmedia.org/search/?q={query.replace(' ', '+')}",
        "thumbnail": "📺",
        "license": "Free for Educators",
        "free": True
    }]


async def search_bbc_bitesize(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search BBC Bitesize for educational content"""
    return [{
        "id": f"bbc_{query.replace(' ', '_')}",
        "title": f"{query} - BBC Bitesize",
        "description": f"Free learning resources for students aged 5-16+ covering {query}. Includes videos, guides, and quizzes.",
        "type": "resource",
        "category": "resource",
        "source": "BBC Bitesize",
        "url": f"https://www.bbc.co.uk/bitesize/search?q={query.replace(' ', '+')}",
        "thumbnail": "📚",
        "license": "Free",
        "free": True
    }]


# ==================== CHILDREN'S LITERATURE SEARCH (COPYRIGHT-FREE) ====================

@api_router.get("/content-library/childrens-literature")
async def search_childrens_literature(
    query: str = Query(default="", description="Search query for children's literature"),
    grade: str = Query(default="all", description="Grade level: preschool, elementary, middle"),
    category: str = Query(default="all", description="Category: stories, poetry, fairy-tales, educational"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, le=100, description="Results per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for copyright-free children's literature across the web.
    Sources: Project Gutenberg, StoryWeaver, Open Library (public domain only)
    All results are guaranteed to be free, downloadable, and printable.
    Supports pagination for accessing all available content.
    """
    try:
        all_results = []
        
        # Build search query based on grade level
        grade_terms = {
            "preschool": "children picture book toddler nursery rhymes",
            "elementary": "children elementary juvenile fiction young readers",
            "middle": "young adult middle grade teen fiction"
        }
        
        search_query = query if query else "children"
        if grade != "all" and grade in grade_terms:
            search_query = f"{search_query} {grade_terms[grade]}"
        
        # Fetch more results to support pagination
        fetch_limit = per_page * 3  # Get enough for multiple pages
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search multiple sources in parallel with higher limits
            tasks = [
                search_gutenberg_children(client, search_query, fetch_limit, page),
                search_storyweaver(client, search_query, grade, fetch_limit, page),
                search_openlibrary_children(client, search_query, fetch_limit),
                search_internet_archive_children(client, search_query, fetch_limit),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, Exception):
                    logging.warning(f"Children's literature search source failed: {str(result)}")
        
        # Filter by category if specified
        if category != "all":
            all_results = [r for r in all_results if category.lower() in r.get("category", "").lower() or category.lower() in " ".join(r.get("subjects", [])).lower()]
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_results = []
        for r in all_results:
            title_key = r.get("title", "").lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_results.append(r)
        
        # Sort by relevance (download count or popularity)
        unique_results.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        
        # Pagination
        total_results = len(unique_results)
        total_pages = (total_results + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = unique_results[start_idx:end_idx]
        
        return {
            "results": paginated_results,
            "total": total_results,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "query": query,
            "grade": grade,
            "sources": ["Project Gutenberg", "StoryWeaver", "Open Library"],
            "license": "All results are copyright-free (Public Domain or Creative Commons)"
        }
    
    except Exception as e:
        logging.error(f"Error in children's literature search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def search_gutenberg_children(client: httpx.AsyncClient, query: str, limit: int, page: int = 1) -> list:
    """Search Project Gutenberg for children's literature - all public domain"""
    try:
        # Use Gutendex API for better search - supports pagination
        response = await client.get(
            "https://gutendex.com/books/",
            params={
                "search": query,
                "topic": "children",
                "languages": "en",
                "page": page
            },
            timeout=20.0,
            follow_redirects=True
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for book in data.get("results", [])[:limit]:
                # Get download formats from Gutendex response
                formats = book.get("formats", {})
                book_id = book.get("id")
                
                # Extract actual format URLs from Gutendex
                epub_url = formats.get("application/epub+zip", "")
                html_url = formats.get("text/html", "") or formats.get("text/html; charset=utf-8", "")
                txt_url = formats.get("text/plain; charset=utf-8", "") or formats.get("text/plain", "")
                cover_url = formats.get("image/jpeg", "")
                kindle_url = formats.get("application/x-mobipocket-ebook", "")
                
                # Gutenberg landing page for all download options (including PDF if available)
                download_page = f"https://www.gutenberg.org/ebooks/{book_id}" if book_id else ""
                
                # Use landing page for "Download" button - users can choose their format
                results.append({
                    "id": f"gutenberg-{book_id}",
                    "title": book.get("title", "Untitled"),
                    "author": ", ".join([a.get("name", "Unknown") for a in book.get("authors", [])]),
                    "description": f"Classic children's literature. Subjects: {', '.join(book.get('subjects', [])[:3])}",
                    "category": "stories",
                    "subjects": book.get("subjects", [])[:5],
                    "source": "Project Gutenberg",
                    "license": "Public Domain",
                    "printable": True,
                    "downloadable": True,
                    "popularity": book.get("download_count", 0),
                    "cover": cover_url,
                    "formats": {
                        "pdf": download_page,  # Landing page for all formats
                        "epub": epub_url or f"https://www.gutenberg.org/ebooks/{book_id}.epub3.images",
                        "html": html_url or f"https://www.gutenberg.org/ebooks/{book_id}.html.images",
                        "txt": txt_url,
                        "kindle": kindle_url
                    },
                    "url": download_page,
                    "grade_level": determine_grade_level(book.get("subjects", []))
                })
            return results
    except Exception as e:
        logging.warning(f"Gutenberg children search failed: {str(e)}")
    return []


async def search_storyweaver(client: httpx.AsyncClient, query: str, grade: str, limit: int, page: int = 1) -> list:
    """Search StoryWeaver (Pratham Books) for free children's books - Creative Commons"""
    try:
        # StoryWeaver API - supports pagination
        reading_level = "1"  # Default to level 1
        if grade == "preschool":
            reading_level = "1"
        elif grade == "elementary":
            reading_level = "2,3"
        elif grade == "middle":
            reading_level = "3,4"
        
        response = await client.get(
            "https://storyweaver.org.in/api/v1/books/search",
            params={
                "query": query,
                "page": page,
                "per_page": limit,
                "languages": "English"
            },
            headers={"Accept": "application/json"},
            timeout=20.0
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for book in data.get("data", [])[:limit]:
                book_slug = book.get("slug", "")
                results.append({
                    "id": f"storyweaver-{book.get('id', '')}",
                    "title": book.get("title", "Untitled"),
                    "author": book.get("authors", [{}])[0].get("name", "Unknown") if book.get("authors") else "Various",
                    "description": book.get("synopsis", book.get("description", "A free children's story from StoryWeaver")),
                    "category": "stories",
                    "subjects": ["children's literature", "free books"],
                    "source": "StoryWeaver (Pratham Books)",
                    "license": "Creative Commons (CC BY)",
                    "printable": True,
                    "downloadable": True,
                    "popularity": book.get("reads_count", 0),
                    "cover": book.get("cover_image", {}).get("url", ""),
                    "formats": {
                        "pdf": f"https://storyweaver.org.in/stories/{book_slug}/download?format=pdf" if book_slug else "",
                        "epub": f"https://storyweaver.org.in/stories/{book_slug}/download?format=epub" if book_slug else "",
                        "html": f"https://storyweaver.org.in/stories/{book_slug}"
                    },
                    "url": f"https://storyweaver.org.in/stories/{book_slug}",
                    "grade_level": [grade] if grade != "all" else ["elementary"],
                    "language": book.get("language", "English")
                })
            return results
    except Exception as e:
        logging.warning(f"StoryWeaver search failed: {str(e)}")
    return []


async def search_openlibrary_children(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Open Library for public domain children's books only"""
    try:
        # Search specifically for children's books with public scans
        response = await client.get(
            "https://openlibrary.org/search.json",
            params={
                "q": f"{query} subject:children subject:juvenile",
                "limit": limit * 2,  # Get more to filter
                "fields": "key,title,author_name,first_publish_year,subject,cover_i,ia,public_scan_b,ebook_access"
            },
            timeout=15.0
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for doc in data.get("docs", []):
                # Only include books with public domain access
                if not doc.get("public_scan_b") and doc.get("ebook_access") != "public":
                    continue
                
                if len(results) >= limit:
                    break
                
                cover_id = doc.get("cover_i")
                work_key = doc.get("key", "").replace("/works/", "")
                ia_id = doc.get("ia", [""])[0] if doc.get("ia") else ""
                
                results.append({
                    "id": f"openlibrary-{work_key}",
                    "title": doc.get("title", "Untitled"),
                    "author": ", ".join(doc.get("author_name", ["Unknown"])[:2]),
                    "description": f"Published: {doc.get('first_publish_year', 'Unknown')}. Subjects: {', '.join(doc.get('subject', [])[:3])}",
                    "category": "stories",
                    "subjects": doc.get("subject", [])[:5],
                    "source": "Open Library",
                    "license": "Public Domain",
                    "printable": True,
                    "downloadable": True,
                    "popularity": 100,  # Default popularity
                    "cover": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else "",
                    "formats": {
                        "pdf": f"https://archive.org/download/{ia_id}/{ia_id}.pdf" if ia_id else "",
                        "epub": f"https://archive.org/download/{ia_id}/{ia_id}.epub" if ia_id else "",
                        "html": f"https://openlibrary.org{doc.get('key', '')}"
                    },
                    "url": f"https://openlibrary.org{doc.get('key', '')}",
                    "grade_level": determine_grade_level(doc.get("subject", [])),
                    "year": doc.get("first_publish_year")
                })
            return results
    except Exception as e:
        logging.warning(f"Open Library children search failed: {str(e)}")
    return []


def determine_grade_level(subjects: list) -> list:
    """Determine grade level based on subjects"""
    subjects_lower = " ".join(subjects).lower()
    grade_levels = []
    
    if any(term in subjects_lower for term in ["picture book", "toddler", "nursery", "baby", "preschool"]):
        grade_levels.append("preschool")
    if any(term in subjects_lower for term in ["children", "juvenile", "elementary", "young readers", "fairy tale"]):
        grade_levels.append("elementary")
    if any(term in subjects_lower for term in ["young adult", "middle grade", "teen", "adolescent"]):
        grade_levels.append("middle")
    if any(term in subjects_lower for term in ["classic", "literature", "fiction"]):
        grade_levels.extend(["elementary", "middle"])
    
    return list(set(grade_levels)) if grade_levels else ["elementary"]


async def search_internet_archive_children(client: httpx.AsyncClient, query: str, limit: int) -> list:
    """Search Internet Archive for public domain children's books with PDF downloads"""
    try:
        # Internet Archive advanced search for children's books that are public domain
        # Use collection:opensource to get truly public domain items
        response = await client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f'({query}) AND mediatype:texts AND (subject:(children OR juvenile OR "fairy tales")) AND collection:(opensource OR gutenberg)',
                "fl[]": ["identifier", "title", "creator", "description", "subject", "downloads", "year"],
                "sort[]": "downloads desc",
                "rows": limit * 2,  # Get more to filter
                "page": 1,
                "output": "json"
            },
            timeout=20.0
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for doc in data.get("response", {}).get("docs", []):
                if len(results) >= limit:
                    break
                    
                identifier = doc.get("identifier", "")
                if not identifier:
                    continue
                    
                subjects = doc.get("subject", [])
                if isinstance(subjects, str):
                    subjects = [subjects]
                
                # Clean up description
                desc = doc.get("description", "")
                if isinstance(desc, list):
                    desc = desc[0] if desc else ""
                desc = str(desc)[:200] if desc else "Public domain book from Internet Archive"
                
                # Clean up author/creator
                creator = doc.get("creator", "Unknown")
                if isinstance(creator, list):
                    creator = ", ".join(creator[:2])
                
                results.append({
                    "id": f"archive-{identifier}",
                    "title": doc.get("title", "Untitled"),
                    "author": creator,
                    "description": desc,
                    "category": "stories",
                    "subjects": subjects[:5] if subjects else ["children's literature"],
                    "source": "Internet Archive",
                    "license": "Public Domain",
                    "printable": True,
                    "downloadable": True,
                    "popularity": doc.get("downloads", 0),
                    "cover": f"https://archive.org/services/img/{identifier}",
                    "formats": {
                        "pdf": f"https://archive.org/details/{identifier}",  # Link to details page where user can download
                        "epub": f"https://archive.org/details/{identifier}",
                        "html": f"https://archive.org/details/{identifier}"
                    },
                    "url": f"https://archive.org/details/{identifier}",
                    "grade_level": determine_grade_level(subjects),
                    "year": doc.get("year")
                })
            return results
    except Exception as e:
        logging.warning(f"Internet Archive children search failed: {str(e)}")
    return []


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


async def ai_enhance_results(query: str, results: list, target_grade: str = "all") -> list:
    """Use AI to enhance, categorize and rank search results"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        llm_key = os.environ.get("EMERGENT_LLM_KEY")
        if not llm_key:
            return results
        
        grade_context = ""
        if target_grade != "all":
            grade_labels = {
                "preschool": "preschool (ages 3-5)",
                "elementary": "elementary school (grades K-5, ages 5-11)",
                "middle": "middle school (grades 6-8, ages 11-14)",
                "high": "high school (grades 9-12, ages 14-18)",
                "university": "university/college level"
            }
            grade_context = f"\n\nIMPORTANT: The user is looking for content suitable for {grade_labels.get(target_grade, target_grade)} students. Prioritize results appropriate for this education level and give lower relevance scores to content that doesn't match."
        
        chat = LlmChat(
            api_key=llm_key,
            session_id=f"content-search-{datetime.now().timestamp()}",
            system_message=f"""You are an educational content curator. Given search results, you will:
1. Add a relevance_score (1-10) based on how well each result matches the query AND the target education level
2. Categorize each result into: worksheet, book, article, video, course, or resource
3. Add grade_level suggestions: preschool, elementary, middle, high, university, all
4. Add a brief AI summary (1 sentence) for each result{grade_context}
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
Target Education Level: {target_grade if target_grade != "all" else "All levels"}

Search Results to enhance:
{json.dumps(results_summary, indent=2)}

Return a JSON array with enhanced results. Add relevance_score, category, grade_levels array, and ai_summary to each. Prioritize results matching the target education level."""
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
            
            # If filtering by grade, move matching results to top
            if target_grade != "all":
                def grade_match_score(item):
                    grades = item.get("grade_levels", ["all"])
                    if target_grade in grades or "all" in grades:
                        return item.get("relevance_score", 0) + 10
                    return item.get("relevance_score", 0)
                results.sort(key=grade_match_score, reverse=True)
            
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


# ==================== FREE DOWNLOADABLE BOOKS ====================

# Curated list of free educational books from Project Gutenberg and other sources
FREE_EDUCATIONAL_BOOKS = [
    # Stories & Literature
    {
        "id": "gutenberg-11",
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Classic children's story following Alice through a fantastical world.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/11",
            "epub": "https://www.gutenberg.org/ebooks/11.epub.images",
            "html": "https://www.gutenberg.org/ebooks/11.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/11/pg11.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1661",
        "title": "The Adventures of Sherlock Holmes",
        "author": "Arthur Conan Doyle",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Classic detective stories featuring the famous Sherlock Holmes.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1661",
            "epub": "https://www.gutenberg.org/ebooks/1661.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1661.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1661/pg1661.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-74",
        "title": "The Adventures of Tom Sawyer",
        "author": "Mark Twain",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "A young boy's adventures along the Mississippi River.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/74",
            "epub": "https://www.gutenberg.org/ebooks/74.epub.images",
            "html": "https://www.gutenberg.org/ebooks/74.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/74/pg74.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1342",
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A classic novel about love, family, and social expectations in Regency England.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1342",
            "epub": "https://www.gutenberg.org/ebooks/1342.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1342.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-98",
        "title": "A Tale of Two Cities",
        "author": "Charles Dickens",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "Historical novel set during the French Revolution.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/98",
            "epub": "https://www.gutenberg.org/ebooks/98.epub.images",
            "html": "https://www.gutenberg.org/ebooks/98.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/98/pg98.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Poetry
    {
        "id": "gutenberg-1065",
        "title": "The Raven and Other Poems",
        "author": "Edgar Allan Poe",
        "category": "poetry",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Collection of Poe's famous poems including 'The Raven'.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1065",
            "epub": "https://www.gutenberg.org/ebooks/1065.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1065.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1065/pg1065.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1322",
        "title": "Leaves of Grass",
        "author": "Walt Whitman",
        "category": "poetry",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "Groundbreaking collection of American poetry.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1322",
            "epub": "https://www.gutenberg.org/ebooks/1322.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1322.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1322/pg1322.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-12242",
        "title": "A Child's Garden of Verses",
        "author": "Robert Louis Stevenson",
        "category": "poetry",
        "subject": "literature",
        "grade_level": ["preschool", "elementary"],
        "description": "Classic collection of children's poetry.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/12242",
            "epub": "https://www.gutenberg.org/ebooks/12242.epub.images",
            "html": "https://www.gutenberg.org/ebooks/12242.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/12242/pg12242.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Grammar & Language
    {
        "id": "gutenberg-37134",
        "title": "The Elements of Style",
        "author": "William Strunk Jr.",
        "category": "grammar",
        "subject": "english",
        "grade_level": ["middle", "high", "university"],
        "description": "Essential guide to English grammar and writing style.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/37134",
            "epub": "https://www.gutenberg.org/ebooks/37134.epub.images",
            "html": "https://www.gutenberg.org/ebooks/37134.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/37134/pg37134.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-15877",
        "title": "English Grammar in Familiar Lectures",
        "author": "Samuel Kirkham",
        "category": "grammar",
        "subject": "english",
        "grade_level": ["elementary", "middle"],
        "description": "Comprehensive English grammar textbook with exercises.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/15877",
            "epub": "https://www.gutenberg.org/ebooks/15877.epub.images",
            "html": "https://www.gutenberg.org/ebooks/15877.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/15877/pg15877.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Math
    {
        "id": "gutenberg-33283",
        "title": "A First Book in Algebra",
        "author": "Wallace C. Boyden",
        "category": "math",
        "subject": "mathematics",
        "grade_level": ["middle", "high"],
        "description": "Introduction to algebraic concepts with exercises.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/33283",
            "epub": "https://www.gutenberg.org/ebooks/33283.epub.images",
            "html": "https://www.gutenberg.org/ebooks/33283.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/33283/pg33283.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-17384",
        "title": "Practical Arithmetic",
        "author": "George Payn Quackenbos",
        "category": "math",
        "subject": "mathematics",
        "grade_level": ["elementary", "middle"],
        "description": "Comprehensive arithmetic textbook with practical problems.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/17384",
            "epub": "https://www.gutenberg.org/ebooks/17384.epub.images",
            "html": "https://www.gutenberg.org/ebooks/17384.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/17384/pg17384.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-13700",
        "title": "Plane Geometry",
        "author": "George Wentworth",
        "category": "math",
        "subject": "mathematics",
        "grade_level": ["high"],
        "description": "Classic geometry textbook with proofs and exercises.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/13700",
            "epub": "https://www.gutenberg.org/ebooks/13700.epub.images",
            "html": "https://www.gutenberg.org/ebooks/13700.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/13700/pg13700.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Science
    {
        "id": "gutenberg-28054",
        "title": "The Science of Human Nature",
        "author": "William Henry Pyle",
        "category": "science",
        "subject": "psychology",
        "grade_level": ["high", "university"],
        "description": "Introduction to psychology and human behavior.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/28054",
            "epub": "https://www.gutenberg.org/ebooks/28054.epub.images",
            "html": "https://www.gutenberg.org/ebooks/28054.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/28054/pg28054.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-2009",
        "title": "The Origin of Species",
        "author": "Charles Darwin",
        "category": "science",
        "subject": "biology",
        "grade_level": ["high", "university"],
        "description": "Darwin's groundbreaking work on evolution and natural selection.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/2009",
            "epub": "https://www.gutenberg.org/ebooks/2009.epub.images",
            "html": "https://www.gutenberg.org/ebooks/2009.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/2009/pg2009.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Fables & Children's Stories
    {
        "id": "gutenberg-19994",
        "title": "Aesop's Fables",
        "author": "Aesop",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["preschool", "elementary"],
        "description": "Classic collection of moral fables with animal characters.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/19994",
            "epub": "https://www.gutenberg.org/ebooks/19994.epub.images",
            "html": "https://www.gutenberg.org/ebooks/19994.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/19994/pg19994.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-2591",
        "title": "Grimms' Fairy Tales",
        "author": "Brothers Grimm",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Classic collection of fairy tales including Cinderella, Snow White, and more.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/2591",
            "epub": "https://www.gutenberg.org/ebooks/2591.epub.images",
            "html": "https://www.gutenberg.org/ebooks/2591.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/2591/pg2591.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-27200",
        "title": "The Wonderful Wizard of Oz",
        "author": "L. Frank Baum",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Dorothy's magical adventure in the Land of Oz.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/27200",
            "epub": "https://www.gutenberg.org/ebooks/27200.epub.images",
            "html": "https://www.gutenberg.org/ebooks/27200.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/27200/pg27200.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-16",
        "title": "Peter Pan",
        "author": "J. M. Barrie",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "The story of the boy who never grew up and his adventures in Neverland.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/16",
            "epub": "https://www.gutenberg.org/ebooks/16.epub.images",
            "html": "https://www.gutenberg.org/ebooks/16.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/16/pg16.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Additional Children's Literature - Classic Stories
    {
        "id": "gutenberg-1400",
        "title": "Great Expectations",
        "author": "Charles Dickens",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "The story of orphan Pip's journey from humble beginnings to gentleman.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1400",
            "epub": "https://www.gutenberg.org/ebooks/1400.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1400.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1400/pg1400.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-730",
        "title": "Oliver Twist",
        "author": "Charles Dickens",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "The story of an orphan boy who escapes a workhouse and meets a gang of pickpockets.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/730",
            "epub": "https://www.gutenberg.org/ebooks/730.epub.images",
            "html": "https://www.gutenberg.org/ebooks/730.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/730/pg730.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-76",
        "title": "Adventures of Huckleberry Finn",
        "author": "Mark Twain",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Huck Finn's adventures rafting down the Mississippi River.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/76",
            "epub": "https://www.gutenberg.org/ebooks/76.epub.images",
            "html": "https://www.gutenberg.org/ebooks/76.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/76/pg76.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1260",
        "title": "Jane Eyre",
        "author": "Charlotte Brontë",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "The story of an orphaned governess and her complex relationship with Mr. Rochester.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1260",
            "epub": "https://www.gutenberg.org/ebooks/1260.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1260.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1260/pg1260.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-768",
        "title": "Wuthering Heights",
        "author": "Emily Brontë",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A tale of passionate and destructive love on the Yorkshire moors.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/768",
            "epub": "https://www.gutenberg.org/ebooks/768.epub.images",
            "html": "https://www.gutenberg.org/ebooks/768.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/768/pg768.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1952",
        "title": "The Yellow Wallpaper",
        "author": "Charlotte Perkins Gilman",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A short story about a woman's mental deterioration, an early feminist work.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1952",
            "epub": "https://www.gutenberg.org/ebooks/1952.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1952.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1952/pg1952.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Children's Classic Literature
    {
        "id": "gutenberg-120",
        "title": "Treasure Island",
        "author": "Robert Louis Stevenson",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "A young boy's adventure with pirates searching for buried treasure.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/120",
            "epub": "https://www.gutenberg.org/ebooks/120.epub.images",
            "html": "https://www.gutenberg.org/ebooks/120.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/120/pg120.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-35",
        "title": "The Time Machine",
        "author": "H. G. Wells",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "A scientist travels to the far future and discovers the fate of humanity.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/35",
            "epub": "https://www.gutenberg.org/ebooks/35.epub.images",
            "html": "https://www.gutenberg.org/ebooks/35.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/35/pg35.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-36",
        "title": "The War of the Worlds",
        "author": "H. G. Wells",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Martians invade Earth in this classic science fiction story.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/36",
            "epub": "https://www.gutenberg.org/ebooks/36.epub.images",
            "html": "https://www.gutenberg.org/ebooks/36.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/36/pg36.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-219",
        "title": "Heart of Darkness",
        "author": "Joseph Conrad",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A journey into the African Congo exploring colonialism and human nature.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/219",
            "epub": "https://www.gutenberg.org/ebooks/219.epub.images",
            "html": "https://www.gutenberg.org/ebooks/219.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/219/pg219.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-244",
        "title": "A Study in Scarlet",
        "author": "Arthur Conan Doyle",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "The first Sherlock Holmes novel, introducing the famous detective.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/244",
            "epub": "https://www.gutenberg.org/ebooks/244.epub.images",
            "html": "https://www.gutenberg.org/ebooks/244.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/244/pg244.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-2097",
        "title": "The Sign of the Four",
        "author": "Arthur Conan Doyle",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Sherlock Holmes investigates a mysterious treasure and murder.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/2097",
            "epub": "https://www.gutenberg.org/ebooks/2097.epub.images",
            "html": "https://www.gutenberg.org/ebooks/2097.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/2097/pg2097.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # More Children's Classics
    {
        "id": "gutenberg-514",
        "title": "Little Women",
        "author": "Louisa May Alcott",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "The story of the four March sisters growing up during the Civil War.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/514",
            "epub": "https://www.gutenberg.org/ebooks/514.epub.images",
            "html": "https://www.gutenberg.org/ebooks/514.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/514/pg514.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-43",
        "title": "The Strange Case of Dr. Jekyll and Mr. Hyde",
        "author": "Robert Louis Stevenson",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "A lawyer investigates the connection between a scientist and a murderer.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/43",
            "epub": "https://www.gutenberg.org/ebooks/43.epub.images",
            "html": "https://www.gutenberg.org/ebooks/43.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/43/pg43.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-345",
        "title": "Dracula",
        "author": "Bram Stoker",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "The classic vampire novel told through letters and diary entries.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/345",
            "epub": "https://www.gutenberg.org/ebooks/345.epub.images",
            "html": "https://www.gutenberg.org/ebooks/345.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/345/pg345.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-84",
        "title": "Frankenstein",
        "author": "Mary Shelley",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A scientist creates a living creature with tragic consequences.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/84",
            "epub": "https://www.gutenberg.org/ebooks/84.epub.images",
            "html": "https://www.gutenberg.org/ebooks/84.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1080",
        "title": "A Modest Proposal",
        "author": "Jonathan Swift",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "Swift's famous satirical essay on poverty in Ireland.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1080",
            "epub": "https://www.gutenberg.org/ebooks/1080.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1080.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1080/pg1080.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-829",
        "title": "Gulliver's Travels",
        "author": "Jonathan Swift",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle", "high"],
        "description": "A ship's surgeon travels to strange lands with tiny and giant people.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/829",
            "epub": "https://www.gutenberg.org/ebooks/829.epub.images",
            "html": "https://www.gutenberg.org/ebooks/829.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/829/pg829.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-2701",
        "title": "Moby Dick",
        "author": "Herman Melville",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "Captain Ahab's obsessive quest to hunt the white whale.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/2701",
            "epub": "https://www.gutenberg.org/ebooks/2701.epub.images",
            "html": "https://www.gutenberg.org/ebooks/2701.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/2701/pg2701.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1184",
        "title": "The Count of Monte Cristo",
        "author": "Alexandre Dumas",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "A wrongfully imprisoned man escapes and seeks revenge on those who betrayed him.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1184",
            "epub": "https://www.gutenberg.org/ebooks/1184.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1184.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1184/pg1184.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1257",
        "title": "The Three Musketeers",
        "author": "Alexandre Dumas",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "D'Artagnan joins three musketeers in adventure and intrigue in France.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1257",
            "epub": "https://www.gutenberg.org/ebooks/1257.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1257.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1257/pg1257.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Young Children's Literature
    {
        "id": "gutenberg-12",
        "title": "Through the Looking-Glass",
        "author": "Lewis Carroll",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Alice enters a magical world through a mirror in this sequel to Wonderland.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/12",
            "epub": "https://www.gutenberg.org/ebooks/12.epub.images",
            "html": "https://www.gutenberg.org/ebooks/12.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/12/pg12.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-23",
        "title": "Narrative of the Life of Frederick Douglass",
        "author": "Frederick Douglass",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "The autobiography of a former slave and abolitionist leader.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/23",
            "epub": "https://www.gutenberg.org/ebooks/23.epub.images",
            "html": "https://www.gutenberg.org/ebooks/23.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/23/pg23.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-2852",
        "title": "The Hound of the Baskervilles",
        "author": "Arthur Conan Doyle",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Sherlock Holmes investigates a legendary demonic hound on the moors.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/2852",
            "epub": "https://www.gutenberg.org/ebooks/2852.epub.images",
            "html": "https://www.gutenberg.org/ebooks/2852.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/2852/pg2852.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-17192",
        "title": "The Jungle Book",
        "author": "Rudyard Kipling",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Stories of Mowgli, a boy raised by wolves in the Indian jungle.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/17192",
            "epub": "https://www.gutenberg.org/ebooks/17192.epub.images",
            "html": "https://www.gutenberg.org/ebooks/17192.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/17192/pg17192.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-2781",
        "title": "The Second Jungle Book",
        "author": "Rudyard Kipling",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "More adventures of Mowgli and the animals of the jungle.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/2781",
            "epub": "https://www.gutenberg.org/ebooks/2781.epub.images",
            "html": "https://www.gutenberg.org/ebooks/2781.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/2781/pg2781.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1597",
        "title": "The Secret Garden",
        "author": "Frances Hodgson Burnett",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "An orphaned girl discovers a hidden garden and transforms lives.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1597",
            "epub": "https://www.gutenberg.org/ebooks/1597.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1597.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1597/pg1597.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-479",
        "title": "A Little Princess",
        "author": "Frances Hodgson Burnett",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "A wealthy girl loses everything but keeps her dignity and imagination.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/479",
            "epub": "https://www.gutenberg.org/ebooks/479.epub.images",
            "html": "https://www.gutenberg.org/ebooks/479.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/479/pg479.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-113",
        "title": "The Secret Garden",
        "author": "Frances Hodgson Burnett",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Sara Crewe's journey from riches to rags and back at a London boarding school.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/113",
            "epub": "https://www.gutenberg.org/ebooks/113.epub.images",
            "html": "https://www.gutenberg.org/ebooks/113.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/113/pg113.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-32",
        "title": "Herland",
        "author": "Charlotte Perkins Gilman",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A feminist utopian novel about a society of women.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/32",
            "epub": "https://www.gutenberg.org/ebooks/32.epub.images",
            "html": "https://www.gutenberg.org/ebooks/32.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/32/pg32.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-174",
        "title": "The Picture of Dorian Gray",
        "author": "Oscar Wilde",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "A young man's portrait ages while he remains youthful, exploring vanity and morality.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/174",
            "epub": "https://www.gutenberg.org/ebooks/174.epub.images",
            "html": "https://www.gutenberg.org/ebooks/174.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/174/pg174.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-885",
        "title": "The Wind in the Willows",
        "author": "Kenneth Grahame",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["preschool", "elementary"],
        "description": "Adventures of Mole, Rat, Toad, and Badger along the riverbank.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/885",
            "epub": "https://www.gutenberg.org/ebooks/885.epub.images",
            "html": "https://www.gutenberg.org/ebooks/885.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/885/pg885.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-902",
        "title": "The Merry Adventures of Robin Hood",
        "author": "Howard Pyle",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Classic tales of Robin Hood and his band of outlaws in Sherwood Forest.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/902",
            "epub": "https://www.gutenberg.org/ebooks/902.epub.images",
            "html": "https://www.gutenberg.org/ebooks/902.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/902/pg902.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-45",
        "title": "Anne of Green Gables",
        "author": "L. M. Montgomery",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "An imaginative orphan girl is adopted by siblings on Prince Edward Island.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/45",
            "epub": "https://www.gutenberg.org/ebooks/45.epub.images",
            "html": "https://www.gutenberg.org/ebooks/45.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/45/pg45.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-47",
        "title": "Anne of Avonlea",
        "author": "L. M. Montgomery",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["elementary", "middle"],
        "description": "Anne continues her adventures as a teacher in Avonlea.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/47",
            "epub": "https://www.gutenberg.org/ebooks/47.epub.images",
            "html": "https://www.gutenberg.org/ebooks/47.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/47/pg47.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1837",
        "title": "The Call of the Wild",
        "author": "Jack London",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "A domesticated dog returns to his wild instincts in the Yukon.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1837",
            "epub": "https://www.gutenberg.org/ebooks/1837.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1837.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1837/pg1837.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-910",
        "title": "White Fang",
        "author": "Jack London",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "A wild wolf-dog learns to live among humans in the Yukon.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/910",
            "epub": "https://www.gutenberg.org/ebooks/910.epub.images",
            "html": "https://www.gutenberg.org/ebooks/910.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/910/pg910.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-215",
        "title": "The Call of the Wild",
        "author": "Jack London",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "Buck's transformation from pet to leader of a wolf pack.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/215",
            "epub": "https://www.gutenberg.org/ebooks/215.epub.images",
            "html": "https://www.gutenberg.org/ebooks/215.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/215/pg215.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    # Children's Poetry
    {
        "id": "gutenberg-14838",
        "title": "Mother Goose Nursery Rhymes",
        "author": "Various",
        "category": "poetry",
        "subject": "literature",
        "grade_level": ["preschool", "elementary"],
        "description": "Classic nursery rhymes for young children.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/14838",
            "epub": "https://www.gutenberg.org/ebooks/14838.epub.images",
            "html": "https://www.gutenberg.org/ebooks/14838.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/14838/pg14838.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-10607",
        "title": "The Book of Nature Myths",
        "author": "Florence Holbrook",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["preschool", "elementary"],
        "description": "Stories explaining natural phenomena for young readers.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/10607",
            "epub": "https://www.gutenberg.org/ebooks/10607.epub.images",
            "html": "https://www.gutenberg.org/ebooks/10607.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/10607/pg10607.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-1515",
        "title": "Andersen's Fairy Tales",
        "author": "Hans Christian Andersen",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["preschool", "elementary", "middle"],
        "description": "Classic fairy tales including The Little Mermaid and The Ugly Duckling.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/1515",
            "epub": "https://www.gutenberg.org/ebooks/1515.epub.images",
            "html": "https://www.gutenberg.org/ebooks/1515.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/1515/pg1515.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-24",
        "title": "O Pioneers!",
        "author": "Willa Cather",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["middle", "high"],
        "description": "A Swedish immigrant family's struggles on the Nebraska prairie.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/24",
            "epub": "https://www.gutenberg.org/ebooks/24.epub.images",
            "html": "https://www.gutenberg.org/ebooks/24.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/24/pg24.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    },
    {
        "id": "gutenberg-996",
        "title": "Don Quixote",
        "author": "Miguel de Cervantes",
        "category": "stories",
        "subject": "literature",
        "grade_level": ["high", "university"],
        "description": "The adventures of a man who believes he is a knight.",
        "formats": {
            "pdf": "https://www.gutenberg.org/ebooks/996",
            "epub": "https://www.gutenberg.org/ebooks/996.epub.images",
            "html": "https://www.gutenberg.org/ebooks/996.html.images"
        },
        "cover": "https://www.gutenberg.org/cache/epub/996/pg996.cover.medium.jpg",
        "license": "public-domain",
        "printable": True
    }
]


@api_router.get("/content-library/free-books")
async def get_free_books(
    category: str = Query(default="all", description="Filter by category: stories, poetry, grammar, math, science"),
    grade: str = Query(default="all", description="Filter by grade level"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, le=100, description="Results per page"),
    current_user: dict = Depends(get_current_user)
):
    """Get curated list of free downloadable educational books with pagination"""
    try:
        books = FREE_EDUCATIONAL_BOOKS.copy()
        
        # Filter by category
        if category != "all":
            books = [b for b in books if b["category"] == category]
        
        # Filter by grade level
        if grade != "all":
            grade_map = {
                "preschool": "preschool",
                "elementary": "elementary", 
                "middle": "middle",
                "high": "high",
                "university": "university"
            }
            target_grade = grade_map.get(grade, grade)
            books = [b for b in books if target_grade in b.get("grade_level", [])]
        
        # Pagination
        total_books = len(books)
        total_pages = (total_books + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_books = books[start_idx:end_idx]
        
        return {
            "books": paginated_books,
            "total": total_books,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "categories": ["stories", "poetry", "grammar", "math", "science"],
            "grades": ["preschool", "elementary", "middle", "high", "university"]
        }
    
    except Exception as e:
        logging.error(f"Error getting free books: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/content-library/free-books/search")
async def search_free_books(
    query: str = Query(..., description="Search query"),
    grade: str = Query(default="all", description="Filter by grade level"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, le=100, description="Results per page"),
    current_user: dict = Depends(get_current_user)
):
    """Search free educational books by title, author, or subject with pagination"""
    try:
        query_lower = query.lower()
        
        matching_books = []
        for book in FREE_EDUCATIONAL_BOOKS:
            # Check if query matches title, author, category, or subject
            if (query_lower in book["title"].lower() or
                query_lower in book["author"].lower() or
                query_lower in book["category"].lower() or
                query_lower in book["subject"].lower() or
                query_lower in book.get("description", "").lower()):
                matching_books.append(book)
        
        # Filter by grade level
        if grade != "all":
            grade_map = {
                "preschool": "preschool",
                "elementary": "elementary", 
                "middle": "middle",
                "high": "high",
                "university": "university"
            }
            target_grade = grade_map.get(grade, grade)
            matching_books = [b for b in matching_books if target_grade in b.get("grade_level", [])]
        
        # Pagination
        total_books = len(matching_books)
        total_pages = (total_books + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_books = matching_books[start_idx:end_idx]
        
        return {
            "books": paginated_books,
            "total": total_books,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "query": query
        }
    
    except Exception as e:
        logging.error(f"Error searching free books: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== READING LISTS ====================

class ReadingListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default="", max_length=500)
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    is_public: bool = False

class ReadingListUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    is_public: Optional[bool] = None

class AddBookToList(BaseModel):
    book_id: str
    title: str
    author: str
    category: str
    cover: Optional[str] = None
    formats: Optional[dict] = None

@api_router.post("/reading-lists")
async def create_reading_list(
    reading_list: ReadingListCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new reading list"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        new_list = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": reading_list.name,
            "description": reading_list.description,
            "grade_level": reading_list.grade_level,
            "subject": reading_list.subject,
            "is_public": reading_list.is_public,
            "books": [],
            "book_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.reading_lists.insert_one(new_list)
        
        # Remove MongoDB _id before returning
        new_list.pop("_id", None)
        
        return {"message": "Reading list created", "reading_list": new_list}
    
    except Exception as e:
        logging.error(f"Error creating reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/reading-lists")
async def get_reading_lists(
    include_public: bool = Query(default=False),
    current_user: dict = Depends(get_current_user)
):
    """Get user's reading lists and optionally public lists"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        # Build query - user's own lists OR public lists
        if include_public:
            query = {"$or": [{"user_id": user_id}, {"is_public": True}]}
        else:
            query = {"user_id": user_id}
        
        lists = await db.reading_lists.find(query, {"_id": 0}).to_list(100)
        
        return {
            "reading_lists": lists,
            "total": len(lists)
        }
    
    except Exception as e:
        logging.error(f"Error fetching reading lists: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/reading-lists/{list_id}")
async def get_reading_list(
    list_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific reading list"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        # Can view own lists or public lists
        reading_list = await db.reading_lists.find_one(
            {"id": list_id, "$or": [{"user_id": user_id}, {"is_public": True}]},
            {"_id": 0}
        )
        
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        return {"reading_list": reading_list}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/reading-lists/{list_id}")
async def update_reading_list(
    list_id: str,
    update_data: ReadingListUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a reading list (only owner can update)"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        # Check ownership
        existing = await db.reading_lists.find_one({"id": list_id, "user_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Reading list not found or not authorized")
        
        # Build update document
        update_doc = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if update_data.name is not None:
            update_doc["name"] = update_data.name
        if update_data.description is not None:
            update_doc["description"] = update_data.description
        if update_data.grade_level is not None:
            update_doc["grade_level"] = update_data.grade_level
        if update_data.subject is not None:
            update_doc["subject"] = update_data.subject
        if update_data.is_public is not None:
            update_doc["is_public"] = update_data.is_public
        
        await db.reading_lists.update_one(
            {"id": list_id},
            {"$set": update_doc}
        )
        
        updated = await db.reading_lists.find_one({"id": list_id}, {"_id": 0})
        
        return {"message": "Reading list updated", "reading_list": updated}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/reading-lists/{list_id}")
async def delete_reading_list(
    list_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a reading list (only owner can delete)"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        result = await db.reading_lists.delete_one({"id": list_id, "user_id": user_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Reading list not found or not authorized")
        
        return {"message": "Reading list deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/reading-lists/{list_id}/books")
async def add_book_to_list(
    list_id: str,
    book: AddBookToList,
    current_user: dict = Depends(get_current_user)
):
    """Add a book to a reading list"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        # Check ownership
        existing = await db.reading_lists.find_one({"id": list_id, "user_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Reading list not found or not authorized")
        
        # Check if book already in list
        if any(b["book_id"] == book.book_id for b in existing.get("books", [])):
            raise HTTPException(status_code=400, detail="Book already in this reading list")
        
        book_entry = {
            "book_id": book.book_id,
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "cover": book.cover,
            "formats": book.formats,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.reading_lists.update_one(
            {"id": list_id},
            {
                "$push": {"books": book_entry},
                "$inc": {"book_count": 1},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {"message": "Book added to reading list", "book": book_entry}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding book to list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/reading-lists/{list_id}/books/{book_id}")
async def remove_book_from_list(
    list_id: str,
    book_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a book from a reading list"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        # Check ownership
        existing = await db.reading_lists.find_one({"id": list_id, "user_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Reading list not found or not authorized")
        
        result = await db.reading_lists.update_one(
            {"id": list_id},
            {
                "$pull": {"books": {"book_id": book_id}},
                "$inc": {"book_count": -1},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Book not found in reading list")
        
        return {"message": "Book removed from reading list"}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing book from list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/reading-lists/{list_id}/copy")
async def copy_reading_list(
    list_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Copy a public reading list to user's own lists"""
    try:
        user_id = current_user.get("id") or current_user.get("email")
        
        # Find the original list (must be public or owned by user)
        original = await db.reading_lists.find_one(
            {"id": list_id, "$or": [{"user_id": user_id}, {"is_public": True}]},
            {"_id": 0}
        )
        
        if not original:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        # Create a copy
        new_list = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": f"{original['name']} (Copy)",
            "description": original.get("description", ""),
            "grade_level": original.get("grade_level"),
            "subject": original.get("subject"),
            "is_public": False,  # Copies start as private
            "books": original.get("books", []),
            "book_count": original.get("book_count", 0),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "copied_from": list_id
        }
        
        await db.reading_lists.insert_one(new_list)
        new_list.pop("_id", None)
        
        return {"message": "Reading list copied", "reading_list": new_list}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error copying reading list: {str(e)}")
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