import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Filter, Play, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

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
        <div className="absolute top-3 left-3 flex gap-2">
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-bold bg-green-500/30 text-green-300 border border-green-400/50 backdrop-blur-sm">
            CC BY
          </span>
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
      toast.success(`Found ${response.data.total} videos!`);
    } catch (error) {
      console.error('Error discovering videos:', error);
      toast.error('Failed to discover videos');
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

      {/* Search Bar */}
      <div className="glass-card p-6 mb-8">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row gap-4">
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
              data-testid="search-button"
              onClick={handleSearch}
              disabled={loading}
              className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-8 py-3 shadow-[0_0_15px_rgba(190,242,100,0.3)] hover:shadow-[0_0_25px_rgba(190,242,100,0.5)] transition-all h-12"
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
            <p className="text-zinc-500">Discovering viral content...</p>
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && videos.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <p className="text-zinc-500">
              Found <span className="text-[#BEF264] font-bold">{videos.length}</span> videos
            </p>
            <div className="flex items-center space-x-2 text-sm text-zinc-600">
              <Filter className="w-4 h-4" />
              <span>Sorted by viral score</span>
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
          <h3 className="text-xl font-bold text-white mb-2">Start Discovering</h3>
          <p className="text-zinc-500 mb-6">Search for creative commons content or browse trending videos</p>
          <Button
            data-testid="browse-button"
            onClick={handleSearch}
            className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-6 py-2"
          >
            Browse Trending
          </Button>
        </div>
      )}
    </div>
  );
};

export default Discover;