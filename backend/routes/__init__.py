"""
Routes package - All API route handlers
"""
from routes.auth import router as auth_router
from routes.images import router as images_router, set_auth_dependency as set_images_auth
from routes.dashboard import router as dashboard_router
from routes.youtube import router as youtube_router, set_auth_dependency as set_youtube_auth
from routes.content import router as content_router, set_auth_dependency as set_content_auth

__all__ = [
    'auth_router', 
    'images_router', 
    'dashboard_router',
    'youtube_router',
    'content_router',
    'set_images_auth',
    'set_youtube_auth',
    'set_content_auth'
]
