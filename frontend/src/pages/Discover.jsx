import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Play, TrendingUp, ShieldCheck, Info, CheckCircle2, Database, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

// License Badge Component
const LicenseBadge = ({ type = 'cc-by' }) => {
  const licenses = {
    'cc-by': {
      name: 'CC BY',
      description: 'Creative Commons Attribution - Commercial use allowed with attribution',
      commercial: true,
      color: 'bg-green-500/30 text-green-300 border-green-400/50'
    }
  };
  
  const license = licenses[type];
  
  return (
    <div className="flex items-center gap-1.5" title={license.description}>
      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-bold ${license.color} backdrop-blur-sm border`}>
        {license.name}
      </span>
      {license.commercial && (
        <ShieldCheck className="w-4 h-4 text-green-400" title="Commercial use allowed" />
      )}
    </div>
  );
};

const VideoCard = ({ video }) => (
  <Link to={`/video/${video.id}`} data-testid="video-card">
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.03, y: -8 }}
      className="glass-card overflow-hidden hover:border-white/20 transition-all group"
    >
      <div className="relative aspect-video bg-zinc-900">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Play className="w-16 h-16 text-[#BEF264]" fill="#BEF264" />
        </div>
        <div className="absolute top-3 left-3">
          <LicenseBadge type="cc-by" />
        </div>
        <div className="absolute top-3 right-3">
          <span className="viral-badge flex items-center space-x-1">
            <TrendingUp className="w-3 h-3" />
            <span>{video.viral_score}</span>
          </span>
        </div>
      </div>
      <div className="p-4">
        <h3 className="text-white font-semibold line-clamp-2 mb-2 text-sm">{video.title}</h3>
        <p className="text-zinc-500 text-xs mb-3">{video.channel}</p>
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-3 text-zinc-600">
            <span>{(video.views || 0).toLocaleString()} views</span>
            <span>{(video.likes || 0).toLocaleString()} likes</span>
          </div>
          <span className="text-zinc-600">
            {Math.floor((video.duration || 0) / 60)}:{String((video.duration || 0) % 60).padStart(2, '0')}
          </span>
        </div>
      </div>
    </motion.div>
  </Link>
);

export const Discover = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [minViews, setMinViews] = useState(1000);
  const [maxResults, setMaxResults] = useState(50);

  const handleSearch = async () => {
    if (!searchQuery.trim() && videos.length > 0) return;
    
    setLoading(true);
    try {
      const response = await api.get('/discover', {
        params: {
          query: searchQuery,
          max_results: maxResults,
          min_views: minViews
        }
      });
      setVideos(response.data.videos);
      
      // Show appropriate message based on response
      if (response.data.cached) {
        toast.info(response.data.message || 'Showing cached results');
      } else {
        toast.success(`Found ${response.data.total} videos!`);
      }
    } catch (error) {
      console.error('Error discovering videos:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to discover videos';
      
      if (error.response?.status === 429) {
        toast.error('YouTube API quota exceeded. Please try again tomorrow or contact support for a new API key.');
      } else {
        toast.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch();
  }, []);

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
          Discover Content
        </h1>
        <p className="text-zinc-500">Find viral CC BY licensed YouTube videos</p>
      </div>

      {/* License Info Banner */}
      <div className="glass-card p-4 mb-6 border-l-4 border-green-500">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-green-500/20 rounded-lg">
            <ShieldCheck className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-white">All Videos Are Commercial-Safe</span>
              <CheckCircle2 className="w-4 h-4 text-green-400" />
            </div>
            <p className="text-xs text-zinc-400">
              Videos shown are licensed under <span className="text-green-400 font-semibold">CC BY (Creative Commons Attribution)</span>. 
              You can use them commercially with proper attribution to the original creator.
            </p>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-zinc-800 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-zinc-400">Commercial Use</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-zinc-400">Modifications Allowed</span>
          </div>
          <div className="flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-zinc-400">Attribution Required</span>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="glass-card p-6 mb-8">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative flex gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
                <Input
                  data-testid="search-input"
                  type="text"
                  placeholder="Search for creative commons content... (e.g., 'cooking tutorial', 'music', 'nature')"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="pl-12 bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white placeholder:text-zinc-600 h-12"
                />
              </div>
              <Button
                data-testid="find-button"
                onClick={handleSearch}
                disabled={loading}
                className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-xl px-6 h-12"
              >
                Find
              </Button>
            </div>
            <Button
              data-testid="search-button"
              onClick={handleSearch}
              disabled={loading}
              className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-8 py-3 shadow-[0_0_15px_rgba(190,242,100,0.3)] hover:shadow-[0_0_25px_rgba(190,242,100,0.5)] transition-all h-12 sm:hidden"
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
          </div>
          
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t border-zinc-800">
            <div className="flex-1">
              <label className="text-xs text-zinc-500 mb-2 block">Minimum Views</label>
              <select
                value={minViews}
                onChange={(e) => setMinViews(parseInt(e.target.value))}
                className="w-full bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white h-10 px-3"
              >
                <option value="0">Any views</option>
                <option value="1000">1,000+ views</option>
                <option value="5000">5,000+ views</option>
                <option value="10000">10,000+ views</option>
                <option value="50000">50,000+ views</option>
                <option value="100000">100,000+ views</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs text-zinc-500 mb-2 block">Max Results</label>
              <select
                value={maxResults}
                onChange={(e) => setMaxResults(parseInt(e.target.value))}
                className="w-full bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white h-10 px-3"
              >
                <option value="20">20 videos</option>
                <option value="50">50 videos</option>
                <option value="100">100 videos</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[#BEF264] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-zinc-500">Discovering CC BY videos...</p>
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && videos.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-500">
              Found <span className="text-[#BEF264] font-bold">{videos.length}</span> CC BY licensed videos
            </p>
            <div className="flex items-center gap-2 text-xs text-green-400">
              <ShieldCheck className="w-4 h-4" />
              <span>All commercial-safe</span>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && videos.length === 0 && (
        <div className="glass-card p-20 text-center">
          <Search className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">No CC BY Videos Found</h3>
          <p className="text-zinc-500 mb-6">Search for a topic to discover Creative Commons licensed content</p>
          <div className="flex flex-wrap justify-center gap-2">
            {['Nature', 'Music', 'Cooking', 'Technology', 'Education'].map((term) => (
              <Button
                key={term}
                onClick={() => {
                  setSearchQuery(term.toLowerCase());
                  setTimeout(() => handleSearch(), 100);
                }}
                variant="outline"
                className="rounded-full border-zinc-700 text-zinc-400 hover:bg-zinc-800"
              >
                {term}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Discover;
