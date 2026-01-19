import { useState, useEffect } from 'react';
import api from '../utils/api';
import { TrendingUp, Video, Upload, BarChart3, Play, Trash2, AlertCircle, Zap, Star, Search } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const StatCard = ({ icon: Icon, label, value, trend, gradient }) => (
  <motion.div
    whileHover={{ scale: 1.05, y: -8 }}
    className={`stat-card card-hover ${gradient}`}
    data-testid={`stat-card-${label.toLowerCase().replace(/\s/g, '-')}`}
  >
    <div className="relative z-10">
      <div className="flex items-start justify-between mb-3">
        <div className="p-3 bg-white/80 backdrop-blur-sm rounded-xl shadow-lg">
          <Icon className="w-7 h-7 text-violet-600" strokeWidth={2.5} />
        </div>
        <Zap className="w-5 h-5 text-amber-400" fill="currentColor" />
      </div>
      <p className="text-slate-600 text-sm mb-1 font-semibold uppercase tracking-wider">{label}</p>
      <h3 className="text-4xl font-black text-slate-900 mb-2" style={{ fontFamily: 'Sora, sans-serif' }}>
        {value}
      </h3>
      {trend && (
        <p className="text-xs text-slate-500 font-medium">
          {trend}
        </p>
      )}
    </div>
  </motion.div>
);

