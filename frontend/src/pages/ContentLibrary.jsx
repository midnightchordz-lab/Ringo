import { useState, useEffect } from 'react';
import api from '../utils/api';
import { 
  Search, BookOpen, GraduationCap, Music, FileText, Scroll, 
  ExternalLink, Heart, Filter, Library, Sparkles, Globe,
  Baby, School, Building2, University, BookMarked, Mic,
  PenTool, FlaskConical, History, ChevronDown, ClipboardList, Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

// Content Categories
const CATEGORIES = [
  { id: 'all', name: 'All Content', icon: Library, color: 'from-violet-500 to-purple-500' },
  { id: 'worksheets', name: 'Activity Sheets', icon: ClipboardList, color: 'from-lime-500 to-green-500' },
  { id: 'stories', name: 'Stories & Fiction', icon: BookOpen, color: 'from-blue-500 to-cyan-500' },
  { id: 'poetry', name: 'Poetry', icon: PenTool, color: 'from-pink-500 to-rose-500' },
  { id: 'educational', name: 'Educational Articles', icon: GraduationCap, color: 'from-green-500 to-emerald-500' },
  { id: 'textbooks', name: 'Textbooks & Courses', icon: BookMarked, color: 'from-orange-500 to-amber-500' },
  { id: 'audiobooks', name: 'Audio Books', icon: Mic, color: 'from-purple-500 to-indigo-500' },
  { id: 'research', name: 'Research Papers', icon: FlaskConical, color: 'from-teal-500 to-cyan-500' },
  { id: 'historical', name: 'Historical Documents', icon: History, color: 'from-amber-500 to-yellow-500' },
];

// Education Levels - Updated with individual grades
const EDUCATION_LEVELS = [
  { id: 'all', name: 'All Levels', icon: Library },
  { id: 'preschool', name: 'Pre-school / Kindergarten', icon: Baby },
  { id: 'grade1', name: 'Grade 1', icon: School },
  { id: 'grade2', name: 'Grade 2', icon: School },
  { id: 'grade3', name: 'Grade 3', icon: School },
  { id: 'grade4', name: 'Grade 4', icon: School },
  { id: 'grade5', name: 'Grade 5', icon: School },
  { id: 'grade6', name: 'Grade 6', icon: Building2 },
  { id: 'grade7', name: 'Grade 7', icon: Building2 },
  { id: 'grade8', name: 'Grade 8', icon: Building2 },
  { id: 'grade9', name: 'Grade 9', icon: GraduationCap },
  { id: 'grade10', name: 'Grade 10', icon: GraduationCap },
  { id: 'primary', name: 'Primary School (1-5)', icon: School },
  { id: 'middle', name: 'Middle School (6-8)', icon: Building2 },
  { id: 'high', name: 'High School (9-12)', icon: GraduationCap },
  { id: 'university', name: 'University / Higher Ed', icon: University },
];

// Curated Resources Database
const CURATED_RESOURCES = [
  // ==================== ACTIVITY SHEETS / WORKSHEETS ====================
  {
    id: 'k5learning',
    name: 'K5 Learning',
    description: 'Free printable worksheets for K-5. Math, reading, spelling, grammar, science, and vocabulary.',
    url: 'https://www.k5learning.com/free-worksheets',
    categories: ['worksheets', 'educational'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'primary'],
    featured: true,
    logo: '📝',
    contentCount: '10,000+ Worksheets'
  },
  {
    id: 'mathdrills',
    name: 'Math-Drills.com',
    description: 'Free math worksheets covering all topics from basic operations to algebra and geometry.',
    url: 'https://www.math-drills.com',
    categories: ['worksheets'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'primary', 'middle', 'high'],
    featured: true,
    logo: '🔢',
    contentCount: '50,000+ Worksheets'
  },
  {
    id: 'worksheetfun',
    name: 'Worksheet Fun',
    description: 'Free printable worksheets for preschool through 5th grade. Tracing, coloring, math, and more.',
    url: 'https://www.worksheetfun.com',
    categories: ['worksheets'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'primary'],
    featured: false,
    logo: '🎨',
    contentCount: '2,000+ Worksheets'
  },
  {
    id: 'commoncoresheets',
    name: 'Common Core Sheets',
    description: 'Free Common Core aligned worksheets for math, ELA, science, and social studies.',
    url: 'https://www.commoncoresheets.com',
    categories: ['worksheets', 'educational'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'primary', 'middle'],
    featured: true,
    logo: '📋',
    contentCount: '20,000+ Worksheets'
  },
  {
    id: 'dadsworksheets',
    name: "Dad's Worksheets",
    description: 'Free printable math worksheets including multiplication, division, fractions, and word problems.',
    url: 'https://www.dadsworksheets.com',
    categories: ['worksheets'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'primary', 'middle'],
    featured: false,
    logo: '➕',
    contentCount: '15,000+ Worksheets'
  },
  {
    id: 'mathworksheets4kids',
    name: 'Math Worksheets 4 Kids',
    description: 'Free math worksheets organized by grade and topic. From counting to calculus.',
    url: 'https://www.mathworksheets4kids.com',
    categories: ['worksheets'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'primary', 'middle', 'high'],
    featured: true,
    logo: '📐',
    contentCount: '30,000+ Worksheets'
  },
  {
    id: 'worksheetworks',
    name: 'WorksheetWorks.com',
    description: 'Generate custom worksheets for math, writing, puzzles, and geography.',
    url: 'https://www.worksheetworks.com',
    categories: ['worksheets'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'primary', 'middle'],
    featured: false,
    logo: '⚙️',
    contentCount: 'Custom Generator'
  },
  {
    id: 'softschools',
    name: 'SoftSchools',
    description: 'Free worksheets, games, and quizzes for math, grammar, science, and social studies.',
    url: 'https://www.softschools.com/worksheets/',
    categories: ['worksheets', 'educational'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'primary', 'middle'],
    featured: false,
    logo: '🎮',
    contentCount: '5,000+ Resources'
  },
  {
    id: 'superteacher',
    name: 'Super Teacher Worksheets',
    description: 'Printable worksheets for reading, math, writing, science, and holidays. Some free content.',
    url: 'https://www.superteacherworksheets.com/full-free.html',
    categories: ['worksheets', 'educational'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'primary', 'middle'],
    featured: true,
    logo: '🦸',
    contentCount: '1,000+ Free Sheets'
  },
  {
    id: 'edhelper',
    name: 'edHelper',
    description: 'Free worksheets for reading comprehension, math, spelling, and critical thinking.',
    url: 'https://www.edhelper.com/teacher-free-stuff.htm',
    categories: ['worksheets', 'educational'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'primary', 'middle'],
    featured: false,
    logo: '🆘',
    contentCount: '3,000+ Free Sheets'
  },
  {
    id: 'turtlediary',
    name: 'Turtle Diary',
    description: 'Free printable worksheets and games for pre-K through 5th grade in all subjects.',
    url: 'https://www.turtlediary.com/worksheets.html',
    categories: ['worksheets'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'primary'],
    featured: false,
    logo: '🐢',
    contentCount: '4,000+ Worksheets'
  },
  {
    id: 'mathgoodies',
    name: 'Math Goodies',
    description: 'Free interactive math lessons and worksheets for grades 5-12. Algebra, geometry, statistics.',
    url: 'https://www.mathgoodies.com/worksheets',
    categories: ['worksheets'],
    levels: ['grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'middle', 'high'],
    featured: false,
    logo: '🍬',
    contentCount: '1,000+ Worksheets'
  },
  {
    id: 'kidslearningstation',
    name: 'Kids Learning Station',
    description: 'Free educational printables for toddlers through 2nd grade. ABCs, numbers, shapes.',
    url: 'https://www.kidslearningstation.com',
    categories: ['worksheets'],
    levels: ['preschool', 'grade1', 'grade2', 'primary'],
    featured: false,
    logo: '🚂',
    contentCount: '2,500+ Printables'
  },
  {
    id: 'helpingwithmath',
    name: 'Helping With Math',
    description: 'Free math worksheets, lessons, and homework help for K-10.',
    url: 'https://www.helpingwithmath.com/worksheets/',
    categories: ['worksheets'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'primary', 'middle', 'high'],
    featured: false,
    logo: '🤝',
    contentCount: '8,000+ Worksheets'
  },
  {
    id: 'superstarworksheets',
    name: 'Superstar Worksheets',
    description: 'Free printable worksheets for pre-K through 8th grade in all subjects.',
    url: 'https://www.superstarworksheets.com',
    categories: ['worksheets', 'educational'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'primary', 'middle'],
    featured: true,
    logo: '⭐',
    contentCount: '10,000+ Worksheets'
  },
  {
    id: 'liveworksheets',
    name: 'Live Worksheets',
    description: 'Interactive worksheets that students can complete online. All subjects, all grades.',
    url: 'https://www.liveworksheets.com',
    categories: ['worksheets', 'educational'],
    levels: ['preschool', 'grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'primary', 'middle', 'high'],
    featured: true,
    logo: '💻',
    contentCount: '1M+ Interactive Sheets'
  },
  {
    id: 'englishworksheetsland',
    name: 'English Worksheets Land',
    description: 'Free ELA worksheets: grammar, reading, writing, vocabulary for all grades.',
    url: 'https://www.englishworksheetsland.com',
    categories: ['worksheets'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'primary', 'middle', 'high'],
    featured: false,
    logo: '📖',
    contentCount: '15,000+ Worksheets'
  },
  {
    id: 'scienceworksheets',
    name: 'Easy Teacher Worksheets',
    description: 'Free science, math, and language arts worksheets for all grade levels.',
    url: 'https://www.easyteacherworksheets.com',
    categories: ['worksheets', 'educational'],
    levels: ['grade1', 'grade2', 'grade3', 'grade4', 'grade5', 'grade6', 'grade7', 'grade8', 'grade9', 'grade10', 'primary', 'middle', 'high'],
    featured: false,
    logo: '🔬',
    contentCount: '10,000+ Worksheets'
  },
  // ==================== EXISTING RESOURCES ====================
  // Project Gutenberg
  {
    id: 'gutenberg',
    name: 'Project Gutenberg',
    description: 'Over 70,000 free eBooks. Classic literature, fiction, and reference works.',
    url: 'https://www.gutenberg.org',
    categories: ['stories', 'poetry', 'historical'],
    levels: ['middle', 'high', 'university'],
    featured: true,
    logo: '📚',
    contentCount: '70,000+ eBooks'
  },
  // Open Library
  {
    id: 'openlibrary',
    name: 'Open Library',
    description: 'Borrow and read over 3 million digital books for free. Part of Internet Archive.',
    url: 'https://openlibrary.org',
    categories: ['stories', 'textbooks', 'educational', 'research'],
    levels: ['primary', 'middle', 'high', 'university'],
    featured: true,
    logo: '📖',
    contentCount: '3M+ Books'
  },
  // Khan Academy
  {
    id: 'khan',
    name: 'Khan Academy',
    description: 'Free courses in math, science, computing, history, art, economics, and more.',
    url: 'https://www.khanacademy.org',
    categories: ['educational', 'textbooks'],
    levels: ['preschool', 'primary', 'middle', 'high', 'university'],
    featured: true,
    logo: '🎓',
    contentCount: '10,000+ Videos'
  },
  // MIT OpenCourseWare
  {
    id: 'mit',
    name: 'MIT OpenCourseWare',
    description: 'Free lecture notes, exams, and videos from MIT. University-level courses.',
    url: 'https://ocw.mit.edu',
    categories: ['textbooks', 'educational', 'research'],
    levels: ['university'],
    featured: true,
    logo: '🏛️',
    contentCount: '2,500+ Courses'
  },
  // LibriVox
  {
    id: 'librivox',
    name: 'LibriVox',
    description: 'Free public domain audiobooks read by volunteers from around the world.',
    url: 'https://librivox.org',
    categories: ['audiobooks', 'stories', 'poetry'],
    levels: ['middle', 'high', 'university'],
    featured: true,
    logo: '🎧',
    contentCount: '18,000+ Audiobooks'
  },
  // Poetry Foundation
  {
    id: 'poetry',
    name: 'Poetry Foundation',
    description: 'Thousands of poems by classic and contemporary poets.',
    url: 'https://www.poetryfoundation.org',
    categories: ['poetry'],
    levels: ['primary', 'middle', 'high', 'university'],
    featured: true,
    logo: '✨',
    contentCount: '50,000+ Poems'
  },
  // Storynory
  {
    id: 'storynory',
    name: 'Storynory',
    description: 'Free audio stories for kids. Fairy tales, myths, educational stories.',
    url: 'https://www.storynory.com',
    categories: ['stories', 'audiobooks'],
    levels: ['preschool', 'primary'],
    featured: false,
    logo: '🧚',
    contentCount: '700+ Stories'
  },
  // International Children\'s Digital Library
  {
    id: 'icdl',
    name: "Int'l Children's Digital Library",
    description: 'Free books for children in 100+ languages from around the world.',
    url: 'http://en.childrenslibrary.org',
    categories: ['stories'],
    levels: ['preschool', 'primary'],
    featured: false,
    logo: '🌍',
    contentCount: '4,600+ Books'
  },
  // CK-12
  {
    id: 'ck12',
    name: 'CK-12 Foundation',
    description: 'Free customizable K-12 textbooks, flashcards, and real-world simulations.',
    url: 'https://www.ck12.org',
    categories: ['textbooks', 'educational'],
    levels: ['primary', 'middle', 'high'],
    featured: true,
    logo: '📘',
    contentCount: '5,000+ Resources'
  },
  // OpenStax
  {
    id: 'openstax',
    name: 'OpenStax',
    description: 'Free peer-reviewed textbooks by Rice University. College-level content.',
    url: 'https://openstax.org',
    categories: ['textbooks', 'educational'],
    levels: ['high', 'university'],
    featured: true,
    logo: '📕',
    contentCount: '50+ Textbooks'
  },
  // CORE
  {
    id: 'core',
    name: 'CORE',
    description: 'Aggregator of open access research papers. Millions of full-text articles.',
    url: 'https://core.ac.uk',
    categories: ['research'],
    levels: ['university'],
    featured: false,
    logo: '🔬',
    contentCount: '200M+ Papers'
  },
  // arXiv
  {
    id: 'arxiv',
    name: 'arXiv',
    description: 'Open access archive for scholarly articles in physics, math, CS, and more.',
    url: 'https://arxiv.org',
    categories: ['research'],
    levels: ['university'],
    featured: true,
    logo: '📄',
    contentCount: '2M+ Papers'
  },
  // DOAJ
  {
    id: 'doaj',
    name: 'DOAJ',
    description: 'Directory of Open Access Journals. Quality-controlled scientific journals.',
    url: 'https://doaj.org',
    categories: ['research'],
    levels: ['university'],
    featured: false,
    logo: '📰',
    contentCount: '9M+ Articles'
  },
  // Internet Archive
  {
    id: 'archive',
    name: 'Internet Archive',
    description: 'Digital library with books, movies, music, and historical web pages.',
    url: 'https://archive.org',
    categories: ['stories', 'historical', 'audiobooks', 'educational'],
    levels: ['middle', 'high', 'university'],
    featured: true,
    logo: '🏛️',
    contentCount: '35M+ Books'
  },
  // Europeana
  {
    id: 'europeana',
    name: 'Europeana',
    description: 'Digital access to European cultural heritage. Art, books, music, videos.',
    url: 'https://www.europeana.eu',
    categories: ['historical', 'educational'],
    levels: ['middle', 'high', 'university'],
    featured: false,
    logo: '🇪🇺',
    contentCount: '50M+ Items'
  },
  // World Digital Library
  {
    id: 'wdl',
    name: 'Library of Congress',
    description: 'Primary source materials from cultures around the world.',
    url: 'https://www.loc.gov/collections/',
    categories: ['historical', 'educational'],
    levels: ['middle', 'high', 'university'],
    featured: false,
    logo: '🗽',
    contentCount: '170M+ Items'
  },
  // Coursera (Free Courses)
  {
    id: 'coursera',
    name: 'Coursera (Free Courses)',
    description: 'Audit thousands of courses from top universities for free.',
    url: 'https://www.coursera.org/courses?query=free',
    categories: ['textbooks', 'educational'],
    levels: ['high', 'university'],
    featured: false,
    logo: '🎯',
    contentCount: '5,000+ Courses'
  },
  // edX
  {
    id: 'edx',
    name: 'edX',
    description: 'Free courses from Harvard, MIT, Berkeley, and more institutions.',
    url: 'https://www.edx.org',
    categories: ['textbooks', 'educational'],
    levels: ['high', 'university'],
    featured: true,
    logo: '🎓',
    contentCount: '3,000+ Courses'
  },
  // PBS LearningMedia
  {
    id: 'pbs',
    name: 'PBS LearningMedia',
    description: 'Free PreK-12 educational resources including videos and lesson plans.',
    url: 'https://www.pbslearningmedia.org',
    categories: ['educational'],
    levels: ['preschool', 'primary', 'middle', 'high'],
    featured: false,
    logo: '📺',
    contentCount: '100,000+ Resources'
  },
  // Smithsonian Learning Lab
  {
    id: 'smithsonian',
    name: 'Smithsonian Learning Lab',
    description: 'Millions of digital resources from Smithsonian museums.',
    url: 'https://learninglab.si.edu',
    categories: ['educational', 'historical'],
    levels: ['primary', 'middle', 'high'],
    featured: false,
    logo: '🏛️',
    contentCount: '4M+ Resources'
  },
  // National Geographic Education
  {
    id: 'natgeo',
    name: 'National Geographic Education',
    description: 'Free geography, science, and exploration educational resources.',
    url: 'https://education.nationalgeographic.org',
    categories: ['educational'],
    levels: ['primary', 'middle', 'high'],
    featured: false,
    logo: '🌎',
    contentCount: '1,000+ Resources'
  },
  // Lit2Go
  {
    id: 'lit2go',
    name: 'Lit2Go',
    description: 'Free online collection of stories and poems in audiobook format.',
    url: 'https://etc.usf.edu/lit2go/',
    categories: ['stories', 'poetry', 'audiobooks'],
    levels: ['primary', 'middle', 'high'],
    featured: false,
    logo: '📖',
    contentCount: '200+ Books'
  },
  // ReadWorks
  {
    id: 'readworks',
    name: 'ReadWorks',
    description: 'Free reading passages and curriculum for K-12 students.',
    url: 'https://www.readworks.org',
    categories: ['stories', 'educational'],
    levels: ['primary', 'middle', 'high'],
    featured: false,
    logo: '📝',
    contentCount: '3,000+ Passages'
  },
  // CommonLit
  {
    id: 'commonlit',
    name: 'CommonLit',
    description: 'Free reading passages and literacy resources for grades 3-12.',
    url: 'https://www.commonlit.org',
    categories: ['stories', 'poetry', 'educational'],
    levels: ['primary', 'middle', 'high'],
    featured: false,
    logo: '📚',
    contentCount: '2,000+ Texts'
  },
];

const ResourceCard = ({ resource, onFavorite, isFavorited }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="glass-card p-5 hover:border-violet-500/50 transition-all group"
      data-testid="resource-card"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{resource.logo}</span>
          <div>
            <h3 className="font-bold text-white group-hover:text-violet-400 transition-colors">
              {resource.name}
            </h3>
            <span className="text-xs text-[#BEF264] font-semibold">
              {resource.contentCount}
            </span>
          </div>
        </div>
        <button
          onClick={() => onFavorite(resource)}
          className={`p-2 rounded-full transition-all ${
            isFavorited 
              ? 'bg-red-500/20 text-red-500' 
              : 'bg-zinc-800 text-zinc-500 hover:bg-red-500/20 hover:text-red-500'
          }`}
          data-testid="favorite-resource-button"
        >
          <Heart className="w-4 h-4" fill={isFavorited ? 'currentColor' : 'none'} />
        </button>
      </div>
      
      <p className="text-zinc-400 text-sm mb-4 line-clamp-2">
        {resource.description}
      </p>
      
      <div className="flex flex-wrap gap-1 mb-4">
        {resource.categories.slice(0, 3).map((cat) => {
          const category = CATEGORIES.find(c => c.id === cat);
          return (
            <span key={cat} className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded-full">
              {category?.name || cat}
            </span>
          );
        })}
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {resource.levels.slice(0, 3).map((level) => {
            const eduLevel = EDUCATION_LEVELS.find(l => l.id === level);
            const Icon = eduLevel?.icon || GraduationCap;
            return (
              <span key={level} className="p-1.5 bg-zinc-800/50 rounded-lg" title={eduLevel?.name}>
                <Icon className="w-3 h-3 text-zinc-500" />
              </span>
            );
          })}
          {resource.levels.length > 3 && (
            <span className="px-2 py-1 text-xs text-zinc-600">+{resource.levels.length - 3}</span>
          )}
        </div>
        
        <Button
          size="sm"
          onClick={() => window.open(resource.url, '_blank')}
          className="bg-violet-600 hover:bg-violet-500 text-white text-xs rounded-full px-4"
          data-testid="visit-resource-button"
        >
          <ExternalLink className="w-3 h-3 mr-1" />
          Visit
        </Button>
      </div>
    </motion.div>
  );
};

export const ContentLibrary = () => {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [favorites, setFavorites] = useState([]);
  const [showFavorites, setShowFavorites] = useState(false);
  const [showLevelDropdown, setShowLevelDropdown] = useState(false);
  const [gutenbergBooks, setGutenbergBooks] = useState([]);
  const [loadingBooks, setLoadingBooks] = useState(false);

  useEffect(() => {
    fetchFavorites();
  }, []);

  const fetchFavorites = async () => {
    try {
      const response = await api.get('/content-library/favorites');
      setFavorites(response.data.favorites || []);
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  };

  const searchGutenberg = async () => {
    if (!searchQuery.trim()) return;
    
    setLoadingBooks(true);
    try {
      const response = await api.get('/content-library/gutenberg/search', {
        params: { query: searchQuery, limit: 12 }
      });
      setGutenbergBooks(response.data.books || []);
    } catch (error) {
      console.error('Error searching Gutenberg:', error);
    } finally {
      setLoadingBooks(false);
    }
  };

  const handleFavorite = async (resource) => {
    const isFavorited = favorites.some(f => f.resource_id === resource.id);
    
    try {
      if (isFavorited) {
        await api.delete(`/content-library/favorites/${resource.id}`);
        setFavorites(favorites.filter(f => f.resource_id !== resource.id));
        toast.success('Removed from favorites');
      } else {
        await api.post('/content-library/favorites', {
          resource_id: resource.id,
          name: resource.name,
          description: resource.description,
          url: resource.url,
          logo: resource.logo,
          categories: resource.categories,
          levels: resource.levels
        });
        setFavorites([...favorites, { ...resource, resource_id: resource.id }]);
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

  // Filter resources
  let filteredResources = CURATED_RESOURCES.filter(resource => {
    const matchesCategory = selectedCategory === 'all' || resource.categories.includes(selectedCategory);
    const matchesLevel = selectedLevel === 'all' || resource.levels.includes(selectedLevel);
    const matchesSearch = !searchQuery || 
      resource.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      resource.description.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesCategory && matchesLevel && matchesSearch;
  });

  if (showFavorites) {
    filteredResources = CURATED_RESOURCES.filter(r => favorites.some(f => f.resource_id === r.id));
  }

  const featuredResources = filteredResources.filter(r => r.featured);
  const otherResources = filteredResources.filter(r => !r.featured);

  const selectedLevelInfo = EDUCATION_LEVELS.find(l => l.id === selectedLevel);

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Library className="w-10 h-10 text-violet-500" />
          <h1 className="text-4xl sm:text-5xl font-bold text-white" style={{ fontFamily: 'Oswald, sans-serif' }}>
            Content Library
          </h1>
        </div>
        <p className="text-zinc-500">Copyright-free educational resources for all learning levels</p>
      </div>

      {/* Search and Filters */}
      <div className="glass-card p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
            <Input
              data-testid="library-search-input"
              type="text"
              placeholder="Search resources..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 bg-zinc-950/50 border-zinc-800 focus:border-violet-500 rounded-lg text-white placeholder:text-zinc-600 h-12"
            />
          </div>
          
          {/* Education Level Dropdown */}
          <div className="relative">
            <Button
              onClick={() => setShowLevelDropdown(!showLevelDropdown)}
              className="h-12 px-4 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg flex items-center gap-2 min-w-[200px] justify-between"
              data-testid="level-dropdown"
            >
              <div className="flex items-center gap-2">
                {selectedLevelInfo && <selectedLevelInfo.icon className="w-4 h-4" />}
                <span>{selectedLevelInfo?.name || 'All Levels'}</span>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${showLevelDropdown ? 'rotate-180' : ''}`} />
            </Button>
            
            <AnimatePresence>
              {showLevelDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute z-50 top-14 left-0 w-full bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl overflow-hidden"
                >
                  {EDUCATION_LEVELS.map((level) => (
                    <button
                      key={level.id}
                      onClick={() => {
                        setSelectedLevel(level.id);
                        setShowLevelDropdown(false);
                      }}
                      className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-zinc-800 transition-colors ${
                        selectedLevel === level.id ? 'bg-violet-600/20 text-violet-400' : 'text-zinc-300'
                      }`}
                    >
                      <level.icon className="w-4 h-4" />
                      <span className="text-sm">{level.name}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Favorites Toggle */}
          <Button
            onClick={() => setShowFavorites(!showFavorites)}
            className={`h-12 px-6 rounded-lg flex items-center gap-2 ${
              showFavorites 
                ? 'bg-red-500 hover:bg-red-600 text-white' 
                : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-300'
            }`}
            data-testid="favorites-toggle"
          >
            <Heart className="w-4 h-4" fill={showFavorites ? 'currentColor' : 'none'} />
            My Favorites ({favorites.length})
          </Button>
        </div>
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
              className={`rounded-full px-4 py-2 flex items-center gap-2 whitespace-nowrap transition-all ${
                isActive
                  ? `bg-gradient-to-r ${category.color} text-white shadow-lg`
                  : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700'
              }`}
              data-testid={`category-${category.id}`}
            >
              <Icon className="w-4 h-4" />
              {category.name}
            </Button>
          );
        })}
      </div>

      {/* Stats Bar */}
      <div className="flex items-center justify-between mb-6 px-2">
        <p className="text-zinc-500">
          Showing <span className="text-[#BEF264] font-bold">{filteredResources.length}</span> resources
          {selectedCategory !== 'all' && (
            <span className="text-zinc-600"> in {CATEGORIES.find(c => c.id === selectedCategory)?.name}</span>
          )}
          {selectedLevel !== 'all' && (
            <span className="text-zinc-600"> for {EDUCATION_LEVELS.find(l => l.id === selectedLevel)?.name}</span>
          )}
        </p>
      </div>

      {/* Featured Resources */}
      {featuredResources.length > 0 && !showFavorites && (
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-[#BEF264]" />
            <h2 className="text-xl font-bold text-white">Featured Resources</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {featuredResources.map((resource) => (
                <ResourceCard
                  key={resource.id}
                  resource={resource}
                  onFavorite={handleFavorite}
                  isFavorited={isFavorited(resource.id)}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Other Resources */}
      {otherResources.length > 0 && (
        <div>
          {!showFavorites && featuredResources.length > 0 && (
            <div className="flex items-center gap-2 mb-4">
              <Globe className="w-5 h-5 text-zinc-500" />
              <h2 className="text-xl font-bold text-white">More Resources</h2>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {otherResources.map((resource) => (
                <ResourceCard
                  key={resource.id}
                  resource={resource}
                  onFavorite={handleFavorite}
                  isFavorited={isFavorited(resource.id)}
                />
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredResources.length === 0 && (
        <div className="glass-card p-20 text-center">
          <Library className="w-20 h-20 text-zinc-700 mx-auto mb-6" strokeWidth={1.5} />
          <h3 className="text-xl font-bold text-white mb-2">
            {showFavorites ? 'No Favorites Yet' : 'No Resources Found'}
          </h3>
          <p className="text-zinc-500 mb-6">
            {showFavorites 
              ? 'Click the heart icon on resources to save them here'
              : 'Try adjusting your filters or search term'}
          </p>
          {showFavorites && (
            <Button
              onClick={() => setShowFavorites(false)}
              className="bg-violet-600 hover:bg-violet-500 text-white rounded-full px-6"
            >
              Browse Resources
            </Button>
          )}
        </div>
      )}

      {/* Quick Access Section */}
      {!showFavorites && selectedCategory === 'all' && selectedLevel === 'all' && !searchQuery && (
        <div className="mt-12">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-violet-500" />
            Quick Access by Education Level
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {EDUCATION_LEVELS.filter(l => l.id !== 'all').map((level) => {
              const Icon = level.icon;
              const count = CURATED_RESOURCES.filter(r => r.levels.includes(level.id)).length;
              return (
                <motion.button
                  key={level.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setSelectedLevel(level.id)}
                  className="glass-card p-4 text-center hover:border-violet-500/50 transition-all"
                >
                  <Icon className="w-8 h-8 mx-auto mb-2 text-violet-500" />
                  <h3 className="font-semibold text-white text-sm mb-1">{level.name}</h3>
                  <p className="text-xs text-zinc-500">{count} resources</p>
                </motion.button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContentLibrary;
