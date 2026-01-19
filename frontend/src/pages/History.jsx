import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Clock, Youtube, Instagram, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';

const platformIcons = {
  youtube: Youtube,
  instagram: Instagram,
};

const platformColors = {
  youtube: 'text-red-500 bg-red-500/20 border-red-500/30',
  instagram: 'text-pink-500 bg-pink-500/20 border-pink-500/30',
};

export const History = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await api.get('/history');
      setPosts(response.data.posts);
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#BEF264] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-500">Loading history...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
          Publishing History
        </h1>
        <p className="text-zinc-500">Track all your posted content</p>
      </div>

      {posts.length > 0 ? (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="text-left p-4 text-zinc-500 font-medium text-sm">Platform</th>
                  <th className="text-left p-4 text-zinc-500 font-medium text-sm">Caption</th>
                  <th className="text-left p-4 text-zinc-500 font-medium text-sm">Hashtags</th>
                  <th className="text-left p-4 text-zinc-500 font-medium text-sm">Posted</th>
                  <th className="text-left p-4 text-zinc-500 font-medium text-sm">Status</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post, index) => {
                  const Icon = platformIcons[post.platform.toLowerCase()] || Clock;
                  const colorClass = platformColors[post.platform.toLowerCase()] || 'text-zinc-500 bg-zinc-500/20';
                  
                  return (
                    <motion.tr
                      key={post.post_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      data-testid="history-row"
                      className="border-b border-zinc-800/50 hover:bg-white/5 transition-colors"
                    >
                      <td className="p-4">
                        <div className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg border ${colorClass}`}>
                          <Icon className="w-4 h-4" />
                          <span className="text-xs font-medium capitalize">{post.platform}</span>
                        </div>
                      </td>
                      <td className="p-4 text-zinc-300 max-w-md">
                        <p className="line-clamp-2">{post.caption}</p>
                      </td>
                      <td className="p-4 text-zinc-500 text-sm max-w-xs">
                        <p className="line-clamp-1">{post.hashtags || 'N/A'}</p>
                      </td>
                      <td className="p-4 text-zinc-500 text-sm">
                        {new Date(post.posted_at).toLocaleString()}
                      </td>
                      <td className="p-4">
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                          ✓ {post.status}
                        </span>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="glass-card p-20 text-center">
          <Clock className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">No Posts Yet</h3>
          <p className="text-zinc-500">Your publishing history will appear here</p>
        </div>
      )}
    </div>
  );
};

export default History;