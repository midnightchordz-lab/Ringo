import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Play, TrendingUp, ShieldCheck, Info, CheckCircle2, Database, Zap, Star, Video, Filter, RefreshCw, ChevronLeft, ChevronRight, ArrowUpDown, FileText, Loader2, Copy, Download, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

// Transcript Modal Component
const TranscriptModal = ({ video, onClose }) => {
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTranscript = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get(`/video/transcript/${video.id}`);
        if (response.data.success) {
          setTranscript(response.data);
          toast.success(`Transcript loaded! ${response.data.word_count} words`);
        } else {
          setError(response.data.error || 'Failed to get transcript');
          toast.error(response.data.error || 'No transcript available');
        }
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to fetch transcript');
        toast.error('Failed to fetch transcript');
      } finally {
        setLoading(false);
      }
    };
    fetchTranscript();
  }, [video.id]);

  const copyToClipboard = () => {
    if (transcript?.full_text) {
      navigator.clipboard.writeText(transcript.full_text);
      toast.success('Transcript copied to clipboard!');
    }
  };

  const downloadTranscript = () => {
    if (transcript?.full_text) {
      const blob = new Blob([transcript.full_text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${video.title.replace(/[^a-z0-9]/gi, '_')}_transcript.txt`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Transcript downloaded!');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-neutral-800 dark:text-white">Video Transcript</h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-1">{video.title}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
          >
            <X className="w-4 h-4 text-neutral-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-10 h-10 text-purple-500 animate-spin mb-4" />
              <p className="text-neutral-600 dark:text-neutral-400">Fetching transcript...</p>
              <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">This may take a few seconds</p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <X className="w-8 h-8 text-red-500" />
              </div>
              <p className="text-red-600 dark:text-red-400 font-medium">{error}</p>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">This video may not have captions available.</p>
            </div>
          ) : transcript ? (
            <div>
              {/* Stats */}
              <div className="flex items-center gap-4 mb-4 p-3 bg-neutral-50 dark:bg-neutral-800 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">Language:</span>
                  <span className="text-xs font-medium text-neutral-800 dark:text-neutral-200 bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 rounded">{transcript.language}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">Words:</span>
                  <span className="text-xs font-medium text-neutral-800 dark:text-neutral-200">{transcript.word_count?.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">Segments:</span>
                  <span className="text-xs font-medium text-neutral-800 dark:text-neutral-200">{transcript.total_segments}</span>
                </div>
              </div>

              {/* Transcript Text */}
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p className="text-neutral-700 dark:text-neutral-300 leading-relaxed whitespace-pre-wrap text-sm">
                  {transcript.full_text}
                </p>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer with actions */}
        {transcript && !loading && !error && (
          <div className="p-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-end gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={copyToClipboard}
              className="flex items-center gap-2"
            >
              <Copy className="w-4 h-4" />
              Copy Text
            </Button>
            <Button
              size="sm"
              onClick={downloadTranscript}
              className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              <Download className="w-4 h-4" />
              Download
            </Button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
};

const VideoCard = ({ video, onTranscribe }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    whileHover={{ y: -8 }}
    className="studio-card studio-card-hover overflow-hidden group"
    data-testid="video-card"
  >
    <Link to={`/video/${video.id}`}>
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
    </Link>
    <div className="p-4">
      <Link to={`/video/${video.id}`}>
        <h3 className="text-neutral-900 dark:text-neutral-100 font-semibold line-clamp-2 mb-2 text-sm leading-tight hover:text-blue-600 dark:hover:text-blue-400 transition-colors">{video.title}</h3>
      </Link>
      <p className="text-blue-600 dark:text-blue-400 text-xs font-medium mb-3">{video.channel}</p>
      <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400 mb-3">
        <div className="flex items-center gap-3">
          <span>{(video.views || 0).toLocaleString()} views</span>
          <span>{(video.likes || 0).toLocaleString()} likes</span>
        </div>
        <span className="bg-neutral-100 dark:bg-neutral-800 px-2 py-1 rounded-full font-medium">
          {Math.floor((video.duration || 0) / 60)}:{String((video.duration || 0) % 60).padStart(2, '0')}
        </span>
      </div>
      {/* Transcribe Button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onTranscribe(video);
        }}
        className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-gradient-to-r from-purple-100 to-pink-100 dark:from-purple-900/30 dark:to-pink-900/30 hover:from-purple-200 hover:to-pink-200 dark:hover:from-purple-900/50 dark:hover:to-pink-900/50 text-purple-700 dark:text-purple-300 rounded-xl text-xs font-semibold transition-all"
        data-testid="transcribe-button"
      >
        <FileText className="w-3.5 h-3.5" />
        Convert to Text
      </button>
    </div>
  </motion.div>
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
  const [transcriptVideo, setTranscriptVideo] = useState(null);

  const handleTranscribe = (video) => {
    setTranscriptVideo(video);
  };

  const handleSearch = async (pageToken = null, isInitialLoad = false) => {
    if (!searchQuery.trim() && videos.length > 0 && !pageToken && !isInitialLoad) return;
    
    setLoading(true);
    try {
      // Always skip cache for user-initiated searches, only use cache on initial page load
      const skipCache = !isInitialLoad;
      
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
      
      // Show success message with total available
      if (response.data.total > 0) {
        const moreMsg = response.data.total_available > response.data.total 
          ? ` (${response.data.total_available?.toLocaleString()}+ available)` 
          : '';
        toast.success(`Found ${response.data.total} videos${moreMsg}`);
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
      handleSearch(nextPageToken, false);
    }
  };

  const handlePrevPage = () => {
    if (prevPageToken) {
      setCurrentPage(prev => prev - 1);
      handleSearch(prevPageToken, false);
    }
  };

  const handleRefresh = () => {
    handleSearch(null, false);
  };

  useEffect(() => {
    // Use cache only on initial load for faster startup
    handleSearch(null, true);
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

      {/* API Status Banner - only show when optimized */}
      {cacheInfo && cacheInfo.optimized && (
        <div className="studio-card p-4 mb-6 border-l-4 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20">
          <div className="flex items-center gap-3">
            <Zap className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <div className="flex-1">
              <span className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">Fresh Results</span>
              <p className="text-xs text-emerald-600 dark:text-emerald-400">Searching YouTube for CC BY licensed videos</p>
            </div>
          </div>
        </div>
      )}

      {/* License Info Banner */}
      <div className="studio-card p-4 mb-6 border-l-4 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/40 rounded-lg flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">All Videos Are Commercial-Safe</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <p className="text-xs text-emerald-700 dark:text-emerald-400">
              Videos shown are licensed under <span className="font-bold">CC BY (Creative Commons Attribution)</span>. 
              You can use them commercially with proper attribution.
            </p>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Commercial Use
          </div>
          <div className="flex items-center gap-1.5 text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Modifications Allowed
          </div>
          <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
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
                  // Fetch fresh results with new sort order
                  setTimeout(() => handleSearch(null, false), 100);
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
