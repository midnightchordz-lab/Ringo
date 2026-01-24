import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Play, FileText, Loader2, Copy, Download, X, ChevronLeft, ChevronRight } from 'lucide-react';
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
        const response = await api.get(`/video/transcript/${video.id}`);
        if (response.data.success) {
          setTranscript(response.data);
          toast.success(`Transcript loaded! ${response.data.word_count} words`);
        } else {
          setError(response.data.error || 'Failed to get transcript');
        }
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to fetch transcript');
      } finally {
        setLoading(false);
      }
    };
    fetchTranscript();
  }, [video.id]);

  const copyToClipboard = () => {
    if (transcript?.full_text) {
      navigator.clipboard.writeText(transcript.full_text);
      toast.success('Copied to clipboard');
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
      toast.success('Downloaded');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.95 }}
        className="bg-white dark:bg-slate-900 rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">Transcript</h3>
            <p className="text-xs text-slate-500 line-clamp-1">{video.title}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[55vh]">
          {loading ? (
            <div className="flex flex-col items-center py-12">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mb-3" />
              <p className="text-sm text-slate-500">Fetching transcript...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-sm text-slate-500">{error.includes('blocking') ? 'Transcript temporarily unavailable' : 'No transcript available'}</p>
            </div>
          ) : transcript ? (
            <div className="space-y-3">
              <div className="flex gap-4 text-xs text-slate-500">
                <span>{transcript.word_count} words</span>
                <span>{transcript.language}</span>
              </div>
              <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 text-sm leading-relaxed whitespace-pre-wrap">
                {transcript.full_text}
              </div>
            </div>
          ) : null}
        </div>

        {transcript && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex gap-2">
            <Button variant="outline" size="sm" onClick={copyToClipboard} className="flex-1">
              <Copy className="w-4 h-4 mr-2" /> Copy
            </Button>
            <Button variant="outline" size="sm" onClick={downloadTranscript} className="flex-1">
              <Download className="w-4 h-4 mr-2" /> Download
            </Button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
};

const VideoCard = ({ video, onTranscribe }) => (
  <div className="clean-card clean-card-hover overflow-hidden group" data-testid="video-card">
    <Link to={`/video/${video.id}`}>
      <div className="relative aspect-video bg-slate-100 dark:bg-slate-800">
        <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
          <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
            <Play className="w-5 h-5 text-slate-900 ml-0.5" fill="currentColor" />
          </div>
        </div>
        <span className="absolute top-2 left-2 badge badge-success text-xs">CC BY</span>
      </div>
    </Link>
    <div className="p-3">
      <Link to={`/video/${video.id}`}>
        <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 mb-1 hover:text-indigo-600 transition-colors">
          {video.title}
        </h3>
      </Link>
      <p className="text-xs text-slate-500 mb-2">{video.channel}</p>
      <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
        <span>{(video.views || 0).toLocaleString()} views</span>
        <span>{Math.floor((video.duration || 0) / 60)}:{String((video.duration || 0) % 60).padStart(2, '0')}</span>
      </div>
      <button
        onClick={(e) => { e.preventDefault(); onTranscribe(video); }}
        className="w-full py-2 text-xs font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 rounded-lg transition-colors flex items-center justify-center gap-1.5"
        data-testid="transcribe-button"
      >
        <FileText className="w-3.5 h-3.5" /> Get Transcript
      </button>
    </div>
  </div>
);

export const Discover = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [nextPageToken, setNextPageToken] = useState(null);
  const [prevPageToken, setPrevPageToken] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [transcriptVideo, setTranscriptVideo] = useState(null);

  const handleSearch = async (pageToken = null) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        query: searchQuery || 'tutorial',
        max_results: '20',
        min_views: '1000',
        sort_by: 'viewCount',
      });
      if (pageToken) params.append('page_token', pageToken);

      const response = await api.get(`/discover?${params}`);
      setVideos(response.data.videos || []);
      setNextPageToken(response.data.next_page_token);
      setPrevPageToken(response.data.prev_page_token);
      
      if (response.data.videos?.length > 0) {
        toast.success(`Found ${response.data.videos.length} videos`);
      }
    } catch (error) {
      toast.error('Failed to fetch videos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch();
  }, []);

  const handleNextPage = () => {
    if (nextPageToken) {
      setCurrentPage(p => p + 1);
      handleSearch(nextPageToken);
      window.scrollTo(0, 0);
    }
  };

  const handlePrevPage = () => {
    if (prevPageToken && currentPage > 1) {
      setCurrentPage(p => p - 1);
      handleSearch(prevPageToken);
      window.scrollTo(0, 0);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto" data-testid="discover-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Videos</h1>
        <p className="text-slate-500 text-sm">Search CC-licensed YouTube videos</p>
      </div>

      {/* Search */}
      <div className="mb-6">
        <form onSubmit={(e) => { e.preventDefault(); setCurrentPage(1); handleSearch(); }} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search videos..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 clean-input"
              data-testid="search-input"
            />
          </div>
          <Button type="submit" disabled={loading} className="btn-primary" data-testid="search-button">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
          </Button>
        </form>
      </div>

      {/* Video Grid */}
      {loading && videos.length === 0 ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      ) : videos.length > 0 ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {videos.map((video) => (
              <VideoCard key={video.id} video={video} onTranscribe={setTranscriptVideo} />
            ))}
          </div>

          {/* Pagination */}
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevPage}
              disabled={!prevPageToken || currentPage === 1}
              className="btn-secondary"
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Previous
            </Button>
            <span className="flex items-center px-3 text-sm text-slate-500">Page {currentPage}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={!nextPageToken}
              className="btn-secondary"
            >
              Next <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </>
      ) : (
        <div className="text-center py-20">
          <p className="text-slate-500">No videos found. Try a different search.</p>
        </div>
      )}

      {/* Transcript Modal */}
      <AnimatePresence>
        {transcriptVideo && (
          <TranscriptModal video={transcriptVideo} onClose={() => setTranscriptVideo(null)} />
        )}
      </AnimatePresence>
    </div>
  );
};

export default Discover;
