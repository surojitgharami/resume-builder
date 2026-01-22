import { useState, useCallback, useEffect } from 'react';

interface User {
  id: string;
  email: string;
}

interface AuthState {
  accessToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// Helper functions for localStorage
const getStoredAuth = (): AuthState => {
  try {
    const stored = localStorage.getItem('authState');
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to parse stored auth state:', error);
  }
  return {
    accessToken: null,
    user: null,
    isAuthenticated: false,
  };
};

const setStoredAuth = (state: AuthState) => {
  try {
    localStorage.setItem('authState', JSON.stringify(state));
  } catch (error) {
    console.error('Failed to store auth state:', error);
  }
};

const clearStoredAuth = () => {
  try {
    localStorage.removeItem('authState');
  } catch (error) {
    console.error('Failed to clear auth state:', error);
  }
};

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>(getStoredAuth);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Persist auth state to localStorage whenever it changes
  useEffect(() => {
    setStoredAuth(authState);
  }, [authState]);

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data: LoginResponse = await response.json();

      // Fetch full user profile after successful login
      let userId = '';
      try {
        const profileResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/profile/me`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${data.access_token}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        });
        
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          userId = profileData.id || '';
        }
      } catch (err) {
        console.warn('Failed to fetch user profile:', err);
      }

      const newAuthState = {
        accessToken: data.access_token,
        user: { id: userId, email },
        isAuthenticated: true,
      };

      setAuthState(newAuthState);
      setStoredAuth(newAuthState);

      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async (): Promise<string | null> => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data: LoginResponse = await response.json();

      setAuthState(prev => ({
        ...prev,
        accessToken: data.access_token,
      }));

      return data.access_token;
    } catch (err) {
      const clearedState = {
        accessToken: null,
        user: null,
        isAuthenticated: false,
      };
      setAuthState(clearedState);
      clearStoredAuth();
      return null;
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    setLoading(true);

    try {
      await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('Logout request failed:', err);
    } finally {
      const clearedState = {
        accessToken: null,
        user: null,
        isAuthenticated: false,
      };
      setAuthState(clearedState);
      clearStoredAuth();
      setLoading(false);
    }
  }, []);

  return {
    ...authState,
    login,
    refresh,
    logout,
    error,
    loading,
  };
};
