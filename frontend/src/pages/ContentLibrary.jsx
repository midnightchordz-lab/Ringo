import { useState, useEffect } from 'react';
import api from '../utils/api';
import { 
  Search, BookOpen, GraduationCap, FileText, 
  ExternalLink, Heart, Library, Sparkles, Globe,
  Baby, School, Building2, University, BookMarked, Mic,
  PenTool, FlaskConical, History, ChevronDown, ClipboardList,
  ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, Info,
  Loader2, Zap, BookOpenCheck, FileQuestion, Video, Newspaper,
  Download, Printer, Book, Plus, List, Users, Lock, Unlock,
  Trash2, Edit2, Copy, X, FolderPlus, ChevronLeft, ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

// License Types with metadata
const LICENSE_TYPES = {
  'public-domain': {
    name: 'Public Domain',
    shortName: 'PD',
    commercial: true,
    derivatives: true,
    attribution: false,
    color: 'bg-green-500',
    textColor: 'text-green-400',
    borderColor: 'border-green-500/50',
    description: 'No restrictions. Free to use for any purpose.'
  },
  'cc-by': {
    name: 'CC BY',
    shortName: 'CC BY',
    commercial: true,
    derivatives: true,
    attribution: true,
    color: 'bg-green-500',
    textColor: 'text-green-400',
    borderColor: 'border-green-500/50',
    description: 'Commercial use allowed. Attribution required.'
  },
  'cc-by-sa': {
    name: 'CC BY-SA',
    shortName: 'CC SA',
    commercial: true,
    derivatives: true,
    attribution: true,
    color: 'bg-green-500',
    textColor: 'text-green-400',
    borderColor: 'border-green-500/50',
    description: 'Commercial use allowed. Share alike required.'
  },
  'cc-by-nc': {
    name: 'CC BY-NC',
    shortName: 'NC',
    commercial: false,
    derivatives: true,
    attribution: true,
    color: 'bg-amber-500',
    textColor: 'text-amber-400',
    borderColor: 'border-amber-500/50',
    description: 'Non-commercial use only. Attribution required.'
  },
  'edu-only': {
    name: 'Educational Use',
    shortName: 'EDU',
    commercial: false,
    derivatives: false,
    attribution: false,
    color: 'bg-orange-500',
    textColor: 'text-orange-400',
    borderColor: 'border-orange-500/50',
    description: 'Free for educational/personal use only.'
  },
  'varies': {
    name: 'Varies',
    shortName: 'Varies',
    commercial: null,
    derivatives: null,
    attribution: null,
    color: 'bg-zinc-500',
    textColor: 'text-zinc-400',
    borderColor: 'border-zinc-500/50',
    description: 'Each item has its own license. Check before use.'
  }
};

// Content Categories for filtering
const CATEGORIES = [
  { id: 'all', name: 'All Content', icon: Library, color: 'from-violet-500 to-purple-500' },
  { id: 'childrens-literature', name: "Children's Literature", icon: BookOpenCheck, color: 'from-pink-500 to-rose-500' },
  { id: 'free-books', name: 'Free Books', icon: Book, color: 'from-amber-500 to-orange-500' },
  { id: 'reading-lists', name: 'Reading Lists', icon: List, color: 'from-indigo-500 to-blue-500' },
  { id: 'worksheet', name: 'Worksheets', icon: ClipboardList, color: 'from-lime-500 to-green-500' },
  { id: 'book', name: 'Books', icon: BookOpen, color: 'from-blue-500 to-cyan-500' },
  { id: 'article', name: 'Articles', icon: Newspaper, color: 'from-pink-500 to-rose-500' },
  { id: 'course', name: 'Courses', icon: GraduationCap, color: 'from-green-500 to-emerald-500' },
  { id: 'video', name: 'Videos', icon: Video, color: 'from-red-500 to-orange-500' },
  { id: 'resource', name: 'Resources', icon: FileText, color: 'from-purple-500 to-indigo-500' },
];

// Education Levels
const EDUCATION_LEVELS = [
  { id: 'all', name: 'All Levels', icon: Library },
  { id: 'preschool', name: 'Pre-school', icon: Baby },
  { id: 'elementary', name: 'Elementary (K-5)', icon: School },
  { id: 'middle', name: 'Middle School (6-8)', icon: Building2 },
  { id: 'high', name: 'High School (9-12)', icon: GraduationCap },
  { id: 'university', name: 'University', icon: University },
];

// Quick search suggestions
const SEARCH_SUGGESTIONS = [
  'STEM worksheets',
  'Math practice',
  'Reading comprehension',
  'Science experiments',
  'History lessons',
  'Grammar exercises',
  'Coding tutorials',
  'Art activities'
];

// License Badge Component
const LicenseBadge = ({ license, showFull = false }) => {
  const licenseInfo = LICENSE_TYPES[license] || LICENSE_TYPES['varies'];
  
  return (
    <div className="flex items-center gap-1.5" title={licenseInfo.description}>
      <span className={`px-2 py-0.5 rounded text-xs font-bold ${licenseInfo.color} text-white`}>
        {showFull ? licenseInfo.name : licenseInfo.shortName}
      </span>
      {licenseInfo.commercial === true && (
        <ShieldCheck className="w-3.5 h-3.5 text-green-400" title="Commercial use allowed" />
      )}
      {licenseInfo.commercial === false && (
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400" title="Non-commercial only" />
      )}
    </div>
  );
};

// Get icon for result type
const getTypeIcon = (type) => {
  switch (type) {
    case 'worksheet': return ClipboardList;
    case 'book': return BookOpen;
    case 'article': return Newspaper;
    case 'course': return GraduationCap;
    case 'video': return Video;
    case 'archive': return History;
    default: return FileText;
  }
};

// Get source color
const getSourceColor = (source) => {
  const colors = {
    'OpenLibrary': 'bg-blue-500',
    'Internet Archive': 'bg-amber-600',
    'Wikipedia': 'bg-zinc-600',
    'K5 Learning': 'bg-green-500',
    'Math-Drills': 'bg-purple-500',
    'Common Core Sheets': 'bg-cyan-500',
    'Live Worksheets': 'bg-pink-500',
    'Superstar Worksheets': 'bg-orange-500',
  };
  return colors[source] || 'bg-violet-500';
};

// Dynamic Search Result Card
const SearchResultCard = ({ result, onFavorite, isFavorited }) => {
  const TypeIcon = getTypeIcon(result.type || result.category);
  const licenseInfo = LICENSE_TYPES[result.license] || LICENSE_TYPES['varies'];
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`glass-card p-5 hover:border-violet-500/50 transition-all group ${
        licenseInfo.commercial === false ? `border-l-4 ${licenseInfo.borderColor}` : ''
      }`}
      data-testid="search-result-card"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {result.thumbnail ? (
            <img 
              src={result.thumbnail} 
              alt={result.title}
              className="w-12 h-12 rounded-lg object-cover bg-zinc-800"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'flex';
              }}
            />
          ) : null}
          <div className={`w-12 h-12 rounded-lg bg-gradient-to-br from-violet-500/20 to-purple-500/20 flex items-center justify-center ${result.thumbnail ? 'hidden' : ''}`}>
            <TypeIcon className="w-6 h-6 text-violet-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-white group-hover:text-violet-400 transition-colors line-clamp-1">
              {result.title}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={`px-2 py-0.5 rounded text-xs font-semibold text-white ${getSourceColor(result.source)}`}>
                {result.source}
              </span>
              {result.relevance_score && (
                <span className="text-xs text-[#BEF264] font-semibold flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  {result.relevance_score}/10
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={() => onFavorite(result)}
          className={`p-2 rounded-full transition-all ${
            isFavorited 
              ? 'bg-red-500/20 text-red-500' 
              : 'bg-zinc-800 text-zinc-500 hover:bg-red-500/20 hover:text-red-500'
          }`}
          data-testid="favorite-result-button"
        >
          <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
        </button>
      </div>
      
      {/* License Badge */}
      <div className="mb-3">
        <LicenseBadge license={result.license} />
      </div>
      
      {/* Description */}
      <p className="text-zinc-400 text-sm mb-3 line-clamp-2">
        {result.ai_summary || result.description || 'No description available'}
      </p>
      
      {/* Authors */}
      {result.authors && result.authors.length > 0 && (
        <p className="text-xs text-zinc-500 mb-2">
          By: {result.authors.slice(0, 2).join(', ')}
          {result.year && ` (${result.year})`}
        </p>
      )}
      
      {/* Grade Levels */}
      {result.grade_levels && result.grade_levels.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {result.grade_levels.slice(0, 3).map((level) => (
            <span key={level} className="px-2 py-0.5 bg-violet-500/20 text-violet-300 text-xs rounded-full">
              {level}
            </span>
          ))}
        </div>
      )}
      
      {/* Subjects */}
      {result.subjects && result.subjects.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {result.subjects.slice(0, 3).map((subject, idx) => (
            <span key={idx} className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded-full">
              {typeof subject === 'string' ? subject.slice(0, 30) : subject}
            </span>
          ))}
        </div>
      )}
      
      <div className="flex items-center justify-between">
        <span className="text-xs text-neutral-500 capitalize">{result.type || result.category}</span>
        <Button
          size="sm"
          onClick={() => window.open(result.url, '_blank')}
          className="bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-full px-4"
          data-testid="visit-result-button"
        >
          <ExternalLink className="w-3 h-3 mr-1" />
          Visit
        </Button>
      </div>
    </motion.div>
  );
};

