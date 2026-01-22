import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Play, TrendingUp, ShieldCheck, Info, CheckCircle2, Database, Zap, Star, Video, Filter, RefreshCw, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const VideoCard = ({ video }) => (
  <Link to={`/video/${video.id}`} data-testid="video-card">
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -8 }}
      className="studio-card studio-card-hover overflow-hidden group"
    >
      <div className="relative aspect-video bg-neutral-100 dark:bg-neutral-800">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-14 h-14 bg-white dark:bg-neutral-800 rounded-full flex items-center justify-center shadow-xl">
            <Play className="w-6 h-6 text-blue-600 dark:text-blue-400 ml-1" fill="currentColor" />
          </div>
        </div>
        <div className="absolute top-3 left-3">
          <span className="bg-emerald-500 text-white text-xs font-bold px-2.5 py-1 rounded-lg shadow-lg flex items-center gap-1">
            <ShieldCheck className="w-3 h-3" /> CC BY
          </span>
        </div>
        <div className="absolute top-3 right-3">
          <span className="bg-gradient-to-r from-red-500 to-orange-500 text-white text-xs font-bold px-2.5 py-1 rounded-lg shadow-lg flex items-center gap-1">
            <Star className="w-3 h-3" fill="currentColor" />
            {video.viral_score}
          </span>
        </div>
      </div>
      <div className="p-4">
        <h3 className="text-neutral-900 dark:text-neutral-100 font-semibold line-clamp-2 mb-2 text-sm leading-tight">{video.title}</h3>
        <p className="text-blue-600 dark:text-blue-400 text-xs font-medium mb-3">{video.channel}</p>
        <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
          <div className="flex items-center gap-3">
            <span>{(video.views || 0).toLocaleString()} views</span>
            <span>{(video.likes || 0).toLocaleString()} likes</span>
          </div>
          <span className="bg-neutral-100 dark:bg-neutral-800 px-2 py-1 rounded-full font-medium">
            {Math.floor((video.duration || 0) / 60)}:{String((video.duration || 0) % 60).padStart(2, '0')}
          </span>
        </div>
      </div>
    </motion.div>
  </Link>
);

const SORT_OPTIONS = [
  { value: 'viewCount', label: 'Most Views' },
  { value: 'date', label: 'Most Recent' },
  { value: 'rating', label: 'Top Rated' },
  { value: 'relevance', label: 'Most Relevant' },
];

