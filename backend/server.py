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
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


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
    max_results: int = Query(default=50, le=100),
    min_views: int = Query(default=1000, description="Minimum view count")
):
    try:
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        
        if youtube_api_key:
            # Use YouTube Data API v3 for better results
            try:
                youtube = build('youtube', 'v3', developerKey=youtube_api_key, cache_discovery=False)
                
                search_query = f"{query}" if query else "tutorial"
                
                # Search ONLY for videos with Creative Commons license
                search_request = youtube.search().list(
                    part='id,snippet',
                    q=search_query,
                    type='video',
                    videoLicense='creativeCommon',  # STRICT CC only filter
                    maxResults=50,
                    order='viewCount',
                    videoDuration='medium'  # 4-20 minutes videos
                )
                search_response = search_request.execute()
                
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                
                if not video_ids:
                    # Try with different search terms for CC content
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
                        "message": "No Creative Commons licensed videos found. Try different search terms like 'creative commons music', 'cc by tutorial', etc."
                    }
                
                # Get detailed statistics - MUST include 'status' to verify CC license
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
                    
                    # STRICT CHECK: Only include if license is explicitly 'creativeCommon'
                    license_type = status.get('license', 'youtube')
                    if license_type != 'creativeCommon':
                        continue
                    
                    views = int(stats.get('viewCount', 0))
                    likes = int(stats.get('likeCount', 0))
                    comments = int(stats.get('commentCount', 0))
                    
                    # Apply minimum views filter
                    if views < min_views:
                        continue
                    
                    # Parse duration
                    duration_str = item['contentDetails']['duration']
                    duration_seconds = parse_youtube_duration(duration_str)
                    
                    # Skip very short or very long videos
                    if duration_seconds < 60 or duration_seconds > 3600:
                        continue
                    
                    # Parse upload date
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
                
                # Limit to max_results
                videos = videos[:max_results]
                
                await db.discovered_videos.delete_many({})
                if videos:
                    # Insert and then fetch back without _id
                    await db.discovered_videos.insert_many(videos)
                    videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
                
                return {"videos": videos, "total": len(videos)}
                
            except HttpError as e:
                error_detail = str(e)
                logging.error(f"YouTube API error: {error_detail}")
                if "quotaExceeded" in error_detail:
                    raise HTTPException(status_code=429, detail="YouTube API quota exceeded. Please try again later.")
                # Don't fallback to yt-dlp for CC-only search
                raise HTTPException(status_code=500, detail=f"YouTube API error: {error_detail}")
        
        # Fallback: Use yt-dlp for search
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
                        'license': license_info or 'Unknown',
                        'is_cc_licensed': is_cc
                    })
            
            videos.sort(key=lambda x: x['viral_score'], reverse=True)
            
            await db.discovered_videos.delete_many({})
            if videos:
                # Insert and then fetch back without _id
                await db.discovered_videos.insert_many(videos)
                videos = await db.discovered_videos.find({}, {"_id": 0}).to_list(length=max_results)
            
            return {"videos": videos, "total": len(videos)}
    
    except Exception as e:
        logging.error(f"Error discovering videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def parse_youtube_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration format (PT1H2M10S) to seconds"""
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

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
                
                # Ensure all values are JSON serializable
                video = {
                    'id': str(video_id),
                    'title': str(info.get('title', '')),
                    'channel': str(info.get('uploader', '')),
                    'thumbnail': str(info.get('thumbnail', '')),
                    'duration': int(info.get('duration', 0) or 0),
                    'views': int(views),
                    'likes': int(likes),
                    'comments': int(comments),
                    'viral_score': float(viral_score),
                    'upload_date': str(upload_date),
                    'license': str(info.get('license', 'Unknown')),
                    'description': str(info.get('description', ''))[:500]
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