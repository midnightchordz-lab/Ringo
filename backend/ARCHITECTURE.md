# Backend Architecture

## Directory Structure

```
/app/backend/
├── server.py           # Main FastAPI application (~5800 lines) - REFACTORING IN PROGRESS
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
│   ├── auth.py         # Authentication routes (INTEGRATED - Jan 24)
│   ├── images.py       # Image search routes (INTEGRATED - Jan 24)
│   ├── dashboard.py    # Stats/settings routes (INTEGRATED - Jan 24)
│   ├── youtube.py      # YouTube transcript routes (INTEGRATED - Jan 22)
│   └── content.py      # Content library routes (INTEGRATED - Jan 24)
│
├── services/           # Business logic and external integrations ✓
│   ├── __init__.py
│   └── youtube_optimizer.py  # YouTube API optimization
│
├── tests/              # Test files
│   └── test_video_transcript_api.py
│
└── utils/              # Utility functions ✓
    ├── __init__.py
    ├── auth.py         # Authentication utilities
    └── helpers.py      # Common helper functions
```

## Module Status

| Module | Status | Description |
|--------|--------|-------------|
| `config.py` | ✅ Complete | Environment variables + Microsoft OAuth config |
| `database.py` | ✅ Complete | MongoDB connection |
| `models/schemas.py` | ✅ Complete | All Pydantic models |
| `services/youtube_optimizer.py` | ✅ Complete | YouTube caching |
| `utils/auth.py` | ✅ Complete | Auth utilities |
| `utils/helpers.py` | ✅ Complete | Helper functions |
| `routes/auth.py` | ✅ **INTEGRATED** | Google, Microsoft, Email/Password auth |
| `routes/images.py` | ✅ **INTEGRATED** | Basic image search/favorites |
| `routes/dashboard.py` | ✅ **INTEGRATED** | Stats, history, settings |
| `routes/youtube.py` | ✅ **INTEGRATED** | Video transcript endpoints |
| `routes/content.py` | ✅ **INTEGRATED** | Content library favorites, reading lists |

## Refactoring Progress (Jan 24, 2026)

### Completed
- ✅ Auth routes fully modularized with Google OAuth, Microsoft OAuth, Email/Password
- ✅ Dashboard routes (stats, history, settings) moved to modular file
- ✅ YouTube transcript routes in separate module
- ✅ Content library favorites/reading lists in separate module
- ✅ Image search basic routes in separate module
- ✅ All modular routes integrated via `api_router.include_router()`
- ✅ Auth dependency injection set up for protected routes

### Line Count Progress
- Original: ~6400 lines
- Current: ~5800 lines
- Reduction: ~600 lines (10%)

### Still in server.py (To Be Migrated)
1. **Video Discovery & Clips** (~700 lines)
   - `/api/discover` - Video search
   - `/api/videos/{video_id}` - Video details  
   - `/api/clips/*` - Clip generation endpoints
   - `/api/clear-videos` - Clear videos

2. **Extended Image Search** (~400 lines)
   - `/api/images/search` - Multi-source image search (Wikimedia, OpenClipart, etc.)
   - Image favorites (duplicate, can be removed after verification)

3. **Content Library Search** (~2500 lines)
   - `/api/content-library/search` - Main search endpoint
   - `/api/content-library/gutenberg/search` - Gutenberg books
   - `/api/content-library/childrens-literature` - Children's books
   - `/api/content-library/worksheets/search` - Worksheets
   - `/api/content-library/free-books` - Free books
   - `/api/content-library/free-books/search` - Free book search
   - `/api/reading-lists/*` - Reading list management (duplicated)

4. **YouTube API Optimization** (~300 lines)
   - `YouTubeAPIOptimizer` class
   - `YouTubePersistentCache` class

### Next Steps
1. Migrate video discovery/clips to `routes/youtube.py` or new `routes/videos.py`
2. Consolidate extended image search into `routes/images.py`
3. Migrate content library search endpoints to `routes/content.py`
4. Move YouTube caching classes to `services/youtube_optimizer.py`
5. Remove duplicate endpoints from server.py

## API Endpoints Summary

### Authentication (`/api/auth/`) - **Modularized**
- POST `/register` - Register new user
- POST `/login` - Login with email/password
- GET `/me` - Get current user
- GET `/verify-email` - Verify email token
- POST `/resend-verification` - Resend verification email
- POST `/google-oauth` - Google OAuth callback
- GET `/microsoft/login` - Microsoft OAuth initiation
- POST `/microsoft/callback` - Microsoft OAuth callback

### Dashboard (`/api/`) - **Modularized**
- GET `/stats` - Dashboard statistics
- GET `/history` - Post history
- POST `/settings/api-keys` - Save API keys
- GET `/settings/api-keys` - Get API keys (masked)

### Images (`/api/images/`) - **Partially Modularized**
- GET `/search` - Search images (extended version in server.py)
- GET `/favorites` - Get user favorites
- POST `/favorites` - Add to favorites
- DELETE `/favorites/{id}` - Remove from favorites

### YouTube (`/api/`) - **Partially Modularized**
- GET `/video/transcript/{video_id}` - Get transcript (modularized)
- GET `/video/transcript/{video_id}/cached` - Cached transcript (modularized)
- GET `/discover` - Search CC-BY videos (in server.py)
- GET `/videos/{id}` - Get video details (in server.py)
- POST `/clips/generate` - Generate clip (in server.py)

### Content Library (`/api/content-library/`) - **Partially Modularized**
- GET `/favorites` - Get favorites (modularized)
- POST `/favorites` - Add to favorites (modularized)
- DELETE `/favorites/{id}` - Remove from favorites (modularized)
- GET `/search` - Dynamic search (in server.py)
- GET `/gutenberg/search` - Gutenberg search (in server.py)
- GET `/childrens-literature` - Children's books (in server.py)

### Reading Lists (`/api/reading-lists/`) - **Partially Modularized**
- Full CRUD operations for reading lists (duplicated - both in module and server.py)