export const Discover = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [minViews, setMinViews] = useState(1000);
  const [maxResults, setMaxResults] = useState(50);
  const [cacheInfo, setCacheInfo] = useState(null);
  const [sortBy, setSortBy] = useState('viewCount');
  const [nextPageToken, setNextPageToken] = useState(null);
  const [prevPageToken, setPrevPageToken] = useState(null);
  const [totalAvailable, setTotalAvailable] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const handleSearch = async (pageToken = null, skipCache = false) => {
    if (!searchQuery.trim() && videos.length > 0 && !pageToken && !skipCache) return;
    
    setLoading(true);
    try {
      const response = await api.get('/discover', {
        params: {
          query: searchQuery,
          max_results: maxResults,
          min_views: minViews,
          sort_by: sortBy,
          page_token: pageToken,
          skip_cache: skipCache
        }
      });
      setVideos(response.data.videos);
      setNextPageToken(response.data.next_page_token);
      setPrevPageToken(response.data.prev_page_token);
      setTotalAvailable(response.data.total_available || response.data.total);
      
      if (!pageToken) {
        setCurrentPage(1);
      }
      
      setCacheInfo({
        cached: response.data.cached || false,
        cacheType: response.data.cache_type,
        optimized: response.data.optimized,
        quotaUser: response.data.quota_user,
        message: response.data.message,
        hasMore: response.data.has_more
      });
      
      if (response.data.cached && !skipCache) {
        toast.info(response.data.message || 'Showing cached results');
      } else if (response.data.optimized) {
        const moreMsg = response.data.has_more ? ` (${response.data.total_available?.toLocaleString()}+ available)` : '';
        toast.success(`Found ${response.data.total} videos${moreMsg}`);
      } else {
        toast.success(`Found ${response.data.total} videos!`);
      }
    } catch (error) {
      console.error('Error discovering videos:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to discover videos';
      
      if (error.response?.status === 429) {
        toast.error('YouTube API quota exceeded. Please try again tomorrow.');
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleNextPage = () => {
    if (nextPageToken) {
      setCurrentPage(prev => prev + 1);
      handleSearch(nextPageToken);
    }
  };

  const handlePrevPage = () => {
    if (prevPageToken) {
      setCurrentPage(prev => prev - 1);
      handleSearch(prevPageToken);
    }
  };

  const handleRefresh = () => {
    handleSearch(null, true);
  };

  useEffect(() => {
    handleSearch();
  }, []);

  return (
    <div className="p-6 lg:p-8 pb-24 lg:pb-8 bg-neutral-50 dark:bg-neutral-950 min-h-screen transition-colors duration-300">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
            <Video className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Discover Videos
            </h1>
            <p className="text-neutral-500 dark:text-neutral-400">Find viral CC BY licensed YouTube content</p>
          </div>
        </div>
      </div>

      {/* Cache Status Banner */}
      {cacheInfo && (cacheInfo.cached || cacheInfo.optimized) && (
        <div className={`studio-card p-4 mb-6 border-l-4 ${cacheInfo.cached ? 'border-amber-500 bg-amber-50' : 'border-emerald-500 bg-emerald-50'}`}>
          <div className="flex items-center gap-3">
            {cacheInfo.cached ? (
              <>
                <Database className="w-5 h-5 text-amber-600" />
                <div className="flex-1">
                  <span className="text-sm font-semibold text-amber-700">Cached Results</span>
                  <p className="text-xs text-amber-600">{cacheInfo.message || 'Showing previously cached videos to save API quota'}</p>
                </div>
              </>
            ) : (
              <>
                <Zap className="w-5 h-5 text-emerald-600" />
                <div className="flex-1">
                  <span className="text-sm font-semibold text-emerald-700">Optimized API Usage</span>
                  <p className="text-xs text-emerald-600">Using field filtering, ETags, and caching to minimize API calls</p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* License Info Banner */}
      <div className="studio-card p-4 mb-6 border-l-4 border-emerald-500 bg-emerald-50">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-emerald-800">All Videos Are Commercial-Safe</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-xs text-emerald-700">
              Videos shown are licensed under <span className="font-bold">CC BY (Creative Commons Attribution)</span>. 
              You can use them commercially with proper attribution.
            </p>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-emerald-200 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-700">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Commercial Use
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Modifications Allowed
          </div>
          <div className="flex items-center gap-1.5 text-amber-600">
            <Info className="w-3.5 h-3.5" />
            Attribution Required
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="studio-card p-6 mb-8">
        <div className="flex flex-col gap-4">
          {/* Main search row */}
          <div className="flex flex-col lg:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 dark:text-neutral-500" />
              <Input
                data-testid="search-input"
                type="text"
                placeholder="Search for videos... (e.g., 'cooking tutorial', 'music', 'nature')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="studio-input-icon w-full"
              />
            </div>
            <div className="flex gap-2">
              <Button
                data-testid="find-button"
                onClick={() => handleSearch()}
                disabled={loading}
                className="btn-primary min-w-[100px]"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  'Find'
                )}
              </Button>
              <Button
                onClick={handleRefresh}
                disabled={loading}
                className="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-xl px-4"
                title="Get fresh results (skip cache)"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          {/* Sort and filter row */}
          <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
            <div className="flex items-center gap-2">
              <ArrowUpDown className="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
              <span className="text-sm text-neutral-600 dark:text-neutral-400">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  handleSearch(null, true);
                }}
                className="text-sm bg-neutral-100 dark:bg-neutral-800 border-0 rounded-lg px-3 py-1.5 text-neutral-700 dark:text-neutral-200 focus:ring-2 focus:ring-blue-500"
              >
                {SORT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            
            {totalAvailable > 0 && (
              <div className="text-sm text-neutral-500 dark:text-neutral-400 ml-auto">
                {totalAvailable.toLocaleString()}+ videos available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Results Count and Pagination */}
      {videos.length > 0 && (
        <div className="flex items-center justify-between mb-6">
          <p className="text-neutral-600 dark:text-neutral-400">
            Found <span className="font-bold text-blue-600 dark:text-blue-400">{videos.length}</span> CC BY licensed videos
            {currentPage > 1 && <span className="text-neutral-400"> (Page {currentPage})</span>}
          </p>
          
          {/* Pagination Controls */}
          <div className="flex items-center gap-2">
            <Button
              onClick={handlePrevPage}
              disabled={!prevPageToken || loading}
              className="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg px-3 py-2 disabled:opacity-50"
              size="sm"
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Previous
            </Button>
            <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm font-medium">
              Page {currentPage}
            </span>
            <Button
              onClick={handleNextPage}
              disabled={!nextPageToken || loading}
              className="bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg px-3 py-2 disabled:opacity-50"
              size="sm"
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-neutral-600 dark:text-neutral-400 font-medium">Searching for videos...</p>
          </div>
        </div>
      )}

      {/* Video Grid */}
      {!loading && videos.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {videos.map((video, index) => (
            <motion.div
              key={video.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <VideoCard video={video} />
            </motion.div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && videos.length === 0 && (
        <div className="studio-card p-16 text-center">
          <div className="w-20 h-20 mx-auto mb-6 bg-blue-100 rounded-2xl flex items-center justify-center">
            <Search className="w-10 h-10 text-blue-600" />
          </div>
          <h3 className="text-xl font-bold text-neutral-900 mb-2">No videos found</h3>
          <p className="text-neutral-500 mb-6">Try searching for something like "tutorial", "music", or "nature"</p>
          <Button onClick={() => { setSearchQuery('tutorial'); handleSearch(); }} className="btn-primary">
            Try "tutorial"
          </Button>
        </div>
      )}
    </div>
  );
};

export default Discover;
