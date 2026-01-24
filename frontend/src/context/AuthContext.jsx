import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  // Initialize auth state from localStorage synchronously
  const getInitialToken = () => localStorage.getItem('token');
  const getInitialUser = () => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        return JSON.parse(storedUser);
      } catch (e) {
        console.error('Error parsing stored user:', e);
        localStorage.removeItem('user');
        return null;
      }
    }
    return null;
  };

  const [user, setUser] = useState(getInitialUser);
  const [token, setToken] = useState(getInitialToken);
  const [isLoading, setIsLoading] = useState(true); // Start with loading true

  // Login function - updates both localStorage and state
  const login = useCallback((accessToken, userData) => {
    localStorage.setItem('token', accessToken);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(accessToken);
    setUser(userData);
    setIsLoading(false);
  }, []);

  // Logout function - clears both localStorage and state
  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setIsLoading(false);
  }, []);

  // Validate token on initial load
  useEffect(() => {
    const validateToken = async () => {
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');
      
      if (!storedToken || !storedUser) {
        setIsLoading(false);
        return;
      }

      try {
        // Verify token is still valid by calling /auth/me
        const response = await axios.get(`${BACKEND_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
          timeout: 5000
        });
        
        // Token is valid - update user data if needed
        if (response.data) {
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
        }
      } catch (error) {
        // Only logout if it's a clear 401 error (token invalid/expired)
        if (error.response?.status === 401) {
          console.log('Token expired or invalid, logging out');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setToken(null);
          setUser(null);
        }
        // For other errors (network, timeout), keep the user logged in
        // They can still use the app, individual API calls will handle errors
      } finally {
        setIsLoading(false);
      }
    };

    validateToken();
  }, []);

  // Check if authenticated
  const isAuthenticated = Boolean(token && user);

  // Listen for storage changes from other tabs
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'token') {
        if (e.newValue) {
          setToken(e.newValue);
        } else {
          setToken(null);
          setUser(null);
        }
      }
      if (e.key === 'user') {
        if (e.newValue) {
          try {
            setUser(JSON.parse(e.newValue));
          } catch (err) {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
