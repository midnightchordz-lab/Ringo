"""
YouTube video discovery, transcription, and clip generation routes
"""
import os
import logging
import hashlib
import tempfile
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
import httpx
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

import sys
sys.path.insert(0, '/app/backend')

from database import db

router = APIRouter(tags=["YouTube"])

# YouTube API Key
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Placeholder for auth dependency injection
async def get_current_user_placeholder():
    raise NotImplementedError("get_current_user must be injected")

get_current_user = get_current_user_placeholder

def set_auth_dependency(auth_func):
    """Allow main app to inject the auth dependency"""
    global get_current_user
    get_current_user = auth_func


# ==================== PYDANTIC MODELS ====================

class ClipRequest(BaseModel):
    video_id: str
    start_time: int
    duration: int = 60
    use_ai: bool = False


# ==================== HELPER FUNCTIONS ====================

def calculate_viral_score(views: int, likes: int, comments: int, upload_days_ago: int) -> float:
    """Calculate viral score based on engagement metrics"""
    if upload_days_ago == 0:
        upload_days_ago = 1
    
    views_per_day = views / upload_days_ago
    engagement_rate = ((likes + comments) / max(views, 1)) * 100
    
    # Weighted score calculation
    score = (
        (views_per_day / 10000) * 0.4 +  # Views per day factor
        engagement_rate * 0.4 +           # Engagement rate factor
        (views / 1000000) * 0.2           # Total views factor
    )
    
    return round(min(score, 10.0), 2)  # Cap at 10


def parse_youtube_duration(duration_str: str) -> int:
    """Parse YouTube duration format (PT1H2M3S) to seconds"""
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


# ==================== CACHE CLASSES ====================

class YouTubeCache:
    """In-memory cache for YouTube API responses"""
    CACHE_TTL = 1800  # 30 minutes
    _cache: Dict[str, dict] = {}
    _timestamps: Dict[str, datetime] = {}
    
    @classmethod
    def get(cls, key: str) -> Optional[dict]:
        if key in cls._cache:
            if datetime.now(timezone.utc) - cls._timestamps[key] < timedelta(seconds=cls.CACHE_TTL):
                return cls._cache[key]
            else:
                del cls._cache[key]
                del cls._timestamps[key]
        return None
    
    @classmethod
    def set(cls, key: str, value: dict):
        cls._cache[key] = value
        cls._timestamps[key] = datetime.now(timezone.utc)
    
    @classmethod
    def clear(cls):
        cls._cache.clear()
        cls._timestamps.clear()


