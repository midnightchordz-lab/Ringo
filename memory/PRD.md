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

### Design Theme Overhaul (Jan 20, 2026)
Implemented "Creative Studio" theme - a bright, welcoming design:
- **Color Palette**: Electric Azure (#006FEE), Coral Pop (#FF5C5C), Sunshine Yellow (#FFC107), Emerald (#10B981)
- **Typography**: Outfit (headings), DM Sans (body)
- **Light Theme**: Neutral-50 backgrounds, white cards with subtle shadows
- **Navigation**: Colorful gradient active states, icon backgrounds matching each section
- **Login/Register**: Split-screen design with feature showcase
- **Cards**: Clean studio-card style with hover animations
- **Buttons**: Gradient primary buttons with glow effects
- **Badges**: Colorful license badges, viral score indicators
- Pages updated: Login, Register, Dashboard, Videos, Images, Content Library

### Backend Refactoring (Jan 20, 2026)
Created modular architecture for maintainability:
- `/app/backend/config.py` - Centralized configuration ✅
- `/app/backend/database.py` - MongoDB connection ✅
- `/app/backend/models/schemas.py` - Pydantic schemas ✅
- `/app/backend/services/youtube_optimizer.py` - YouTube caching ✅
- `/app/backend/utils/auth.py` - Authentication utilities ✅
- `/app/backend/utils/helpers.py` - Common helpers ✅
- `/app/backend/routes/auth.py` - Auth route templates ✅
- `/app/backend/routes/images.py` - Image route templates ✅
- `/app/backend/routes/dashboard.py` - Dashboard route templates ✅
- `/app/backend/ARCHITECTURE.md` - Full documentation ✅
- All modules tested and importing correctly
- `server.py` remains as entry point (working)

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

### Core Features - Content Library (ENHANCED Jan 21, 2026)
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
- Category filters: All Content, **Free Books**, Worksheets, Books, Articles, Courses, Videos, Resources
- Education level filters: Pre-school, Elementary, Middle, High, University
- Save resources to favorites
- Quick search suggestions for common queries
- Source badges showing where content came from
- License information for each result

### Web-Wide Search Enhancement (Jan 21, 2026) ✅ NEW
Implemented comprehensive, multi-source search for all content categories:

**COURSES** (7 sources):
- OpenStax - Free peer-reviewed textbooks
- MIT OpenCourseWare - MIT course materials
- Wikiversity - Free learning resources (MediaWiki API)
- Wikibooks - Free textbooks (MediaWiki API)
- freeCodeCamp - Free coding courses
- Codecademy - Interactive coding tutorials
- YouTube Educational - Course playlists

**VIDEOS** (3 sources):
- YouTube (Creative Commons) - CC-licensed educational videos
- Internet Archive - Public domain documentaries & lectures
- TED Talks - Expert talks on various topics

**RESOURCES** (8 sources):
- OER Commons - Open Educational Resources
- MERLOT - Curated learning materials
- Internet Archive - Educational texts & documents
- Smithsonian Learning Lab - Museum resources
- Library of Congress - Primary historical sources
- PBS LearningMedia - PreK-12 educational resources
- BBC Bitesize - UK educational content
- National Geographic Education - Geography & science resources

### Core Features - Reading Lists (NEW Jan 20, 2026)
- **Create curated book collections** for specific grades or subjects
- **Reading List management**: Create, edit, delete lists
- **Add books** from Free Books section to any reading list
- **Public/Private toggle**: Share lists with other teachers or keep private
- **Copy public lists**: Teachers can copy shared reading lists to their own collection
- **List metadata**: Name, description, grade level, subject
- **View list details**: See all books in a list with download options
- Endpoints: `/api/reading-lists`, `/api/reading-lists/{id}`, `/api/reading-lists/{id}/books`, `/api/reading-lists/{id}/copy`

### Core Features - Free Books Section (ENHANCED Jan 21, 2026)
- **62 curated free books** from Project Gutenberg (public domain)
- **Categories**: Stories, Poetry, Grammar, Math, Science
- **Book cards** display: Title, Author, Category badge, Public Domain badge, Printable badge, Grade levels
- **Download options**: PDF, EPUB, Read Online
- **Category filters**: All Books, Stories, Poetry, Grammar, Math, Science
- **Grade level filtering**: Pre-school through University
- **Search within books**: Search by title, author, or subject
- **PAGINATION**: 50 items per page with navigation controls (Previous/Next, page numbers)
- Endpoints: `/api/content-library/free-books`, `/api/content-library/free-books/search`

### Core Features - Children's Literature Search (NEW Jan 20, 2026)
- **Dynamic copyright-free search** across multiple sources:
  - Project Gutenberg (via Gutendex API)
  - StoryWeaver (Creative Commons books)
  - Open Library (public domain)
- **PAGINATION**: 50 items per page with navigation controls
- Search and filter by grade level
- All results are downloadable and printable
- Endpoints: `/api/content-library/childrens-literature`

### Core Features - Content Library Search (ENHANCED Jan 21, 2026)
- Searches across OpenLibrary, Internet Archive, Wikipedia, OER Commons
- AI-powered result enhancement and categorization
- **PAGINATION**: 50 items per page with navigation controls
- Endpoints: `/api/content-library/search`

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

### Reading Lists
- POST `/api/reading-lists` - Create new reading list (NEW)
- GET `/api/reading-lists` - Get user's reading lists (NEW)
- GET `/api/reading-lists/{id}` - Get specific reading list (NEW)
- PUT `/api/reading-lists/{id}` - Update reading list (NEW)
- DELETE `/api/reading-lists/{id}` - Delete reading list (NEW)
- POST `/api/reading-lists/{id}/books` - Add book to list (NEW)
- DELETE `/api/reading-lists/{id}/books/{book_id}` - Remove book from list (NEW)
- POST `/api/reading-lists/{id}/copy` - Copy public list to own lists (NEW)

### Content Library
- GET `/api/content-library/search` - Dynamic search with pagination (page, per_page params)
- GET `/api/content-library/childrens-literature` - Children's literature search with pagination
- GET `/api/content-library/worksheets/search` - Worksheet-specific search (NEW)
- GET `/api/content-library/free-books` - Get curated free books with pagination (page, per_page params)
- GET `/api/content-library/free-books/search` - Search free books with pagination
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
January 22, 2026 - Fixed Image Type Filter

### Image Type Filter Fix (Jan 22, 2026) ✅ NEW
- **Fixed conditional logic** in `/api/images/search` endpoint:
  - Photos: Searches Unsplash and Pexels (both work)
  - Illustrations/Vectors: ONLY queries Pixabay (the only source that supports these types)
- **Clear error messaging** when Pixabay API key is not configured for illustration/vector searches
- **UI Enhancement**: Added "(Pixabay)" label to Illustrations and Vectors filter buttons to indicate they require Pixabay
- **Configuration**: Added `PIXABAY_API_KEY` placeholder to `/app/backend/.env`

**Note**: To enable illustration and vector search, users must:
1. Create a free Pixabay account at https://pixabay.com
2. Get their API key from the API documentation page
3. Add `PIXABAY_API_KEY=your_key_here` to `/app/backend/.env`


## Recent Changes (Jan 21, 2026)

### FEATURE: Dark Mode Toggle (COMPLETED)
- **Added theme context** at `/app/frontend/src/context/ThemeContext.jsx`
- **Theme toggle in sidebar** - Animated switch with sun/moon icons
- **Persistent theme** - Saved to localStorage, respects system preference
- **CSS updates** - Added dark mode variants to all utility classes in index.css
- **Components updated**:
  - Layout.jsx - Sidebar, navigation, user section
  - Dashboard.jsx - Stats cards, video cards, loading state
  - ContentLibrary.jsx - Search results, cards, badges
- **Smooth transitions** - 300ms transition on background/color changes

### FEATURE: Comprehensive Web-Wide Search (COMPLETED)
- **Problem**: Content Library categories (Courses, Videos, Resources) were returning limited results from only 1-2 sources
- **Solution**: Implemented multi-source search for each category:
  - **Courses**: Added Wikiversity, Wikibooks, freeCodeCamp, Codecademy APIs (total 7 sources)
  - **Videos**: Enhanced YouTube CC search + Internet Archive enhanced + TED Talks (3 sources)
  - **Resources**: Added Smithsonian, Library of Congress, PBS LearningMedia, BBC Bitesize, National Geographic (total 8 sources)
- **New search functions added**:
  - `search_wikiversity_courses()` - MediaWiki API for Wikiversity
  - `search_wikibooks_courses()` - MediaWiki API for Wikibooks
  - `search_freecodecamp_courses()` - freeCodeCamp curriculum
  - `search_codecademy_courses()` - Codecademy courses
  - `search_youtube_videos_comprehensive()` - Enhanced YouTube CC search
  - `search_internet_archive_videos_enhanced()` - Multi-category video search
  - `search_smithsonian_resources()` - Smithsonian Learning Lab
  - `search_national_geographic_edu()` - National Geographic Education
  - `search_library_of_congress()` - Library of Congress API
  - `search_pbs_learningmedia()` - PBS LearningMedia
  - `search_bbc_bitesize()` - BBC Bitesize education
- **Files changed**: `/app/backend/server.py`
- **Test results**:
  - Courses: 28+ results from 7 sources
  - Videos: 186+ results from 3 sources (all CC licensed)
  - Resources: 37+ results from 8 sources

### BUG FIX: Gutenberg PDF 404 Errors (Previous session)
- **Problem**: PDF download links returned 404 because Project Gutenberg doesn't serve direct .pdf files at `/ebooks/{id}.pdf`
- **Solution**: Updated all book URLs:
  - "Download" button now links to Gutenberg landing page (`/ebooks/{id}`) where users can choose format
  - EPUB links corrected to use `.epub.images` suffix for direct download
  - HTML links corrected to use `.html.images` suffix for online reading
- **Files changed**: `/app/backend/server.py` (FREE_EDUCATIONAL_BOOKS array and dynamic search functions)
- **Frontend updated**: Button labels changed from "PDF" to "Download" with helpful tooltips

### Pagination Feature Implementation
- **Backend**: Added `page` and `per_page` query parameters to all Content Library endpoints
- **Frontend**: Added `PaginationControls` component with page navigation
- **Tests**: 12 pytest tests passing (100% success rate)
