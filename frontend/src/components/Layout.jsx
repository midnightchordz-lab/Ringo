import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, Clock, Sparkles, TrendingUp, LogOut, Image, Library, Video, ChevronRight, Sun, Moon } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useTheme } from '../context/ThemeContext';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard', color: 'blue' },
  { path: '/discover', icon: Video, label: 'Videos', color: 'coral' },
  { path: '/images', icon: Image, label: 'Images', color: 'purple' },
  { path: '/library', icon: Library, label: 'Library', color: 'green' },
  { path: '/history', icon: Clock, label: 'History', color: 'yellow' },
];

const colorClasses = {
  blue: { bg: 'bg-blue-100 dark:bg-blue-900/40', text: 'text-blue-600 dark:text-blue-400', active: 'from-blue-600 to-indigo-600' },
  coral: { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-500 dark:text-red-400', active: 'from-red-500 to-orange-500' },
  purple: { bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-600 dark:text-purple-400', active: 'from-purple-600 to-pink-600' },
  green: { bg: 'bg-emerald-100 dark:bg-emerald-900/40', text: 'text-emerald-600 dark:text-emerald-400', active: 'from-emerald-600 to-green-600' },
  yellow: { bg: 'bg-amber-100 dark:bg-amber-900/40', text: 'text-amber-600 dark:text-amber-400', active: 'from-amber-500 to-yellow-500' },
  gray: { bg: 'bg-neutral-100 dark:bg-neutral-800', text: 'text-neutral-600 dark:text-neutral-400', active: 'from-neutral-600 to-neutral-700' },
};

export const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    toast.success('Logged out successfully');
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-neutral-50 dark:bg-neutral-950 transition-colors duration-300">
      {/* Desktop Sidebar - Light & Clean */}
      <aside className="hidden lg:flex flex-col w-72 bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800 shadow-sm transition-colors duration-300">
        {/* Logo */}
        <div className="p-6 border-b border-neutral-100 dark:border-neutral-800">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/30">
                <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-r from-red-500 to-orange-500 rounded-full animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gradient" style={{ fontFamily: 'Outfit, sans-serif' }}>
                ContentFlow
              </h1>
              <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">Creative Studio</p>
            </div>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            const colors = colorClasses[item.color];
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <motion.div
                  whileHover={{ x: 4 }}
                  whileTap={{ scale: 0.98 }}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                    isActive
                      ? `bg-gradient-to-r ${colors.active} text-white shadow-lg`
                      : 'text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                  }`}
                >
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                    isActive ? 'bg-white/20' : colors.bg
                  }`}>
                    <Icon className={`w-5 h-5 ${isActive ? 'text-white' : colors.text}`} strokeWidth={2} />
                  </div>
                  <span className="font-semibold flex-1">{item.label}</span>
                  {isActive && (
                    <ChevronRight className="w-4 h-4 text-white/70" />
                  )}
                </motion.div>
              </Link>
            );
          })}
        </nav>
        
        {/* User Section */}
        <div className="p-4 border-t border-neutral-100 dark:border-neutral-800 space-y-3">
          {/* Theme Toggle */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={toggleTheme}
            className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
            data-testid="theme-toggle"
          >
            <div className="flex items-center space-x-3">
              {theme === 'dark' ? (
                <Moon className="w-5 h-5 text-indigo-500" />
              ) : (
                <Sun className="w-5 h-5 text-amber-500" />
              )}
              <span className="font-medium text-neutral-700 dark:text-neutral-200">
                {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
              </span>
            </div>
            <div className={`w-12 h-6 rounded-full p-1 transition-colors duration-300 ${
              theme === 'dark' ? 'bg-indigo-600' : 'bg-neutral-300'
            }`}>
              <motion.div 
                className="w-4 h-4 bg-white rounded-full shadow-sm"
                animate={{ x: theme === 'dark' ? 24 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            </div>
          </motion.button>
          
          {/* User Card */}
          <div className="studio-card p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                {(user.full_name || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100 truncate">{user.full_name || 'User'}</p>
                <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">{user.email || ''}</p>
              </div>
            </div>
          </div>
          
          {/* Logout Button */}
          <Button
            onClick={handleLogout}
            className="w-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 hover:bg-red-50 dark:hover:bg-red-900/30 hover:text-red-600 dark:hover:text-red-400 font-semibold rounded-xl py-2.5 flex items-center justify-center transition-colors"
            data-testid="logout-button"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="h-full"
        >
          <Outlet />
        </motion.div>
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="lg:hidden fixed bottom-0 w-full bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800 z-50 shadow-lg transition-colors duration-300">
        <div className="flex justify-around items-center h-16 px-2">
          {navItems.slice(0, 5).map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            const colors = colorClasses[item.color];
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`mobile-nav-${item.label.toLowerCase()}`}
                className="flex flex-col items-center justify-center flex-1"
              >
                <motion.div
                  whileTap={{ scale: 0.9 }}
                  className={`flex flex-col items-center space-y-0.5 px-3 py-1.5 rounded-xl transition-all ${
                    isActive ? `bg-gradient-to-r ${colors.active} text-white` : 'text-neutral-500'
                  }`}
                >
                  <Icon className="w-5 h-5" strokeWidth={2} />
                  <span className="text-[10px] font-semibold">{item.label}</span>
                </motion.div>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
};

export default Layout;
