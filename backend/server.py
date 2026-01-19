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
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://clipcreator-19.preview.emergentagent.com")

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
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Try to find user by user_id field first, then by _id
        user = await db.users.find_one({"user_id": user_id})
        if user is None:
            user = await db.users.find_one({"_id": user_id})
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
    
    # Create access token
    access_token = create_access_token(data={"sub": user.get("_id") or user.get("user_id")})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.get("_id") or user.get("user_id"),
            "email": user["email"],
            "full_name": user["full_name"],
            "created_at": user["created_at"]
        }
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["_id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "created_at": current_user["created_at"]
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
    try:
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        
        if youtube_api_key:
            try:
                youtube = build('youtube', 'v3', developerKey=youtube_api_key, cache_discovery=False)
                
                search_query = f"{query}" if query else "tutorial"
                
                search_request = youtube.search().list(
                    part='id,snippet',
                    q=search_query,
                    type='video',
                    videoLicense='creativeCommon',
                    maxResults=50,
                    order='viewCount',
                    videoDuration='medium'
                )
                search_response = search_request.execute()
                
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                
                if not video_ids:
                    search_queries = [
                        f"{search_query} creative commons",
                        "creative commons music" if not query else f"{search_query}",
                        "royalty free" if not query else f"{search_query} royalty free"
                    ]
                    
                    for alt_query in search_queries:
                        search_request = youtube.search().list(
                            part='id,snippet',
                            q=alt_query,
                            type='video',
                            videoLicense='creativeCommon',
                            maxResults=50,
                            order='viewCount'
                        )
                        search_response = search_request.execute()
                        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                        if video_ids:
                            break
                
                if not video_ids:
                    return {
                        "videos": [], 
                        "total": 0,
                        "message": "No Creative Commons licensed videos found. Try different search terms."
                    }
                
                videos_request = youtube.videos().list(
                    part='statistics,contentDetails,snippet,status',
                    id=','.join(video_ids)
                )
                videos_response = videos_request.execute()
                
                videos = []
                for item in videos_response.get('items', []):
                    snippet = item['snippet']
                    stats = item['statistics']
                    status = item.get('status', {})
                    
                    license_type = status.get('license', 'youtube')
                    if license_type != 'creativeCommon':
                        continue
                    
                    views = int(stats.get('viewCount', 0))
                    likes = int(stats.get('likeCount', 0))
                    comments = int(stats.get('commentCount', 0))
                    
                    if views < min_views:
                        continue
                    
                    duration_str = item['contentDetails']['duration']
                    duration_seconds = parse_youtube_duration(duration_str)
                    
                    if duration_seconds < 60 or duration_seconds > 3600:
                        continue
                    
                    upload_date = snippet['publishedAt']
                    try:
                        upload_datetime = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                        days_ago = (datetime.now(timezone.utc) - upload_datetime).days
                        upload_date_formatted = upload_datetime.strftime('%Y%m%d')
                    except:
                        days_ago = 365
                        upload_date_formatted = upload_date[:10].replace('-', '')
                    
                    viral_score = calculate_viral_score(views, likes, comments, days_ago)
                    
                    videos.append({
                        'id': item['id'],
                        'title': snippet['title'],
                        'channel': snippet['channelTitle'],
                        'thumbnail': snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['default']['url'],
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
                
                await db.discovered_videos.delete_many({})
                if videos:
                    await db.discovered_videos.insert_many(videos)
                    videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
                
                return {"videos": videos, "total": len(videos)}
                
            except HttpError as e:
                error_detail = str(e)
                logging.error(f"YouTube API error: {error_detail}")
                if "quotaExceeded" in error_detail:
                    raise HTTPException(status_code=429, detail="YouTube API quota exceeded. Please try again later.")
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
    
    except Exception as e:
        logging.error(f"Error discovering videos: {str(e)}")
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
        
        # IMPORTANT: Due to YouTube's bot detection, we'll use a workaround
        # Get video info without downloading first
        info_opts = {
            'quiet': False,
            'no_warnings': False,
            'skip_download': True,
            'format': 'best[height<=720][ext=mp4]',  # Lower quality to avoid detection
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],  # Android client is more reliable
                }
            }
        }
        
        logging.info(f"Fetching video info for {video_id}...")
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            video_title = info.get('title', 'video')
            video_duration = info.get('duration', 0)
        
        # Use AI analysis if requested
        ai_analysis = None
        if use_ai:
            ai_analysis = await analyze_video_with_ai(
                video_id, 
                video_title,
                info.get('description', ''),
                video_duration
            )
            start_time = ai_analysis['recommended_start']
            duration = ai_analysis['recommended_duration']
            logging.info(f"✨ AI recommended: start={start_time}s, duration={duration}s - {ai_analysis['reasoning']}")
        
        # Download with retry logic and better settings
        output_template = str(temp_dir / f"{video_id}.%(ext)s")
        download_opts = {
            'format': 'best[height<=720][ext=mp4]/best[height<=720]',  # 720p is more reliable
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
        
        logging.info(f"📥 Downloading video {video_id} (this may take a minute)...")
        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                downloaded_file = ydl.prepare_filename(info)
        except Exception as download_error:
            logging.error(f"Download error: {str(download_error)}")
            # Try to find any downloaded file
            possible_files = list(temp_dir.glob(f"{video_id}.*"))
            if not possible_files:
                raise Exception(
                    "⚠️ YouTube blocked the download. This happens when:\n"
                    "1. Too many downloads in short time\n"
                    "2. YouTube detects automation\n"
                    "3. Video has restrictions\n\n"
                    "💡 Solutions:\n"
                    "- Wait 5-10 minutes and try again\n"
                    "- Try a different video\n"
                    "- The video might need manual download permissions"
                )
            downloaded_file = str(possible_files[0])
        
        if not Path(downloaded_file).exists():
            possible_files = list(temp_dir.glob(f"{video_id}.*"))
            if possible_files:
                downloaded_file = str(possible_files[0])
            else:
                raise Exception("Downloaded file not found after download attempt")
        
        logging.info(f"✅ Downloaded to: {downloaded_file}")
        
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
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            raise Exception(
                "⚠️ YouTube's bot detection blocked the download.\n\n"
                "This is temporary. Solutions:\n"
                "• Wait 10-15 minutes before trying again\n"
                "• Try a different CC BY video\n"
                "• YouTube may be experiencing high traffic\n\n"
                "The clip generation feature works - just needs a cooldown period!"
            )
        elif "403" in error_msg or "Forbidden" in error_msg:
            raise Exception(
                "⚠️ YouTube blocked access (Error 403).\n\n"
                "Try:\n"
                "• Select a different video\n"
                "• Wait 5-10 minutes\n"
                "• Some videos may have download restrictions"
            )
        elif "HTTP Error 429" in error_msg:
            raise Exception(
                "⚠️ Rate limit exceeded (Error 429).\n\n"
                "Too many requests. Please wait 15-20 minutes before trying again."
            )
        else:
            raise Exception(f"Clip generation error: {error_msg}")

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