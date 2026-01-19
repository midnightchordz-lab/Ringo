import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import Discover from '@/pages/Discover';
import VideoPreview from '@/pages/VideoPreview';
import History from '@/pages/History';
import Settings from '@/pages/Settings';
import '@/App.css';

function App() {
  return (
    <div className="App min-h-screen bg-zinc-950">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
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