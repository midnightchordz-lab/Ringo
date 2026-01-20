# ContentFlow - YouTube CC Content Discovery Platform

## Original Problem Statement
Build a full-stack application that:
1. Scans YouTube for copyright-free (CC BY) content
2. Ranks discovered videos based on a "viral score"
3. Creates short clips (9:16 format) from these videos
4. Includes AI analysis to find the best part of the video for clip generation
5. Posts the generated reels to YouTube and Instagram accounts
6. User registration and login system (JWT, Google, and Apple ID)
7. Email verification for new user registrations
8. Professional, vibrant UI for corporate/education clients
9. Button to clear discovered videos from the dashboard
10. Remove "Made with Emergent" branding
11. Copyright-free images search from Unsplash & Pexels
12. **NEW**: Content Library for copyright-free educational resources

## Tech Stack
- **Frontend**: React, React Router, Axios, Tailwind CSS, Framer Motion, Shadcn/UI
- **Backend**: FastAPI (Python), MongoDB (via Motor)
- **Authentication**: JWT (python-jose, passlib), Google OAuth via Emergent Auth
- **Integrations**: YouTube Data API v3, Resend (email), Emergent LLM Key (AI analysis), yt-dlp, Pexels API, Unsplash API, Project Gutenberg API

## What's Been Implemented (Completed)

### Backend Refactoring (Jan 20, 2026)
Created modular architecture for maintainability:
- `/app/backend/config.py` - Centralized configuration
- `/app/backend/database.py` - MongoDB connection
- `/app/backend/models/` - Pydantic schemas
- `/app/backend/services/` - Business logic (YouTube optimizer)
- `/app/backend/utils/` - Auth utilities and helpers
- `/app/backend/routes/` - Route templates (ready for migration)
- `/app/backend/ARCHITECTURE.md` - Full documentation
- Note: `server.py` still monolithic; modules created for gradual migration

### UI Updates (Jan 20, 2026)
- Renamed "Discover" to "Videos" in the sidebar navigation
- Added "Find" button next to search bars on Videos, Images, and Content Library pages
- Fixed JWT login issue where ObjectId was not JSON serializable
- Fixed get_current_user to properly handle email-based JWT tokens

### Authentication System
- JWT-based registration and login
- Google OAuth integration via Emergent Auth
- Email verification flow using Resend
- Protected API routes with Bearer token authentication
- Supports both JWT tokens and Emergent session tokens

### Core Features - Videos
- Video discovery with YouTube Data API (CC-BY license filter)
- Viral score ranking algorithm
- Dashboard with stats (videos found, clips made, posts live)
- Clear videos functionality
- Video preview page with embedded YouTube player
- AI-powered clip analysis backend (uses Emergent LLM Key)

### Core Features - Images
- Search copyright-free images from Pexels and Unsplash
- Download images directly
- Copy image URLs to clipboard
- Save images to favorites collection
- View and manage favorites
- Source badges (Pexels/Unsplash)
- Photographer attribution with links

### Core Features - Content Library (ENHANCED Jan 20, 2026)
- **Dynamic AI-Powered Search** - searches across multiple sources in real-time:
  - OpenLibrary (3M+ books)
  - Internet Archive (35M+ items)
  - Wikipedia (6M+ articles)
  - Educational worksheet sites (K5 Learning, Math-Drills, Common Core Sheets, etc.)
- **AI Enhancement** - uses GPT-4.1-mini via Emergent LLM Key to:
  - Score relevance (1-10)
  - Categorize results (worksheet, book, article, course, video, resource)
  - Suggest grade levels
  - Generate AI summaries
- Category filters: All Content, Worksheets, Books, Articles, Courses, Videos, Resources
- Education level filters: Pre-school, Elementary, Middle, High, University
- Save resources to favorites
- Quick search suggestions for common queries
- Source badges showing where content came from
- License information for each result

### UI/UX
- Vibrant gradient theme (violet, purple, pink accents)
- Responsive layout with sidebar navigation
- Professional card designs with hover effects
- Loading states and toast notifications
- "Videos" tab (renamed from "Discover"), Images tab, and Content Library tab in sidebar
- "Find" button added to all search bars

## Current Issues

### P1 - High Priority
- **Clip Generation Blocked**: YouTube bot detection blocking yt-dlp downloads (403 Forbidden)

