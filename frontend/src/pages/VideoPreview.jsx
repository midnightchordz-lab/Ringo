import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Scissors, TrendingUp, Eye, ThumbsUp, MessageCircle, Calendar, PlayCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const YouTubePlayer = ({ videoId }) => {
  return (
    <div className="relative w-full h-full">
      <iframe
        src={`https://www.youtube.com/embed/${videoId}?modestbranding=1&rel=0`}
        title="YouTube video player"
        frameBorder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        className="absolute inset-0 w-full h-full"
      />
    </div>
  );
};

export const VideoPreview = () => {
  const { videoId } = useParams();
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startTime, setStartTime] = useState(0);
  const [clipDuration, setClipDuration] = useState(45);
  const [useAI, setUseAI] = useState(true);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [analyzingAI, setAnalyzingAI] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [caption, setCaption] = useState('');
  const [hashtags, setHashtags] = useState('#viral #trending');
  const [posting, setPosting] = useState(false);
  const [clipId, setClipId] = useState(null);

  useEffect(() => {
    fetchVideoDetails();
  }, [videoId]);

  const fetchVideoDetails = async () => {
    try {
      const response = await axios.get(`${API}/videos/${videoId}`);
      setVideo(response.data);
      setCaption(`Check out this amazing content! 🎬`);
    } catch (error) {
      console.error('Error fetching video:', error);
      toast.error('Failed to load video');
    } finally {
      setLoading(false);
    }
  };

  const handleAIAnalysis = async () => {
    setAnalyzingAI(true);
    try {
      const response = await axios.get(`${API}/clips/ai-analyze/${videoId}`);
      const analysis = response.data.analysis;
      setAiAnalysis(analysis);
      setStartTime(analysis.recommended_start);
      setClipDuration(analysis.recommended_duration);
      toast.success(`AI found the perfect moment: ${analysis.reasoning}`);
    } catch (error) {
      console.error('Error analyzing with AI:', error);
      toast.error('AI analysis failed, using default timing');
    } finally {
      setAnalyzingAI(false);
    }
  };

  const handleGenerateClip = async () => {
    setGenerating(true);
    try {
      const response = await axios.post(`${API}/clips/generate`, {
        video_id: videoId,
        start_time: startTime,
        duration: clipDuration,
        use_ai_analysis: useAI
      });
      setClipId(response.data.clip_id);
      toast.success(response.data.message);
    } catch (error) {
      console.error('Error generating clip:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate clip');
    } finally {
      setGenerating(false);
    }
  };

  const handlePost = async () => {
    if (!clipId) {
      toast.error('Please generate a clip first');
      return;
    }

    setPosting(true);
    try {
      await axios.post(`${API}/post`, {
        clip_id: clipId,
        caption: caption,
        platforms: ['youtube', 'instagram'],
        hashtags: hashtags
      });
      toast.success('Posted to social media!');
    } catch (error) {
      console.error('Error posting:', error);
      toast.error('Failed to post');
    } finally {
      setPosting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#BEF264] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-500">Loading video...</p>
        </div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-zinc-500">Video not found</p>
          <Link to="/discover">
            <Button className="mt-4">Back to Discover</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Back Button */}
      <Link to="/discover">
        <Button
          data-testid="back-button"
          variant="ghost"
          className="mb-6 text-zinc-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Discover
        </Button>
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Video Player */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card overflow-hidden">
            <div className="aspect-video bg-zinc-900 relative">
              <YouTubePlayer videoId={videoId} />
            </div>
          </div>

          {/* Video Info */}
          <div className="glass-card p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-bold bg-green-500/30 text-green-300 border border-green-400/50">
                    ✓ CC BY Licensed
                  </span>
                </div>
                <h1 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
                  {video.title}
                </h1>
                <p className="text-zinc-500">{video.channel}</p>
              </div>
              <span className="viral-badge flex items-center space-x-1 ml-4">
                <TrendingUp className="w-4 h-4" />
                <span>{video.viral_score}</span>
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
              <div className="flex items-center space-x-2 text-zinc-400">
                <Eye className="w-4 h-4" />
                <span className="text-sm">{(video.views || 0).toLocaleString()}</span>
              </div>
              <div className="flex items-center space-x-2 text-zinc-400">
                <ThumbsUp className="w-4 h-4" />
                <span className="text-sm">{(video.likes || 0).toLocaleString()}</span>
              </div>
              <div className="flex items-center space-x-2 text-zinc-400">
                <MessageCircle className="w-4 h-4" />
                <span className="text-sm">{(video.comments || 0).toLocaleString()}</span>
              </div>
              <div className="flex items-center space-x-2 text-zinc-400">
                <Calendar className="w-4 h-4" />
                <span className="text-sm">{video.upload_date}</span>
              </div>
            </div>

            {video.description && (
              <div className="border-t border-zinc-800 pt-4">
                <p className="text-zinc-400 text-sm line-clamp-3">{video.description}</p>
              </div>
            )}
          </div>
        </div>

        {/* Clip Generator Panel */}
        <div className="space-y-6">
          <div className="glass-card p-6">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center" style={{ fontFamily: 'Oswald, sans-serif' }}>
              <Scissors className="w-5 h-5 mr-2 text-[#BEF264]" />
              Generate Clip
            </h2>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-500 mb-2 block">Start Time (seconds)</label>
                <Input
                  data-testid="start-time-input"
                  type="number"
                  min="0"
                  max={video.duration || 0}
                  value={startTime}
                  onChange={(e) => setStartTime(parseInt(e.target.value) || 0)}
                  className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white"
                />
              </div>

              <div>
                <label className="text-sm text-zinc-500 mb-2 block">Clip Duration (seconds)</label>
                <Input
                  data-testid="clip-duration-input"
                  type="number"
                  min="10"
                  max="60"
                  value={clipDuration}
                  onChange={(e) => setClipDuration(parseInt(e.target.value) || 30)}
                  className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white"
                />
                <p className="text-xs text-zinc-600 mt-1">10-60 seconds recommended</p>
              </div>

              <Button
                data-testid="generate-clip-button"
                onClick={handleGenerateClip}
                disabled={generating}
                className="w-full bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full py-3"
              >
                {generating ? 'Generating...' : 'Generate Clip'}
              </Button>

              {clipId && (
                <div className="p-3 bg-green-500/20 border border-green-500/30 rounded-lg">
                  <p className="text-green-400 text-sm">✓ Clip generated successfully!</p>
                </div>
              )}
            </div>
          </div>

          {/* Post Configuration */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-bold text-white mb-4" style={{ fontFamily: 'Oswald, sans-serif' }}>
              Post Configuration
            </h3>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-500 mb-2 block">Caption</label>
                <Textarea
                  data-testid="caption-input"
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  placeholder="Write a compelling caption..."
                  className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white min-h-24"
                />
              </div>

              <div>
                <label className="text-sm text-zinc-500 mb-2 block">Hashtags</label>
                <Input
                  data-testid="hashtags-input"
                  value={hashtags}
                  onChange={(e) => setHashtags(e.target.value)}
                  placeholder="#viral #trending"
                  className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white"
                />
              </div>

              <Button
                data-testid="post-button"
                onClick={handlePost}
                disabled={!clipId || posting}
                className="w-full bg-purple-500 text-white hover:bg-purple-600 font-bold rounded-full py-3"
              >
                {posting ? 'Posting...' : 'Post to Social Media'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPreview;