import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Discover from '@/pages/Discover';
import VideoPreview from '@/pages/VideoPreview';
import History from '@/pages/History';
import Settings from '@/pages/Settings';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import '@/App.css';

// Protected Route wrapper
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  return token ? children : <Navigate to="/login" replace />;
};

function App() {
  return (
    <div className="App min-h-screen">
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Protected routes */}
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="discover" element={<Discover />} />
            <Route path="video/:videoId" element={<VideoPreview />} />
            <Route path="history" element={<History />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" />
    </div>
  );
}

export default App;