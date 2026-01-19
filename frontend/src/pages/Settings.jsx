import { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings as SettingsIcon, Key, Save, Youtube, Instagram } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Settings = () => {
  const [youtubeKey, setYoutubeKey] = useState('');
  const [instagramToken, setInstagramToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings/api-keys`);
      if (response.data.youtube_api_key) {
        setYoutubeKey(response.data.youtube_api_key);
      }
      if (response.data.instagram_access_token) {
        setInstagramToken(response.data.instagram_access_token);
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.post(`${API}/settings/api-keys`, {
        youtube_api_key: youtubeKey,
        instagram_access_token: instagramToken
      });
      toast.success('Settings saved successfully!');
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#BEF264] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-500">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: 'Oswald, sans-serif' }}>
          Settings
        </h1>
        <p className="text-zinc-500">Configure your API keys and preferences</p>
      </div>

      {/* API Keys Section */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-center space-x-3 mb-6">
          <Key className="w-6 h-6 text-[#BEF264]" />
          <h2 className="text-xl font-bold text-white" style={{ fontFamily: 'Oswald, sans-serif' }}>
            API Keys
          </h2>
        </div>

        <div className="space-y-6">
          {/* YouTube API Key */}
          <div>
            <label className="flex items-center space-x-2 text-sm text-zinc-400 mb-2">
              <Youtube className="w-4 h-4 text-red-500" />
              <span>YouTube Data API Key</span>
            </label>
            <Input
              data-testid="youtube-api-key-input"
              type="password"
              placeholder="Enter your YouTube API key"
              value={youtubeKey}
              onChange={(e) => setYoutubeKey(e.target.value)}
              className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white"
            />
            <p className="text-xs text-zinc-600 mt-2">
              Get your API key from{' '}
              <a
                href="https://console.cloud.google.com/apis/credentials"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#BEF264] hover:underline"
              >
                Google Cloud Console
              </a>
            </p>
          </div>

          {/* Instagram Access Token */}
          <div>
            <label className="flex items-center space-x-2 text-sm text-zinc-400 mb-2">
              <Instagram className="w-4 h-4 text-pink-500" />
              <span>Instagram Access Token</span>
            </label>
            <Input
              data-testid="instagram-token-input"
              type="password"
              placeholder="Enter your Instagram access token"
              value={instagramToken}
              onChange={(e) => setInstagramToken(e.target.value)}
              className="bg-zinc-950/50 border-zinc-800 focus:border-[#BEF264] focus:ring-1 focus:ring-[#BEF264] rounded-lg text-white"
            />
            <p className="text-xs text-zinc-600 mt-2">
              Get your access token from{' '}
              <a
                href="https://developers.facebook.com/apps/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#BEF264] hover:underline"
              >
                Meta for Developers
              </a>
            </p>
          </div>
        </div>

        <Button
          data-testid="save-settings-button"
          onClick={handleSave}
          disabled={saving}
          className="mt-6 bg-[#BEF264] text-zinc-900 hover:bg-[#A3E635] font-bold rounded-full px-8 py-3 shadow-[0_0_15px_rgba(190,242,100,0.3)] hover:shadow-[0_0_25px_rgba(190,242,100,0.5)] transition-all"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>

      {/* Info Card */}
      <div className="glass-card p-6 bg-blue-500/10 border-blue-500/20">
        <h3 className="text-lg font-bold text-white mb-3" style={{ fontFamily: 'Oswald, sans-serif' }}>
          ℹ️ API Usage Information
        </h3>
        <ul className="space-y-2 text-sm text-zinc-400">
          <li>• YouTube Data API has a daily quota limit of 10,000 units</li>
          <li>• Instagram Graph API limits posts to 25 per day per account</li>
          <li>• Your API keys are stored securely and never shared</li>
          <li>• Make sure your APIs are enabled in their respective consoles</li>
        </ul>
      </div>
    </div>
  );
};

export default Settings;