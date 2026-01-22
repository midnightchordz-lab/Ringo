"""
Content Library routes - search, favorites, free books, reading lists
This module handles all educational content search and management
"""
import os
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import httpx

import sys
sys.path.insert(0, '/app/backend')

from database import db

router = APIRouter(prefix="/content-library", tags=["Content Library"])

# Placeholder for auth dependency injection
async def get_current_user_placeholder():
    raise NotImplementedError("get_current_user must be injected")

get_current_user = get_current_user_placeholder

def set_auth_dependency(auth_func):
    """Allow main app to inject the auth dependency"""
    global get_current_user
    get_current_user = auth_func


# ==================== PYDANTIC MODELS ====================

class ContentFavorite(BaseModel):
    resource_id: str
    title: str
    type: str
    source: str
    url: str
    license: Optional[str] = None
    author: Optional[str] = None


class ReadingListCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    grade_level: Optional[str] = "all"
    subject: Optional[str] = "general"
    is_public: bool = False


class ReadingListUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    is_public: Optional[bool] = None


class BookToList(BaseModel):
    book_id: str
    title: str
    author: Optional[str] = None
    category: Optional[str] = None
    download_url: Optional[str] = None
    cover_image: Optional[str] = None


# ==================== LICENSE HELPER FUNCTIONS ====================

ALLOWED_CC_LICENSES = [
    "cc by", "cc-by", "cc by 4.0", "cc by 3.0", "creative commons",
    "cc by-sa", "cc-by-sa", "cc by sa", 
    "cc by-nd", "cc-by-nd", "cc by nd",
    "cc0", "public domain", "pd", "no known copyright",
    "open access", "open-access"
]

ALWAYS_CC_SOURCES = [
    "openstax", "wikiversity", "wikibooks", "wikimedia", "wikipedia",
    "oer commons", "internet archive", "library of congress",
    "youtube (cc)", "ted", "arxiv", "pubmed", "doaj",
    "ck-12", "freecodecamp", "mit opencourseware", "project gutenberg",
    "storyweaver", "open library"
]


def filter_cc_licensed_content(results: list) -> list:
    """Filter results to only include content with valid CC licenses"""
    filtered = []
    for result in results:
        license_str = str(result.get("license", "")).lower().strip()
        source_str = str(result.get("source", "")).lower().strip()
        
        is_cc_source = any(s in source_str for s in ALWAYS_CC_SOURCES)
        is_cc_license = any(l in license_str for l in ALLOWED_CC_LICENSES)
        
        if is_cc_source or is_cc_license:
            result["license"] = normalize_cc_license(result.get("license", ""), source_str)
            result["cc_verified"] = True
            filtered.append(result)
    
    return filtered


def normalize_cc_license(license_str: str, source: str = "") -> str:
    """Normalize license string to standard CC format"""
    license_lower = license_str.lower().strip()
    
    if any(pd in license_lower for pd in ["public domain", "pd", "cc0"]):
        return "Public Domain (CC0)"
    if "by-sa" in license_lower or "share alike" in license_lower:
        return "CC BY-SA 4.0"
    if "by-nd" in license_lower:
        return "CC BY-ND 4.0"
    if any(cc in license_lower for cc in ["cc by", "creative commons", "attribution"]):
        return "CC BY 4.0"
    if "open access" in license_lower:
        return "Open Access (CC BY)"
    
    return get_source_default_license(source) or license_str


def get_source_default_license(source: str) -> str:
    """Get default license for known CC sources"""
    source_lower = source.lower()
    
    defaults = {
        "openstax": "CC BY 4.0",
        "wikipedia": "CC BY-SA 3.0",
        "wikiversity": "CC BY-SA 3.0",
        "wikibooks": "CC BY-SA 3.0",
        "project gutenberg": "Public Domain",
        "internet archive": "Public Domain",
        "storyweaver": "CC BY 4.0",
        "open library": "Public Domain",
        "arxiv": "Open Access",
        "ted": "CC BY-NC-ND 4.0"
    }
    
    for key, license_val in defaults.items():
        if key in source_lower:
            return license_val
    
    return "CC BY"


# ==================== FAVORITES ENDPOINTS ====================

