import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Create axios instance with auth interceptor
const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 30000 // 30 second timeout to prevent page freeze
});

// Add token to all requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 errors - DON'T auto-redirect or clear tokens
// Let the AuthContext and ProtectedRoute handle authentication state
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle timeout errors
    if (error.code === 'ECONNABORTED') {
      console.error('Request timed out:', error.config?.url);
      return Promise.reject(new Error('Request timed out. Please try again.'));
    }
    
    // Log 401 errors for debugging but DON'T auto-logout or redirect
    // This prevents race conditions and unwanted logouts during navigation
    if (error.response?.status === 401) {
      console.warn('401 Unauthorized response:', error.config?.url);
      // Don't clear tokens or redirect - let the component/AuthContext handle it
      // The ProtectedRoute will redirect to login if needed
    }
    return Promise.reject(error);
  }
);

export default api;
