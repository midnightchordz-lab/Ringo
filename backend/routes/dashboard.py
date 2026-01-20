"""
Dashboard, stats, history, and settings routes
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

import sys
sys.path.insert(0, '/app/backend')

from database import db

router = APIRouter(tags=["Dashboard"])


class APIKeysModel(BaseModel):
    youtube_api_key: Optional[str] = None
    instagram_access_token: Optional[str] = None


@router.get("/history")
async def get_post_history(limit: int = 50):
    """Get post history"""
    try:
        posts = await db.social_posts.find({}, {"_id": 0}).sort("posted_at", -1).limit(limit).to_list(length=limit)
        return {"posts": posts, "total": len(posts)}
    
    except Exception as e:
        logging.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
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


@router.post("/settings/api-keys")
async def save_api_keys(keys: APIKeysModel):
    """Save API keys to settings"""
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


@router.get("/settings/api-keys")
async def get_api_keys():
    """Get API keys (masked)"""
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
