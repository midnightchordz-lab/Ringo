import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Search, BookOpen, GraduationCap, FileText, ExternalLink, Heart, Loader2, Book, Baby } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

// Simple tabs
const TABS = [
  { id: 'search', label: 'Search', icon: Search },
  { id: 'books', label: 'Free Books', icon: Book },
  { id: 'children', label: "Children's Books", icon: Baby },
  { id: 'courses', label: 'Courses', icon: GraduationCap },
];

// Content type icons
const getTypeIcon = (type) => {
  const icons = { book: BookOpen, course: GraduationCap, article: FileText };
  return icons[type] || FileText;
};

// Simple license badge
const LicenseBadge = ({ license }) => {
  const isCC = license?.toLowerCase().includes('cc') || license?.toLowerCase().includes('public');
  return (
    <span className={`badge text-xs ${isCC ? 'badge-success' : 'badge-muted'}`}>
      {license?.replace('CC BY', 'CC').substring(0, 12) || 'Free'}
    </span>
  );
};

// Content Card Component
const ContentCard = ({ item, onFavorite, isFavorited }) => {
  const TypeIcon = getTypeIcon(item.type);
  
  return (
    <div className="clean-card clean-card-hover p-4" data-testid="content-card">
      <div className="flex gap-3">
        {/* Icon/Thumbnail */}
        <div className="w-12 h-12 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
          {item.thumbnail && !item.thumbnail.startsWith('�') ? (
            <img src={item.thumbnail} alt="" className="w-full h-full object-cover rounded-lg" onError={(e) => e.target.style.display = 'none'} />
          ) : (
            <TypeIcon className="w-5 h-5 text-slate-500" />
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-sm text-slate-900 dark:text-slate-100 line-clamp-2">{item.title}</h3>
            <button
              onClick={() => onFavorite(item)}
              className={`p-1.5 rounded-lg flex-shrink-0 ${isFavorited ? 'text-red-500' : 'text-slate-400 hover:text-red-500'}`}
            >
              <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
            </button>
          </div>
          
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-slate-500">{item.source}</span>
            <LicenseBadge license={item.license} />
          </div>
          
          {item.description && (
            <p className="text-xs text-slate-500 line-clamp-2 mt-2">{item.description}</p>
          )}
        </div>
      </div>
      
      <div className="flex justify-end mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
        <Button
          size="sm"
          variant="outline"
          onClick={() => window.open(item.url, '_blank')}
          className="text-xs"
        >
          <ExternalLink className="w-3 h-3 mr-1" /> Open
        </Button>
      </div>
    </div>
  );
};

// Book Card Component
const BookCard = ({ book, onFavorite, isFavorited }) => (
  <div className="clean-card clean-card-hover overflow-hidden" data-testid="book-card">
    <div className="aspect-[3/4] bg-slate-100 dark:bg-slate-800 relative">
      {book.cover ? (
        <img src={book.cover} alt={book.title} className="w-full h-full object-cover" onError={(e) => e.target.parentElement.innerHTML = '<div class="w-full h-full flex items-center justify-center"><svg class="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg></div>'} />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <Book className="w-8 h-8 text-slate-400" />
        </div>
      )}
      <button
        onClick={() => onFavorite(book)}
        className={`absolute top-2 right-2 p-1.5 rounded-lg bg-white/90 dark:bg-slate-800/90 ${isFavorited ? 'text-red-500' : 'text-slate-400 hover:text-red-500'}`}
      >
        <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
      </button>
    </div>
    <div className="p-3">
      <h3 className="font-medium text-sm text-slate-900 dark:text-slate-100 line-clamp-2">{book.title}</h3>
      {book.author && <p className="text-xs text-slate-500 mt-1">{book.author}</p>}
      <div className="flex items-center justify-between mt-2">
        <LicenseBadge license={book.license || 'Public Domain'} />
        {book.download_url && (
          <a href={book.download_url} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-600 hover:underline">
            Download
          </a>
        )}
      </div>
    </div>
  </div>
);

export const ContentLibrary = () => {
  const [activeTab, setActiveTab] = useState('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [books, setBooks] = useState([]);
  const [childrenBooks, setChildrenBooks] = useState([]);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [favorites, setFavorites] = useState([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    fetchFavorites();
  }, []);

  useEffect(() => {
    if (activeTab === 'books') fetchBooks();
    if (activeTab === 'children') fetchChildrenBooks();
    if (activeTab === 'courses') fetchCourses();
  }, [activeTab]);

  const fetchFavorites = async () => {
    try {
      const response = await api.get('/content-library/favorites');
      setFavorites(response.data.favorites || []);
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  };

  const fetchBooks = async () => {
    setLoading(true);
    try {
      const response = await api.get('/content-library/free-books', { params: { per_page: 20 } });
      setBooks(response.data.books || []);
    } catch (error) {
      toast.error('Failed to fetch books');
    } finally {
      setLoading(false);
    }
  };

  const fetchChildrenBooks = async () => {
    setLoading(true);
    try {
      const response = await api.get('/content-library/childrens-literature', { params: { per_page: 20 } });
      // API returns 'results' not 'books'
      setChildrenBooks(response.data.results || response.data.books || []);
    } catch (error) {
      toast.error('Failed to fetch children\'s books');
    } finally {
      setLoading(false);
    }
  };

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const response = await api.get('/content-library/search', { params: { query: 'programming course', type: 'course', per_page: 20 } });
      setCourses(response.data.results || []);
    } catch (error) {
      toast.error('Failed to fetch courses');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search term');
      return;
    }
    setLoading(true);
    try {
      const response = await api.get('/content-library/search', { params: { query: searchQuery, per_page: 20 } });
      const searchResults = response.data.results || [];
      console.log('Search results:', searchResults.length, searchResults);
      setResults(searchResults);
      if (searchResults.length > 0) {
        toast.success(`Found ${searchResults.length} results`);
      } else {
        toast.info('No results found');
      }
    } catch (error) {
      console.error('Search error:', error);
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleFavorite = async (item) => {
    const isFavorited = favorites.some(f => f.resource_id === item.id);
    try {
      if (isFavorited) {
        await api.delete(`/content-library/favorites/${item.id}`);
        setFavorites(prev => prev.filter(f => f.resource_id !== item.id));
        toast.success('Removed from favorites');
      } else {
        await api.post('/content-library/favorites', {
          resource_id: item.id,
          title: item.title,
          type: item.type || 'resource',
          source: item.source,
          url: item.url,
          license: item.license,
        });
        setFavorites(prev => [...prev, { resource_id: item.id }]);
        toast.success('Added to favorites');
      }
    } catch (error) {
      toast.error('Failed to update favorites');
    }
  };

  const isFavorited = (item) => favorites.some(f => f.resource_id === item.id);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto" data-testid="content-library-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Content Library</h1>
        <p className="text-slate-500 text-sm">Find free educational resources, books, and courses</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-200 dark:border-slate-800 pb-3">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Search Tab */}
      {activeTab === 'search' && (
        <div>
          <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }} className="flex gap-2 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search articles, courses, resources..."
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

          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : results.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <AnimatePresence>
                {results.map((item) => (
                  <ContentCard key={item.id} item={item} onFavorite={handleFavorite} isFavorited={isFavorited(item)} />
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="text-center py-20">
              <Search className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">Search for educational content to get started</p>
            </div>
          )}
        </div>
      )}

      {/* Books Tab */}
      {activeTab === 'books' && (
        <div>
          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : books.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {books.map((book) => (
                <BookCard key={book.id} book={book} onFavorite={handleFavorite} isFavorited={isFavorited(book)} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20">
              <Book className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">No books found</p>
            </div>
          )}
        </div>
      )}

      {/* Children's Books Tab */}
      {activeTab === 'children' && (
        <div>
          <p className="text-sm text-slate-500 mb-4">Free children's books with monetization-friendly licenses</p>
          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : childrenBooks.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {childrenBooks.map((book) => (
                <BookCard key={book.id} book={book} onFavorite={handleFavorite} isFavorited={isFavorited(book)} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20">
              <Baby className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">No children's books found</p>
            </div>
          )}
        </div>
      )}

      {/* Courses Tab */}
      {activeTab === 'courses' && (
        <div>
          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            </div>
          ) : courses.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {courses.map((course) => (
                <ContentCard key={course.id} item={course} onFavorite={handleFavorite} isFavorited={isFavorited(course)} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20">
              <GraduationCap className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">No courses found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ContentLibrary;
