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

### Core Features - Content Library (NEW)
- 24 curated copyright-free educational resources
- 8 content categories: Stories, Poetry, Educational Articles, Textbooks, Audio Books, Research Papers, Historical Documents
- 5 education levels: Pre-school, Primary, Middle School, High School, University
- Search and filter by category/level
- Save resources to favorites
- Project Gutenberg book search integration
- Featured resources section
- Quick access by education level

### UI/UX
- Vibrant gradient theme (violet, purple, pink accents)
- Responsive layout with sidebar navigation
- Professional card designs with hover effects
- Loading states and toast notifications
- Images tab and Content Library tab in sidebar

## Current Issues

### P1 - High Priority
- **Clip Generation Blocked**: YouTube bot detection blocking yt-dlp downloads (403 Forbidden)

### P2 - Medium Priority  
- **Email Verification**: Requires valid RESEND_API_KEY for production

## Pending Features (Not Yet Implemented)

### P0 - Required
- Post clips to YouTube and Instagram (original requirement)
- Apple OAuth login (user requested)

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register new user
- POST `/api/auth/login` - Login with email/password
- GET `/api/auth/me` - Get current user info
- GET `/api/auth/verify-email?token=` - Verify email
- POST `/api/auth/google-oauth` - Google OAuth flow

### Video Discovery
- GET `/api/discover?query=&max_results=&min_views=` - Search CC-BY videos
- GET `/api/videos/{video_id}` - Get video details
- POST `/api/clear-videos` - Clear all discovered videos

### Images
- GET `/api/images/search?query=&per_page=` - Search copyright-free images
- GET `/api/images/favorites` - Get user's favorite images
- POST `/api/images/favorites` - Add image to favorites
- DELETE `/api/images/favorites/{image_id}` - Remove from favorites

### Content Library (NEW)
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
