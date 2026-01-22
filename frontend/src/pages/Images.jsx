import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Download, Link2, Heart, Image as ImageIcon, ExternalLink, ShieldCheck, CheckCircle2, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
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

  const getSourceColor = (source) => {
    switch(source) {
      case 'unsplash': return 'bg-neutral-800';
      case 'pexels': return 'bg-teal-600';
      case 'pixabay': return 'bg-green-600';
      case 'wikimedia': return 'bg-blue-600';
      case 'openclipart': return 'bg-orange-500';
      default: return 'bg-purple-600';
    }
  };

  const getSourceName = (source) => {
    switch(source) {
      case 'unsplash': return 'Unsplash';
      case 'pexels': return 'Pexels';
      case 'pixabay': return 'Pixabay';
      case 'wikimedia': return 'Wikimedia';
      case 'openclipart': return 'OpenClipart';
      default: return source;
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
          <span className={`text-xs font-bold px-2.5 py-1 rounded-lg text-white shadow-lg ${getSourceColor(image.source)}`}>
            {getSourceName(image.source)}
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
        <p className="text-neutral-900 dark:text-neutral-100 font-medium text-sm line-clamp-1 mb-2">{image.title || 'Untitled'}</p>
        <div className="flex items-center justify-between">
          <a 
            href={image.photographer_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-xs font-medium flex items-center gap-1"
          >
            by {image.photographer}
            <ExternalLink className="w-3 h-3" />
          </a>
          {image.likes > 0 && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
              <Heart className="w-3 h-3" /> {image.likes}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// Pagination Component
const PaginationControls = ({ currentPage, totalPages, totalItems, perPage, onPageChange, isLoading }) => {
  if (totalPages <= 1) return null;
  
  const startItem = (currentPage - 1) * perPage + 1;
  const endItem = Math.min(currentPage * perPage, totalItems);
  
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white dark:bg-neutral-900 rounded-xl shadow-sm border border-neutral-100 dark:border-neutral-800">
      <div className="text-sm text-neutral-600 dark:text-neutral-400">
        Showing <span className="font-semibold text-neutral-900 dark:text-neutral-100">{startItem}-{endItem}</span> of{' '}
        <span className="font-semibold text-neutral-900 dark:text-neutral-100">{totalItems.toLocaleString()}</span> images
      </div>
      
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1 || isLoading}
          className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentPage === 1 || isLoading
              ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-600 cursor-not-allowed'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700'
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>
        
        <span className="px-4 py-2 bg-purple-500 text-white rounded-lg font-semibold">
          {currentPage} / {totalPages}
        </span>
        
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages || isLoading}
          className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentPage === totalPages || isLoading
              ? 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-600 cursor-not-allowed'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-neutral-200 dark:hover:bg-neutral-700'
          }`}
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export const Images = () => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [favorites, setFavorites] = useState([]);
  const [showFavorites, setShowFavorites] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalImages, setTotalImages] = useState(0);
  const [selectedSource, setSelectedSource] = useState('all');
  const [sources, setSources] = useState([]);
  const [selectedType, setSelectedType] = useState('all');
  const perPage = 50;

  // Image Type Filters
  const IMAGE_TYPES = [
    { id: 'all', name: 'All Images', icon: '🖼️' },
    { id: 'photo', name: 'Photos', icon: '📷' },
    { id: 'illustration', name: 'Illustrations', icon: '🎨' },
    { id: 'vector', name: 'Vectors', icon: '📐' },
  ];

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

  const handleSearch = async (page = 1) => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search term');
      return;
    }
    
    setLoading(true);
    try {
      const response = await api.get('/images/search', {
        params: { 
          query: searchQuery, 
          page: page,
          per_page: perPage,
          source: selectedSource,
          image_type: selectedType !== 'all' ? selectedType : undefined
        }
      });
      setImages(response.data.images || []);
      setTotalImages(response.data.total || 0);
      setTotalPages(response.data.total_pages || 1);
      setCurrentPage(response.data.page || 1);
      setSources(response.data.sources || []);
      
      // Check if there's an error message from the backend (e.g., Pixabay not configured)
      if (response.data.error) {
        toast.warning(response.data.error);
      } else if (page === 1) {
        if (response.data.total === 0) {
          toast.info('No images found. Try different search terms or filters.');
        } else {
          toast.success(`Found ${response.data.total.toLocaleString()} images!`);
        }
      }
    } catch (error) {
      console.error('Error searching images:', error);
      toast.error('Failed to search images');
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    handleSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSourceFilter = (source) => {
    setSelectedSource(source);
    if (searchQuery.trim()) {
      setCurrentPage(1);
      setTimeout(() => handleSearch(1), 100);
    }
  };

  const handleTypeFilter = (type) => {
    setSelectedType(type);
    if (searchQuery.trim()) {
      setCurrentPage(1);
      setTimeout(() => handleSearch(1), 100);
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
    <div className="p-6 lg:p-8 pb-24 lg:pb-8 bg-neutral-50 dark:bg-neutral-950 min-h-screen transition-colors duration-300">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
            <ImageIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Image Search
            </h1>
            <p className="text-neutral-500 dark:text-neutral-400">Find stunning copyright-free images from across the web</p>
          </div>
        </div>
      </div>

      {/* License Info */}
      <div className="studio-card p-4 mb-6 border-l-4 border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/40 rounded-lg flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">100% Free to Use</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <p className="text-xs text-emerald-700 dark:text-emerald-400">
              All images are <span className="font-bold">Creative Commons licensed</span> (CC BY, CC BY-SA, CC0). Sources: <span className="font-bold">Pexels</span>, <span className="font-bold">Unsplash</span>, <span className="font-bold">Pixabay</span>, <span className="font-bold">Wikimedia Commons</span>, <span className="font-bold">OpenClipart</span>
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="studio-card p-6 mb-6">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 dark:text-neutral-500" />
              <Input
                data-testid="image-search-input"
                type="text"
                placeholder="Search for images... (e.g., 'mountains', 'technology', 'food')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch(1)}
                className="studio-input-icon w-full"
              />
            </div>
            <Button
              data-testid="image-find-button"
              onClick={() => handleSearch(1)}
              disabled={loading}
              className="btn-primary min-w-[100px]"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Find'
              )}
            </Button>
            <Button
              onClick={() => setShowFavorites(!showFavorites)}
              className={`rounded-xl px-6 py-3 flex items-center gap-2 font-semibold transition-all ${
                showFavorites 
                  ? 'bg-red-500 hover:bg-red-600 text-white' 
                  : 'bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200'
              }`}
              data-testid="favorites-toggle"
            >
              <Heart className="w-4 h-4" fill={showFavorites ? 'currentColor' : 'none'} />
              Favorites ({favorites.length})
            </Button>
          </div>
          
          {/* Image Type Filter */}
          <div className="flex items-center gap-2 flex-wrap pb-4 border-b border-neutral-100 dark:border-neutral-800">
            <span className="text-sm text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
              <ImageIcon className="w-4 h-4" /> Type:
            </span>
            {IMAGE_TYPES.map((type) => (
              <button
                key={type.id}
                onClick={() => handleTypeFilter(type.id)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
                  selectedType === type.id
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/30'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                }`}
                data-testid={`type-filter-${type.id}`}
                title={
                  type.id === 'illustration' || type.id === 'vector' 
                    ? 'Requires Pixabay (only source with illustrations/vectors)' 
                    : ''
                }
              >
                <span>{type.icon}</span>
                {type.name}
              </button>
            ))}
          </div>
          
          {/* Source Filter */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-neutral-500 dark:text-neutral-400 flex items-center gap-1">
              <Filter className="w-4 h-4" /> Source:
            </span>
            {[
              { id: 'all', name: 'All Sources', color: 'bg-purple-500' },
              { id: 'pexels', name: 'Pexels', color: 'bg-teal-500', hint: 'Photos' },
              { id: 'unsplash', name: 'Unsplash', color: 'bg-neutral-700', hint: 'Photos' },
              { id: 'pixabay', name: 'Pixabay', color: 'bg-green-500', hint: 'All Types' },
              { id: 'wikimedia', name: 'Wikimedia', color: 'bg-blue-500', hint: 'CC BY' },
              { id: 'openclipart', name: 'OpenClipart', color: 'bg-orange-500', hint: 'Vectors' }
            ].map((source) => (
              <button
                key={source.id}
                onClick={() => handleSourceFilter(source.id)}
                title={source.hint}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                  selectedSource === source.id
                    ? `${source.color} text-white shadow-md`
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                }`}
              >
                {source.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Results Count */}
      {!showFavorites && totalImages > 0 && (
        <div className="mb-6 flex items-center justify-between">
          <p className="text-neutral-600 dark:text-neutral-400">
            Found <span className="font-bold text-purple-600 dark:text-purple-400">{totalImages.toLocaleString()}</span> images
            {selectedType !== 'all' && (
              <span className="ml-2 text-pink-600 dark:text-pink-400">
                ({IMAGE_TYPES.find(t => t.id === selectedType)?.name})
              </span>
            )}
            {sources.length > 0 && (
              <span className="text-sm text-neutral-500 dark:text-neutral-500 ml-2">
                from {sources.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(', ')}
              </span>
            )}
          </p>
        </div>
      )}
      
      {showFavorites && (
        <div className="mb-6">
          <p className="text-neutral-600 dark:text-neutral-400">
            Showing <span className="font-bold text-red-500 dark:text-red-400">{favorites.length}</span> favorite images
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-neutral-600 dark:text-neutral-400 font-medium">Searching for images...</p>
          </div>
        </div>
      )}

      {/* Image Grid */}
      {!loading && displayImages.length > 0 && (
        <>
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
          
          {/* Pagination */}
          {!showFavorites && (
            <PaginationControls
              currentPage={currentPage}
              totalPages={totalPages}
              totalItems={totalImages}
              perPage={perPage}
              onPageChange={handlePageChange}
              isLoading={loading}
            />
          )}
        </>
      )}

      {/* Empty State */}
      {!loading && displayImages.length === 0 && (
        <div className="studio-card p-16 text-center">
          <div className="w-20 h-20 mx-auto mb-6 bg-purple-100 dark:bg-purple-900/40 rounded-2xl flex items-center justify-center">
            {showFavorites ? (
              <Heart className="w-10 h-10 text-purple-600 dark:text-purple-400" />
            ) : (
              <ImageIcon className="w-10 h-10 text-purple-600 dark:text-purple-400" />
            )}
          </div>
          <h3 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
            {showFavorites ? 'No favorites yet' : 'Start searching'}
          </h3>
          <p className="text-neutral-500 dark:text-neutral-400 mb-6">
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
