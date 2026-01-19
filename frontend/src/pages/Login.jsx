import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Mail, Lock, Sparkles, ArrowRight } from 'lucide-react';
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

      // Store token and user info
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      toast.success(`Welcome back, ${response.data.user.full_name}!`);
      navigate('/');
    } catch (error) {
      console.error('Login error:', error);
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 gradient-primary rounded-2xl mb-4 shadow-xl">
            <Sparkles className="w-8 h-8 text-white" fill="white" />
          </div>
          <h1 className="text-4xl font-black mb-2 bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent" style={{ fontFamily: 'Sora, sans-serif' }}>
            Welcome Back
          </h1>
          <p className="text-slate-600 text-lg">Sign in to continue to ContentFlow</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-8"
        >
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@example.com"
                  className="pl-12 h-12 border-2 border-slate-200 focus:border-violet-500 rounded-xl"
                  data-testid="email-input"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="pl-12 h-12 border-2 border-slate-200 focus:border-violet-500 rounded-xl"
                  data-testid="password-input"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full gradient-primary text-white font-bold rounded-xl py-6 text-lg shadow-lg shadow-violet-500/30 hover:shadow-xl hover:shadow-violet-500/40"
              data-testid="login-button"
            >
              {loading ? 'Signing in...' : (
                <span className="flex items-center justify-center">
                  Sign In
                  <ArrowRight className="w-5 h-5 ml-2" />
                </span>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-slate-600">
              Don't have an account?{' '}
              <Link to="/register" className="font-bold text-violet-600 hover:text-violet-700">
                Sign up
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Login;