"""
Routes package - All API route handlers
"""
from routes.auth import router as auth_router
from routes.images import router as images_router
from routes.dashboard import router as dashboard_router

__all__ = ['auth_router', 'images_router', 'dashboard_router']
