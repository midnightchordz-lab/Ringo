"""
Common utility functions
"""
import re
from datetime import datetime, timezone


def parse_youtube_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration format (PT1H2M30S) to seconds"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def calculate_viral_score(views: int, likes: int, comments: int, upload_days_ago: int) -> float:
    """Calculate viral score based on engagement metrics"""
    if views == 0:
        return 0.0
    
    engagement_rate = ((likes + comments * 2) / views) * 100
    recency_factor = max(0, 100 - upload_days_ago) / 100
    
    viral_score = (engagement_rate * 0.7) + (recency_factor * 30)
    
    return min(round(viral_score, 2), 100.0)


def format_duration(seconds: int) -> str:
    """Format seconds to HH:MM:SS or MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
