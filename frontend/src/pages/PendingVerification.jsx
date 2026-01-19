import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Mail, Sparkles, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const PendingVerification = () => {
  const [resending, setResending] = useState(false);
  const navigate = useNavigate();
  
  const userEmail = new URLSearchParams(window.location.search).get('email') || 'your email';

  const handleResendEmail = async () => {
    setResending(true);
    try {
      await axios.post(`${API}/auth/resend-verification`, { email: userEmail });
      toast.success('Verification email sent! Check your inbox.');
    } catch (error) {
      console.error('Resend error:', error);
      toast.error('Failed to resend email');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 gradient-primary rounded-2xl mb-4 shadow-xl">
            <Mail className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-black mb-2 bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent" style={{ fontFamily: 'Sora, sans-serif' }}>
            Check Your Email
          </h1>
          <p className="text-slate-600 text-lg">One more step to get started</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-8"
        >
          <div className="text-center space-y-6">
            <div className="w-20 h-20 bg-gradient-to-br from-violet-100 to-purple-100 rounded-full flex items-center justify-center mx-auto">
              <Mail className="w-10 h-10 text-violet-600" />
            </div>

            <div>
              <h2 className="text-xl font-bold text-slate-900 mb-3">Verify your email address</h2>
              <p className="text-slate-600 mb-2">
                We've sent a verification link to:
              </p>
              <p className="font-bold text-violet-600">{userEmail}</p>
            </div>

            <div className="bg-violet-50 border border-violet-200 rounded-xl p-4">
              <p className="text-sm text-slate-700">
                Click the link in the email to verify your account and start using ContentFlow.
              </p>
            </div>

            <div className="space-y-3">
              <p className="text-sm text-slate-600">Didn't receive the email?</p>
              <Button
                onClick={handleResendEmail}
                disabled={resending}
                className="w-full gradient-secondary text-white font-bold rounded-xl py-3"
                data-testid="resend-button"
              >
                {resending ? 'Sending...' : 'Resend Verification Email'}
              </Button>
            </div>

            <div className="pt-4 border-t border-slate-200">
              <Link to="/login" className="text-violet-600 hover:text-violet-700 font-semibold">
                ← Back to Login
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default PendingVerification;