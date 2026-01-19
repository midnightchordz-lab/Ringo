import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Download, Link2, Heart, Image as ImageIcon, ExternalLink, X, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const ImageCard = ({ image, onFavorite, onCopyUrl, isFavorited }) => {
  const [isHovered, setIsHovered] = useState(false);
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
      // Fallback: open in new tab
      window.open(image.download_url, '_blank');
      toast.info('Opening image in new tab');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="relative rounded-xl overflow-hidden group cursor-pointer"
      style={{ backgroundColor: image.color || '#1a1a2e' }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      data-testid="image-card"
    >
      <img
        src={image.thumbnail}
        alt={image.title}
        className="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-105"
        loading="lazy"
      />
      
      {/* Source Badge */}
      <div className="absolute top-2 left-2">
        <span className={`px-2 py-1 rounded-md text-xs font-bold backdrop-blur-sm ${
          image.source === 'unsplash' 
            ? 'bg-black/50 text-white' 
            : 'bg-teal-500/80 text-white'
        }`}>
          {image.source === 'unsplash' ? 'Unsplash' : 'Pexels'}
        </span>
      </div>

      {/* Favorite Button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onFavorite(image);
        }}
        className={`absolute top-2 right-2 p-2 rounded-full backdrop-blur-sm transition-all ${
          isFavorited 
            ? 'bg-red-500 text-white' 
            : 'bg-black/50 text-white hover:bg-red-500'
        }`}
        data-testid="favorite-button"
      >
        <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
      </button>

      {/* Hover Overlay */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent flex flex-col justify-end p-4"
          >
            <h3 className="text-white font-semibold text-sm line-clamp-2 mb-1">
              {image.title}
            </h3>
            <p className="text-white/70 text-xs mb-3">
              by {image.photographer}
            </p>
            
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload();
                }}
                disabled={downloading}
                className="flex-1 bg-white text-black hover:bg-white/90 text-xs py-1"
                data-testid="download-button"
              >
                <Download className="w-3 h-3 mr-1" />
                {downloading ? 'Downloading...' : 'Download'}
              </Button>
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onCopyUrl(image.url);
                }}
                className="bg-white/20 text-white hover:bg-white/30 text-xs py-1"
                data-testid="copy-url-button"
              >
                <Link2 className="w-3 h-3" />
              </Button>
              <Button
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(image.photographer_url, '_blank');
                }}
                className="bg-white/20 text-white hover:bg-white/30 text-xs py-1"
              >
                <ExternalLink className="w-3 h-3" />
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const Images = () => {
  const [images, setImages] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('search'); // 'search' or 'favorites'
  const [hasSearched, setHasSearched] = useState(false);

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
    setHasSearched(true);
    try {
      const response = await api.get('/images/search', {
        params: {
          query: searchQuery,
          per_page: 30
        }
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
    const isFavorited = favorites.some(f => f.image_id === image.id);
    
    try {
      if (isFavorited) {
        await api.delete(`/images/favorites/${image.id}`);
        setFavorites(favorites.filter(f => f.image_id !== image.id));
        toast.success('Removed from favorites');
      } else {
        await api.post('/images/favorites', {
          image_id: image.id,
          url: image.url,
          thumbnail: image.thumbnail,
          title: image.title,
          photographer: image.photographer,
          source: image.source,
          download_url: image.download_url,
          width: image.width,
          height: image.height
        });
        setFavorites([...favorites, { ...image, image_id: image.id }]);
        toast.success('Added to favorites!');
      }
    } catch (error) {
      console.error('Error updating favorite:', error);
      toast.error(error.response?.data?.detail || 'Failed to update favorites');
    }
  };

  const handleCopyUrl = (url) => {
    navigator.clipboard.writeText(url);
    toast.success('Image URL copied to clipboard!');
  };

  const isFavorited = (imageId) => {
    return favorites.some(f => f.image_id === imageId);
  };

  const displayImages = activeTab === 'search' ? images : favorites.map(f => ({
    ...f,
    id: f.image_id
  }));

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
          Free Images
        </h1>
        <p className="text-zinc-500">Search copyright-free images from Unsplash & Pexels</p>
      </div>

      {/* Search Bar */}
      <div className="glass-card p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
            <Input
              data-testid="image-search-input"
              type="text"
              placeholder="Search for images... (e.g., 'mountains', 'technology', 'food')"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="pl-12 bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white placeholder:text-zinc-600 h-12"
            />
          </div>
          <Button
            data-testid="image-search-button"
            onClick={handleSearch}
            disabled={loading}
            className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-8 py-3 shadow-[0_0_15px_rgba(190,242,100,0.3)] hover:shadow-[0_0_25px_rgba(190,242,100,0.5)] transition-all h-12"
          >
            {loading ? 'Searching...' : 'Search'}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          onClick={() => setActiveTab('search')}
          className={`rounded-full px-6 py-2 font-semibold transition-all ${
            activeTab === 'search'
              ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
          data-testid="tab-search"
        >
          <Search className="w-4 h-4 mr-2" />
          Search Results
          {images.length > 0 && (
            <span className="ml-2 bg-white/20 px-2 py-0.5 rounded-full text-xs">
              {images.length}
            </span>
          )}
        </Button>
        <Button
          onClick={() => setActiveTab('favorites')}
          className={`rounded-full px-6 py-2 font-semibold transition-all ${
            activeTab === 'favorites'
              ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white shadow-lg'
              : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
          }`}
          data-testid="tab-favorites"
        >
          <Heart className="w-4 h-4 mr-2" />
          My Favorites
          {favorites.length > 0 && (
            <span className="ml-2 bg-white/20 px-2 py-0.5 rounded-full text-xs">
              {favorites.length}
            </span>
          )}
        </Button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[#BEF264] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-zinc-500">Searching for beautiful images...</p>
          </div>
        </div>
      )}

      {/* Results Grid */}
      {!loading && displayImages.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-zinc-500">
              {activeTab === 'search' ? 'Found' : 'You have'}{' '}
              <span className="text-[#BEF264] font-bold">{displayImages.length}</span>{' '}
              {activeTab === 'search' ? 'images' : 'favorite images'}
            </p>
            <div className="flex items-center gap-2 text-xs text-zinc-600">
              <span className="px-2 py-1 bg-black/30 rounded">Unsplash</span>
              <span className="px-2 py-1 bg-teal-500/30 rounded text-teal-400">Pexels</span>
            </div>
          </div>
          
          <motion.div 
            layout
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
          >
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
          </motion.div>
        </div>
      )}

      {/* Empty States */}
      {!loading && activeTab === 'search' && !hasSearched && (
        <div className="glass-card p-20 text-center">
          <ImageIcon className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">Discover Free Images</h3>
          <p className="text-zinc-500 mb-6">Search millions of copyright-free photos from Unsplash and Pexels</p>
          <div className="flex flex-wrap justify-center gap-2">
            {['Nature', 'Technology', 'Business', 'Food', 'Travel'].map((term) => (
              <Button
                key={term}
                onClick={() => {
                  setSearchQuery(term.toLowerCase());
                  setTimeout(() => handleSearch(), 100);
                }}
                variant="outline"
                className="rounded-full border-zinc-700 text-zinc-400 hover:bg-zinc-800"
              >
                {term}
              </Button>
            ))}
          </div>
        </div>
      )}

      {!loading && activeTab === 'search' && hasSearched && images.length === 0 && (
        <div className="glass-card p-20 text-center">
          <Search className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">No Images Found</h3>
          <p className="text-zinc-500">Try a different search term</p>
        </div>
      )}

      {!loading && activeTab === 'favorites' && favorites.length === 0 && (
        <div className="glass-card p-20 text-center">
          <Heart className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">No Favorites Yet</h3>
          <p className="text-zinc-500 mb-6">Search for images and click the heart icon to save them here</p>
          <Button
            onClick={() => setActiveTab('search')}
            className="bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-6 py-2"
          >
            Start Searching
          </Button>
        </div>
      )}
    </div>
  );
};

export default Images;
