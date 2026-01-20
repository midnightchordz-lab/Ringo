import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Discover from '@/pages/Discover';
import Images from '@/pages/Images';
import ContentLibrary from '@/pages/ContentLibrary';
import VideoPreview from '@/pages/VideoPreview';
import History from '@/pages/History';
import Settings from '@/pages/Settings';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import AuthCallback from '@/pages/AuthCallback';
import MicrosoftCallback from '@/pages/MicrosoftCallback';
import VerifyEmail from '@/pages/VerifyEmail';
import PendingVerification from '@/pages/PendingVerification';
import '@/App.css';

// Protected Route wrapper
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" replace />;
};

// Router component to handle auth callback detection
function AppRouter() {
  const location = useLocation();
  
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  // Detect session_id in URL fragment synchronously during render
  if (location.hash?.includes('session_id=') || location.pathname === '/auth/callback') {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/pending-verification" element={<PendingVerification />} />
      
      {/* Protected routes */}
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Dashboard />} />
        <Route path="discover" element={<Discover />} />
        <Route path="images" element={<Images />} />
        <Route path="library" element={<ContentLibrary />} />
        <Route path="video/:videoId" element={<VideoPreview />} />
        <Route path="history" element={<History />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <div className="App min-h-screen">
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
      <Toaster position="bottom-right" />
    </div>
  );
}

export default App;