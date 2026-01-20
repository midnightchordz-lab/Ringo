import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Download, Link2, Heart, Image as ImageIcon, ExternalLink, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const ImageCard = ({ image, onFavorite, onCopyUrl, isFavorited }) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const response = await fetch(image.download_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${image.title.replace(/[^a-z0-9]/gi, '_')}_${image.source}.jpg`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Image downloaded!');
    } catch (error) {
      console.error('Download error:', error);
      window.open(image.download_url, '_blank');
      toast.info('Opening image in new tab');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="studio-card overflow-hidden group"
      style={{ backgroundColor: image.color || '#f5f5f5' }}
      data-testid="image-card"
    >
      <div className="relative">
        <img
          src={image.thumbnail}
          alt={image.title}
          className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
        
        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-neutral-700 hover:bg-blue-500 hover:text-white transition-colors shadow-lg"
            title="Download"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={() => onCopyUrl(image.url)}
            className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-neutral-700 hover:bg-blue-500 hover:text-white transition-colors shadow-lg"
            title="Copy URL"
          >
            <Link2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => onFavorite(image)}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors shadow-lg ${
              isFavorited ? 'bg-red-500 text-white' : 'bg-white text-neutral-700 hover:bg-red-500 hover:text-white'
            }`}
            title="Favorite"
          >
            <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
          </button>
        </div>
        
        {/* Source Badge */}
        <div className="absolute top-2 left-2">
          <span className={`text-xs font-bold px-2.5 py-1 rounded-lg text-white shadow-lg ${
            image.source === 'unsplash' ? 'bg-neutral-800' : 'bg-teal-600'
          }`}>
            {image.source === 'unsplash' ? 'Unsplash' : 'Pexels'}
          </span>
        </div>
        
        {/* Free Badge */}
        <div className="absolute top-2 right-2">
          <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-emerald-500 text-white shadow-lg flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Free
          </span>
        </div>
      </div>
      
      <div className="p-4">
        <p className="text-neutral-900 font-medium text-sm line-clamp-1 mb-2">{image.title || 'Untitled'}</p>
        <a 
          href={image.photographer_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-700 text-xs font-medium flex items-center gap-1"
        >
          by {image.photographer}
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </motion.div>
  );
};

export const Images = () => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [favorites, setFavorites] = useState([]);
  const [showFavorites, setShowFavorites] = useState(false);

  useEffect(() => {
    fetchFavorites();
  }, []);

  const fetchFavorites = async () => {
    try {
      const response = await api.get('/images/favorites');
      setFavorites(response.data.favorites || []);
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search term');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.get('/images/search', {
        params: { query: searchQuery, per_page: 30 }
      });
      setImages(response.data.images || []);
      toast.success(`Found ${response.data.total} images!`);
    } catch (error) {
      console.error('Error searching images:', error);
      toast.error('Failed to search images');
    } finally {
      setLoading(false);
    }
  };

  const handleFavorite = async (image) => {
    const isFav = favorites.some(f => f.id === image.id);
    
    try {
      if (isFav) {
        await api.delete(`/images/favorites/${image.id}`);
        setFavorites(favorites.filter(f => f.id !== image.id));
        toast.success('Removed from favorites');
      } else {
        await api.post('/images/favorites', image);
        setFavorites([...favorites, image]);
        toast.success('Added to favorites!');
      }
    } catch (error) {
      console.error('Error updating favorite:', error);
      toast.error('Failed to update favorites');
    }
  };

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    toast.success('URL copied to clipboard!');
  };

  const isFavorited = (imageId) => favorites.some(f => f.id === imageId);
  const displayImages = showFavorites ? favorites : images;

  return (
    <div className="p-6 lg:p-8 pb-24 lg:pb-8 bg-neutral-50 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
            <ImageIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Image Search
            </h1>
            <p className="text-neutral-500">Find stunning copyright-free images</p>
          </div>
        </div>
      </div>

      {/* License Info */}
      <div className="studio-card p-4 mb-6 border-l-4 border-emerald-500 bg-emerald-50">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-emerald-800">100% Free to Use</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            </div>
            <p className="text-xs text-emerald-700">
              All images from <span className="font-bold">Unsplash</span> and <span className="font-bold">Pexels</span> are free for commercial use. No attribution required!
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="studio-card p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
              <Input
                data-testid="image-search-input"
                type="text"
                placeholder="Search for images... (e.g., 'mountains', 'technology', 'food')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="pl-12 studio-input"
              />
            </div>
            <Button
              data-testid="image-find-button"
              onClick={handleSearch}
              disabled={loading}
              className="btn-primary min-w-[100px]"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Find'
              )}
            </Button>
          </div>
          <Button
            onClick={() => setShowFavorites(!showFavorites)}
            className={`rounded-xl px-6 py-3 flex items-center gap-2 font-semibold transition-all ${
              showFavorites 
                ? 'bg-red-500 hover:bg-red-600 text-white' 
                : 'bg-neutral-100 hover:bg-neutral-200 text-neutral-700'
            }`}
            data-testid="favorites-toggle"
          >
            <Heart className="w-4 h-4" fill={showFavorites ? 'currentColor' : 'none'} />
            Favorites ({favorites.length})
          </Button>
        </div>
      </div>

      {/* Results Count */}
      {displayImages.length > 0 && (
        <div className="mb-6">
          <p className="text-neutral-600">
            {showFavorites ? (
              <>Showing <span className="font-bold text-red-500">{favorites.length}</span> favorite images</>
            ) : (
              <>Found <span className="font-bold text-blue-600">{images.length}</span> images</>
            )}
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-neutral-600 font-medium">Searching for images...</p>
          </div>
        </div>
      )}

      {/* Image Grid */}
      {!loading && displayImages.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          <AnimatePresence>
            {displayImages.map((image) => (
              <ImageCard
                key={image.id}
                image={image}
                onFavorite={handleFavorite}
                onCopyUrl={handleCopyUrl}
                isFavorited={isFavorited(image.id)}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Empty State */}
      {!loading && displayImages.length === 0 && (
        <div className="studio-card p-16 text-center">
          <div className="w-20 h-20 mx-auto mb-6 bg-purple-100 rounded-2xl flex items-center justify-center">
            {showFavorites ? (
              <Heart className="w-10 h-10 text-purple-600" />
            ) : (
              <ImageIcon className="w-10 h-10 text-purple-600" />
            )}
          </div>
          <h3 className="text-xl font-bold text-neutral-900 mb-2">
            {showFavorites ? 'No favorites yet' : 'Start searching'}
          </h3>
          <p className="text-neutral-500 mb-6">
            {showFavorites 
              ? 'Search for images and click the heart icon to save them here'
              : 'Enter a search term to find stunning free images'
            }
          </p>
          {showFavorites && (
            <Button onClick={() => setShowFavorites(false)} className="btn-primary">
              Browse Images
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default Images;