const VideoCard = ({ video }) => (
  <Link to={`/video/${video.id}`} data-testid="top-video-card">
    <motion.div
      whileHover={{ scale: 1.05, y: -8 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card card-hover overflow-hidden group"
    >
      <div className="relative aspect-video bg-gradient-to-br from-violet-200 to-purple-200">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center justify-center">
          <motion.div
            initial={{ scale: 0 }}
            whileHover={{ scale: 1 }}
            className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-2xl"
          >
            <Play className="w-8 h-8 text-violet-600 ml-1" fill="currentColor" />
          </motion.div>
        </div>
        <div className="absolute top-3 left-3">
          <span className="cc-badge backdrop-blur-md">
            CC BY
          </span>
        </div>
        <div className="absolute top-3 right-3">
          <div className="viral-badge flex items-center space-x-1 backdrop-blur-md">
            <Star className="w-3 h-3" fill="currentColor" />
            <span>{video.viral_score}</span>
          </div>
        </div>
      </div>
      <div className="p-4 bg-gradient-to-br from-white/90 to-violet-50/50">
        <h4 className="text-slate-900 font-bold line-clamp-2 mb-2 leading-snug">{video.title}</h4>
        <p className="text-violet-600 text-sm font-semibold mb-3">{video.channel}</p>
        <div className="flex items-center justify-between text-xs font-medium">
          <span className="text-slate-600">{(video.views || 0).toLocaleString()} views</span>
          <span className="text-slate-500">{Math.floor((video.duration || 0) / 60)}:{String((video.duration || 0) % 60).padStart(2, '0')}</span>
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
      const response = await api.get('/stats');
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
      const response = await api.post('/clear-videos');
      toast.success(response.data.message);
      setShowClearModal(false);
      fetchStats();
    } catch (error) {
      console.error('Error clearing videos:', error);
      toast.error('Failed to clear videos');
    } finally {
      setClearing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-20 h-20 gradient-primary rounded-3xl animate-spin mb-4 mx-auto flex items-center justify-center">
            <div className="w-16 h-16 bg-gradient-to-br from-violet-50 via-sky-50 to-pink-50 rounded-2xl"></div>
          </div>
          <p className="text-slate-700 font-semibold text-lg">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-24 lg:pb-8">
      {/* Header */}
      <div className="mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-5xl sm:text-6xl font-black mb-2" 
            style={{ fontFamily: 'Sora, sans-serif' }}
          >
            <span className="bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
              Dashboard
            </span>
          </motion.h1>
          <p className="text-slate-600 text-lg font-medium">Your content command center ✨</p>
        </div>
        {stats?.total_videos_discovered > 0 && (
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              data-testid="clear-videos-button"
              onClick={() => setShowClearModal(true)}
              className="gradient-secondary text-white font-bold rounded-xl px-6 py-3 shadow-lg shadow-red-500/30 hover:shadow-xl hover:shadow-red-500/40"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Videos
            </Button>
          </motion.div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Video}
          label="Videos Found"
          value={stats?.total_videos_discovered || 0}
          gradient="bg-gradient-to-br from-violet-100 to-purple-100"
        />
        <StatCard
          icon={TrendingUp}
          label="Clips Made"
          value={stats?.total_clips_generated || 0}
          gradient="bg-gradient-to-br from-cyan-100 to-blue-100"
        />
        <StatCard
          icon={Upload}
          label="Posts Live"
          value={stats?.total_posts_published || 0}
          gradient="bg-gradient-to-br from-pink-100 to-rose-100"
        />
        <StatCard
          icon={BarChart3}
          label="Viral Score"
          value={stats?.top_videos?.[0]?.viral_score?.toFixed(1) || '0.0'}
          gradient="bg-gradient-to-br from-amber-100 to-orange-100"
        />
      </div>

      {/* Top Videos Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Sora, sans-serif' }}>
            🔥 Top Viral Videos
          </h2>
          <Link to="/discover">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                data-testid="discover-more-button"
                className="gradient-accent text-white font-bold rounded-xl px-8 py-3 shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40"
              >
                <Search className="w-4 h-4 mr-2" />
                Discover More
              </Button>
            </motion.div>
          </Link>
        </div>

        {stats?.top_videos && stats.top_videos.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
            {stats.top_videos.map((video, index) => (
              <motion.div
                key={video.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <VideoCard video={video} />
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="glass-card p-16 text-center bg-gradient-to-br from-violet-50 to-purple-50">
            <div className="w-24 h-24 mx-auto mb-6 gradient-primary rounded-3xl flex items-center justify-center shadow-xl">
              <Video className="w-12 h-12 text-white" strokeWidth={2} />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">No videos yet!</h3>
            <p className="text-slate-600 mb-6 text-lg">Start discovering amazing CC content</p>
            <Link to="/discover">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  data-testid="start-discovering-button"
                  className="gradient-primary text-white font-bold rounded-xl px-8 py-4 text-lg shadow-xl shadow-violet-500/30"
                >
                  Start Discovering ✨
                </Button>
              </motion.div>
            </Link>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-3xl font-bold text-slate-900 mb-6" style={{ fontFamily: 'Sora, sans-serif' }}>
          📊 Recent Posts
        </h2>
        {stats?.recent_posts && stats.recent_posts.length > 0 ? (
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-violet-100 to-purple-100">
                  <tr className="border-b-2 border-violet-200">
                    <th className="text-left p-4 text-violet-700 font-bold text-sm">Platform</th>
                    <th className="text-left p-4 text-violet-700 font-bold text-sm">Caption</th>
                    <th className="text-left p-4 text-violet-700 font-bold text-sm">Posted</th>
                    <th className="text-left p-4 text-violet-700 font-bold text-sm">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_posts.map((post) => (
                    <tr key={post.post_id} className="border-b border-violet-100 hover:bg-violet-50/50 transition-colors">
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-bold gradient-accent text-white shadow-sm">
                          {post.platform}
                        </span>
                      </td>
                      <td className="p-4 text-slate-700 font-medium max-w-md truncate">{post.caption}</td>
                      <td className="p-4 text-slate-600 text-sm font-medium">
                        {new Date(post.posted_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-emerald-400 to-green-500 text-white shadow-sm">
                          ✓ {post.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="glass-card p-16 text-center bg-gradient-to-br from-pink-50 to-rose-50">
            <div className="w-24 h-24 mx-auto mb-6 gradient-secondary rounded-3xl flex items-center justify-center shadow-xl">
              <Upload className="w-12 h-12 text-white" strokeWidth={2} />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">No posts yet!</h3>
            <p className="text-slate-600 text-lg">Your published content will appear here</p>
          </div>
        )}
      </div>

      {/* Clear Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowClearModal(false)}>
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="glass-card p-8 max-w-md w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start space-x-4">
              <div className="w-14 h-14 bg-gradient-to-br from-red-400 to-pink-500 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg">
                <AlertCircle className="w-7 h-7 text-white" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <h3 className="text-2xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Sora, sans-serif' }}>Clear All Videos?</h3>
                <p className="text-slate-600 mb-6 font-medium">
                  This will remove all <span className="font-bold text-violet-600">{stats?.total_videos_discovered}</span> discovered videos. This action cannot be undone.
                </p>
                <div className="flex space-x-3">
                  <Button
                    onClick={() => setShowClearModal(false)}
                    className="flex-1 bg-slate-200 text-slate-700 hover:bg-slate-300 font-bold rounded-xl py-3"
                    disabled={clearing}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleClearVideos}
                    disabled={clearing}
                    className="flex-1 gradient-secondary text-white font-bold rounded-xl py-3 shadow-lg shadow-red-500/30"
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
