# Backend Architecture

## Directory Structure

```
/app/backend/
├── server.py           # Main FastAPI application (entry point)
├── config.py           # Environment variables and configuration ✓
├── database.py         # MongoDB connection ✓
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not in git)
│
├── models/             # Pydantic models for request/response ✓
│   ├── __init__.py
│   └── schemas.py      # All data models
│
├── routes/             # API route handlers ✓
│   ├── __init__.py
│   ├── auth.py         # Authentication routes (ready)
│   ├── images.py       # Image search routes (ready)
│   └── dashboard.py    # Stats/settings routes (ready)
│
├── services/           # Business logic and external integrations ✓
│   ├── __init__.py
│   └── youtube_optimizer.py  # YouTube API optimization
│
└── utils/              # Utility functions ✓
    ├── __init__.py
    ├── auth.py         # Authentication utilities
    └── helpers.py      # Common helper functions
```

## Module Status

| Module | Status | Description |
|--------|--------|-------------|
| `config.py` | ✅ Complete | Environment variables |
| `database.py` | ✅ Complete | MongoDB connection |
| `models/schemas.py` | ✅ Complete | All Pydantic models |
| `services/youtube_optimizer.py` | ✅ Complete | YouTube caching |
| `utils/auth.py` | ✅ Complete | Auth utilities |
| `utils/helpers.py` | ✅ Complete | Helper functions |
| `routes/auth.py` | ✅ Ready | Auth endpoints template |
| `routes/images.py` | ✅ Ready | Image endpoints template |
| `routes/dashboard.py` | ✅ Ready | Dashboard endpoints template |

## Modules

### config.py
Central configuration loading from environment variables:
- `MONGO_URL`, `DB_NAME` - Database
- `SECRET_KEY`, `ALGORITHM` - JWT Auth
- `RESEND_API_KEY`, `SENDER_EMAIL` - Email
- `YOUTUBE_API_KEY` - YouTube API
- `EMERGENT_LLM_KEY` - AI features
- `PEXELS_API_KEY`, `UNSPLASH_API_KEY` - Image search

### database.py
MongoDB client initialization using Motor (async driver).

### models/schemas.py
Pydantic models for:
- Authentication (UserRegister, UserLogin, Token, UserResponse)
- Videos (VideoMetadata, ClipRequest, PostRequest)
- Images (ImageFavorite)
- Content Library (ContentFavorite)

### services/youtube_optimizer.py
YouTube API optimization with:
- In-memory caching (30 min TTL)
- MongoDB persistent caching (6 hour TTL)
- Field filtering to reduce quota usage
- ETag conditional requests
- Batch requests (50 videos per call)
- Per-user quota tracking (quotaUser)

### utils/auth.py
Authentication utilities:
- Password hashing (bcrypt)
- JWT token creation/validation
- `get_current_user` dependency for protected routes

### utils/helpers.py
Common helpers:
- `parse_youtube_duration()` - Parse ISO 8601 duration
- `calculate_viral_score()` - Calculate engagement score
- `format_duration()` - Format seconds to MM:SS

## Refactoring Plan

The current `server.py` (2400+ lines) should be gradually refactored:

1. **Phase 1** (Complete): Create module structure and utilities
2. **Phase 2**: Move auth routes to `routes/auth.py`
3. **Phase 3**: Move video routes to `routes/videos.py`
4. **Phase 4**: Move image routes to `routes/images.py`
5. **Phase 5**: Move content library routes to `routes/content.py`
6. **Phase 6**: Move dashboard/stats routes to `routes/dashboard.py`

Each phase should be tested before proceeding to the next.

## API Endpoints Summary

### Authentication (`/api/auth/`)
- POST `/register` - Register new user
- POST `/login` - Login with email/password
- GET `/me` - Get current user
- GET `/verify-email` - Verify email token
- POST `/resend-verification` - Resend verification email
- POST `/google-oauth` - Google OAuth callback

### Videos (`/api/`)
- GET `/discover` - Search CC-BY videos (optimized)
- GET `/videos/{id}` - Get video details
- POST `/videos/{id}/generate_clip` - Generate clip
- POST `/clear-videos` - Clear discovered videos
- GET `/youtube/cache-stats` - Cache statistics
- POST `/youtube/clear-cache` - Clear caches

### Images (`/api/images/`)
- GET `/search` - Search Pexels/Unsplash
- GET `/favorites` - Get user favorites
- POST `/favorites` - Add to favorites
- DELETE `/favorites/{id}` - Remove from favorites

### Content Library (`/api/content-library/`)
- GET `/search` - Dynamic search across web
- GET `/worksheets/search` - Worksheet-specific search
- GET `/favorites` - Get favorites
- POST `/favorites` - Add to favorites
- DELETE `/favorites/{id}` - Remove from favorites
- GET `/gutenberg/search` - Search Project Gutenberg

### Dashboard (`/api/`)
- GET `/stats` - Dashboard statistics
- GET `/history` - Post history
