"""
Application configuration and environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# JWT Authentication
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production-09876543210")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Email (Resend)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

# Frontend URL for email links
FRONTEND_URL = os.environ.get("FRONTEND_URL") or os.environ.get("APP_URL", "http://localhost:3000")

# YouTube API
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# Image APIs
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
UNSPLASH_API_KEY = os.environ.get("UNSPLASH_API_KEY")

# Microsoft OAuth
MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET")
MICROSOFT_TENANT = "common"  # Allows any Microsoft account
