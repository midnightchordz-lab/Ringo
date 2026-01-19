import { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, Video, Upload, BarChart3, Play, Trash2, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StatCard = ({ icon: Icon, label, value, trend, color = 'text-indigo-600' }) => (
  <motion.div
    whileHover={{ scale: 1.02, y: -2 }}
    className="glass-card card-hover p-6"
    data-testid={`stat-card-${label.toLowerCase().replace(/\s/g, '-')}`}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="text-slate-600 text-sm mb-2 font-medium">{label}</p>
        <h3 className={`text-3xl font-bold ${color}`} style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          {value}
        </h3>
        {trend && (
          <p className="text-xs text-slate-500 mt-2">
            {trend}
          </p>
        )}
      </div>
      <div className="p-3 bg-slate-100 rounded-xl">
        <Icon className={`w-6 h-6 ${color}`} strokeWidth={2} />
      </div>
    </div>
  </motion.div>
);

const VideoCard = ({ video }) => (
  <Link to={`/video/${video.id}`} data-testid="top-video-card">
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="glass-card card-hover overflow-hidden group"
    >
      <div className="relative aspect-video bg-slate-100">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Play className="w-12 h-12 text-white" fill="white" />
        </div>
        <div className="absolute top-3 left-3">
          <span className="cc-badge">
            CC BY
          </span>
        </div>
        <div className="absolute top-3 right-3">
          <span className="viral-badge">{video.viral_score}</span>
        </div>
      </div>
      <div className="p-4">
        <h4 className="text-slate-900 font-semibold line-clamp-2 mb-2">{video.title}</h4>
        <p className="text-slate-600 text-sm">{video.channel}</p>
        <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
          <span>{(video.views || 0).toLocaleString()} views</span>
          <span>{Math.floor((video.duration || 0) / 60)}:{String((video.duration || 0) % 60).padStart(2, '0')}</span>
        </div>
      </div>
    </motion.div>
  </Link>
);

export const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showClearModal, setShowClearModal] = useState(false);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearVideos = async () => {
    setClearing(true);
    try {
      const response = await axios.post(`${API}/clear-videos`);
      toast.success(response.data.message);
      setShowClearModal(false);
      fetchStats(); // Refresh stats
    } catch (error) {
      console.error('Error clearing videos:', error);
      toast.error('Failed to clear videos');
    } finally {
      setClearing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Dashboard
          </h1>
          <p className="text-slate-600">Your content command center</p>
        </div>
        {stats?.total_videos_discovered > 0 && (
          <Button
            data-testid="clear-videos-button"
            onClick={() => setShowClearModal(true)}
            variant="outline"
            className="border-red-200 text-red-600 hover:bg-red-50 hover:border-red-300"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear Videos
          </Button>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Video}
          label="Videos Discovered"
          value={stats?.total_videos_discovered || 0}
          color="text-indigo-600"
        />
        <StatCard
          icon={TrendingUp}
          label="Clips Generated"
          value={stats?.total_clips_generated || 0}
          color="text-purple-600"
        />
        <StatCard
          icon={Upload}
          label="Posts Published"
          value={stats?.total_posts_published || 0}
          color="text-pink-600"
        />
        <StatCard
          icon={BarChart3}
          label="Avg Viral Score"
          value={stats?.top_videos?.[0]?.viral_score?.toFixed(1) || '0.0'}
          color="text-amber-600"
        />
      </div>

      {/* Top Videos Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Top Viral Videos
          </h2>
          <Link to="/discover">
            <Button
              data-testid="discover-more-button"
              className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 font-semibold rounded-lg px-6 py-2 shadow-sm"
            >
              Discover More
            </Button>
          </Link>
        </div>

        {stats?.top_videos && stats.top_videos.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
            {stats.top_videos.map((video) => (
              <VideoCard key={video.id} video={video} />
            ))}
          </div>
        ) : (
          <div className="glass-card p-12 text-center">
            <Video className="w-16 h-16 text-slate-300 mx-auto mb-4" strokeWidth={1.5} />
            <p className="text-slate-600 mb-4">No videos discovered yet</p>
            <Link to="/discover">
              <Button
                data-testid="start-discovering-button"
                className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 font-semibold rounded-lg px-6 py-2"
              >
                Start Discovering
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-6" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Recent Posts
        </h2>
        {stats?.recent_posts && stats.recent_posts.length > 0 ? (
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr className="border-b border-slate-200">
                    <th className="text-left p-4 text-slate-600 font-semibold text-sm">Platform</th>
                    <th className="text-left p-4 text-slate-600 font-semibold text-sm">Caption</th>
                    <th className="text-left p-4 text-slate-600 font-semibold text-sm">Posted</th>
                    <th className="text-left p-4 text-slate-600 font-semibold text-sm">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_posts.map((post) => (
                    <tr key={post.post_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                          {post.platform}
                        </span>
                      </td>
                      <td className="p-4 text-slate-700 max-w-md truncate">{post.caption}</td>
                      <td className="p-4 text-slate-600 text-sm">
                        {new Date(post.posted_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                          {post.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="glass-card p-12 text-center">
            <Upload className="w-16 h-16 text-slate-300 mx-auto mb-4" strokeWidth={1.5} />
            <p className="text-slate-600">No posts published yet</p>
          </div>
        )}
      </div>

      {/* Clear Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowClearModal(false)}>
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start space-x-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-slate-900 mb-2">Clear All Videos?</h3>
                <p className="text-slate-600 mb-6">
                  This will remove all {stats?.total_videos_discovered} discovered videos from your dashboard. This action cannot be undone.
                </p>
                <div className="flex space-x-3">
                  <Button
                    onClick={() => setShowClearModal(false)}
                    variant="outline"
                    className="flex-1"
                    disabled={clearing}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleClearVideos}
                    disabled={clearing}
                    className="flex-1 bg-red-600 text-white hover:bg-red-700"
                  >
                    {clearing ? 'Clearing...' : 'Clear Videos'}
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
