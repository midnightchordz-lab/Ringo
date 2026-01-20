import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, Clock, Settings, Sparkles, TrendingUp, LogOut, Image, Library, Video } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard' },
  { path: '/discover', icon: Video, label: 'Videos' },
  { path: '/images', icon: Image, label: 'Images' },
  { path: '/library', icon: Library, label: 'Content Library' },
  { path: '/history', icon: Clock, label: 'History' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

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
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-72 glass-card m-4 mr-0 rounded-3xl relative overflow-hidden">
        {/* Decorative gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 via-purple-500/5 to-pink-500/5 pointer-events-none"></div>
        
        <div className="p-6 border-b border-violet-200/50 relative z-10">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-12 h-12 gradient-primary rounded-2xl flex items-center justify-center shadow-lg">
                <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} fill="white" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-r from-amber-400 to-orange-500 rounded-full animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent" style={{ fontFamily: 'Sora, sans-serif' }}>
                ContentFlow
              </h1>
              <p className="text-xs font-semibold text-violet-500">AI-Powered Platform</p>
            </div>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-2 relative z-10">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
              >
                <motion.div
                  whileHover={{ scale: 1.03, x: 4 }}
                  whileTap={{ scale: 0.98 }}
                  className={`flex items-center space-x-3 px-4 py-3.5 rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'gradient-primary text-white shadow-lg shadow-violet-500/30'
                      : 'text-slate-700 hover:bg-violet-100/60'
                  }`}
                >
                  <Icon className="w-5 h-5" strokeWidth={2.5} />
                  <span className="font-semibold">{item.label}</span>
                  {isActive && (
                    <TrendingUp className="w-4 h-4 ml-auto" strokeWidth={2.5} />
                  )}
                </motion.div>
              </Link>
            );
          })}
        </nav>
        
        {/* Stats preview */}
        <div className="p-4 border-t border-violet-200/50 relative z-10 space-y-3">
          <div className="glass-card p-4 bg-gradient-to-br from-violet-500/10 to-purple-500/10 border-violet-300/50">
            <p className="text-xs font-bold text-violet-600 uppercase tracking-wider mb-2">Logged in as</p>
            <p className="text-sm font-bold text-slate-900 truncate">{user.full_name || 'User'}</p>
            <p className="text-xs text-slate-600 truncate">{user.email || ''}</p>
          </div>
          <Button
            onClick={handleLogout}
            className="w-full bg-red-100 text-red-600 hover:bg-red-200 font-bold rounded-xl py-2 flex items-center justify-center"
            data-testid="logout-button"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="h-full"
        >
          <Outlet />
        </motion.div>
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="lg:hidden fixed bottom-0 w-full glass-card border-t-2 border-violet-200/50 z-50 rounded-t-3xl">
        <div className="flex justify-around items-center h-20 px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`mobile-nav-${item.label.toLowerCase()}`}
                className="flex flex-col items-center justify-center flex-1"
              >
                <motion.div
                  whileTap={{ scale: 0.9 }}
                  className={`flex flex-col items-center space-y-1 px-3 py-2 rounded-xl transition-all ${
                    isActive ? 'gradient-primary text-white shadow-lg' : 'text-slate-600'
                  }`}
                >
                  <Icon className="w-6 h-6" strokeWidth={2.5} />
                  <span className="text-xs font-bold">{item.label}</span>
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