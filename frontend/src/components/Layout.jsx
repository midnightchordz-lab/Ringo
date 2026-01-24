import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, Clock, LogOut, Image, Library, Video, Sun, Moon, Settings } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard' },
  { path: '/discover', icon: Video, label: 'Videos' },
  { path: '/images', icon: Image, label: 'Images' },
  { path: '/library', icon: Library, label: 'Library' },
  { path: '/history', icon: Clock, label: 'History' },
];

export const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully');
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800">
        {/* Logo */}
        <div className="p-5 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Video className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900 dark:text-slate-100">ContentFlow</span>
          </div>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <div
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium text-sm">{item.label}</span>
                </div>
              </Link>
            );
          })}
        </nav>
        
        {/* Bottom Section */}
        <div className="p-3 border-t border-slate-100 dark:border-slate-800 space-y-1">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            data-testid="theme-toggle"
          >
            {theme === 'dark' ? (
              <Sun className="w-5 h-5" />
            ) : (
              <Moon className="w-5 h-5" />
            )}
            <span className="font-medium text-sm">
              {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </span>
          </button>
          
          {/* User & Logout */}
          <div className="pt-2 mt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-semibold text-sm">
                {user?.full_name?.charAt(0) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                  {user?.full_name || 'User'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                  {user?.email || ''}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors mt-1"
              data-testid="logout-button"
            >
              <LogOut className="w-5 h-5" />
              <span className="font-medium text-sm">Log out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 z-50">
        <div className="flex justify-around py-2">
          {navItems.slice(0, 5).map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center gap-1 px-3 py-2 ${
                  isActive
                    ? 'text-indigo-600 dark:text-indigo-400'
                    : 'text-slate-500 dark:text-slate-400'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
};

export default Layout;
