import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { ToastProvider } from './contexts/ToastContext';
import { ToastContainer } from './components/ToastContainer';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Profile } from './pages/Profile';
import { ResumeBuilder } from './pages/ResumeBuilder';
import { GenerateResume } from './pages/GenerateResume';
import { ProfileSetup } from './pages/ProfileSetup';
import { NewResumeBuilder } from './pages/NewResumeBuilder';
import { ResumeDetail } from './pages/ResumeDetail';
import { ProfileJsonInput } from './pages/ProfileJsonInput';
import { useAuth } from './hooks/useAuth';
import { ErrorBoundary } from './components/ErrorBoundary';

// Protected Route wrapper
interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <div className="min-h-screen">
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Protected Routes */}
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/resumes/new"
                  element={
                    <ProtectedRoute>
                      <ResumeBuilder />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/resumes"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/generate-resume"
                  element={
                    <ProtectedRoute>
                      <GenerateResume />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/profile/setup"
                  element={
                    <ProtectedRoute>
                      <ProfileSetup />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/profile/json-import"
                  element={
                    <ProtectedRoute>
                      <ProfileJsonInput />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/resumes/builder"
                  element={
                    <ProtectedRoute>
                      <NewResumeBuilder />
                    </ProtectedRoute>
                  }
                />

                <Route
                  path="/resumes/:id"
                  element={
                    <ProtectedRoute>
                      <ResumeDetail />
                    </ProtectedRoute>
                  }
                />

                {/* Redirect root to dashboard */}
                <Route path="/" element={<Navigate to="/dashboard" replace />} />

                {/* 404 Not Found */}
                <Route
                  path="*"
                  element={
                    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                      <div className="text-center">
                        <h1 className="text-6xl font-bold gradient-text mb-4">404</h1>
                        <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">Page not found</p>
                        <a
                          href="/"
                          className="px-6 py-3 bg-gradient-to-r from-primary-600 to-secondary-600 text-white rounded-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 inline-block"
                        >
                          Go Home
                        </a>
                      </div>
                    </div>
                  }
                />
              </Routes>

              <ToastContainer />
            </div>
          </Router>
        </ToastProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
