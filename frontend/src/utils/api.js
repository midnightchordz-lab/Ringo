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

// Handle 401 errors - but DON'T auto-redirect, let components handle it
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle timeout errors
    if (error.code === 'ECONNABORTED') {
      console.error('Request timed out:', error.config?.url);
      return Promise.reject(new Error('Request timed out. Please try again.'));
    }
    
    // Log 401 errors for debugging but don't auto-logout
    // This prevents race conditions during navigation
    if (error.response?.status === 401) {
      console.warn('401 Unauthorized response:', error.config?.url);
      // Only clear credentials if it's NOT a timing issue
      // (i.e., if we made a request without a token at all)
      const requestHadToken = error.config?.headers?.Authorization;
      if (!requestHadToken) {
        // Request was made without token - redirect to login
        const isOnAuthPage = window.location.pathname.includes('/login') || 
                             window.location.pathname.includes('/register') ||
                             window.location.pathname.includes('/verify-email') ||
                             window.location.pathname.includes('/auth/callback');
        if (!isOnAuthPage) {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
      }
      // If request had token but got 401, token might be expired
      // Don't auto-redirect - let user retry or the component handle it
    }
    return Promise.reject(error);
  }
);

export default api;
