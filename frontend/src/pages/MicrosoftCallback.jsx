import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../utils/api';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const MicrosoftCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const { login } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (errorParam) {
        console.error('Microsoft OAuth error:', errorParam, errorDescription);
        setError(errorDescription || 'Authentication failed');
        toast.error(errorDescription || 'Microsoft sign in failed');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received');
        toast.error('Authentication failed - no code received');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      try {
        // Exchange code for token
        const redirectUri = window.location.origin + '/auth/microsoft/callback';
        
        const response = await api.post('/auth/microsoft/callback', 
          new URLSearchParams({
            code: code,
            redirect_uri: redirectUri
          }),
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded'
            }
          }
        );

        if (response.data.access_token) {
          // Use auth context login - this updates state reactively
          login(response.data.access_token, response.data.user);
          
          toast.success(`Welcome, ${response.data.user.full_name || response.data.user.email}!`);
          navigate('/');
        } else {
          throw new Error('No access token received');
        }
      } catch (error) {
        console.error('Microsoft callback error:', error);
        const errorMessage = error.response?.data?.detail || 'Authentication failed';
        setError(errorMessage);
        toast.error(errorMessage);
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate, login]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center p-8 bg-white rounded-2xl shadow-xl max-w-md">
        {error ? (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-neutral-800 mb-2">Authentication Failed</h2>
            <p className="text-neutral-500 mb-4">{error}</p>
            <p className="text-sm text-neutral-400">Redirecting to login...</p>
          </>
        ) : (
          <>
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
            <h2 className="text-xl font-bold text-neutral-800 mb-2">Signing you in...</h2>
            <p className="text-neutral-500">Completing Microsoft authentication</p>
          </>
        )}
      </div>
    </div>
  );
};

export default MicrosoftCallback;
