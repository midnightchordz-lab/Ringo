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

## Tech Stack
- **Frontend**: React, React Router, Axios, Tailwind CSS, Framer Motion, Shadcn/UI
- **Backend**: FastAPI (Python), MongoDB (via Motor)
- **Authentication**: JWT (python-jose, passlib), Google OAuth via Emergent Auth
- **Integrations**: YouTube Data API v3, Resend (email), Emergent LLM Key (AI analysis), yt-dlp

## What's Been Implemented (Completed)

### Authentication System
- JWT-based registration and login
- Google OAuth integration via Emergent Auth
- Email verification flow using Resend
- Protected API routes with Bearer token authentication

### Core Features
- Video discovery with YouTube Data API (CC-BY license filter)
- Viral score ranking algorithm
- Dashboard with stats (videos found, clips made, posts live)
- Clear videos functionality
- Video preview page with embedded YouTube player
- AI-powered clip analysis backend (uses Emergent LLM Key)

### UI/UX
- Vibrant gradient theme (violet, purple, pink accents)
- Responsive layout with sidebar navigation
- Professional card designs with hover effects
- Loading states and toast notifications
- "Made with Emergent" branding removed

## Current Issues

### P0 - Critical (None currently)
All core features working after fixes

### P1 - High Priority
- **Clip Generation Blocked**: YouTube bot detection blocking yt-dlp downloads (403 Forbidden)
  - Workaround needed: User cookies or alternative approach

### P2 - Medium Priority  
- **Email Verification**: Requires valid RESEND_API_KEY for production
  - Current placeholder: re_123456789

### P3 - Low Priority
- Dashboard header gradient may have low contrast on some displays

## Pending Features (Not Yet Implemented)

### P0 - Required
- Post clips to YouTube and Instagram (original requirement)
- Apple OAuth login (user requested)

### P1 - Should Have
- Video download alternative to bypass YouTube restrictions
- Real email verification flow with valid Resend API key

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - Login with email/password
- GET `/api/auth/me` - Get current user info
- GET `/api/auth/verify-email?token=` - Verify email
- POST `/api/auth/resend-verification` - Resend verification email
- POST `/api/auth/google-oauth` - Google OAuth flow

### Video Discovery
- GET `/api/discover?query=&max_results=&min_views=` - Search CC-BY videos
- GET `/api/videos/{video_id}` - Get video details
- POST `/api/clear-videos` - Clear all discovered videos

### Clips & Posting
- GET `/api/clips/ai-analyze/{video_id}` - AI analysis for best clip timing
- POST `/api/clips/generate` - Generate clip (currently broken)
- POST `/api/post` - Post clip to social media (not implemented)

### Dashboard
- GET `/api/stats` - Dashboard statistics
- GET `/api/history` - Post history

### Settings
- GET `/api/settings/api-keys` - Get saved API keys
- POST `/api/settings/api-keys` - Save API keys

## Database Collections (MongoDB)
- `users` - User accounts with auth info
- `discovered_videos` - Cached video data from YouTube
- `clips` - Generated clips metadata
- `posts` - Social media post history
- `api_keys` - User API keys for YouTube/Instagram

## Test Credentials
- Email: testuser123@test.com
- Password: Test123456
- Status: Email verified

## Files of Reference
- `/app/backend/server.py` - All backend logic
- `/app/frontend/src/pages/` - React page components
- `/app/frontend/src/utils/api.js` - Auth interceptor
- `/app/frontend/src/index.css` - Global styles
- `/app/backend/.env` - Backend secrets

## Last Updated
January 19, 2026 - Fixed video discovery authentication bug, all 17 backend tests passing
