import { Outlet, Link, useLocation } from 'react-router-dom';
import { Home, Search, Clock, Settings, Sparkles, Youtube, Instagram } from 'lucide-react';
import { motion } from 'framer-motion';

const navItems = [
  { path: '/', icon: Home, label: 'Dashboard' },
  { path: '/discover', icon: Search, label: 'Discover' },
  { path: '/history', icon: Clock, label: 'History' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export const Layout = () => {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-[#09090B] overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-zinc-950 border-r border-zinc-800 fixed h-full">
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Sparkles className="w-8 h-8 text-[#BEF264]" strokeWidth={1.5} />
              <div className="absolute inset-0 blur-xl bg-[#BEF264] opacity-20"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white" style={{ fontFamily: 'Oswald, sans-serif' }}>ViralFlow</h1>
              <p className="text-xs text-zinc-500">Studio</p>
            </div>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'bg-[#BEF264]/10 text-[#BEF264] border border-[#BEF264]/20'
                    : 'text-zinc-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-5 h-5" strokeWidth={1.5} />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        
        <div className="p-4 border-t border-zinc-800">
          <div className="glass-card p-4 space-y-2">
            <p className="text-xs text-zinc-500 uppercase tracking-wider">Connected</p>
            <div className="flex items-center space-x-2">
              <Youtube className="w-4 h-4 text-red-500" />
              <Instagram className="w-4 h-4 text-pink-500" />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 lg:ml-64 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          <Outlet />
        </motion.div>
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="lg:hidden fixed bottom-0 w-full bg-zinc-950/90 backdrop-blur-lg border-t border-zinc-800 z-50">
        <div className="flex justify-around items-center h-16">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`mobile-nav-${item.label.toLowerCase()}`}
                className={`flex flex-col items-center justify-center space-y-1 px-3 py-2 rounded-lg transition-colors ${
                  isActive ? 'text-[#BEF264]' : 'text-zinc-400'
                }`}
              >
                <Icon className="w-5 h-5" strokeWidth={1.5} />
                <span className="text-xs">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
};

export default Layout;