@router.get("/favorites")
async def get_content_favorites(current_user: dict = Depends(lambda: get_current_user)):
    """Get user's favorite content resources"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        favorites = await db.content_library_favorites.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(length=100)
        
        return {
            "favorites": favorites,
            "total": len(favorites)
        }
    except Exception as e:
        logging.error(f"Error getting favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favorites")
async def add_content_favorite(
    favorite: ContentFavorite,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Add a resource to favorites"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        existing = await db.content_library_favorites.find_one({
            "user_id": user_id,
            "resource_id": favorite.resource_id
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Resource already in favorites")
        
        await db.content_library_favorites.insert_one({
            "user_id": user_id,
            "resource_id": favorite.resource_id,
            "title": favorite.title,
            "type": favorite.type,
            "source": favorite.source,
            "url": favorite.url,
            "license": favorite.license,
            "author": favorite.author,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"message": "Resource added to favorites", "resource_id": favorite.resource_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favorites/{resource_id}")
async def remove_content_favorite(
    resource_id: str,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Remove a resource from favorites"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        result = await db.content_library_favorites.delete_one({
            "user_id": user_id,
            "resource_id": resource_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Resource not found in favorites")
        
        return {"message": "Resource removed from favorites", "resource_id": resource_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== READING LISTS ENDPOINTS ====================

@router.post("/reading-lists", tags=["Reading Lists"])
async def create_reading_list(
    list_data: ReadingListCreate,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Create a new reading list"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        import uuid
        list_id = str(uuid.uuid4())
        
        reading_list = {
            "list_id": list_id,
            "user_id": user_id,
            "name": list_data.name,
            "description": list_data.description,
            "grade_level": list_data.grade_level,
            "subject": list_data.subject,
            "is_public": list_data.is_public,
            "books": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.reading_lists.insert_one(reading_list)
        
        return {
            "message": "Reading list created",
            "list_id": list_id,
            "name": list_data.name
        }
    
    except Exception as e:
        logging.error(f"Error creating reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reading-lists", tags=["Reading Lists"])
async def get_reading_lists(current_user: dict = Depends(lambda: get_current_user)):
    """Get user's reading lists"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        lists = await db.reading_lists.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(length=100)
        
        return {
            "reading_lists": lists,
            "total": len(lists)
        }
    
    except Exception as e:
        logging.error(f"Error getting reading lists: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reading-lists/{list_id}", tags=["Reading Lists"])
async def get_reading_list(
    list_id: str,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Get a specific reading list"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        reading_list = await db.reading_lists.find_one(
            {"list_id": list_id, "$or": [{"user_id": user_id}, {"is_public": True}]},
            {"_id": 0}
        )
        
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        return reading_list
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/reading-lists/{list_id}", tags=["Reading Lists"])
async def update_reading_list(
    list_id: str,
    update_data: ReadingListUpdate,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Update a reading list"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.reading_lists.update_one(
            {"list_id": list_id, "user_id": user_id},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        return {"message": "Reading list updated", "list_id": list_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reading-lists/{list_id}", tags=["Reading Lists"])
async def delete_reading_list(
    list_id: str,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Delete a reading list"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        result = await db.reading_lists.delete_one({
            "list_id": list_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        return {"message": "Reading list deleted", "list_id": list_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reading-lists/{list_id}/books", tags=["Reading Lists"])
async def add_book_to_list(
    list_id: str,
    book: BookToList,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Add a book to a reading list"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        reading_list = await db.reading_lists.find_one({
            "list_id": list_id,
            "user_id": user_id
        })
        
        if not reading_list:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        existing_books = reading_list.get("books", [])
        if any(b.get("book_id") == book.book_id for b in existing_books):
            raise HTTPException(status_code=400, detail="Book already in list")
        
        book_entry = {
            "book_id": book.book_id,
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "download_url": book.download_url,
            "cover_image": book.cover_image,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.reading_lists.update_one(
            {"list_id": list_id, "user_id": user_id},
            {
                "$push": {"books": book_entry},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {"message": "Book added to list", "book_id": book.book_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error adding book to list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/reading-lists/{list_id}/books/{book_id}", tags=["Reading Lists"])
async def remove_book_from_list(
    list_id: str,
    book_id: str,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Remove a book from a reading list"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        result = await db.reading_lists.update_one(
            {"list_id": list_id, "user_id": user_id},
            {
                "$pull": {"books": {"book_id": book_id}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Reading list not found")
        
        return {"message": "Book removed from list", "book_id": book_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error removing book from list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reading-lists/{list_id}/copy", tags=["Reading Lists"])
async def copy_reading_list(
    list_id: str,
    current_user: dict = Depends(lambda: get_current_user)
):
    """Copy a public reading list to user's own collection"""
    try:
        user_id = str(current_user.get("_id") or current_user.get("user_id") or current_user.get("email"))
        
        original = await db.reading_lists.find_one({
            "list_id": list_id,
            "is_public": True
        })
        
        if not original:
            raise HTTPException(status_code=404, detail="Public reading list not found")
        
        import uuid
        new_list_id = str(uuid.uuid4())
        
        copied_list = {
            "list_id": new_list_id,
            "user_id": user_id,
            "name": f"{original['name']} (Copy)",
            "description": original.get("description", ""),
            "grade_level": original.get("grade_level", "all"),
            "subject": original.get("subject", "general"),
            "is_public": False,
            "books": original.get("books", []),
            "copied_from": list_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.reading_lists.insert_one(copied_list)
        
        return {
            "message": "Reading list copied",
            "new_list_id": new_list_id,
            "name": copied_list["name"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error copying reading list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
