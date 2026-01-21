import { useState, useEffect } from 'react';
import api from '../utils/api';
import { TrendingUp, Video, Upload, BarChart3, Play, Trash2, AlertCircle, Zap, Star, Search, Sparkles, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const StatCard = ({ icon: Icon, label, value, color, trend }) => {
  const colorClasses = {
    blue: { bg: 'bg-blue-50 dark:bg-blue-900/20', icon: 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400', border: 'border-blue-100 dark:border-blue-800' },
    coral: { bg: 'bg-red-50 dark:bg-red-900/20', icon: 'bg-red-100 dark:bg-red-900/40 text-red-500 dark:text-red-400', border: 'border-red-100 dark:border-red-800' },
    purple: { bg: 'bg-purple-50 dark:bg-purple-900/20', icon: 'bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400', border: 'border-purple-100 dark:border-purple-800' },
    yellow: { bg: 'bg-amber-50 dark:bg-amber-900/20', icon: 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400', border: 'border-amber-100 dark:border-amber-800' },
  };
  const classes = colorClasses[color] || colorClasses.blue;

  return (
    <motion.div
      whileHover={{ y: -4 }}
      className={`studio-card studio-card-hover p-6 ${classes.bg} border ${classes.border}`}
      data-testid={`stat-card-${label.toLowerCase().replace(/\s/g, '-')}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${classes.icon}`}>
          <Icon className="w-6 h-6" strokeWidth={2} />
        </div>
        {trend && (
          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/40 px-2 py-1 rounded-full">
            {trend}
          </span>
        )}
      </div>
      <p className="text-neutral-500 dark:text-neutral-400 text-sm font-medium mb-1">{label}</p>
      <h3 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100" style={{ fontFamily: 'Outfit, sans-serif' }}>
        {value}
      </h3>
    </motion.div>
  );
};

const VideoCard = ({ video }) => (
  <Link to={`/video/${video.id}`} data-testid="top-video-card">
    <motion.div
      whileHover={{ y: -8 }}
      className="studio-card studio-card-hover overflow-hidden group"
    >
      <div className="relative aspect-video bg-neutral-100 dark:bg-neutral-800">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="w-14 h-14 bg-white dark:bg-neutral-800 rounded-full flex items-center justify-center shadow-xl">
            <Play className="w-6 h-6 text-blue-600 dark:text-blue-400 ml-1" fill="currentColor" />
          </div>
        </div>
        <div className="absolute top-3 left-3">
          <span className="bg-emerald-500 text-white text-xs font-bold px-2.5 py-1 rounded-lg shadow-lg">
            CC BY
          </span>
        </div>
        <div className="absolute top-3 right-3">
          <div className="bg-gradient-to-r from-red-500 to-orange-500 text-white text-xs font-bold px-2.5 py-1 rounded-lg shadow-lg flex items-center gap-1">
            <Star className="w-3 h-3" fill="currentColor" />
            {video.viral_score}
          </div>
        </div>
      </div>
      <div className="p-4">
        <h4 className="text-neutral-900 font-semibold line-clamp-2 mb-2 leading-tight">{video.title}</h4>
        <p className="text-blue-600 text-sm font-medium mb-2">{video.channel}</p>
        <div className="flex items-center justify-between text-xs text-neutral-500">
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
  const user = JSON.parse(localStorage.getItem('user') || '{}');

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
      <div className="flex items-center justify-center h-screen bg-neutral-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-neutral-600 font-medium">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 pb-24 lg:pb-8 bg-neutral-50 min-h-screen">
      {/* Welcome Header */}
      <div className="mb-8">
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4"
        >
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold text-neutral-900 mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Welcome back, <span className="text-gradient">{user.full_name?.split(' ')[0] || 'Creator'}</span>! 👋
            </h1>
            <p className="text-neutral-500 text-lg">Here's what's happening with your content today.</p>
          </div>
          <div className="flex gap-3">
            {stats?.total_videos_discovered > 0 && (
              <Button
                data-testid="clear-videos-button"
                onClick={() => setShowClearModal(true)}
                className="bg-red-50 text-red-600 hover:bg-red-100 font-semibold rounded-xl px-5 py-2.5 border border-red-200"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Clear Videos
              </Button>
            )}
            <Link to="/discover">
              <Button className="btn-primary">
                <Search className="w-4 h-4 mr-2" />
                Discover Videos
              </Button>
            </Link>
          </div>
        </motion.div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6 mb-8">
        <StatCard
          icon={Video}
          label="Videos Found"
          value={stats?.total_videos_discovered || 0}
          color="blue"
        />
        <StatCard
          icon={TrendingUp}
          label="Clips Made"
          value={stats?.total_clips_generated || 0}
          color="purple"
        />
        <StatCard
          icon={Upload}
          label="Posts Live"
          value={stats?.total_posts_published || 0}
          color="coral"
        />
        <StatCard
          icon={BarChart3}
          label="Top Viral Score"
          value={stats?.top_videos?.[0]?.viral_score?.toFixed(1) || '0.0'}
          color="yellow"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Link to="/discover" className="block">
          <motion.div 
            whileHover={{ y: -4 }}
            className="studio-card p-6 bg-gradient-to-br from-blue-500 to-indigo-600 text-white"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-lg mb-1">Find Videos</h3>
                <p className="text-blue-100 text-sm">Discover CC licensed content</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Video className="w-6 h-6" />
              </div>
            </div>
          </motion.div>
        </Link>
        
        <Link to="/images" className="block">
          <motion.div 
            whileHover={{ y: -4 }}
            className="studio-card p-6 bg-gradient-to-br from-purple-500 to-pink-600 text-white"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-lg mb-1">Browse Images</h3>
                <p className="text-purple-100 text-sm">Free stock photos</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Sparkles className="w-6 h-6" />
              </div>
            </div>
          </motion.div>
        </Link>
        
        <Link to="/library" className="block">
          <motion.div 
            whileHover={{ y: -4 }}
            className="studio-card p-6 bg-gradient-to-br from-emerald-500 to-green-600 text-white"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-lg mb-1">Content Library</h3>
                <p className="text-emerald-100 text-sm">Educational resources</p>
              </div>
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <ArrowRight className="w-6 h-6" />
              </div>
            </div>
          </motion.div>
        </Link>
      </div>

      {/* Top Videos Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-neutral-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
            🔥 Top Viral Videos
          </h2>
          <Link to="/discover" className="text-blue-600 hover:text-blue-700 font-semibold text-sm flex items-center gap-1">
            View All <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {stats?.top_videos && stats.top_videos.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-5">
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
          <div className="studio-card p-12 text-center">
            <div className="w-20 h-20 mx-auto mb-6 bg-blue-100 rounded-2xl flex items-center justify-center">
              <Video className="w-10 h-10 text-blue-600" />
            </div>
            <h3 className="text-xl font-bold text-neutral-900 mb-2">No videos discovered yet</h3>
            <p className="text-neutral-500 mb-6">Start exploring CC licensed content to build your library</p>
            <Link to="/discover">
              <Button className="btn-primary">
                <Search className="w-4 h-4 mr-2" />
                Start Discovering
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 mb-6" style={{ fontFamily: 'Outfit, sans-serif' }}>
          📊 Recent Activity
        </h2>
        {stats?.recent_posts && stats.recent_posts.length > 0 ? (
          <div className="studio-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-neutral-50 border-b border-neutral-200">
                  <tr>
                    <th className="text-left p-4 text-neutral-600 font-semibold text-sm">Platform</th>
                    <th className="text-left p-4 text-neutral-600 font-semibold text-sm">Caption</th>
                    <th className="text-left p-4 text-neutral-600 font-semibold text-sm">Posted</th>
                    <th className="text-left p-4 text-neutral-600 font-semibold text-sm">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_posts.map((post) => (
                    <tr key={post.post_id} className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
                      <td className="p-4">
                        <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-xs font-semibold">
                          {post.platform}
                        </span>
                      </td>
                      <td className="p-4 text-neutral-700 max-w-md truncate">{post.caption}</td>
                      <td className="p-4 text-neutral-500 text-sm">
                        {new Date(post.posted_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-semibold">
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
          <div className="studio-card p-12 text-center bg-neutral-50">
            <div className="w-20 h-20 mx-auto mb-6 bg-purple-100 rounded-2xl flex items-center justify-center">
              <Upload className="w-10 h-10 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-neutral-900 mb-2">No activity yet</h3>
            <p className="text-neutral-500">Your published content will appear here</p>
          </div>
        )}
      </div>

      {/* Clear Confirmation Modal */}
      {showClearModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowClearModal(false)}>
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="studio-card p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <AlertCircle className="w-6 h-6 text-red-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-neutral-900 mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>Clear All Videos?</h3>
                <p className="text-neutral-600 mb-6">
                  This will remove all <span className="font-bold text-blue-600">{stats?.total_videos_discovered}</span> discovered videos. This action cannot be undone.
                </p>
                <div className="flex gap-3">
                  <Button
                    onClick={() => setShowClearModal(false)}
                    className="flex-1 bg-neutral-100 text-neutral-700 hover:bg-neutral-200 font-semibold rounded-xl"
                    disabled={clearing}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleClearVideos}
                    disabled={clearing}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl"
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
