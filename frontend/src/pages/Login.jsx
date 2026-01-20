import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Mail, Lock, Sparkles, ArrowRight, Play, Zap, Shield, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, {
        email,
        password
      });

      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      toast.success(`Welcome back, ${response.data.user.full_name}!`);
      
      setTimeout(() => {
        navigate('/');
      }, 100);
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = () => {
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleMicrosoftSignIn = async () => {
    try {
      // Get Microsoft OAuth URL from backend
      const response = await api.get('/auth/microsoft/login');
      const authUrl = response.data.auth_url;
      window.location.href = authUrl;
    } catch (error) {
      console.error('Microsoft sign in error:', error);
      toast.error('Failed to initiate Microsoft sign in');
    }
  };

  return (
    <div className="min-h-screen flex bg-white">
      {/* Left Side - Branding & Features */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 p-12 flex-col justify-between relative overflow-hidden">
        {/* Decorative Elements */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2"></div>
        
        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-white/20 backdrop-blur-xl rounded-xl flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>ContentFlow</span>
          </div>
          
          <h2 className="text-4xl lg:text-5xl font-bold text-white leading-tight mb-6" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Create amazing content with <span className="text-yellow-300">copyright-free</span> media
          </h2>
          <p className="text-blue-100 text-lg mb-8">
            Discover viral videos, images, and educational resources - all free to use commercially.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="relative z-10 space-y-4">
          <div className="flex items-center gap-4 bg-white/10 backdrop-blur-xl rounded-xl p-4">
            <div className="w-10 h-10 bg-yellow-400 rounded-lg flex items-center justify-center">
              <Play className="w-5 h-5 text-yellow-900" fill="currentColor" />
            </div>
            <div>
              <p className="text-white font-semibold">CC Licensed Videos</p>
              <p className="text-blue-200 text-sm">Find viral content ready for reuse</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 bg-white/10 backdrop-blur-xl rounded-xl p-4">
            <div className="w-10 h-10 bg-emerald-400 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-emerald-900" />
            </div>
            <div>
              <p className="text-white font-semibold">Commercial Safe</p>
              <p className="text-blue-200 text-sm">All content cleared for business use</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 bg-white/10 backdrop-blur-xl rounded-xl p-4">
            <div className="w-10 h-10 bg-pink-400 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-pink-900" />
            </div>
            <div>
              <p className="text-white font-semibold">AI-Powered</p>
              <p className="text-blue-200 text-sm">Smart search and recommendations</p>
            </div>
          </div>
        </div>

        {/* Testimonial */}
        <div className="relative z-10 bg-white/10 backdrop-blur-xl rounded-xl p-6 mt-8">
          <p className="text-white/90 italic mb-4">"ContentFlow has completely transformed how we source content. The time saved is incredible!"</p>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center text-white font-bold">
              S
            </div>
            <div>
              <p className="text-white font-semibold">Sarah Chen</p>
              <p className="text-blue-200 text-sm">Content Manager, TechCorp</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12 bg-neutral-50">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl mb-4 shadow-lg">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gradient" style={{ fontFamily: 'Outfit, sans-serif' }}>ContentFlow</h1>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="text-3xl font-bold text-neutral-900 mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Welcome back! 👋
            </h1>
            <p className="text-neutral-500">Sign in to your account to continue</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="studio-card p-8"
          >
            {/* Google Sign In */}
            <Button
              type="button"
              onClick={handleGoogleSignIn}
              className="w-full bg-white border-2 border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 font-semibold rounded-xl py-6 mb-3 flex items-center justify-center gap-3 transition-all"
              data-testid="google-signin-button"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </Button>

            {/* Microsoft Sign In */}
            <Button
              type="button"
              onClick={handleMicrosoftSignIn}
              className="w-full bg-white border-2 border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 font-semibold rounded-xl py-6 mb-6 flex items-center justify-center gap-3 transition-all"
              data-testid="microsoft-signin-button"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#F25022" d="M1 1h10v10H1z"/>
                <path fill="#00A4EF" d="M1 13h10v10H1z"/>
                <path fill="#7FBA00" d="M13 1h10v10H13z"/>
                <path fill="#FFB900" d="M13 13h10v10H13z"/>
              </svg>
              Continue with Microsoft
            </Button>

            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-neutral-200"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-neutral-500">or sign in with email</span>
              </div>
            </div>

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 z-10" />
                  <Input
                    data-testid="email-input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="studio-input-icon"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 z-10" />
                  <Input
                    data-testid="password-input"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="studio-input-icon"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-6 text-base"
                data-testid="login-button"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Signing in...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    Sign In <ArrowRight className="w-5 h-5" />
                  </span>
                )}
              </Button>
            </form>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-center mt-6 text-neutral-600"
          >
            Don't have an account?{' '}
            <Link to="/register" className="text-blue-600 hover:text-blue-700 font-semibold">
              Create one free
            </Link>
          </motion.p>
        </div>
      </div>
    </div>
  );
};

export default Login;
