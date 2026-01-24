"""
Image search and favorites routes
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, HTTPException, Depends, Query
import httpx

import sys
sys.path.insert(0, '/app/backend')

from database import db
from config import PEXELS_API_KEY, UNSPLASH_API_KEY

router = APIRouter(prefix="/images", tags=["Images"])


# Import get_current_user from the main app (will be injected)
async def get_current_user_placeholder():
    raise NotImplementedError("get_current_user must be injected")

get_current_user = get_current_user_placeholder


def set_auth_dependency(auth_func):
    """Allow main app to inject the auth dependency"""
    global get_current_user
    get_current_user = auth_func


@router.get("/search")
async def search_images(
    query: str = Query(..., description="Search query for images"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, le=50),
    source: str = Query(default="all", description="Filter by source: all, pexels, unsplash, pixabay"),
    image_type: str = Query(default=None, description="Filter by type: photo, illustration, vector"),
    current_user: dict = Depends(lambda: get_current_user)
):
    """Search for copyright-free images from Unsplash, Pexels, and Pixabay"""
    try:
        images = []
        sources_used = []
        
        unsplash_key = UNSPLASH_API_KEY or ''
        pexels_key = PEXELS_API_KEY or 'QsPCgrnUhMSwyA25GWLfqMdYdJZw2Rthp33l24iYFCrTpuJcwUEBGAhq'
        pixabay_key = os.environ.get('PIXABAY_API_KEY', '48aborj-d9156e13058fcef0a68ac7cf4')  # Free API key
        
        # Normalize image_type - treat 'all' same as None
        effective_image_type = None if image_type == 'all' else image_type
        
        async with httpx.AsyncClient() as client:
            # Search Unsplash (supports photos only, not illustrations/vectors)
            if unsplash_key and source in ['all', 'unsplash'] and effective_image_type in [None, 'photo']:
                try:
                    unsplash_response = await client.get(
                        "https://api.unsplash.com/search/photos",
                        params={
                            "query": query,
                            "page": page,
                            "per_page": per_page // 2,
                            "orientation": "landscape"
                        },
                        headers={"Authorization": f"Client-ID {unsplash_key}"},
                        timeout=10.0
                    )
                    if unsplash_response.status_code == 200:
                        sources_used.append("unsplash")
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
                                "likes": photo.get("likes", 0),
                                "image_type": "photo"
                            })
                except Exception as e:
                    logging.warning(f"Unsplash API error: {str(e)}")
            
            # Search Pexels (supports photos only)
            if source in ['all', 'pexels'] and effective_image_type in [None, 'photo']:
                try:
                    pexels_response = await client.get(
                        "https://api.pexels.com/v1/search",
                        params={"query": query, "page": page, "per_page": per_page},
                        headers={"Authorization": pexels_key},
                        timeout=10.0
                    )
                    if pexels_response.status_code == 200:
                        sources_used.append("pexels")
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
                                "likes": 0,
                                "image_type": "photo"
                            })
                except Exception as e:
                    logging.warning(f"Pexels API error: {str(e)}")
            
            # Search Pixabay (supports photos, illustrations, vectors)
            if source in ['all', 'pixabay']:
                try:
                    # Pixabay image_type: all, photo, illustration, vector
                    pixabay_type = effective_image_type if effective_image_type in ['photo', 'illustration', 'vector'] else 'all'
                    
                    pixabay_response = await client.get(
                        "https://pixabay.com/api/",
                        params={
                            "key": pixabay_key,
                            "q": query,
                            "page": page,
                            "per_page": per_page,
                            "image_type": pixabay_type,
                            "safesearch": "true"
                        },
                        timeout=10.0
                    )
                    if pixabay_response.status_code == 200:
                        sources_used.append("pixabay")
                        pixabay_data = pixabay_response.json()
                        for photo in pixabay_data.get("hits", []):
                            # Determine the image type based on pixabay's type field
                            img_type = photo.get("type", "photo")
                            if img_type == "vector":
                                img_type = "vector"
                            elif img_type == "illustration":
                                img_type = "illustration"
                            else:
                                img_type = "photo"
                            
                            images.append({
                                "id": f"pixabay_{photo['id']}",
                                "url": photo.get("largeImageURL") or photo.get("webformatURL"),
                                "thumbnail": photo.get("previewURL") or photo.get("webformatURL"),
                                "title": photo.get("tags", "Untitled").replace(",", ", "),
                                "photographer": photo.get("user", "Unknown"),
                                "photographer_url": f"https://pixabay.com/users/{photo.get('user', 'unknown')}-{photo.get('user_id', '')}",
                                "source": "pixabay",
                                "download_url": photo.get("largeImageURL") or photo.get("fullHDURL") or photo.get("webformatURL"),
                                "width": photo.get("imageWidth", 0),
                                "height": photo.get("imageHeight", 0),
                                "color": "#000000",
                                "likes": photo.get("likes", 0),
                                "image_type": img_type
                            })
                except Exception as e:
                    logging.warning(f"Pixabay API error: {str(e)}")
        
        # Filter by image_type if specified (for cases where API didn't filter)
        if image_type and image_type != 'all':
            images = [img for img in images if img.get("image_type") == image_type]
        
        # Interleave results from all sources for variety
        unsplash_images = [img for img in images if img["source"] == "unsplash"]
        pexels_images = [img for img in images if img["source"] == "pexels"]
        pixabay_images = [img for img in images if img["source"] == "pixabay"]
        
        combined = []
        max_len = max(len(unsplash_images), len(pexels_images), len(pixabay_images), 1)
        for i in range(max_len):
            if i < len(unsplash_images):
                combined.append(unsplash_images[i])
            if i < len(pexels_images):
                combined.append(pexels_images[i])
            if i < len(pixabay_images):
                combined.append(pixabay_images[i])
        
        return {
            "images": combined[:per_page],
            "total": len(combined),
            "page": page,
            "per_page": per_page,
            "query": query,
            "sources": sources_used,
            "image_type": image_type
        }
    
    except Exception as e:
        logging.error(f"Error searching images: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favorites")
async def add_image_favorite(
    image_data: Dict,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Add an image to user's favorites"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        image_id = image_data.get("id")
        
        if not image_id:
            raise HTTPException(status_code=400, detail="Image ID is required")
        
        existing = await db.image_favorites.find_one({
            "user_id": user_id,
            "image_id": image_id
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Image already in favorites")
        
        await db.image_favorites.insert_one({
            "user_id": user_id,
            "image_id": image_id,
            "image_data": image_data,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"message": "Image added to favorites", "image_id": image_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding image favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/favorites")
async def get_image_favorites(current_user: dict = Depends(lambda: get_current_user)):
    """Get user's favorite images"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        favorites = await db.image_favorites.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(length=100)
        
        return {
            "favorites": [fav.get("image_data") for fav in favorites if fav.get("image_data")],
            "total": len(favorites)
        }
    
    except Exception as e:
        logging.error(f"Error getting image favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favorites/{image_id}")
async def remove_image_favorite(
    image_id: str,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Remove an image from user's favorites"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        result = await db.image_favorites.delete_one({
            "user_id": user_id,
            "image_id": image_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Image not found in favorites")
        
        return {"message": "Image removed from favorites", "image_id": image_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing image favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
