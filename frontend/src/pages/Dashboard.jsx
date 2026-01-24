import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Video, Image, BookOpen, Clock, ArrowRight, Search } from 'lucide-react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '../context/AuthContext';

const StatCard = ({ icon: Icon, label, value, href }) => (
  <Link to={href}>
    <motion.div
      whileHover={{ y: -2 }}
      className="clean-card clean-card-hover p-5 cursor-pointer"
      data-testid={`stat-card-${label.toLowerCase().replace(/\s/g, '-')}`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">{label}</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
        </div>
        <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <Icon className="w-5 h-5 text-slate-600 dark:text-slate-400" />
        </div>
      </div>
    </motion.div>
  </Link>
);

const QuickAction = ({ icon: Icon, title, description, href, color }) => {
  const colorMap = {
    indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400',
    emerald: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400',
    amber: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400',
  };
  
  return (
    <Link to={href}>
      <motion.div
        whileHover={{ y: -2 }}
        className="clean-card clean-card-hover p-5 h-full"
      >
        <div className={`w-10 h-10 rounded-lg ${colorMap[color]} flex items-center justify-center mb-4`}>
          <Icon className="w-5 h-5" />
        </div>
        <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">{title}</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
      </motion.div>
    </Link>
  );
};

const RecentVideo = ({ video }) => (
  <Link to={`/video/${video.id}`}>
    <motion.div
      whileHover={{ y: -2 }}
      className="clean-card clean-card-hover overflow-hidden"
    >
      <div className="aspect-video bg-slate-100 dark:bg-slate-800 relative">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-2 right-2">
          <span className="badge badge-success text-xs">CC BY</span>
        </div>
      </div>
      <div className="p-4">
        <h4 className="font-medium text-slate-900 dark:text-slate-100 line-clamp-1 text-sm">{video.title}</h4>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{video.channel}</p>
      </div>
    </motion.div>
  </Link>
);

export const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[80vh]">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const firstName = user?.full_name?.split(' ')[0] || 'there';

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto" data-testid="dashboard">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
          Welcome back, {firstName}
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Find copyright-free content for your projects
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={Video}
          label="Videos Found"
          value={stats?.total_videos_discovered || 0}
          href="/discover"
        />
        <StatCard
          icon={Image}
          label="Images Saved"
          value={stats?.total_favorite_images || 0}
          href="/images"
        />
        <StatCard
          icon={BookOpen}
          label="Resources"
          value={stats?.total_content_favorites || 0}
          href="/library"
        />
        <StatCard
          icon={Clock}
          label="Recent Activity"
          value={stats?.total_clips_generated || 0}
          href="/history"
        />
      </div>

      {/* Quick Actions */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickAction
            icon={Video}
            title="Find Videos"
            description="Search CC-licensed YouTube videos"
            href="/discover"
            color="indigo"
          />
          <QuickAction
            icon={Image}
            title="Browse Images"
            description="High-quality stock photos & illustrations"
            href="/images"
            color="emerald"
          />
          <QuickAction
            icon={BookOpen}
            title="Content Library"
            description="Articles, courses, and free books"
            href="/library"
            color="amber"
          />
        </div>
      </div>

      {/* Recent Videos */}
      {stats?.top_videos?.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Recent Videos</h2>
            <Link to="/discover" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {stats.top_videos.slice(0, 4).map((video) => (
              <RecentVideo key={video.id} video={video} />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!stats?.top_videos?.length && (
        <div className="clean-card p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Start discovering content
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-sm mx-auto">
            Search for copyright-free videos, images, and educational resources.
          </p>
          <Link to="/discover">
            <Button className="btn-primary">
              <Search className="w-4 h-4 mr-2" />
              Start Searching
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
