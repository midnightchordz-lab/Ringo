import { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, Video, Upload, BarChart3, Play } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StatCard = ({ icon: Icon, label, value, trend, color = 'text-[#BEF264]' }) => (
  <motion.div
    whileHover={{ scale: 1.02, y: -4 }}
    className="glass-card p-6 hover:border-white/20 transition-all"
    data-testid={`stat-card-${label.toLowerCase().replace(/\s/g, '-')}`}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="text-zinc-500 text-sm mb-2">{label}</p>
        <h3 className={`text-3xl font-bold ${color}`} style={{ fontFamily: 'Oswald, sans-serif' }}>
          {value}
        </h3>
        {trend && (
          <p className="text-xs text-zinc-600 mt-2">
            {trend}
          </p>
        )}
      </div>
      <div className="p-3 bg-zinc-800/50 rounded-xl">
        <Icon className={`w-6 h-6 ${color}`} strokeWidth={1.5} />
      </div>
    </div>
  </motion.div>
);

const VideoCard = ({ video }) => (
  <Link to={`/video/${video.id}`} data-testid="top-video-card">
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="glass-card overflow-hidden hover:border-white/20 transition-all group"
    >
      <div className="relative aspect-video bg-zinc-900">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Play className="w-12 h-12 text-white" fill="white" />
        </div>
        <div className="absolute top-3 right-3">
          <span className="viral-badge">{video.viral_score}</span>
        </div>
      </div>
      <div className="p-4">
        <h4 className="text-white font-semibold line-clamp-2 mb-2">{video.title}</h4>
        <p className="text-zinc-500 text-sm">{video.channel}</p>
        <div className="flex items-center justify-between mt-3 text-xs text-zinc-600">
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#BEF264] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
          Dashboard
        </h1>
        <p className="text-zinc-500">Your viral content command center</p>
      </div>

      {/* Stats Grid - Bento Layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Video}
          label="Videos Discovered"
          value={stats?.total_videos_discovered || 0}
          color="text-[#BEF264]"
        />
        <StatCard
          icon={TrendingUp}
          label="Clips Generated"
          value={stats?.total_clips_generated || 0}
          color="text-purple-400"
        />
        <StatCard
          icon={Upload}
          label="Posts Published"
          value={stats?.total_posts_published || 0}
          color="text-pink-400"
        />
        <StatCard
          icon={BarChart3}
          label="Avg Viral Score"
          value={stats?.top_videos?.[0]?.viral_score?.toFixed(1) || '0.0'}
          color="text-yellow-400"
        />
      </div>

      {/* Top Videos Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Oswald, sans-serif' }}>
            Top Viral Videos
          </h2>
          <Link to="/discover">
            <Button
              data-testid="discover-more-button"
              className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-6 py-2 shadow-[0_0_15px_rgba(190,242,100,0.3)] hover:shadow-[0_0_25px_rgba(190,242,100,0.5)] transition-all"
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
            <Video className="w-16 h-16 text-zinc-700 mx-auto mb-4" strokeWidth={1.5} />
            <p className="text-zinc-500 mb-4">No videos discovered yet</p>
            <Link to="/discover">
              <Button
                data-testid="start-discovering-button"
                className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-6 py-2"
              >
                Start Discovering
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-6" style={{ fontFamily: 'Oswald, sans-serif' }}>
          Recent Posts
        </h2>
        {stats?.recent_posts && stats.recent_posts.length > 0 ? (
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-zinc-800">
                    <th className="text-left p-4 text-zinc-500 font-medium text-sm">Platform</th>
                    <th className="text-left p-4 text-zinc-500 font-medium text-sm">Caption</th>
                    <th className="text-left p-4 text-zinc-500 font-medium text-sm">Posted</th>
                    <th className="text-left p-4 text-zinc-500 font-medium text-sm">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_posts.map((post) => (
                    <tr key={post.post_id} className="border-b border-zinc-800/50 hover:bg-white/5 transition-colors">
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-800 text-white">
                          {post.platform}
                        </span>
                      </td>
                      <td className="p-4 text-zinc-300 max-w-md truncate">{post.caption}</td>
                      <td className="p-4 text-zinc-500 text-sm">
                        {new Date(post.posted_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
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
            <Upload className="w-16 h-16 text-zinc-700 mx-auto mb-4" strokeWidth={1.5} />
            <p className="text-zinc-500">No posts published yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;