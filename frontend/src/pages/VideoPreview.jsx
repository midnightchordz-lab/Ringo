import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../utils/api';
import { 
  ArrowLeft, Scissors, TrendingUp, Eye, ThumbsUp, MessageCircle, 
  Calendar, PlayCircle, Sparkles, AlertTriangle, ExternalLink, 
  Copy, Play, ShieldCheck, Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { motion } from 'framer-motion';

const YouTubePlayer = ({ videoId, startTime = 0, endTime = null }) => {
  const params = new URLSearchParams({
    modestbranding: '1',
    rel: '0',
    start: startTime.toString(),
  });
  
  if (endTime) {
    params.set('end', endTime.toString());
  }
  
  return (
    <div className="relative w-full h-full">
      <iframe
        src={`https://www.youtube.com/embed/${videoId}?${params.toString()}`}
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
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [analyzingAI, setAnalyzingAI] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [caption, setCaption] = useState('');
  const [hashtags, setHashtags] = useState('#viral #trending #ccby');

  useEffect(() => {
    fetchVideoDetails();
  }, [videoId]);

  const fetchVideoDetails = async () => {
    try {
      const response = await api.get(`/videos/${videoId}`);
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
      const response = await api.get(`/clips/ai-analyze/${videoId}`);
      const analysis = response.data.analysis;
      setAiAnalysis(analysis);
      setStartTime(analysis.recommended_start);
      setClipDuration(analysis.recommended_duration);
      toast.success(`AI found the best moment!`);
    } catch (error) {
      console.error('Error analyzing with AI:', error);
      toast.error('AI analysis failed. Try manual selection.');
    } finally {
      setAnalyzingAI(false);
    }
  };

  const handlePreviewClip = () => {
    setShowPreview(true);
    toast.success(`Previewing clip from ${startTime}s to ${startTime + clipDuration}s`);
  };

  const copyEmbedCode = () => {
    const embedCode = `<iframe width="315" height="560" src="https://www.youtube.com/embed/${videoId}?start=${startTime}&end=${startTime + clipDuration}" frameborder="0" allowfullscreen></iframe>`;
    navigator.clipboard.writeText(embedCode);
    toast.success('Embed code copied!');
  };

  const copyWatchUrl = () => {
    const url = `https://www.youtube.com/watch?v=${videoId}&t=${startTime}s`;
    navigator.clipboard.writeText(url);
    toast.success('Watch URL copied!');
  };

  const openInYouTube = () => {
    window.open(`https://www.youtube.com/watch?v=${videoId}&t=${startTime}s`, '_blank');
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
              <YouTubePlayer 
                videoId={videoId} 
                startTime={showPreview ? startTime : 0}
                endTime={showPreview ? startTime + clipDuration : null}
              />
            </div>
            
            {/* Clip Preview Indicator */}
            {showPreview && (
              <div className="bg-[#BEF264]/20 border-t border-[#BEF264]/30 px-4 py-2 flex items-center justify-between">
                <span className="text-[#BEF264] text-sm font-semibold flex items-center gap-2">
                  <Play className="w-4 h-4" />
                  Previewing: {startTime}s - {startTime + clipDuration}s
                </span>
                <Button
                  size="sm"
                  onClick={() => setShowPreview(false)}
                  className="bg-zinc-800 text-white text-xs"
                >
                  Show Full Video
                </Button>
              </div>
            )}
          </div>

          {/* Video Info */}
          <div className="glass-card p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-bold bg-green-500/30 text-green-300 border border-green-400/50">
                    <ShieldCheck className="w-4 h-4 mr-1.5" />
                    CC BY Licensed
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

          {/* License & Usage Info */}
          <div className="glass-card p-4 border-l-4 border-green-500">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-white font-semibold mb-1">Commercial Use Allowed</p>
                <p className="text-xs text-zinc-400">
                  This CC BY video can be used commercially. Remember to provide attribution to: <span className="text-white">{video.channel}</span>
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Clip Generator Panel */}
        <div className="space-y-6">
          {/* AI Analysis */}
          <div className="glass-card p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center" style={{ fontFamily: 'Oswald, sans-serif' }}>
              <Sparkles className="w-5 h-5 mr-2 text-[#BEF264]" />
              AI Clip Analysis
            </h2>
            
            <p className="text-zinc-400 text-sm mb-4">
              Let AI analyze the video and find the best moment for a viral clip.
            </p>

            <Button
              data-testid="ai-analyze-button"
              onClick={handleAIAnalysis}
              disabled={analyzingAI}
              className="w-full bg-gradient-to-r from-violet-600 to-purple-600 text-white font-bold rounded-full py-3 mb-4"
            >
              {analyzingAI ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Find Best Clip Moment
                </>
              )}
            </Button>

            {aiAnalysis && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-violet-500/20 border border-violet-500/30 rounded-lg"
              >
                <p className="text-violet-300 text-sm font-semibold mb-2">AI Recommendation:</p>
                <p className="text-white text-sm mb-2">
                  Start at <span className="text-[#BEF264] font-bold">{aiAnalysis.recommended_start}s</span>, 
                  Duration: <span className="text-[#BEF264] font-bold">{aiAnalysis.recommended_duration}s</span>
                </p>
                <p className="text-zinc-400 text-xs">{aiAnalysis.reasoning}</p>
              </motion.div>
            )}
          </div>

          {/* Manual Clip Settings */}
          <div className="glass-card p-6">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center" style={{ fontFamily: 'Oswald, sans-serif' }}>
              <Scissors className="w-5 h-5 mr-2 text-[#BEF264]" />
              Clip Settings
            </h2>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-500 mb-2 block">Start Time (seconds)</label>
                <Input
                  data-testid="start-time-input"
                  type="number"
                  min="0"
                  max={video.duration || 3600}
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
                <p className="text-xs text-zinc-600 mt-1">10-60 seconds recommended for reels</p>
              </div>

              <Button
                data-testid="preview-clip-button"
                onClick={handlePreviewClip}
                className="w-full bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full py-3"
              >
                <PlayCircle className="w-4 h-4 mr-2" />
                Preview Clip
              </Button>
            </div>
          </div>

          {/* Export Options */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-bold text-white mb-4" style={{ fontFamily: 'Oswald, sans-serif' }}>
              Export & Share
            </h3>

            <div className="space-y-3">
              <Button
                onClick={copyEmbedCode}
                variant="outline"
                className="w-full justify-start border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              >
                <Copy className="w-4 h-4 mr-2" />
                Copy Embed Code
              </Button>
              
              <Button
                onClick={copyWatchUrl}
                variant="outline"
                className="w-full justify-start border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              >
                <Copy className="w-4 h-4 mr-2" />
                Copy Watch URL
              </Button>
              
              <Button
                onClick={openInYouTube}
                variant="outline"
                className="w-full justify-start border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Open in YouTube
              </Button>
            </div>

            {/* Download Notice */}
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-amber-300 text-xs font-semibold">Download Tip</p>
                  <p className="text-zinc-400 text-xs mt-1">
                    To download, use a browser extension or yt-dlp with cookies. Remember to credit the creator!
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Post Configuration */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-bold text-white mb-4" style={{ fontFamily: 'Oswald, sans-serif' }}>
              Caption Template
            </h3>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-500 mb-2 block">Caption</label>
                <Textarea
                  data-testid="caption-input"
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  placeholder="Write a compelling caption..."
                  className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white min-h-20"
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
                onClick={() => {
                  const fullCaption = `${caption}\n\n📹 Credit: ${video.channel}\n\n${hashtags}`;
                  navigator.clipboard.writeText(fullCaption);
                  toast.success('Caption with attribution copied!');
                }}
                className="w-full bg-purple-500 text-white hover:bg-purple-600 font-bold rounded-full py-3"
              >
                <Copy className="w-4 h-4 mr-2" />
                Copy Caption with Attribution
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoPreview;
