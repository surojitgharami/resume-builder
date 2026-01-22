import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { apiRequest } from '../services/api';

interface Resume {
  resume_id: string;
  job_description: string;
  generated_at?: string;  // Backend uses this field
  created_at?: string;    // Keep for backward compatibility
  sections: Array<{ title: string; content: string }>;
}

export const Dashboard: React.FC = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, thisMonth: 0 });
  const { accessToken, refresh } = useAuth();
  const { showToast } = useToast();

  useEffect(() => {
    const ctrl = new AbortController();
    let mounted = true;

    // Only load resumes if user is authenticated
    if (!accessToken) {
      setLoading(false);
      return () => {
        mounted = false;
        ctrl.abort();
      };
    }

    (async () => {
      try {
        const data = await apiRequest<Resume[]>(
          '/api/v1/resumes/list?limit=6',
          { method: 'GET', signal: ctrl.signal },
          accessToken,
          refresh
        );

        if (mounted) {
          setResumes(data);

          // Calculate stats
          const now = new Date();
          const thisMonth = data.filter(r => {
            const created = new Date(r.created_at || r.generated_at || Date.now());
            return created.getMonth() === now.getMonth() && created.getFullYear() === now.getFullYear();
          }).length;

          setStats({ total: data.length, thisMonth });
        }
      } catch (err: any) {
        if (!ctrl.signal.aborted && mounted) {
          showToast('Failed to load resumes', 'error');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    })();

    return () => {
      mounted = false;
      ctrl.abort();
    };
  }, [accessToken]);


  const truncateText = (text: string | undefined | null, maxLength: number) => {
    if (!text) return 'No description';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <Layout>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Manage your AI-generated resumes
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card variant="gradient">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    Total Resumes
                  </p>
                  <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                    {stats.total}
                  </p>
                </div>
                <div className="p-3 bg-primary-600 rounded-full">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
              </div>
            </div>
          </Card>

          <Card variant="gradient">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    This Month
                  </p>
                  <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">
                    {stats.thisMonth}
                  </p>
                </div>
                <div className="p-3 bg-secondary-600 rounded-full">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
            </div>
          </Card>

          <Card variant="gradient">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
                    Quick Action
                  </p>
                  <Link to="/generate-resume">
                    <Button variant="primary" size="sm" className="mt-2">
                      Create Resume
                    </Button>
                  </Link>
                </div>
                <div className="p-3 bg-accent-600 rounded-full">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Recent Resumes */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Recent Resumes
            </h2>
            <Link to="/resumes">
              <Button variant="ghost" size="sm">
                View All
              </Button>
            </Link>
          </div>

          {loading ? (
            <div className="py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : resumes.length === 0 ? (
            <Card>
              <div className="p-12 text-center">
                <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No resumes yet
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  Get started by creating your first AI-powered resume
                </p>
                <Link to="/generate-resume">
                  <Button variant="primary">
                    Create Your First Resume
                  </Button>
                </Link>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {resumes.map((resume) => (
                <Card key={resume.resume_id} hover>
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                          {resume.sections[0]?.title || 'Untitled Resume'}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                          {truncateText(resume.job_description, 100)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-4">
                      <span>{new Date(resume.generated_at || resume.created_at || Date.now()).toLocaleDateString()}</span>
                      <span>{resume.sections.length} sections</span>
                    </div>

                    <div className="flex gap-2">
                      <Link to={`/resumes/${resume.resume_id}`} className="flex-1">
                        <Button variant="primary" size="sm" className="w-full">
                          View
                        </Button>
                      </Link>
                      <Button variant="outline" size="sm">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};
