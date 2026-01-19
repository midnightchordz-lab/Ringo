import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get('token');

    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link');
      return;
    }

    verifyEmail(token);
  }, []);

  const verifyEmail = async (token) => {
    try {
      const response = await axios.get(`${API}/auth/verify-email`, {
        params: { token }
      });

      if (response.data.success) {
        setStatus('success');
        setMessage(response.data.message);

        // Store token and user if provided
        if (response.data.access_token) {
          localStorage.setItem('token', response.data.access_token);
          localStorage.setItem('user', JSON.stringify(response.data.user));
        }

        // Redirect after 2 seconds
        setTimeout(() => {
          navigate('/');
        }, 2000);
      }
    } catch (error) {
      console.error('Verification error:', error);
      setStatus('error');
      setMessage(error.response?.data?.detail || 'Verification failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card p-12 max-w-md w-full text-center"
      >
        {status === 'verifying' && (
          <>
            <Loader className="w-16 h-16 mx-auto mb-6 text-violet-600 animate-spin" />
            <h1 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Sora, sans-serif' }}>
              Verifying your email...
            </h1>
            <p className="text-slate-600">Please wait a moment</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Sora, sans-serif' }}>
              Email Verified! 🎉
            </h1>
            <p className="text-slate-600 mb-6">{message}</p>
            <p className="text-sm text-slate-500">Redirecting to dashboard...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 bg-red-100 rounded-full flex items-center justify-center">
              <XCircle className="w-10 h-10 text-red-600" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Sora, sans-serif' }}>
              Verification Failed
            </h1>
            <p className="text-slate-600 mb-6">{message}</p>
            <Link to="/login">
              <Button className="gradient-primary text-white font-bold rounded-xl px-6 py-3">
                Back to Login
              </Button>
            </Link>
          </>
        )}
      </motion.div>
    </div>
  );
};

export default VerifyEmail;