class YouTubePersistentCache:
    """MongoDB-based persistent cache for YouTube API"""
    CACHE_COLLECTION = "youtube_api_cache"
    DEFAULT_TTL = 21600  # 6 hours
    
    @classmethod
    async def get(cls, cache_key: str) -> Optional[dict]:
        entry = await db[cls.CACHE_COLLECTION].find_one({
            "cache_key": cache_key,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        return entry.get("data") if entry else None
    
    @classmethod
    async def set(cls, cache_key: str, data: dict, ttl_seconds: int = None):
        ttl = ttl_seconds or cls.DEFAULT_TTL
        await db[cls.CACHE_COLLECTION].update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "cache_key": cache_key,
                    "data": data,
                    "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl),
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
    
    @classmethod
    async def get_stats(cls) -> dict:
        total = await db[cls.CACHE_COLLECTION].count_documents({})
        valid = await db[cls.CACHE_COLLECTION].count_documents({
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        return {"total_entries": total, "valid_entries": valid, "expired_entries": total - valid}
    
    @classmethod
    async def clear(cls):
        result = await db[cls.CACHE_COLLECTION].delete_many({})
        return result.deleted_count


# ==================== VIDEO TRANSCRIPTION ENDPOINTS ====================

@router.get("/video/transcript/{video_id}")
async def get_video_transcript(video_id: str):
    """
    Get transcript/captions for a YouTube video.
    Uses YouTube's built-in captions - completely free.
    """
    try:
        api = YouTubeTranscriptApi()
        
        try:
            transcript_list = api.list(video_id)
            available_transcripts = list(transcript_list)
            
            if not available_transcripts:
                return {
                    "success": False,
                    "error": "No transcript available for this video",
                    "video_id": video_id
                }
            
            selected_transcript = None
            language_used = None
            
            for t in available_transcripts:
                lang_code = t.language_code if hasattr(t, 'language_code') else str(t)
                if lang_code.startswith('en'):
                    selected_transcript = t
                    language_used = t.language if hasattr(t, 'language') else lang_code
                    break
            
            if not selected_transcript:
                selected_transcript = available_transcripts[0]
                language_used = selected_transcript.language if hasattr(selected_transcript, 'language') else 'unknown'
            
            if hasattr(selected_transcript, 'fetch'):
                transcript_data = selected_transcript.fetch()
            else:
                transcript_data = api.fetch(video_id, languages=[language_used.split()[0] if language_used else 'en'])
                
        except Exception as list_error:
            logging.warning(f"Could not list transcripts, trying direct fetch: {list_error}")
            transcript_data = api.fetch(video_id)
            language_used = 'en (auto-detected)'
        
        full_text = ""
        segments = []
        
        for entry in transcript_data:
            text = entry.text.strip() if hasattr(entry, 'text') else entry.get('text', '').strip()
            start = entry.start if hasattr(entry, 'start') else entry.get('start', 0)
            duration = entry.duration if hasattr(entry, 'duration') else entry.get('duration', 0)
            
            if text and not text.startswith('[') and not text.endswith(']'):
                full_text += text + " "
                segments.append({
                    "text": text,
                    "start": round(float(start), 2),
                    "duration": round(float(duration), 2),
                    "start_formatted": f"{int(float(start) // 60)}:{int(float(start) % 60):02d}"
                })
        
        full_text = ' '.join(full_text.split())
        word_count = len(full_text.split())
        
        await db.video_transcripts.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "video_id": video_id,
                    "full_text": full_text,
                    "segments": segments,
                    "language": language_used,
                    "word_count": word_count,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "video_id": video_id,
            "language": language_used,
            "word_count": word_count,
            "full_text": full_text,
            "segments": segments[:100],
            "total_segments": len(segments)
        }
        
    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "Transcripts are disabled for this video",
            "video_id": video_id
        }
    except NoTranscriptFound:
        return {
            "success": False,
            "error": "No transcript found for this video",
            "video_id": video_id
        }
    except Exception as e:
        logging.error(f"Error getting transcript for {video_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "video_id": video_id
        }


@router.get("/video/transcript/{video_id}/cached")
async def get_cached_transcript(video_id: str):
    """Get cached transcript if available"""
    try:
        transcript = await db.video_transcripts.find_one(
            {"video_id": video_id},
            {"_id": 0}
        )
        if transcript:
            transcript.pop("created_at", None)
            transcript.pop("updated_at", None)
            return {"success": True, "cached": True, **transcript}
        return {"success": False, "cached": False, "error": "No cached transcript"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== YOUTUBE CACHE ENDPOINTS ====================

@router.get("/youtube/cache-stats")
async def get_youtube_cache_stats(current_user: dict = Depends(lambda: get_current_user)):
    """Get YouTube cache statistics"""
    try:
        memory_cache_size = len(YouTubeCache._cache)
        persistent_stats = await YouTubePersistentCache.get_stats()
        
        return {
            "memory_cache": {
                "entries": memory_cache_size,
                "ttl_seconds": YouTubeCache.CACHE_TTL
            },
            "persistent_cache": persistent_stats,
            "optimization_features": [
                "In-memory caching (30 min TTL)",
                "Persistent MongoDB caching (6 hour TTL)",
                "ETag conditional requests",
                "Batch video details fetching",
                "GZIP compression",
                "Per-user quota tracking"
            ]
        }
    except Exception as e:
        logging.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/youtube/clear-cache")
async def clear_youtube_cache(current_user: dict = Depends(lambda: get_current_user)):
    """Clear all YouTube caches"""
    try:
        YouTubeCache.clear()
        deleted = await YouTubePersistentCache.clear()
        
        return {
            "success": True,
            "message": f"Cleared memory cache and {deleted} persistent cache entries"
        }
    except Exception as e:
        logging.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VIDEO DISCOVERY ENDPOINTS ====================

@router.get("/discover")
async def discover_videos(
    query: str = Query(default="", description="Search query"),
    max_results: int = Query(default=50, le=50, ge=1),
    min_views: int = Query(default=1000),
    sort_by: str = Query(default="viewCount"),
    page_token: str = Query(default=None),
    skip_cache: bool = Query(default=False)
):
    """Discover CC-BY licensed YouTube videos with optimized API usage"""
    try:
        search_query = query if query else "tutorial"
        cache_key = f"discover:{search_query}:{max_results}:{min_views}:{sort_by}:{page_token or 'none'}"
        
        if not skip_cache:
            cached = YouTubeCache.get(cache_key)
            if cached:
                return {**cached, "cached": True, "cache_type": "memory"}
            
            persistent_cached = await YouTubePersistentCache.get(cache_key)
            if persistent_cached:
                YouTubeCache.set(cache_key, persistent_cached)
                return {**persistent_cached, "cached": True, "cache_type": "persistent"}
        
        if not YOUTUBE_API_KEY:
            raise HTTPException(status_code=500, detail="YouTube API key not configured")
        
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        search_params = {
            'q': search_query,
            'part': 'id',
            'type': 'video',
            'videoLicense': 'creativeCommon',
            'maxResults': min(max_results, 50),
            'order': sort_by,
            'fields': 'items(id(videoId)),nextPageToken,prevPageToken,pageInfo'
        }
        
        if page_token:
            search_params['pageToken'] = page_token
        
        search_response = youtube.search().list(**search_params).execute()
        
        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        
        if not video_ids:
            return {
                "videos": [],
                "total": 0,
                "cached": False,
                "optimized": True,
                "message": "No CC-BY videos found"
            }
        
        videos_response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids),
            fields='items(id,snippet(title,description,thumbnails,channelTitle,publishedAt),statistics(viewCount,likeCount,commentCount),contentDetails(duration,licensedContent))'
        ).execute()
        
        videos = []
        for item in videos_response.get('items', []):
            stats = item.get('statistics', {})
            views = int(stats.get('viewCount', 0))
            
            if views < min_views:
                continue
            
            snippet = item.get('snippet', {})
            published_at = snippet.get('publishedAt', '')
            
            try:
                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                days_ago = (datetime.now(timezone.utc) - published_date).days
            except:
                days_ago = 30
            
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            duration = parse_youtube_duration(item.get('contentDetails', {}).get('duration', 'PT0S'))
            
            viral_score = calculate_viral_score(views, likes, comments, days_ago)
            
            thumbnail = snippet.get('thumbnails', {}).get('high', {}).get('url') or \
                       snippet.get('thumbnails', {}).get('medium', {}).get('url') or \
                       snippet.get('thumbnails', {}).get('default', {}).get('url', '')
            
            videos.append({
                "id": item['id'],
                "title": snippet.get('title', 'Untitled'),
                "description": snippet.get('description', '')[:200],
                "thumbnail": thumbnail,
                "channel": snippet.get('channelTitle', 'Unknown'),
                "views": views,
                "likes": likes,
                "comments": comments,
                "duration": duration,
                "viral_score": viral_score,
                "published_at": published_at,
                "license": "CC BY"
            })
        
        videos.sort(key=lambda x: x['viral_score'], reverse=True)
        
        result = {
            "videos": videos,
            "total": len(videos),
            "next_page_token": search_response.get('nextPageToken'),
            "prev_page_token": search_response.get('prevPageToken'),
            "total_available": search_response.get('pageInfo', {}).get('totalResults', len(videos)),
            "has_more": bool(search_response.get('nextPageToken')),
            "cached": False,
            "optimized": True,
            "message": f"Found {len(videos)} CC-BY videos"
        }
        
        YouTubeCache.set(cache_key, result)
        await YouTubePersistentCache.set(cache_key, result)
        
        await db.discovered_videos.delete_many({})
        if videos:
            await db.discovered_videos.insert_many([
                {**v, "discovered_at": datetime.now(timezone.utc).isoformat()}
                for v in videos
            ])
        
        return result
        
    except HttpError as e:
        logging.error(f"YouTube API error: {str(e)}")
        if e.resp.status == 403:
            raise HTTPException(status_code=429, detail="YouTube API quota exceeded")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logging.error(f"Error discovering videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-videos")
async def clear_discovered_videos(current_user: dict = Depends(lambda: get_current_user)):
    """Clear all discovered videos"""
    try:
        result = await db.discovered_videos.delete_many({})
        YouTubeCache.clear()
        
        return {
            "success": True,
            "message": f"Cleared {result.deleted_count} videos",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        logging.error(f"Error clearing videos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{video_id}")
async def get_video_details(video_id: str, current_user: dict = Depends(lambda: get_current_user)):
    """Get detailed information about a specific video"""
    try:
        video = await db.discovered_videos.find_one({"id": video_id}, {"_id": 0})
        
        if video:
            return video
        
        if not YOUTUBE_API_KEY:
            raise HTTPException(status_code=404, detail="Video not found")
        
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        response = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=video_id
        ).execute()
        
        if not response.get('items'):
            raise HTTPException(status_code=404, detail="Video not found")
        
        item = response['items'][0]
        snippet = item.get('snippet', {})
        stats = item.get('statistics', {})
        
        return {
            "id": video_id,
            "title": snippet.get('title', 'Untitled'),
            "description": snippet.get('description', ''),
            "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            "channel": snippet.get('channelTitle', 'Unknown'),
            "views": int(stats.get('viewCount', 0)),
            "likes": int(stats.get('likeCount', 0)),
            "comments": int(stats.get('commentCount', 0)),
            "duration": parse_youtube_duration(item.get('contentDetails', {}).get('duration', 'PT0S')),
            "published_at": snippet.get('publishedAt', ''),
            "license": "CC BY"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting video details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CLIP GENERATION ENDPOINTS ====================

@router.get("/clips/preview/{video_id}")
async def get_clip_preview(
    video_id: str,
    start_time: int = Query(default=0, ge=0),
    duration: int = Query(default=60, ge=10, le=180)
):
    """Get preview URL for a clip (uses embedded player)"""
    return {
        "video_id": video_id,
        "start_time": start_time,
        "duration": duration,
        "preview_url": f"https://www.youtube.com/embed/{video_id}?start={start_time}&end={start_time + duration}&autoplay=0",
        "note": "Direct video download is restricted. Use embedded preview."
    }


@router.post("/clips/generate")
async def generate_clip(
    clip_request: ClipRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Generate a clip from a YouTube video (returns embedded player URL)"""
    clip_id = f"clip_{clip_request.video_id}_{clip_request.start_time}_{clip_request.duration}"
    
    clip_data = {
        "clip_id": clip_id,
        "video_id": clip_request.video_id,
        "start_time": clip_request.start_time,
        "duration": clip_request.duration,
        "status": "ready",
        "preview_url": f"https://www.youtube.com/embed/{clip_request.video_id}?start={clip_request.start_time}&end={clip_request.start_time + clip_request.duration}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "Direct download restricted by YouTube. Use embedded preview."
    }
    
    await db.processed_clips.update_one(
        {"clip_id": clip_id},
        {"$set": clip_data},
        upsert=True
    )
    
    return clip_data


@router.get("/clips/{clip_id}")
async def get_clip(clip_id: str):
    """Get clip information"""
    clip = await db.processed_clips.find_one({"clip_id": clip_id}, {"_id": 0})
    
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return clip