### P2 - Medium Priority  
- **Email Verification**: Requires valid RESEND_API_KEY for production

## Pending Features (Not Yet Implemented)

### P0 - Required
- Post clips to YouTube and Instagram (original requirement)
- Apple OAuth login (user requested)

## YouTube API Optimization (Implemented Jan 20, 2026)

### Features Implemented:
1. **Cache Data Store** - Dual-layer caching:
   - In-memory cache (30 min TTL) for fast repeated queries
   - MongoDB persistent cache (6 hour TTL) survives restarts
2. **Request Only Necessary Fields** - Uses `fields` parameter to request minimal data
3. **GZIP Compression** - Enabled for reduced data transfer
4. **Conditional Requests (ETags)** - Stores and uses ETags to skip unchanged data
5. **Batch Requests** - Video details fetched in batches of 50
6. **quotaUser Tracking** - Per-user quota tracking via hashed user ID

### New API Endpoints:
- GET `/api/youtube/cache-stats` - View cache statistics
- POST `/api/youtube/clear-cache` - Clear all YouTube caches

### Frontend Indicators:
- "Cached Results" banner (amber) when showing cached data
- "Optimized API Usage" banner (green) when using fresh optimized requests
- Toast notifications for cache/optimization status

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - Login with email/password
- GET `/api/auth/me` - Get current user info
- GET `/api/auth/verify-email?token=` - Verify email
- POST `/api/auth/google-oauth` - Google OAuth flow

### Video Discovery
- GET `/api/discover?query=&max_results=&min_views=` - Search CC-BY videos (optimized)
- GET `/api/videos/{video_id}` - Get video details
- POST `/api/clear-videos` - Clear all discovered videos
- GET `/api/youtube/cache-stats` - Cache statistics (NEW)
- POST `/api/youtube/clear-cache` - Clear caches (NEW)

### Images
- GET `/api/images/search?query=&per_page=` - Search copyright-free images
- GET `/api/images/favorites` - Get user's favorite images
- POST `/api/images/favorites` - Add image to favorites
- DELETE `/api/images/favorites/{image_id}` - Remove from favorites

### Content Library
- GET `/api/content-library/search` - Dynamic search across web sources (NEW)
- GET `/api/content-library/worksheets/search` - Worksheet-specific search (NEW)
- GET `/api/content-library/favorites` - Get favorite resources
- POST `/api/content-library/favorites` - Add resource to favorites
- DELETE `/api/content-library/favorites/{resource_id}` - Remove from favorites
- GET `/api/content-library/gutenberg/search?query=` - Search Project Gutenberg

### Dashboard
- GET `/api/stats` - Dashboard statistics
- GET `/api/history` - Post history

## Database Collections (MongoDB)
- `users` - User accounts with auth info
- `user_sessions` - Emergent OAuth session tokens
- `discovered_videos` - Cached video data from YouTube
- `youtube_api_cache` - Persistent cache for YouTube API responses (NEW)
- `favorite_images` - User's saved images
- `content_library_favorites` - User's saved content resources (NEW)
- `clips` - Generated clips metadata
- `posts` - Social media post history

## Content Library Resources (24 total)
- **Featured**: Project Gutenberg, Open Library, Khan Academy, MIT OpenCourseWare, LibriVox, Poetry Foundation, CK-12, OpenStax, arXiv, Internet Archive, edX
- **More**: Storynory, Int'l Children's Digital Library, CORE, DOAJ, Europeana, Library of Congress, Coursera, PBS LearningMedia, Smithsonian, National Geographic Education, Lit2Go, ReadWorks, CommonLit

## Files of Reference
- `/app/backend/server.py` - All backend logic
- `/app/frontend/src/pages/Images.jsx` - Images search page
- `/app/frontend/src/pages/ContentLibrary.jsx` - Content Library page (NEW)
- `/app/frontend/src/pages/` - React page components
- `/app/frontend/src/utils/api.js` - Auth interceptor
- `/app/frontend/src/components/Layout.jsx` - Sidebar navigation
- `/app/backend/.env` - Backend secrets (includes UNSPLASH_API_KEY)

## Last Updated
January 19, 2026 - Added comprehensive Content Library feature with 24 resources, all categories and education levels
