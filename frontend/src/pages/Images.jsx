import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, Download, Heart, ExternalLink, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const ImageCard = ({ image, onFavorite, isFavorited }) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const response = await fetch(image.download_url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${image.title.replace(/[^a-z0-9]/gi, '_')}.jpg`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Downloaded');
    } catch (error) {
      window.open(image.download_url, '_blank');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="clean-card overflow-hidden group"
      data-testid="image-card"
    >
      <div className="relative aspect-[4/3] bg-slate-100 dark:bg-slate-800">
        <img
          src={image.thumbnail}
          alt={image.title}
          className="w-full h-full object-cover"
          loading="lazy"
        />
        
        {/* Hover Actions */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="w-9 h-9 bg-white rounded-lg flex items-center justify-center text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={() => onFavorite(image)}
            className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
              isFavorited ? 'bg-red-500 text-white' : 'bg-white text-slate-700 hover:bg-slate-100'
            }`}
          >
            <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
          </button>
          <a
            href={image.url}
            target="_blank"
            rel="noopener noreferrer"
            className="w-9 h-9 bg-white rounded-lg flex items-center justify-center text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>

        {/* Source Badge */}
        <span className="absolute bottom-2 left-2 badge badge-muted text-xs capitalize">
          {image.source}
        </span>
      </div>
      
      <div className="p-3">
        <p className="text-sm text-slate-900 dark:text-slate-100 line-clamp-1">{image.title}</p>
        {image.photographer && (
          <p className="text-xs text-slate-500 mt-1">by {image.photographer}</p>
        )}
      </div>
    </motion.div>
  );
};

const TYPE_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'photo', label: 'Photos' },
  { value: 'illustration', label: 'Illustrations' },
  { value: 'vector', label: 'Vectors' },
];

export const Images = () => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [imageType, setImageType] = useState('all');
  const [favorites, setFavorites] = useState([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchFavorites();
  }, []);

  // Track if user has searched at least once
  const [hasSearched, setHasSearched] = useState(false);

  // Auto-search when image type changes (if user has already searched)
  useEffect(() => {
    if (hasSearched && searchQuery.trim()) {
      // Use the new imageType value directly in the API call
      const doSearch = async () => {
        setLoading(true);
        try {
          const response = await api.get('/images/search', {
            params: {
              query: searchQuery,
              per_page: 20,
              page: 1,
              image_type: imageType,
            }
          });
          
          setImages(response.data.images || []);
          setPage(1);
          
          if (response.data.images?.length > 0) {
            toast.success(`Found ${response.data.images.length} ${imageType === 'all' ? '' : imageType} images`);
          } else {
            toast.info('No images found. Try a different search term or filter.');
          }
        } catch (error) {
          toast.error('Failed to search images');
        } finally {
          setLoading(false);
        }
      };
      doSearch();
    }
  }, [imageType]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchFavorites = async () => {
    try {
      const response = await api.get('/images/favorites');
      setFavorites(response.data.favorites || []);
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  };

  const handleSearch = async (newPage = 1) => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search term');
      return;
    }
    setHasSearched(true);
    
    setLoading(true);
    try {
      const response = await api.get('/images/search', {
        params: {
          query: searchQuery,
          per_page: 20,
          page: newPage,
          image_type: imageType,
        }
      });
      
      setImages(response.data.images || []);
      setPage(newPage);
      
      if (response.data.images?.length > 0) {
        toast.success(`Found ${response.data.images.length} images from ${response.data.sources?.join(', ') || 'various sources'}`);
      } else {
        toast.info('No images found. Try a different search term or filter.');
      }
    } catch (error) {
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
        setFavorites(prev => prev.filter(f => f.image_id !== image.id));
        toast.success('Removed from favorites');
      } else {
        await api.post('/images/favorites', {
          image_id: image.id,
          title: image.title,
          thumbnail: image.thumbnail,
          url: image.url,
          download_url: image.download_url,
          source: image.source,
          photographer: image.photographer,
        });
        setFavorites(prev => [...prev, { image_id: image.id }]);
        toast.success('Added to favorites');
      }
    } catch (error) {
      toast.error('Failed to update favorites');
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto" data-testid="images-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Images</h1>
        <p className="text-slate-500 text-sm">Search free stock photos and illustrations</p>
      </div>

      {/* Search & Filters */}
      <div className="mb-6 space-y-3">
        <form onSubmit={(e) => { e.preventDefault(); handleSearch(1); }} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search images..."
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

        {/* Type Filter */}
        <div className="flex gap-2">
          {TYPE_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setImageType(option.value)}
              data-testid={`filter-${option.value}`}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                imageType === option.value
                  ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        </div>
      ) : images.length > 0 ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
            <AnimatePresence>
              {images.map((image) => (
                <ImageCard
                  key={image.id}
                  image={image}
                  onFavorite={handleFavorite}
                  isFavorited={favorites.some(f => f.image_id === image.id)}
                />
              ))}
            </AnimatePresence>
          </div>

          {/* Pagination */}
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSearch(page - 1)}
              disabled={page === 1}
              className="btn-secondary"
            >
              Previous
            </Button>
            <span className="flex items-center px-3 text-sm text-slate-500">Page {page}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSearch(page + 1)}
              className="btn-secondary"
            >
              Next
            </Button>
          </div>
        </>
      ) : (
        <div className="text-center py-20">
          <p className="text-slate-500">Search for images to get started</p>
        </div>
      )}
    </div>
  );
};

export default Images;