// Free Book Card Component
const FreeBookCard = ({ book, onFavorite, isFavorited, onAddToList, readingLists = [] }) => {
  const [showListMenu, setShowListMenu] = useState(false);
  
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="studio-card p-5 hover:shadow-lg transition-all"
      data-testid="free-book-card"
    >
      <div className="flex gap-4">
        {/* Book Cover */}
        <div className="w-20 h-28 flex-shrink-0 rounded-lg overflow-hidden bg-neutral-100 shadow-md">
          {book.cover ? (
            <img src={book.cover} alt={book.title} className="w-full h-full object-cover" onError={(e) => e.target.style.display = 'none'} />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-amber-100 to-orange-100 flex items-center justify-center">
              <Book className="w-8 h-8 text-amber-600" />
            </div>
          )}
        </div>
        
        {/* Book Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-bold text-neutral-900 line-clamp-2 leading-tight">{book.title}</h3>
            <div className="flex items-center gap-1 flex-shrink-0">
              {/* Add to Reading List Button */}
              <div className="relative">
                <button
                  onClick={() => setShowListMenu(!showListMenu)}
                  className="p-1.5 rounded-full bg-indigo-100 text-indigo-600 hover:bg-indigo-200 transition-all"
                  title="Add to Reading List"
                  data-testid="add-to-list-btn"
                >
                  <FolderPlus className="w-4 h-4" />
                </button>
                {showListMenu && (
                  <div className="absolute right-0 top-8 w-48 bg-white rounded-lg shadow-xl border border-neutral-200 z-50 py-2">
                    <p className="px-3 py-1 text-xs text-neutral-500 font-medium">Add to list:</p>
                    {readingLists.length > 0 ? (
                      readingLists.map(list => (
                        <button
                          key={list.id}
                          onClick={() => {
                            onAddToList(list.id, book);
                            setShowListMenu(false);
                          }}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-indigo-50 flex items-center gap-2"
                        >
                          <List className="w-3 h-3 text-indigo-500" />
                          <span className="truncate">{list.name}</span>
                        </button>
                      ))
                    ) : (
                      <p className="px-3 py-2 text-xs text-neutral-400">No reading lists yet</p>
                    )}
                    <div className="border-t border-neutral-100 mt-1 pt-1">
                      <button
                        onClick={() => {
                          setShowListMenu(false);
                          onAddToList('create-new', book);
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-indigo-600 hover:bg-indigo-50 flex items-center gap-2 font-medium"
                      >
                        <Plus className="w-3 h-3" />
                        Create New List
                      </button>
                    </div>
                  </div>
                )}
              </div>
              {/* Favorite Button */}
              <button
                onClick={() => onFavorite(book)}
                className={`p-1.5 rounded-full transition-all ${
                  isFavorited ? 'bg-red-100 text-red-500' : 'bg-neutral-100 text-neutral-400 hover:bg-red-100 hover:text-red-500'
                }`}
              >
                <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
              </button>
            </div>
          </div>
          
          <p className="text-sm text-blue-600 font-medium mb-2">{book.author}</p>
          
          <div className="flex flex-wrap gap-1.5 mb-3">
            <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full font-medium capitalize">
              {book.category}
            </span>
            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full font-medium flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Public Domain
            </span>
            {book.printable && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium flex items-center gap-1">
                <Printer className="w-3 h-3" /> Printable
              </span>
            )}
          </div>
          
          <p className="text-xs text-neutral-500 line-clamp-2 mb-3">{book.description}</p>
          
          {/* Grade Levels */}
          <div className="flex flex-wrap gap-1 mb-3">
            {book.grade_level?.map((level) => (
              <span key={level} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full capitalize">
                {level}
              </span>
            ))}
          </div>
          
          {/* Download Buttons */}
          <div className="flex flex-wrap gap-2">
            {book.formats?.pdf && (
              <a
                href={book.formats.pdf}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition-colors"
                title="Download from Project Gutenberg"
              >
                <Download className="w-3 h-3" /> Download
              </a>
            )}
            {book.formats?.epub && (
              <a
                href={book.formats.epub}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold rounded-lg transition-colors"
                title="Download EPUB format"
              >
                <Download className="w-3 h-3" /> EPUB
              </a>
            )}
            {book.formats?.html && (
              <a
                href={book.formats.html}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-semibold rounded-lg transition-colors"
                title="Read online in browser"
              >
                <ExternalLink className="w-3 h-3" /> Read Online
              </a>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Reading List Card Component
const ReadingListCard = ({ list, onView, onEdit, onDelete, onCopy, isOwner }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="studio-card p-5 hover:shadow-lg transition-all cursor-pointer"
      onClick={() => onView(list)}
      data-testid="reading-list-card"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center shadow-md">
            <List className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-neutral-900">{list.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-neutral-500">{list.book_count || 0} books</span>
              {list.is_public ? (
                <span className="flex items-center gap-1 text-xs text-emerald-600">
                  <Unlock className="w-3 h-3" /> Public
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-neutral-400">
                  <Lock className="w-3 h-3" /> Private
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {isOwner ? (
            <>
              <button
                onClick={() => onEdit(list)}
                className="p-1.5 rounded-full bg-neutral-100 text-neutral-500 hover:bg-blue-100 hover:text-blue-600 transition-all"
                title="Edit"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDelete(list)}
                className="p-1.5 rounded-full bg-neutral-100 text-neutral-500 hover:bg-red-100 hover:text-red-600 transition-all"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          ) : (
            <button
              onClick={() => onCopy(list)}
              className="p-1.5 rounded-full bg-neutral-100 text-neutral-500 hover:bg-indigo-100 hover:text-indigo-600 transition-all"
              title="Copy to My Lists"
            >
              <Copy className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      
      {list.description && (
        <p className="text-sm text-neutral-500 mb-3 line-clamp-2">{list.description}</p>
      )}
      
      <div className="flex flex-wrap gap-2">
        {list.grade_level && (
          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full capitalize">
            {list.grade_level}
          </span>
        )}
        {list.subject && (
          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full capitalize">
            {list.subject}
          </span>
        )}
      </div>
      
      {/* Preview of books */}
      {list.books && list.books.length > 0 && (
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-neutral-100">
          <div className="flex -space-x-2">
            {list.books.slice(0, 4).map((book, idx) => (
              <div
                key={book.book_id || idx}
                className="w-8 h-10 rounded bg-gradient-to-br from-amber-100 to-orange-100 border-2 border-white flex items-center justify-center"
                title={book.title}
              >
                <Book className="w-4 h-4 text-amber-600" />
              </div>
            ))}
            {list.books.length > 4 && (
              <div className="w-8 h-10 rounded bg-neutral-100 border-2 border-white flex items-center justify-center text-xs font-bold text-neutral-500">
                +{list.books.length - 4}
              </div>
            )}
          </div>
          <span className="text-xs text-neutral-400">Click to view all books</span>
        </div>
      )}
    </motion.div>
  );
};

// Create/Edit Reading List Modal
const ReadingListModal = ({ isOpen, onClose, onSave, editList = null }) => {
  const [name, setName] = useState(editList?.name || '');
  const [description, setDescription] = useState(editList?.description || '');
  const [gradeLevel, setGradeLevel] = useState(editList?.grade_level || '');
  const [subject, setSubject] = useState(editList?.subject || '');
  const [isPublic, setIsPublic] = useState(editList?.is_public || false);
  const [saving, setSaving] = useState(false);
  
  useEffect(() => {
    if (editList) {
      setName(editList.name || '');
      setDescription(editList.description || '');
      setGradeLevel(editList.grade_level || '');
      setSubject(editList.subject || '');
      setIsPublic(editList.is_public || false);
    } else {
      setName('');
      setDescription('');
      setGradeLevel('');
      setSubject('');
      setIsPublic(false);
    }
  }, [editList, isOpen]);
  
  const handleSubmit = async () => {
    if (!name.trim()) {
      toast.error('Please enter a name for the reading list');
      return;
    }
    setSaving(true);
    await onSave({
      name: name.trim(),
      description: description.trim(),
      grade_level: gradeLevel || null,
      subject: subject || null,
      is_public: isPublic
    });
    setSaving(false);
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-neutral-900">
            {editList ? 'Edit Reading List' : 'Create Reading List'}
          </h2>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-neutral-100">
            <X className="w-5 h-5 text-neutral-500" />
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">Name *</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Grade 3 Science Books"
              className="w-full"
              data-testid="list-name-input"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this reading list for?"
              className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              rows={3}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Grade Level</label>
              <select
                value={gradeLevel}
                onChange={(e) => setGradeLevel(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Any Grade</option>
                <option value="preschool">Pre-school</option>
                <option value="elementary">Elementary</option>
                <option value="middle">Middle School</option>
                <option value="high">High School</option>
                <option value="university">University</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Subject</label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-200 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Any Subject</option>
                <option value="stories">Stories</option>
                <option value="poetry">Poetry</option>
                <option value="grammar">Grammar</option>
                <option value="math">Math</option>
                <option value="science">Science</option>
                <option value="history">History</option>
              </select>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-3 bg-neutral-50 rounded-lg">
            <button
              onClick={() => setIsPublic(!isPublic)}
              className={`relative w-12 h-6 rounded-full transition-colors ${isPublic ? 'bg-indigo-500' : 'bg-neutral-300'}`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${isPublic ? 'left-7' : 'left-1'}`} />
            </button>
            <div>
              <p className="text-sm font-medium text-neutral-700 flex items-center gap-2">
                {isPublic ? <Unlock className="w-4 h-4 text-emerald-500" /> : <Lock className="w-4 h-4 text-neutral-400" />}
                {isPublic ? 'Public List' : 'Private List'}
              </p>
              <p className="text-xs text-neutral-500">
                {isPublic ? 'Other teachers can discover and copy this list' : 'Only you can see this list'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex gap-3 mt-6">
          <Button onClick={onClose} variant="outline" className="flex-1">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={saving || !name.trim()}
            className="flex-1 bg-indigo-500 hover:bg-indigo-600 text-white"
            data-testid="save-list-btn"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            {editList ? 'Save Changes' : 'Create List'}
          </Button>
        </div>
      </motion.div>
    </div>
  );
};

// View Reading List Detail Modal
const ReadingListDetailModal = ({ isOpen, onClose, list, onRemoveBook }) => {
  if (!isOpen || !list) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-neutral-100">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center">
                <List className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-neutral-900">{list.name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm text-neutral-500">{list.book_count || 0} books</span>
                  {list.is_public && <span className="text-xs text-emerald-600 flex items-center gap-1"><Unlock className="w-3 h-3" /> Public</span>}
                </div>
              </div>
            </div>
            <button onClick={onClose} className="p-2 rounded-full hover:bg-neutral-100">
              <X className="w-5 h-5 text-neutral-500" />
            </button>
          </div>
          {list.description && <p className="text-sm text-neutral-500 mt-3">{list.description}</p>}
          <div className="flex gap-2 mt-3">
            {list.grade_level && <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full capitalize">{list.grade_level}</span>}
            {list.subject && <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full capitalize">{list.subject}</span>}
          </div>
        </div>
        
        {/* Books List */}
        <div className="flex-1 overflow-y-auto p-6">
          {list.books && list.books.length > 0 ? (
            <div className="space-y-3">
              {list.books.map((book) => (
                <div key={book.book_id} className="flex items-center gap-4 p-3 bg-neutral-50 rounded-xl">
                  <div className="w-12 h-16 rounded-lg bg-gradient-to-br from-amber-100 to-orange-100 flex items-center justify-center flex-shrink-0">
                    <Book className="w-6 h-6 text-amber-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-neutral-900 truncate">{book.title}</h4>
                    <p className="text-sm text-blue-600">{book.author}</p>
                    <span className="text-xs text-neutral-400 capitalize">{book.category}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {book.formats?.pdf && (
                      <a href={book.formats.pdf} target="_blank" rel="noopener noreferrer" className="p-2 bg-red-100 text-red-600 rounded-lg hover:bg-red-200 transition-colors">
                        <Download className="w-4 h-4" />
                      </a>
                    )}
                    {onRemoveBook && (
                      <button
                        onClick={() => onRemoveBook(list.id, book.book_id)}
                        className="p-2 bg-neutral-100 text-neutral-500 rounded-lg hover:bg-red-100 hover:text-red-600 transition-colors"
                        title="Remove from list"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Book className="w-16 h-16 text-neutral-200 mx-auto mb-4" />
              <p className="text-neutral-500">No books in this list yet</p>
              <p className="text-sm text-neutral-400 mt-1">Add books from the Free Books section</p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

// Pagination Component
const PaginationControls = ({ 
  currentPage, 
  totalPages, 
  totalItems, 
  perPage,
  onPageChange, 
  isLoading 
}) => {
  if (totalPages <= 1) return null;
  
  const startItem = (currentPage - 1) * perPage + 1;
  const endItem = Math.min(currentPage * perPage, totalItems);
  
  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - 2);
    let end = Math.min(totalPages, start + maxVisible - 1);
    
    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }
    
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  };
  
  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 p-4 bg-white rounded-xl shadow-sm border border-neutral-100" data-testid="pagination-controls">
      {/* Results info */}
      <div className="text-sm text-neutral-600">
        Showing <span className="font-semibold text-neutral-900">{startItem}-{endItem}</span> of{' '}
        <span className="font-semibold text-neutral-900">{totalItems}</span> results
      </div>
      
      {/* Page controls */}
      <div className="flex items-center gap-2">
        {/* Previous button */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1 || isLoading}
          className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentPage === 1 || isLoading
              ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed'
              : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
          }`}
          data-testid="pagination-prev"
        >
          <ChevronLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Previous</span>
        </button>
        
        {/* Page numbers */}
        <div className="flex items-center gap-1">
          {getPageNumbers()[0] > 1 && (
            <>
              <button
                onClick={() => onPageChange(1)}
                disabled={isLoading}
                className="w-10 h-10 rounded-lg text-sm font-medium bg-neutral-100 text-neutral-700 hover:bg-neutral-200 transition-colors"
              >
                1
              </button>
              {getPageNumbers()[0] > 2 && (
                <span className="px-2 text-neutral-400">...</span>
              )}
            </>
          )}
          
          {getPageNumbers().map((page) => (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              disabled={isLoading}
              className={`w-10 h-10 rounded-lg text-sm font-medium transition-all ${
                currentPage === page
                  ? 'bg-gradient-to-r from-emerald-500 to-green-600 text-white shadow-md'
                  : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
              }`}
              data-testid={`pagination-page-${page}`}
            >
              {page}
            </button>
          ))}
          
          {getPageNumbers()[getPageNumbers().length - 1] < totalPages && (
            <>
              {getPageNumbers()[getPageNumbers().length - 1] < totalPages - 1 && (
                <span className="px-2 text-neutral-400">...</span>
              )}
              <button
                onClick={() => onPageChange(totalPages)}
                disabled={isLoading}
                className="w-10 h-10 rounded-lg text-sm font-medium bg-neutral-100 text-neutral-700 hover:bg-neutral-200 transition-colors"
              >
                {totalPages}
              </button>
            </>
          )}
        </div>
        
        {/* Next button */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages || isLoading}
          className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
            currentPage === totalPages || isLoading
              ? 'bg-neutral-100 text-neutral-400 cursor-not-allowed'
              : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
          }`}
          data-testid="pagination-next"
        >
          <span className="hidden sm:inline">Next</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export const ContentLibrary = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [favorites, setFavorites] = useState([]);
  const [showFavorites, setShowFavorites] = useState(false);
  const [showLevelDropdown, setShowLevelDropdown] = useState(false);
  const [searchSources, setSearchSources] = useState([]);
  const [freeBooks, setFreeBooks] = useState([]);
  const [loadingBooks, setLoadingBooks] = useState(false);
  
  // Children's Literature State
  const [childrensLiterature, setChildrensLiterature] = useState([]);
  const [loadingChildrens, setLoadingChildrens] = useState(false);
  
  // Reading Lists State
  const [readingLists, setReadingLists] = useState([]);
  const [loadingLists, setLoadingLists] = useState(false);
  const [showListModal, setShowListModal] = useState(false);
  const [editingList, setEditingList] = useState(null);
  const [selectedList, setSelectedList] = useState(null);
  const [showListDetail, setShowListDetail] = useState(false);
  const [includePublicLists, setIncludePublicLists] = useState(false);
  const [pendingBook, setPendingBook] = useState(null);
  
  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [perPage] = useState(50);
  
  // Pagination state for different sections
  const [childrensPage, setChildrensPage] = useState(1);
  const [childrensTotalPages, setChildrensTotalPages] = useState(1);
  const [childrensTotalResults, setChildrensTotalResults] = useState(0);
  
  const [freeBooksPage, setFreeBooksPage] = useState(1);
  const [freeBooksTotalPages, setFreeBooksTotalPages] = useState(1);
  const [freeBooksTotalResults, setFreeBooksTotalResults] = useState(0);
  
  const [searchPage, setSearchPage] = useState(1);
  const [searchTotalPages, setSearchTotalPages] = useState(1);
  const [searchTotalResults, setSearchTotalResults] = useState(0);

  useEffect(() => {
    fetchFavorites();
    fetchReadingLists();
  }, []);
  
  // Fetch children's literature when category changes or on initial load
  useEffect(() => {
    if (selectedCategory === 'childrens-literature') {
      fetchChildrensLiterature();
    }
  }, [selectedCategory, selectedLevel]);
  
  const fetchChildrensLiterature = async (query = '', page = 1) => {
    setLoadingChildrens(true);
    try {
      const response = await api.get('/content-library/childrens-literature', {
        params: {
          query: query,
          grade: selectedLevel !== 'all' ? selectedLevel : 'all',
          page: page,
          per_page: perPage
        }
      });
      setChildrensLiterature(response.data.results || []);
      setSearchSources(response.data.sources || []);
      setChildrensPage(response.data.page || 1);
      setChildrensTotalPages(response.data.total_pages || 1);
      setChildrensTotalResults(response.data.total || 0);
      if (response.data.results?.length > 0 && page === 1) {
        toast.success(`Found ${response.data.total} copyright-free children's books!`);
      }
    } catch (error) {
      console.error('Error fetching children\'s literature:', error);
      toast.error('Failed to search children\'s literature');
    } finally {
      setLoadingChildrens(false);
    }
  };
  
  // Fetch reading lists
  const fetchReadingLists = async () => {
    setLoadingLists(true);
    try {
      const response = await api.get('/reading-lists', { params: { include_public: includePublicLists } });
      setReadingLists(response.data.reading_lists || []);
    } catch (error) {
      console.error('Error fetching reading lists:', error);
    } finally {
      setLoadingLists(false);
    }
  };
  
  // Refetch when include_public changes
  useEffect(() => {
    if (selectedCategory === 'reading-lists') {
      fetchReadingLists();
    }
  }, [includePublicLists, selectedCategory]);

  // Create or update reading list
  const handleSaveList = async (listData) => {
    try {
      if (editingList) {
        await api.put(`/reading-lists/${editingList.id}`, listData);
        toast.success('Reading list updated!');
      } else {
        const response = await api.post('/reading-lists', listData);
        // If there's a pending book, add it to the new list
        if (pendingBook && response.data.reading_list) {
          await handleAddBookToList(response.data.reading_list.id, pendingBook);
        }
        toast.success('Reading list created!');
      }
      setShowListModal(false);
      setEditingList(null);
      setPendingBook(null);
      fetchReadingLists();
    } catch (error) {
      console.error('Error saving reading list:', error);
      toast.error('Failed to save reading list');
    }
  };
  
  // Delete reading list
  const handleDeleteList = async (list) => {
    if (!confirm(`Delete "${list.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/reading-lists/${list.id}`);
      toast.success('Reading list deleted');
      fetchReadingLists();
    } catch (error) {
      console.error('Error deleting reading list:', error);
      toast.error('Failed to delete reading list');
    }
  };
  
  // Copy a public reading list
  const handleCopyList = async (list) => {
    try {
      await api.post(`/reading-lists/${list.id}/copy`);
      toast.success('Reading list copied to your lists!');
      fetchReadingLists();
    } catch (error) {
      console.error('Error copying reading list:', error);
      toast.error('Failed to copy reading list');
    }
  };
  
  // Add book to reading list
  const handleAddBookToList = async (listId, book) => {
    if (listId === 'create-new') {
      setPendingBook(book);
      setEditingList(null);
      setShowListModal(true);
      return;
    }
    
    try {
      await api.post(`/reading-lists/${listId}/books`, {
        book_id: book.id,
        title: book.title,
        author: book.author,
        category: book.category,
        cover: book.cover,
        formats: book.formats
      });
      toast.success(`Added "${book.title}" to reading list!`);
      fetchReadingLists();
    } catch (error) {
      if (error.response?.status === 400) {
        toast.error('Book already in this reading list');
      } else {
        console.error('Error adding book to list:', error);
        toast.error('Failed to add book to list');
      }
    }
  };
  
  // Remove book from reading list
  const handleRemoveBookFromList = async (listId, bookId) => {
    try {
      await api.delete(`/reading-lists/${listId}/books/${bookId}`);
      toast.success('Book removed from list');
      // Refresh the selected list
      const response = await api.get(`/reading-lists/${listId}`);
      setSelectedList(response.data.reading_list);
      fetchReadingLists();
    } catch (error) {
      console.error('Error removing book from list:', error);
      toast.error('Failed to remove book');
    }
  };

  useEffect(() => {
    fetchFavorites();
  }, []);

  // Fetch free books when category changes to free-books
  useEffect(() => {
    if (selectedCategory === 'free-books') {
      fetchFreeBooks();
    }
  }, [selectedCategory, selectedLevel]);

  const fetchFreeBooks = async (page = 1) => {
    setLoadingBooks(true);
    try {
      const params = { page: page, per_page: perPage };
      if (selectedLevel !== 'all') {
        params.grade = selectedLevel;
      }
      const response = await api.get('/content-library/free-books', { params });
      setFreeBooks(response.data.books || []);
      setFreeBooksPage(response.data.page || 1);
      setFreeBooksTotalPages(response.data.total_pages || 1);
      setFreeBooksTotalResults(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching free books:', error);
      toast.error('Failed to load free books');
    } finally {
      setLoadingBooks(false);
    }
  };

  const fetchFavorites = async () => {
    try {
      const response = await api.get('/content-library/favorites');
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
    
    setIsSearching(true);
    setHasSearched(true);
    
    // If in children's literature category, search children's books
    if (selectedCategory === 'childrens-literature') {
      try {
        const response = await api.get('/content-library/childrens-literature', {
          params: { 
            query: searchQuery,
            grade: selectedLevel !== 'all' ? selectedLevel : 'all',
            page: page,
            per_page: perPage
          }
        });
        setChildrensLiterature(response.data.results || []);
        setSearchSources(response.data.sources || []);
        setChildrensPage(response.data.page || 1);
        setChildrensTotalPages(response.data.total_pages || 1);
        setChildrensTotalResults(response.data.total || 0);
        if (page === 1) {
          toast.success(`Found ${response.data.total} copyright-free children's books!`);
        }
      } catch (error) {
        console.error('Error searching children\'s literature:', error);
        toast.error('Search failed');
      } finally {
        setIsSearching(false);
      }
      return;
    }
    
    // If in free-books category, search within free books
    if (selectedCategory === 'free-books') {
      try {
        const response = await api.get('/content-library/free-books/search', {
          params: { 
            query: searchQuery,
            grade: selectedLevel !== 'all' ? selectedLevel : undefined,
            page: page,
            per_page: perPage
          }
        });
        setFreeBooks(response.data.books || []);
        setFreeBooksPage(response.data.page || 1);
        setFreeBooksTotalPages(response.data.total_pages || 1);
        setFreeBooksTotalResults(response.data.total || 0);
        if (page === 1) {
          toast.success(`Found ${response.data.total} books!`);
        }
      } catch (error) {
        console.error('Error searching free books:', error);
        toast.error('Search failed');
      } finally {
        setIsSearching(false);
      }
      return;
    }
    
    try {
      const response = await api.get('/content-library/search', {
        params: {
          query: searchQuery,
          category: selectedCategory,
          grade: selectedLevel !== 'all' ? selectedLevel : undefined,
          page: page,
          per_page: perPage
        }
      });
      
      setSearchResults(response.data.results || []);
      setSearchSources(response.data.sources || []);
      setSearchPage(response.data.page || 1);
      setSearchTotalPages(response.data.total_pages || 1);
      setSearchTotalResults(response.data.total || 0);
      if (page === 1) {
        toast.success(`Found ${response.data.total} resources!`);
      }
    } catch (error) {
      console.error('Error searching content:', error);
      toast.error('Search failed. Please try again.');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleFavorite = async (resource) => {
    const resourceId = resource.id;
    const isFav = favorites.some(f => f.resource_id === resourceId);
    
    try {
      if (isFav) {
        await api.delete(`/content-library/favorites/${resourceId}`);
        setFavorites(favorites.filter(f => f.resource_id !== resourceId));
        toast.success('Removed from favorites');
      } else {
        await api.post('/content-library/favorites', {
          resource_id: resourceId,
          name: resource.title,
          description: resource.description || resource.ai_summary,
          url: resource.url,
          logo: resource.thumbnail || '📚',
          categories: [resource.type || resource.category],
          levels: resource.grade_levels || ['all']
        });
        setFavorites([...favorites, { ...resource, resource_id: resourceId }]);
        toast.success('Added to favorites!');
      }
    } catch (error) {
      console.error('Error updating favorite:', error);
      toast.error('Failed to update favorites');
    }
  };

  const isFavorited = (resourceId) => {
    return favorites.some(f => f.resource_id === resourceId);
  };

  // Pagination handlers
  const handleChildrensPageChange = (newPage) => {
    setChildrensPage(newPage);
    fetchChildrensLiterature(searchQuery, newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  const handleFreeBooksPageChange = (newPage) => {
    setFreeBooksPage(newPage);
    fetchFreeBooks(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  
  const handleSearchPageChange = (newPage) => {
    setSearchPage(newPage);
    handleSearch(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Filter results by category
  let displayResults = searchResults;
  if (selectedCategory !== 'all') {
    displayResults = searchResults.filter(r => 
      (r.type || r.category) === selectedCategory
    );
  }

  const selectedLevelInfo = EDUCATION_LEVELS.find(l => l.id === selectedLevel);

  return (
    <div className="p-6 lg:p-8 pb-24 lg:pb-8 bg-neutral-50 min-h-screen">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-green-600 rounded-xl flex items-center justify-center shadow-lg">
            <Library className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Content Library
            </h1>
            <p className="text-neutral-500">Search copyright-free educational resources across the web</p>
          </div>
        </div>
      </div>

      {/* AI-Powered Badge */}
      <div className="studio-card p-4 mb-6 border-l-4 border-purple-500 bg-purple-50">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-purple-800">AI-Powered Search</span>
              <Zap className="w-4 h-4 text-amber-500" />
            </div>
            <p className="text-xs text-purple-700">
              Searches <span className="text-blue-600 font-semibold">OpenLibrary</span>, 
              <span className="text-amber-600 font-semibold"> Internet Archive</span>, 
              <span className="text-neutral-700 font-semibold"> Wikipedia</span>, and 
              <span className="text-emerald-600 font-semibold"> educational worksheet sites</span> 
              {' '}for free content. AI categorizes and ranks results.
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="studio-card p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
              <Input
                data-testid="library-search-input"
                type="text"
                placeholder="Search for worksheets, books, articles... (e.g., 'STEM worksheets', 'math practice')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="studio-input-icon w-full"
              />
            </div>
            <Button
              data-testid="library-find-button"
              onClick={handleSearch}
              disabled={isSearching}
              className="btn-primary min-w-[100px]"
            >
              {isSearching ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'Find'
              )}
            </Button>
          </div>
          
          {/* Education Level Dropdown */}
          <div className="relative">
            <Button
              onClick={() => setShowLevelDropdown(!showLevelDropdown)}
              className="h-12 px-4 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-xl flex items-center gap-2 min-w-[200px] justify-between font-semibold"
              data-testid="level-dropdown"
            >
              <div className="flex items-center gap-2">
                {selectedLevelInfo && <selectedLevelInfo.icon className="w-4 h-4" />}
                <span className="text-sm whitespace-nowrap">{selectedLevelInfo?.name || 'All Levels'}</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${showLevelDropdown ? 'rotate-180' : ''}`} />
            </Button>
            
            <AnimatePresence>
              {showLevelDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 top-14 left-0 min-w-[220px] bg-white border border-neutral-200 rounded-xl shadow-xl overflow-hidden"
                >
                  {EDUCATION_LEVELS.map((level) => (
                    <button
                      key={level.id}
                      onClick={() => {
                        setSelectedLevel(level.id);
                        setShowLevelDropdown(false);
                      }}
                      className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-neutral-50 transition-colors ${
                        selectedLevel === level.id ? 'bg-emerald-50 text-emerald-700' : 'text-neutral-700'
                      }`}
                    >
                      <level.icon className="w-4 h-4 flex-shrink-0" />
                      <span className="text-sm font-medium whitespace-nowrap">{level.name}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Favorites Toggle */}
          <Button
            onClick={() => setShowFavorites(!showFavorites)}
            className={`h-12 px-6 rounded-xl flex items-center gap-2 font-semibold ${
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

        {/* Quick Search Suggestions */}
        {!hasSearched && (
          <div className="mt-4 pt-4 border-t border-neutral-200">
            <p className="text-xs text-neutral-500 mb-2">Quick searches:</p>
            <div className="flex flex-wrap gap-2">
              {SEARCH_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setSearchQuery(suggestion);
                    setTimeout(() => handleSearch(), 100);
                  }}
                  className="px-3 py-1.5 bg-neutral-100 hover:bg-neutral-200 text-neutral-600 hover:text-neutral-900 text-xs rounded-full transition-colors font-medium"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2 mb-6 overflow-x-auto pb-2">
        {CATEGORIES.map((category) => {
          const Icon = category.icon;
          const isActive = selectedCategory === category.id;
          return (
            <Button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`rounded-full px-4 py-2 flex items-center gap-2 whitespace-nowrap transition-all font-medium ${
                isActive
                  ? `bg-gradient-to-r ${category.color} text-white shadow-lg scale-105`
                  : 'bg-white border-2 border-neutral-200 text-neutral-700 hover:border-neutral-400 hover:bg-neutral-50 shadow-sm'
              }`}
              data-testid={`category-${category.id}`}
            >
              <Icon className={`w-4 h-4 ${isActive ? '' : 'text-neutral-500'}`} />
              {category.name}
            </Button>
          );
        })}
      </div>

      {/* Loading State */}
      {(isSearching || loadingBooks) && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-neutral-600">
              {selectedCategory === 'free-books' ? 'Loading free books...' : 'Searching across multiple sources...'}
            </p>
            <p className="text-xs text-neutral-500 mt-2">
              {selectedCategory === 'free-books' ? 'Project Gutenberg • Internet Archive' : 'OpenLibrary • Internet Archive • Wikipedia • Educational Sites'}
            </p>
          </div>
        </div>
      )}

      {/* Children's Literature View */}
      {!isSearching && !loadingChildrens && selectedCategory === 'childrens-literature' && !showFavorites && (
        <div data-testid="childrens-literature-section">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-neutral-800 flex items-center gap-2">
                  <BookOpenCheck className="w-6 h-6 text-pink-500" />
                  Copyright-Free Children's Literature
                </h2>
                <p className="text-sm text-neutral-500 mt-1">
                  Public domain & Creative Commons books from Project Gutenberg, StoryWeaver & Open Library
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>All books are free to download, print & share</span>
              </div>
            </div>
            
            {/* Sources */}
            {searchSources.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {searchSources.map((source) => (
                  <span key={source} className="px-3 py-1 bg-pink-100 text-pink-700 text-xs rounded-full font-medium">
                    {source}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          {/* Results Count */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-neutral-600">
              Showing <span className="text-pink-600 font-bold">{childrensTotalResults}</span> children's books
              {childrensTotalPages > 1 && (
                <span className="text-neutral-500 ml-2">(Page {childrensPage} of {childrensTotalPages})</span>
              )}
            </p>
          </div>

          {/* Results Grid */}
          {childrensLiterature.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <AnimatePresence>
                {childrensLiterature.map((book) => (
                  <motion.div
                    key={book.id}
                    layout
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="studio-card p-5 hover:shadow-lg transition-all"
                  >
                    <div className="flex gap-4">
                      {/* Book Cover */}
                      <div className="w-20 h-28 flex-shrink-0 rounded-lg overflow-hidden bg-neutral-100 shadow-md">
                        {book.cover ? (
                          <img src={book.cover} alt={book.title} className="w-full h-full object-cover" onError={(e) => e.target.style.display = 'none'} />
                        ) : (
                          <div className="w-full h-full bg-gradient-to-br from-pink-100 to-rose-100 flex items-center justify-center">
                            <Book className="w-8 h-8 text-pink-600" />
                          </div>
                        )}
                      </div>
                      
                      {/* Book Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h3 className="font-bold text-neutral-900 line-clamp-2 leading-tight">{book.title}</h3>
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <button
                              onClick={() => handleFavorite(book)}
                              className={`p-1.5 rounded-full transition-all ${
                                isFavorited(book.id) ? 'bg-red-100 text-red-500' : 'bg-neutral-100 text-neutral-400 hover:bg-red-100 hover:text-red-500'
                              }`}
                            >
                              <Heart className="w-4 h-4" fill={isFavorited(book.id) ? 'currentColor' : 'none'} />
                            </button>
                          </div>
                        </div>
                        
                        <p className="text-sm text-blue-600 font-medium mb-2">{book.author}</p>
                        
                        <div className="flex flex-wrap gap-1.5 mb-3">
                          <span className="px-2 py-0.5 bg-pink-100 text-pink-700 text-xs rounded-full font-medium">
                            {book.source}
                          </span>
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full font-medium flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> {book.license}
                          </span>
                          {book.printable && (
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium flex items-center gap-1">
                              <Printer className="w-3 h-3" /> Printable
                            </span>
                          )}
                        </div>
                        
                        <p className="text-xs text-neutral-500 line-clamp-2 mb-3">{book.description}</p>
                        
                        {/* Grade Levels */}
                        <div className="flex flex-wrap gap-1 mb-3">
                          {book.grade_level?.map((level) => (
                            <span key={level} className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full capitalize">
                              {level}
                            </span>
                          ))}
                        </div>
                        
                        {/* Download Buttons */}
                        <div className="flex flex-wrap gap-2">
                          {book.formats?.pdf && (
                            <a
                              href={book.formats.pdf}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition-colors"
                              title="Download from Project Gutenberg"
                            >
                              <Download className="w-3 h-3" /> Download
                            </a>
                          )}
                          {book.formats?.epub && (
                            <a
                              href={book.formats.epub}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold rounded-lg transition-colors"
                              title="Download EPUB format"
                            >
                              <Download className="w-3 h-3" /> EPUB
                            </a>
                          )}
                          {book.formats?.html && (
                            <a
                              href={book.formats.html}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-semibold rounded-lg transition-colors"
                              title="Read online in browser"
                            >
                              <ExternalLink className="w-3 h-3" /> Read Online
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="studio-card p-16 text-center">
              <BookOpenCheck className="w-20 h-20 text-pink-200 mx-auto mb-6" strokeWidth={1.5} />
              <h3 className="text-xl font-bold text-neutral-800 mb-2">Search for Children's Literature</h3>
              <p className="text-neutral-500 mb-6 max-w-md mx-auto">
                Enter a search term above to find copyright-free children's books from Project Gutenberg, StoryWeaver, and Open Library.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {['fairy tales', 'adventure stories', 'nursery rhymes', 'classic children', 'picture books'].map((term) => (
                  <button
                    key={term}
                    onClick={() => {
                      setSearchQuery(term);
                      setTimeout(() => {
                        fetchChildrensLiterature(term);
                      }, 100);
                    }}
                    className="px-4 py-2 bg-pink-100 text-pink-700 rounded-full text-sm hover:bg-pink-200 transition-colors"
                  >
                    {term}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* Pagination for Children's Literature */}
          {childrensLiterature.length > 0 && (
            <PaginationControls
              currentPage={childrensPage}
              totalPages={childrensTotalPages}
              totalItems={childrensTotalResults}
              perPage={perPage}
              onPageChange={handleChildrensPageChange}
              isLoading={loadingChildrens}
            />
          )}
        </div>
      )}

      {/* Loading State for Children's Literature */}
      {loadingChildrens && selectedCategory === 'childrens-literature' && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-pink-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-neutral-600">Searching copyright-free children's books...</p>
            <p className="text-xs text-neutral-500 mt-2">Project Gutenberg • StoryWeaver • Open Library</p>
          </div>
        </div>
      )}

      {/* Free Books View */}
      {!isSearching && !loadingBooks && selectedCategory === 'free-books' && !showFavorites && (
        <div data-testid="free-books-section">
          {/* Category Filter Pills for Free Books */}
          <div className="flex flex-wrap gap-2 mb-6">
            {['all', 'stories', 'poetry', 'grammar', 'math', 'science'].map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  const params = { page: 1, per_page: perPage };
                  if (cat !== 'all') params.category = cat;
                  if (selectedLevel !== 'all') params.grade = selectedLevel;
                  api.get('/content-library/free-books', { params })
                    .then(res => {
                      setFreeBooks(res.data.books || []);
                      setFreeBooksPage(res.data.page || 1);
                      setFreeBooksTotalPages(res.data.total_pages || 1);
                      setFreeBooksTotalResults(res.data.total || 0);
                    })
                    .catch(err => console.error(err));
                }}
                className={`px-4 py-2 rounded-full text-sm font-medium capitalize transition-all ${
                  cat === 'all' 
                    ? 'bg-amber-500 text-white shadow-md'
                    : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                }`}
                data-testid={`free-books-filter-${cat}`}
              >
                {cat === 'all' ? '📚 All Books' : cat}
              </button>
            ))}
          </div>

          {/* Books Count */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-neutral-600">
              Showing <span className="text-amber-600 font-bold">{freeBooksTotalResults}</span> free downloadable books
            </p>
            <div className="flex items-center gap-2 text-xs text-neutral-500">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>All books are public domain - free to download and print</span>
            </div>
          </div>

          {/* Books Grid */}
          {freeBooks.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <AnimatePresence>
                {freeBooks.map((book) => (
                  <FreeBookCard
                    key={book.id}
                    book={book}
                    onFavorite={handleFavorite}
                    isFavorited={isFavorited(book.id)}
                    onAddToList={handleAddBookToList}
                    readingLists={readingLists}
                  />
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="studio-card p-16 text-center">
              <Book className="w-20 h-20 text-amber-300 mx-auto mb-6" strokeWidth={1.5} />
              <h3 className="text-xl font-bold text-neutral-800 mb-2">No Books Found</h3>
              <p className="text-neutral-500 mb-6">Try selecting a different category or grade level</p>
              <Button
                onClick={() => {
                  fetchFreeBooks(1);
                }}
                className="bg-amber-500 hover:bg-amber-600 text-white rounded-full px-6"
              >
                Show All Books
              </Button>
            </div>
          )}
          
          {/* Pagination for Free Books */}
          {freeBooks.length > 0 && (
            <PaginationControls
              currentPage={freeBooksPage}
              totalPages={freeBooksTotalPages}
              totalItems={freeBooksTotalResults}
              perPage={perPage}
              onPageChange={handleFreeBooksPageChange}
              isLoading={loadingBooks}
            />
          )}
        </div>
      )}

      {/* Reading Lists View */}
      {!isSearching && !loadingLists && selectedCategory === 'reading-lists' && !showFavorites && (
        <div data-testid="reading-lists-section">
          {/* Header with Create Button */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-neutral-800 flex items-center gap-2">
                <List className="w-6 h-6 text-indigo-500" />
                My Reading Lists
              </h2>
              <p className="text-sm text-neutral-500 mt-1">Create curated book collections for your classes</p>
            </div>
            <Button
              onClick={() => {
                setEditingList(null);
                setShowListModal(true);
              }}
              className="bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl flex items-center gap-2"
              data-testid="create-list-btn"
            >
              <Plus className="w-4 h-4" />
              Create List
            </Button>
          </div>
          
          {/* Toggle for Public Lists */}
          <div className="studio-card p-4 mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Users className="w-5 h-5 text-indigo-500" />
              <div>
                <p className="font-medium text-neutral-800">Discover Public Lists</p>
                <p className="text-xs text-neutral-500">See reading lists shared by other teachers</p>
              </div>
            </div>
            <button
              onClick={() => setIncludePublicLists(!includePublicLists)}
              className={`relative w-12 h-6 rounded-full transition-colors ${includePublicLists ? 'bg-indigo-500' : 'bg-neutral-300'}`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${includePublicLists ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
          
          {/* Lists Grid */}
          {readingLists.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {readingLists.map((list) => (
                  <ReadingListCard
                    key={list.id}
                    list={list}
                    onView={(l) => {
                      setSelectedList(l);
                      setShowListDetail(true);
                    }}
                    onEdit={(l) => {
                      setEditingList(l);
                      setShowListModal(true);
                    }}
                    onDelete={handleDeleteList}
                    onCopy={handleCopyList}
                    isOwner={true} // TODO: Check actual ownership
                  />
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="studio-card p-16 text-center">
              <List className="w-20 h-20 text-indigo-200 mx-auto mb-6" strokeWidth={1.5} />
              <h3 className="text-xl font-bold text-neutral-800 mb-2">No Reading Lists Yet</h3>
              <p className="text-neutral-500 mb-6 max-w-md mx-auto">
                Create your first reading list to organize books for your students. 
                Perfect for lesson planning and class assignments!
              </p>
              <Button
                onClick={() => {
                  setEditingList(null);
                  setShowListModal(true);
                }}
                className="bg-indigo-500 hover:bg-indigo-600 text-white rounded-full px-6"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Your First List
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Search Results */}
      {!isSearching && hasSearched && displayResults.length > 0 && !showFavorites && selectedCategory !== 'free-books' && selectedCategory !== 'reading-lists' && selectedCategory !== 'childrens-literature' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-neutral-600">
              Found <span className="text-emerald-600 font-bold">{searchTotalResults}</span> resources
              {searchSources.length > 0 && (
                <span className="text-xs text-neutral-500 ml-2">
                  from {searchSources.join(', ')}
                </span>
              )}
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {displayResults.map((result) => (
                <SearchResultCard
                  key={result.id}
                  result={result}
                  onFavorite={handleFavorite}
                  isFavorited={isFavorited(result.id)}
                />
              ))}
            </AnimatePresence>
          </div>
          
          {/* Pagination for Search Results */}
          <PaginationControls
            currentPage={searchPage}
            totalPages={searchTotalPages}
            totalItems={searchTotalResults}
            perPage={perPage}
            onPageChange={handleSearchPageChange}
            isLoading={isSearching}
          />
        </div>
      )}

      {/* Favorites View */}
      {!isSearching && showFavorites && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Heart className="w-5 h-5 text-red-500" fill="currentColor" />
            <h2 className="text-xl font-bold text-white">My Favorites</h2>
          </div>
          {favorites.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {favorites.map((fav) => (
                  <SearchResultCard
                    key={fav.resource_id}
                    result={{
                      id: fav.resource_id,
                      title: fav.name,
                      description: fav.description,
                      url: fav.url,
                      thumbnail: fav.logo && fav.logo.length > 2 ? fav.logo : null,
                      type: fav.categories?.[0] || 'resource',
                      license: 'varies',
                      grade_levels: fav.levels
                    }}
                    onFavorite={handleFavorite}
                    isFavorited={true}
                  />
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="glass-card p-20 text-center">
              <Heart className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
              <h3 className="text-xl font-bold text-white mb-2">No Favorites Yet</h3>
              <p className="text-zinc-500 mb-6">Search for content and click the heart icon to save them here</p>
              <Button
                onClick={() => setShowFavorites(false)}
                className="bg-violet-600 hover:bg-violet-500 text-white rounded-full px-6"
              >
                Start Searching
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Empty Search State */}
      {!isSearching && hasSearched && displayResults.length === 0 && !showFavorites && selectedCategory !== 'free-books' && selectedCategory !== 'reading-lists' && selectedCategory !== 'childrens-literature' && (
        <div className="glass-card p-20 text-center">
          <FileQuestion className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">No Results Found</h3>
          <p className="text-zinc-500 mb-6">Try different keywords or browse suggestions below</p>
          <div className="flex flex-wrap justify-center gap-2">
            {SEARCH_SUGGESTIONS.slice(0, 5).map((suggestion) => (
              <Button
                key={suggestion}
                onClick={() => {
                  setSearchQuery(suggestion);
                  setTimeout(() => handleSearch(), 100);
                }}
                variant="outline"
                className="rounded-full border-zinc-700 text-zinc-400 hover:bg-zinc-800"
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Initial State - Before Search */}
      {!isSearching && !loadingBooks && !loadingChildrens && !hasSearched && !showFavorites && selectedCategory !== 'free-books' && selectedCategory !== 'reading-lists' && selectedCategory !== 'childrens-literature' && (
        <div className="studio-card p-16 text-center">
          <BookOpenCheck className="w-24 h-24 text-emerald-500/50 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-2xl font-bold text-neutral-800 mb-3">Discover Free Educational Content</h3>
          <p className="text-neutral-500 mb-8 max-w-lg mx-auto">
            Search millions of copyright-free resources including worksheets, books, articles, 
            and educational materials from trusted sources worldwide.
          </p>
          
          {/* Featured Sources */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto mb-8">
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-center">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                <BookOpen className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-xs font-semibold text-neutral-800">OpenLibrary</p>
              <p className="text-xs text-neutral-500">3M+ Books</p>
            </div>
            <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 text-center">
              <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                <History className="w-5 h-5 text-amber-500" />
              </div>
              <p className="text-xs font-semibold text-neutral-800">Internet Archive</p>
              <p className="text-xs text-neutral-500">35M+ Items</p>
            </div>
            <div className="bg-neutral-50 border border-neutral-200 rounded-xl p-4 text-center">
              <div className="w-10 h-10 bg-neutral-400/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                <Globe className="w-5 h-5 text-neutral-600" />
              </div>
              <p className="text-xs font-semibold text-neutral-800">Wikipedia</p>
              <p className="text-xs text-neutral-500">6M+ Articles</p>
            </div>
            <div className="bg-green-50 border border-green-100 rounded-xl p-4 text-center">
              <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                <ClipboardList className="w-5 h-5 text-green-500" />
              </div>
              <p className="text-xs font-semibold text-neutral-800">Worksheets</p>
              <p className="text-xs text-neutral-500">100K+ Sheets</p>
            </div>
          </div>

          <p className="text-sm text-neutral-600 mb-6">
            Try searching: "STEM worksheets", "math practice grade 5", "science experiments"
          </p>
          
          {/* Quick Search Suggestions */}
          <div className="flex flex-wrap justify-center gap-2">
            {['Math worksheets', 'Science experiments', 'Reading activities', 'History lessons', 'Art projects'].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => {
                  setSearchQuery(suggestion);
                  setTimeout(() => handleSearch(1), 100);
                }}
                className="px-4 py-2 bg-emerald-100 text-emerald-700 rounded-full text-sm hover:bg-emerald-200 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Reading List Modal */}
      <ReadingListModal
        isOpen={showListModal}
        onClose={() => {
          setShowListModal(false);
          setEditingList(null);
          setPendingBook(null);
        }}
        onSave={handleSaveList}
        editList={editingList}
      />
      
      {/* Reading List Detail Modal */}
      <ReadingListDetailModal
        isOpen={showListDetail}
        onClose={() => {
          setShowListDetail(false);
          setSelectedList(null);
        }}
        list={selectedList}
        onRemoveBook={handleRemoveBookFromList}
      />
    </div>
  );
};

export default ContentLibrary;
