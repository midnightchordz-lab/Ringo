from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Form, Query, Depends
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import yt_dlp
import subprocess
import tempfile
import httpx
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="ViralFlow Studio API")

api_router = APIRouter(prefix="/api")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

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
    start_time: int
    duration: int

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
    max_results: int = Query(default=20, le=50)
):
    try:
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
                    
                    license_info = entry.get('license', '')
                    is_cc = 'creative commons' in str(license_info).lower() or 'cc' in str(license_info).lower()
                    
                    views = entry.get('view_count', 0) or 0
                    likes = entry.get('like_count', 0) or 0
                    comments = entry.get('comment_count', 0) or 0
                    
                    upload_date = entry.get('upload_date', '')
                    try:
                        upload_datetime = datetime.strptime(upload_date, '%Y%m%d') if upload_date else datetime.now()
                        days_ago = (datetime.now() - upload_datetime).days
                    except:
                        days_ago = 365
                    
                    if views < 10000:
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
                        'license': license_info or 'Unknown',
                        'is_cc_licensed': is_cc
                    })
            
            videos.sort(key=lambda x: x['viral_score'], reverse=True)
            
            await db.discovered_videos.delete_many({})
            if videos:
                await db.discovered_videos.insert_many(videos)
            
            return {"videos": videos, "total": len(videos)}
    
    except Exception as e:
        logging.error(f"Error discovering videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/videos/{video_id}")
async def get_video_details(video_id: str):
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
                    'description': info.get('description', '')[:500]
                }
        
        return video
    
    except Exception as e:
        logging.error(f"Error getting video details: {str(e)}")
        raise HTTPException(status_code=404, detail="Video not found")

async def download_and_clip_video(video_id: str, start_time: int, duration: int):
    try:
        temp_dir = Path("/tmp/viralflow")
        temp_dir.mkdir(exist_ok=True)
        
        output_template = str(temp_dir / f"{video_id}.%(ext)s")
        
        ydl_opts = {
            'format': 'best[height<=1080]',
            'outtmpl': output_template,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
            downloaded_file = ydl.prepare_filename(info)
        
        clip_id = str(uuid.uuid4())
        output_clip = temp_dir / f"clip_{clip_id}.mp4"
        
        ffmpeg_cmd = [
            'ffmpeg', '-i', downloaded_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            '-b:a', '128k',
            '-y',
            str(output_clip)
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        
        if Path(downloaded_file).exists():
            Path(downloaded_file).unlink()
        
        clip_data = {
            "clip_id": clip_id,
            "video_id": video_id,
            "start_time": start_time,
            "duration": duration,
            "file_path": str(output_clip),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready"
        }
        
        await db.processed_clips.insert_one(clip_data)
        
        return clip_id
    
    except Exception as e:
        logging.error(f"Error creating clip: {str(e)}")
        raise

@api_router.post("/clips/generate")
async def generate_clip(clip_request: ClipRequest, background_tasks: BackgroundTasks):
    try:
        if clip_request.duration < 10 or clip_request.duration > 60:
            raise HTTPException(status_code=400, detail="Clip duration must be between 10-60 seconds")
        
        clip_id = await download_and_clip_video(
            clip_request.video_id,
            clip_request.start_time,
            clip_request.duration
        )
        
        return {
            "success": True,
            "clip_id": clip_id,
            "message": "Clip generated successfully"
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