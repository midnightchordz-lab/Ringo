"""
YouTube API Optimization Service

Implements:
1. Cache Data Store - caches frequently accessed data
2. Request Only Necessary Fields - uses part and fields parameters
3. GZIP Compression - reduces data transfer
4. Conditional Requests - ETags for change detection
5. Batch Requests - combines multiple API calls
6. quotaUser - tracks usage per user
"""
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from googleapiclient.errors import HttpError

from database import db


class YouTubeAPIOptimizer:
    """In-memory cache for YouTube API responses"""
    
    _etag_cache: Dict[str, str] = {}
    _data_cache: Dict[str, dict] = {}
    _cache_timestamps: Dict[str, datetime] = {}
    CACHE_TTL_MINUTES = 30
    
    # Minimal fields to request (reduces quota usage)
    SEARCH_FIELDS = "items(id/videoId),nextPageToken"
    VIDEO_FIELDS = "items(id,snippet(title,channelTitle,publishedAt,thumbnails/high/url,description),statistics(viewCount,likeCount,commentCount),contentDetails/duration,status/license)"
    
    @classmethod
    def get_cache_key(cls, operation: str, params: dict) -> str:
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{operation}:{param_str}".encode()).hexdigest()
    
    @classmethod
    def is_cache_valid(cls, cache_key: str) -> bool:
        if cache_key not in cls._cache_timestamps:
            return False
        age = datetime.now() - cls._cache_timestamps[cache_key]
        return age.total_seconds() < cls.CACHE_TTL_MINUTES * 60
    
    @classmethod
    def get_cached_data(cls, cache_key: str) -> Optional[dict]:
        if cls.is_cache_valid(cache_key) and cache_key in cls._data_cache:
            logging.info(f"YouTube API: Cache hit for {cache_key[:8]}...")
            return cls._data_cache[cache_key]
        return None
    
    @classmethod
    def set_cache(cls, cache_key: str, data: dict, etag: str = None):
        cls._data_cache[cache_key] = data
        cls._cache_timestamps[cache_key] = datetime.now()
        if etag:
            cls._etag_cache[cache_key] = etag
        logging.info(f"YouTube API: Cached data for {cache_key[:8]}...")
    
    @classmethod
    def get_etag(cls, cache_key: str) -> Optional[str]:
        return cls._etag_cache.get(cache_key)
    
    @classmethod
    async def search_videos(
        cls, 
        youtube, 
        query: str, 
        max_results: int = 50,
        user_id: str = None
    ) -> dict:
        params = {"q": query, "max": max_results}
        cache_key = cls.get_cache_key("search", params)
        
        cached = cls.get_cached_data(cache_key)
        if cached:
            return cached
        
        request_params = {
            "part": "id",
            "q": query,
            "type": "video",
            "videoLicense": "creativeCommon",
            "maxResults": min(max_results, 50),
            "order": "viewCount",
            "videoDuration": "medium",
            "fields": cls.SEARCH_FIELDS,
        }
        
        if user_id:
            request_params["quotaUser"] = hashlib.md5(user_id.encode()).hexdigest()[:40]
        
        try:
            search_request = youtube.search().list(**request_params)
            
            etag = cls.get_etag(cache_key)
            if etag:
                search_request.headers["If-None-Match"] = etag
            
            response = search_request.execute()
            response_etag = response.get("etag")
            cls.set_cache(cache_key, response, response_etag)
            
            return response
            
        except HttpError as e:
            if e.resp.status == 304:
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
        if not video_ids:
            return {"items": []}
        
        params = {"ids": ",".join(sorted(video_ids))}
        cache_key = cls.get_cache_key("videos", params)
        
        cached = cls.get_cached_data(cache_key)
        if cached:
            return cached
        
        all_items = []
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            request_params = {
                "part": "statistics,contentDetails,snippet,status",
                "id": ",".join(batch_ids),
                "fields": cls.VIDEO_FIELDS,
            }
            
            if user_id:
                request_params["quotaUser"] = hashlib.md5(user_id.encode()).hexdigest()[:40]
            
            videos_request = youtube.videos().list(**request_params)
            
            batch_cache_key = cls.get_cache_key("videos_batch", {"ids": ",".join(batch_ids)})
            etag = cls.get_etag(batch_cache_key)
            if etag:
                videos_request.headers["If-None-Match"] = etag
            
            try:
                response = videos_request.execute()
                all_items.extend(response.get("items", []))
                cls.set_cache(batch_cache_key, response, response.get("etag"))
                
            except HttpError as e:
                if e.resp.status == 304:
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


class YouTubePersistentCache:
    """MongoDB-based persistent cache for YouTube API results"""
    
    CACHE_COLLECTION = "youtube_api_cache"
    CACHE_TTL_HOURS = 6
    
    @classmethod
    async def get_cached_search(cls, query: str, min_views: int) -> Optional[List[dict]]:
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
    async def cleanup_expired(cls):
        result = await db[cls.CACHE_COLLECTION].delete_many({
            "expires_at": {"$lt": datetime.now(timezone.utc)}
        })
        if result.deleted_count > 0:
            logging.info(f"YouTube Persistent Cache: Cleaned up {result.deleted_count} expired entries")
