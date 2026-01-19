import { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const sessionId = params.get('session_id');

        if (!sessionId) {
          toast.error('Invalid authentication response');
          navigate('/login');
          return;
        }

        // Exchange session_id for user data
        const response = await axios.post(`${API}/auth/google-oauth`, 
          new URLSearchParams({ session_id: sessionId }),
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            }
          }
        );

        // Store token and user info
        localStorage.setItem('token', response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));

        // Clear URL fragment and redirect to dashboard
        window.history.replaceState(null, '', '/');
        toast.success(`Welcome, ${response.data.user.full_name}! 🎉`);
        navigate('/', { replace: true, state: { user: response.data.user } });

      } catch (error) {
        console.error('Auth callback error:', error);
        toast.error('Authentication failed. Please try again.');
        navigate('/login');
      }
    };

    processAuth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="w-20 h-20 gradient-primary rounded-3xl animate-spin mb-4 mx-auto flex items-center justify-center">
          <div className="w-16 h-16 bg-gradient-to-br from-violet-50 via-sky-50 to-pink-50 rounded-2xl"></div>
        </div>
        <p className="text-slate-700 font-semibold text-lg">Completing sign in...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
