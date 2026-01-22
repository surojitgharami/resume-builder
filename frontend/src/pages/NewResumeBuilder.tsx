// src/pages/NewResumeBuilder.tsx
/**
 * Hybrid Resume Builder with AI Enhancement
 * 
 * Creates resumes from user profile with optional AI enhancement.
 * Users can toggle AI enhancement for different sections.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { getProfile } from '../services/profileApi';
import { apiRequest } from '../services/api';

interface ResumeSection {
    title: string;
    content: string;
    order: number;
    ai_enhanced: boolean;
}

interface ResumeResponse {
    resume_id: string;
    sections: ResumeSection[];
    generated_at: string;
    status: string;
    download_url?: string;
    job_description?: string;
    ai_enhanced_sections: Record<string, boolean>;
}

export const NewResumeBuilder: React.FC = () => {
    const navigate = useNavigate();
    const { accessToken, refresh } = useAuth();
    const { showToast } = useToast();

    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [hasProfile, setHasProfile] = useState(false);

    // Form state
    const [jobDescription, setJobDescription] = useState('');
    const [useAI, setUseAI] = useState(false);
    const [enhanceSummary, setEnhanceSummary] = useState(true);
    const [enhanceExperience, setEnhanceExperience] = useState(true);
    const [enhanceProjects, setEnhanceProjects] = useState(false);
    const [tone, setTone] = useState('professional');

    // Generated resume
    const [resume, setResume] = useState<ResumeResponse | null>(null);

    useEffect(() => {
        // Only check profile if user is authenticated
        if (accessToken) {
            checkProfile();
        } else {
            setLoading(false);
        }
    }, [accessToken]);

    const checkProfile = async () => {
        try {
            setLoading(true);
            await getProfile(accessToken, refresh);
            setHasProfile(true);
        } catch (err: any) {
            if (err.message?.includes('404') || err.message?.includes('not found')) {
                // No profile found, redirect to setup
                showToast('Please create your profile first', 'info');
                navigate('/profile/setup');
            } else {
                showToast('Failed to load profile', 'error');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        try {
            setGenerating(true);

            // Fetch user profile first
            const userProfile = await getProfile(accessToken, refresh);

            // Build proper ResumeDraft payload matching backend model
            // Map UserProfile fields to ResumeDraft structure
            const requestBody = {
                profile: {
                    full_name: userProfile.full_name || "User Name",
                    email: userProfile.contact?.email,
                    phone: userProfile.contact?.phone,
                    location: userProfile.contact?.location,
                    summary: userProfile.summary,
                    linkedin: userProfile.contact?.linkedin,
                    github: userProfile.contact?.github,
                    website: userProfile.contact?.website || userProfile.contact?.portfolio,
                },
                // Transform experience: title -> position, bullets -> achievements
                experience: (userProfile.experience || []).map(exp => ({
                    company: exp.company,
                    position: exp.title, // UserProfile uses 'title', ResumeDraft uses 'position'
                    start_date: exp.start_date,
                    end_date: exp.end_date,
                    current: exp.is_current,
                    location: exp.location,
                    achievements: exp.bullets || [], // UserProfile uses 'bullets', ResumeDraft uses 'achievements'
                })),
                // Transform education
                education: (userProfile.education || []).map(edu => ({
                    school: edu.school,
                    degree: edu.degree,
                    start_date: edu.start_date,
                    end_date: edu.end_date,
                    location: edu.location,
                    gpa: edu.gpa,
                })),
                // Backend expects Skills object (not array) with technical, languages, frameworks fields
                skills: userProfile.skills && userProfile.skills.length > 0 ? {
                    technical: userProfile.skills,
                    languages: [],
                    frameworks: [],
                    tools: [],
                    soft_skills: [],
                    certifications: []
                } : undefined, // Optional field, can be omitted if no skills
                projects: (userProfile.projects || []).map(proj => ({
                    name: proj.name,
                    description: proj.description,
                    technologies: proj.technologies || [],
                    url: proj.link,
                    highlights: proj.highlights || [],
                })),
                ai_enhancement: {
                    enhance_summary: useAI && enhanceSummary,
                    enhance_experience: useAI && enhanceExperience,
                    enhance_projects: useAI && enhanceProjects,
                    custom_instructions: tone !== 'professional' ? `Use a ${tone} tone` : undefined,
                },
                job_description: jobDescription || undefined,
            };

            const response = await apiRequest<{ resume_id: string; status: string }>(
                '/api/v1/resumes',
                {
                    method: 'POST',
                    body: JSON.stringify(requestBody),
                },
                accessToken,
                refresh
            );

            // Show success message with resume ID
            showToast(`Resume generation started! ID: ${response.resume_id}`, 'success');

            // Navigate to dashboard to see resume status
            setTimeout(() => navigate('/dashboard'), 1500);
        } catch (err: any) {
            showToast(err.message || 'Failed to create resume', 'error');
        } finally {
            setGenerating(false);
        }
    };

    const handleDownloadPDF = async () => {
        if (!resume) return;

        try {
            const response = await apiRequest<{ pdf_url: string }>(
                `/api/v1/resumes/${resume.resume_id}/download-pdf`,
                { method: 'GET' },
                accessToken,
                refresh
            );

            if (response.pdf_url) {
                // Open PDF in new tab
                window.open(response.pdf_url, '_blank');
            }
        } catch (err) {
            showToast('Failed to download PDF', 'error');
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex justify-center items-center min-h-screen">
                    <LoadingSpinner size="lg" />
                </div>
            </Layout>
        );
    }

    if (!hasProfile) {
        return null; // Will redirect
    }

    return (
        <Layout>
            <div className="max-w-7xl mx-auto py-8 px-4">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Create Resume
                    </h1>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        Generate a professional resume from your profile with optional AI enhancement
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Left: Configuration */}
                    <div className="space-y-6">
                        {/* Job Description */}
                        <Card>
                            <div className="p-6">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                                    Job Description (Optional)
                                </h2>
                                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                                    Paste a job description to tailor your resume with AI
                                </p>
                                <textarea
                                    value={jobDescription}
                                    onChange={(e) => setJobDescription(e.target.value)}
                                    rows={8}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                    placeholder="Paste job description here..."
                                />
                            </div>
                        </Card>

                        {/* AI Enhancement Settings */}
                        <Card>
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                            AI Enhancement
                                        </h2>
                                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                            Let AI improve your content
                                        </p>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={useAI}
                                            onChange={(e) => setUseAI(e.target.checked)}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                                    </label>
                                </div>

                                {useAI && (
                                    <div className="space-y-3 mt-4 pl-4 border-l-2 border-primary-500">
                                        <label className="flex items-center space-x-3">
                                            <input
                                                type="checkbox"
                                                checked={enhanceSummary}
                                                onChange={(e) => setEnhanceSummary(e.target.checked)}
                                                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                            />
                                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                                Enhance Professional Summary
                                            </span>
                                        </label>

                                        <label className="flex items-center space-x-3">
                                            <input
                                                type="checkbox"
                                                checked={enhanceExperience}
                                                onChange={(e) => setEnhanceExperience(e.target.checked)}
                                                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                            />
                                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                                Enhance Experience Bullets
                                            </span>
                                        </label>

                                        <label className="flex items-center space-x-3">
                                            <input
                                                type="checkbox"
                                                checked={enhanceProjects}
                                                onChange={(e) => setEnhanceProjects(e.target.checked)}
                                                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                            />
                                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                                Enhance Project Descriptions
                                            </span>
                                        </label>
                                    </div>
                                )}
                            </div>
                        </Card>

                        {/* Template Settings */}
                        <Card>
                            <div className="p-6">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                                    Template Settings
                                </h2>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Tone
                                    </label>
                                    <select
                                        value={tone}
                                        onChange={(e) => setTone(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                    >
                                        <option value="professional">Professional</option>
                                        <option value="technical">Technical</option>
                                        <option value="creative">Creative</option>
                                        <option value="casual">Casual</option>
                                    </select>
                                </div>
                            </div>
                        </Card>

                        {/* Generate Button */}
                        <Button
                            variant="primary"
                            onClick={handleGenerate}
                            disabled={generating}
                            className="w-full"
                        >
                            {generating ? (
                                <>
                                    <LoadingSpinner size="sm" />
                                    <span className="ml-2">Generating Resume...</span>
                                </>
                            ) : (
                                '✨ Generate Resume'
                            )}
                        </Button>
                    </div>

                    {/* Right: Preview */}
                    <div>
                        <Card>
                            <div className="p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                        Preview
                                    </h2>
                                    {resume && (
                                        <Button variant="outline" size="sm" onClick={handleDownloadPDF}>
                                            📄 Download PDF
                                        </Button>
                                    )}
                                </div>

                                {!resume ? (
                                    <div className="text-center py-12">
                                        <div className="text-6xl mb-4">📝</div>
                                        <p className="text-gray-500 dark:text-gray-400">
                                            Configure your settings and click "Generate Resume" to see a preview
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-6 max-h-[800px] overflow-y-auto">
                                        {resume.sections.map((section, index) => (
                                            <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <h3 className="font-semibold text-gray-900 dark:text-white">
                                                        {section.title}
                                                    </h3>
                                                    {section.ai_enhanced && (
                                                        <span className="px-2 py-0.5 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 text-xs rounded-full">
                                                            ✨ AI Enhanced
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                                                    {section.content}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </Card>

                        {resume && (
                            <div className="mt-4 flex gap-4">
                                <Button
                                    variant="outline"
                                    onClick={() => navigate('/dashboard')}
                                    className="flex-1"
                                >
                                    View All Resumes
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={() => {
                                        setResume(null);
                                        setJobDescription('');
                                    }}
                                    className="flex-1"
                                >
                                    Create Another
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};
