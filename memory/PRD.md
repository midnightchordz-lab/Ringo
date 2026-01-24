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
- **Authentication**: JWT (python-jose, passlib), Google OAuth via Emergent Auth, Microsoft OAuth
- **Integrations**: YouTube Data API v3, Resend (email), Emergent LLM Key (AI analysis), yt-dlp, Pexels API, Unsplash API, Project Gutenberg API

## What's Been Implemented (Latest - Jan 24, 2026)

### Image Search Bug Fix (Jan 24, 2026) ✅ COMPLETED
- **Issue**: Image search returned empty results when "All" filter was selected
- **Root Cause**: The condition `image_type in [None, "photo"]` failed when `image_type="all"` was passed
- **Fix**: Added normalization to treat `image_type='all'` same as `None` in both `server.py` and `routes/images.py`
- **Result**: Image search now returns results correctly from Unsplash, Pexels, and other sources

### Backend Refactoring Phase 2 (Jan 24, 2026) ✅ COMPLETED
- **Goal**: Continue breaking down the monolithic `server.py` and integrate modular routes
- **Result**: All modular routes integrated, duplicates removed

**Changes Made**:
1. **Updated `/app/backend/routes/auth.py`** - Complete auth module with Google OAuth, Microsoft OAuth, Email/Password auth
2. **Updated `/app/backend/config.py`** - Added Microsoft OAuth config
3. **Integrated all modular routers in `server.py`**: auth, youtube, images, dashboard, content
4. **Removed duplicate endpoints from server.py**

**Lines Reduced**: 6397 → 5810 (587 lines removed, ~10% reduction)

### Professional UI Redesign (Jan 24, 2026) ✅ COMPLETED
- Complete redesign from "Creative Studio" to "Soft Utility" professional design
- Clean sidebar navigation, essential information only
- Professional typography: Inter (body) + Manrope (headings)

### Automatic Logout Bug Fix (Jan 22, 2026) ✅ COMPLETED
- Created `AuthContext` with reactive state management
- Fixed race conditions with React state updates

### Video-to-Text Transcription Feature (Jan 22, 2026) ✅ COMPLETED
- Convert YouTube videos to text transcripts
- Backend: `youtube-transcript-api` library
- Frontend: TranscriptModal with copy/download functionality

## Current Issues

### P0 - Critical (BLOCKED)
- **YouTube video download**: Server-side downloads blocked by YouTube's bot detection
- **Clip Generation**: Cannot generate clips without video downloads

### P1 - High Priority
- **Microsoft OAuth**: Requires user to configure Redirect URI in Azure AD
- **Email Verification**: Requires valid RESEND_API_KEY

### P2 - Medium Priority
- **Backend Refactoring**: Continue migrating remaining 5800 lines from server.py

## Pending Features

### P0 - Required
- Post clips to YouTube and Instagram (original requirement)
- Apple OAuth login (user requested)

### P1 - Improvements
- Extend dark mode to remaining pages
- Add animations and micro-interactions

## API Endpoints Summary

### Authentication (Modularized ✅)
- POST `/api/auth/register`, `/api/auth/login`, `/api/auth/google-oauth`
- GET `/api/auth/me`, `/api/auth/verify-email`, `/api/auth/microsoft/login`
- POST `/api/auth/microsoft/callback`, `/api/auth/resend-verification`

### Dashboard (Modularized ✅)
- GET `/api/stats`, `/api/history`
- POST/GET `/api/settings/api-keys`

### Videos (Partially Modularized)
- GET `/api/discover`, `/api/videos/{id}`, `/api/youtube/cache-stats`
- GET `/api/video/transcript/{id}` ✅ Modularized
- POST `/api/clips/generate`, `/api/clear-videos`, `/api/youtube/clear-cache`

### Images (Modularized ✅)
- GET `/api/images/search`, `/api/images/favorites`
- POST/DELETE `/api/images/favorites`

### Content Library (Partially Modularized)
- GET/POST/DELETE `/api/content-library/favorites` ✅ Modularized
- GET `/api/content-library/search`, `/api/content-library/childrens-literature`
- GET `/api/content-library/free-books`, `/api/content-library/worksheets/search`

## Files of Reference
- `/app/backend/server.py` - Main backend (~5810 lines)
- `/app/backend/routes/auth.py` - Complete auth module
- `/app/backend/routes/youtube.py` - Transcript endpoints
- `/app/backend/routes/dashboard.py` - Stats/settings endpoints
- `/app/backend/routes/images.py` - Image search endpoints
- `/app/backend/routes/content.py` - Content library favorites
- `/app/backend/ARCHITECTURE.md` - Architecture documentation
- `/app/frontend/src/context/AuthContext.jsx` - Auth state management
- `/app/frontend/src/pages/ContentLibrary.jsx` - Content library UI

## Last Updated
January 24, 2026 - Backend Refactoring Phase 2 Complete
