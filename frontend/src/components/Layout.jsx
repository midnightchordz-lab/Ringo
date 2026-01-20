import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, Clock, Settings, Sparkles, TrendingUp, LogOut, Image, Library, Video, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard', color: 'blue' },
  { path: '/discover', icon: Video, label: 'Videos', color: 'coral' },
  { path: '/images', icon: Image, label: 'Images', color: 'purple' },
  { path: '/library', icon: Library, label: 'Library', color: 'green' },
  { path: '/history', icon: Clock, label: 'History', color: 'yellow' },
  { path: '/settings', icon: Settings, label: 'Settings', color: 'gray' },
];

const colorClasses = {
  blue: { bg: 'bg-blue-100', text: 'text-blue-600', active: 'from-blue-600 to-indigo-600' },
  coral: { bg: 'bg-red-100', text: 'text-red-500', active: 'from-red-500 to-orange-500' },
  purple: { bg: 'bg-purple-100', text: 'text-purple-600', active: 'from-purple-600 to-pink-600' },
  green: { bg: 'bg-emerald-100', text: 'text-emerald-600', active: 'from-emerald-600 to-green-600' },
  yellow: { bg: 'bg-amber-100', text: 'text-amber-600', active: 'from-amber-500 to-yellow-500' },
  gray: { bg: 'bg-neutral-100', text: 'text-neutral-600', active: 'from-neutral-600 to-neutral-700' },
};

export const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    toast.success('Logged out successfully');
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-neutral-50">
      {/* Desktop Sidebar - Light & Clean */}
      <aside className="hidden lg:flex flex-col w-72 bg-white border-r border-neutral-200 shadow-sm">
        {/* Logo */}
        <div className="p-6 border-b border-neutral-100">
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
              <p className="text-xs font-medium text-neutral-500">Creative Studio</p>
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
                      : 'text-neutral-600 hover:bg-neutral-100'
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
        <div className="p-4 border-t border-neutral-100 space-y-3">
          {/* User Card */}
          <div className="studio-card p-4 bg-gradient-to-br from-blue-50 to-indigo-50">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                {(user.full_name || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-neutral-900 truncate">{user.full_name || 'User'}</p>
                <p className="text-xs text-neutral-500 truncate">{user.email || ''}</p>
              </div>
            </div>
          </div>
          
          {/* Logout Button */}
          <Button
            onClick={handleLogout}
            className="w-full bg-neutral-100 text-neutral-700 hover:bg-red-50 hover:text-red-600 font-semibold rounded-xl py-2.5 flex items-center justify-center transition-colors"
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
      <nav className="lg:hidden fixed bottom-0 w-full bg-white border-t border-neutral-200 z-50 shadow-lg">
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
