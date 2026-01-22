import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import api from '../utils/api';
import { motion } from 'framer-motion';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '../context/AuthContext';

export const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const verifyEmail = useCallback(async (token) => {
    try {
      const response = await api.get('/auth/verify-email', {
        params: { token }
      });

      if (response.data.success) {
        setStatus('success');
        setMessage(response.data.message);

        // Use auth context login if token provided
        if (response.data.access_token) {
          login(response.data.access_token, response.data.user);
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
  }, [navigate, login]);

  useEffect(() => {
    const token = searchParams.get('token');

    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link');
      return;
    }

    verifyEmail(token);
  }, [searchParams, verifyEmail]);

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
              Email Verified!
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
