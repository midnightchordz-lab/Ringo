import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Create axios instance with auth interceptor
const api = axios.create({
  baseURL: `${BACKEND_URL}/api`
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

// Handle 401 errors (token expired) - but only for non-auth endpoints
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect to login if:
    // 1. It's a 401 error
    // 2. Not already on login/register page
    // 3. Not an auth-related endpoint (to prevent logout loops)
    const isAuthEndpoint = error.config?.url?.includes('/auth/');
    const isOnAuthPage = window.location.pathname === '/login' || 
                         window.location.pathname === '/register' ||
                         window.location.pathname === '/verify-email';
    
    if (error.response?.status === 401 && !isAuthEndpoint && !isOnAuthPage) {
      // Double check if token exists - if it does, might be a race condition
      const token = localStorage.getItem('token');
      if (!token) {
        // No token, redirect to login
        window.location.href = '/login';
      }
      // If token exists but got 401, it might be expired - let the component handle it
    }
    return Promise.reject(error);
  }
);

export default api;
