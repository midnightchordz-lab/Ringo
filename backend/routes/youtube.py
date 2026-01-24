"""
YouTube video transcription routes
Other YouTube endpoints (discover, clips, cache) remain in server.py
"""
import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

import sys
sys.path.insert(0, '/app/backend')

from database import db

router = APIRouter(tags=["YouTube Transcription"])

# Placeholder for auth dependency injection (not needed for transcript endpoints)
async def get_current_user_placeholder():
    raise NotImplementedError("get_current_user must be injected")

get_current_user = get_current_user_placeholder

def set_auth_dependency(auth_func):
    """Allow main app to inject the auth dependency"""
    global get_current_user
    get_current_user = auth_func


# ==================== VIDEO TRANSCRIPTION ENDPOINTS ====================

@router.get("/video/transcript/{video_id}")
async def get_video_transcript(video_id: str):
    """
    Get transcript/captions for a YouTube video.
    Uses YouTube's built-in captions - completely free.
    No authentication required as this accesses public YouTube data.
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
            
            # Try to find English transcript first
            for t in available_transcripts:
                lang_code = t.language_code if hasattr(t, 'language_code') else str(t)
                if lang_code.startswith('en'):
                    selected_transcript = t
                    language_used = t.language if hasattr(t, 'language') else lang_code
                    break
            
            # If no English, use first available
            if not selected_transcript:
                selected_transcript = available_transcripts[0]
                language_used = selected_transcript.language if hasattr(selected_transcript, 'language') else 'unknown'
            
            # Fetch the transcript
            if hasattr(selected_transcript, 'fetch'):
                transcript_data = selected_transcript.fetch()
            else:
                transcript_data = api.fetch(video_id, languages=[language_used.split()[0] if language_used else 'en'])
                
        except Exception as list_error:
            logging.warning(f"Could not list transcripts, trying direct fetch: {list_error}")
            transcript_data = api.fetch(video_id)
            language_used = 'en (auto-detected)'
        
        # Format the transcript
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
        
        # Store in database for caching
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
        error_str = str(e)
        logging.error(f"Error getting transcript for {video_id}: {error_str}")
        
        # Check for common YouTube blocking errors
        if "IP" in error_str and ("blocked" in error_str.lower() or "cloud provider" in error_str.lower()):
            return {
                "success": False,
                "error": "YouTube is blocking transcript requests from this server. This is a known limitation when running from cloud servers. Try using a different video or check if the video has captions enabled.",
                "error_type": "ip_blocked",
                "video_id": video_id
            }
        elif "Could not retrieve" in error_str:
            return {
                "success": False,
                "error": "Could not retrieve transcript. The video may not have captions, or YouTube may be temporarily blocking requests.",
                "error_type": "retrieval_failed",
                "video_id": video_id
            }
        
        return {
            "success": False,
            "error": "Failed to fetch transcript. Please try again later.",
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
