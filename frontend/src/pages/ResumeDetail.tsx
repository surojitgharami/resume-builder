import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { apiRequest } from '../services/api';
import DOMPurify from 'dompurify';

interface ResumeDetail {
    resume_id: string;
    user_id: string;
    job_description?: string;
    generated_at?: string;
    created_at?: string;
    status: string;
    sections: Array<{ title: string; content: string }>;
    download_url?: string;
    error_message?: string;
}

interface UserProfile {
    full_name: string;
    contact: {
        email: string;
        phone?: string;
        linkedin?: string;
        github?: string;
        website?: string;
    };
    photo_url?: string;
}

export const ResumeDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const { accessToken, refresh } = useAuth();
    const { showToast } = useToast();
    const [resume, setResume] = useState<ResumeDetail | null>(null);
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const ctrl = new AbortController();
        let mounted = true;

        if (!id || !accessToken) {
            setLoading(false);
            return;
        }

        const fetchData = async () => {
            try {
                // Fetch Resume
                const resumeData = await apiRequest<ResumeDetail>(
                    `/api/v1/resumes/${id}`,
                    { method: 'GET', signal: ctrl.signal },
                    accessToken,
                    refresh
                );

                if (mounted) setResume(resumeData);

                // Fetch Profile (to display real name in preview)
                try {
                    const profileData = await apiRequest<UserProfile>(
                        `/api/v1/profile`,
                        { method: 'GET', signal: ctrl.signal },
                        accessToken,
                        refresh
                    );
                    if (mounted) setProfile(profileData);
                } catch (err) {
                    console.warn('Failed to load profile for preview header:', err);
                }

            } catch (error: any) {
                if (!ctrl.signal.aborted && mounted) {
                    console.error('Failed to load resume:', error);
                    showToast('Failed to load resume details', 'error');
                }
            } finally {
                if (mounted) setLoading(false);
            }
        };

        fetchData();

        return () => {
            mounted = false;
            ctrl.abort();
        };
    }, [id, accessToken]);

    if (loading) {
        return (
            <Layout>
                <div className="py-12">
                    <LoadingSpinner size="lg" />
                </div>
            </Layout>
        );
    }

    if (!resume) {
        return (
            <Layout>
                <div className="max-w-4xl mx-auto">
                    <Card>
                        <div className="p-12 text-center">
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Resume not found</h3>
                            <Link to="/dashboard"><Button variant="primary">Back to Dashboard</Button></Link>
                        </div>
                    </Card>
                </div>
            </Layout>
        );
    }

    const createdDate = new Date(resume.generated_at || resume.created_at || Date.now()).toLocaleDateString();

    const getPhotoUrl = (url?: string) => {
        if (!url) return null;
        if (url.startsWith('http')) return url;
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
    };

    // Check if we have real data or should show placeholders
    const displayName = profile?.full_name || "YOUR NAME";
    const displayEmail = profile?.contact?.email || "email@example.com";
    const displayPhone = profile?.contact?.phone || "123-456-7890";

    // LaTeX-style CSS-in-JS
    const latexFontFamily = '"Latin Modern Roman", "Times New Roman", Times, serif';

    const cleanContent = (content: string): string => {
        if (!content) return '';

        // Split into lines
        let lines = content.split('\n');

        // Filter out conversational filler and redundant headers
        lines = lines.map(line => {
            let trimmed = line.trim();
            // Remove conversational prefixes but keep content
            trimmed = trimmed.replace(/^(Here is|Here's|Note:|However,|This section|Given the job description|I've kept|I'm excited).*?:\s*/i, '');
            trimmed = trimmed.replace(/^(Here is|Here's|Note:|However,|This section|Given the job description|I've kept|I'm excited)[^:]*$/i, '');

            return trimmed;
        }).filter(line => {
            // Remove empty lines
            if (!line) return false;

            // Remove redundant self-headers (e.g. "**Professional Summary:**")
            if (line.match(/^\*\*.*\*\*$/) && lines.length > 5) {
                // Check if it's just a header and we have other content
                return true;
            }

            return true;
        });

        return lines.join('\n');
    };

    const renderMarkdown = (text: string): string => {
        if (!text) return '';
        // Sanitize first
        let result = DOMPurify.sanitize(text);

        // Convert **bold** to <strong>
        result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // Convert *italic* to <em>
        result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Convert various bullet styles at start of line to standard bullet
        result = result.replace(/^[*+\-•]\s+/gm, '• ');

        return result;
    };

    return (
        <Layout>
            <div className="max-w-4xl mx-auto space-y-6 animate-fade-in font-sans">
                {/* Control Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <Link to="/dashboard" className="text-primary-600 hover:text-primary-700 dark:text-primary-400 mb-2 inline-flex items-center">
                            ← Back to Dashboard
                        </Link>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mt-2">Resume Details</h1>
                        <p className="mt-2 text-gray-600 dark:text-gray-400">Created on {createdDate}</p>
                    </div>
                    {resume.download_url && (
                        <a href={resume.download_url} target="_blank" rel="noopener noreferrer">
                            <Button variant="primary">Download PDF</Button>
                        </a>
                    )}
                </div>

                {/* Status Badge & Profile Warning */}
                <div className="flex items-center gap-4">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${resume.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
                        {resume.status.charAt(0).toUpperCase() + resume.status.slice(1)}
                    </span>
                    {!profile && (
                        <span className="text-amber-600 text-sm flex items-center bg-amber-50 px-3 py-2 rounded border border-amber-200">
                            ⚠️ <strong>Action Required:</strong> Profile incomplete. Resume contains generic text.
                            <Link to="/profile" className="ml-2 underline font-bold hover:text-amber-800">Edit Profile & Regenerate</Link>
                        </span>
                    )}
                </div>

                {/* Preview Container - Scaled A4 Representation 
                     Matched to LaTeX: 9pt font, 0.4in top/bottom, 0.5in left/right margins
                 */}
                <div className="bg-white text-black shadow-lg rounded-none mx-auto border border-gray-300 overflow-hidden"
                    style={{
                        width: '210mm',
                        minHeight: '297mm',
                        padding: '10.16mm 12.7mm', // 0.4in = 10.16mm, 0.5in = 12.7mm
                        fontFamily: latexFontFamily,
                        fontSize: '9pt',
                        lineHeight: '1.2'
                    }}>

                    {/* Header Simulation */}
                    <div className="flex justify-between items-start mb-1">
                        <div className="w-2/3">
                            <div style={{ height: '2pt' }}></div>
                            <h1 className="font-bold uppercase mb-1 leading-none" style={{ fontFamily: latexFontFamily, fontSize: '17.28pt' }}>
                                {displayName}
                            </h1>
                            <div style={{ fontSize: '9pt' }}>
                                <div className="mb-0.5">
                                    <span className="font-bold">Email: </span>
                                    <span className="mr-2">{displayEmail}</span>
                                </div>
                                <div className="mb-0.5">
                                    <span className="font-bold">Phone: </span>
                                    <span>{displayPhone}</span>
                                </div>
                                {profile?.contact?.linkedin && (
                                    <div className="mb-0.5"><span className="font-bold">LinkedIn: </span>{profile.contact.linkedin}</div>
                                )}
                                {profile?.contact?.github && (
                                    <div className="mb-0.5"><span className="font-bold">GitHub: </span>{profile.contact.github}</div>
                                )}
                                {profile?.contact?.website && (
                                    <div className="mb-0.5"><span className="font-bold">Portfolio: </span>{profile.contact.website}</div>
                                )}
                            </div>
                        </div>
                        <div className="w-1/3 flex justify-end">
                            {profile?.photo_url ? (
                                <img
                                    src={getPhotoUrl(profile.photo_url) || ''}
                                    alt="Profile"
                                    className="w-[3cm] h-[3cm] object-cover border border-gray-300"
                                />
                            ) : profile ? (
                                <img
                                    src={`https://ui-avatars.com/api/?name=${encodeURIComponent(displayName || 'User')}&background=e2e8f0&color=64748b&size=256`}
                                    alt="Profile"
                                    className="w-[3cm] h-[3cm] object-cover border border-gray-300"
                                />
                            ) : (
                                <div className="w-[3cm] h-[3cm] bg-gray-100 flex items-center justify-center text-[8pt] text-gray-400 border border-dashed border-gray-300">
                                    No Photo
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Content Rendering Loop */}
                    {resume.sections
                        .filter(section => section.title.toUpperCase() !== 'CONTACT INFORMATION')
                        .map((section, index) => (
                            <div key={index} className="mb-2">
                                {/* Section Title (\sectiontitle) */}
                                <div className="uppercase font-bold tracking-wide mb-0"
                                    style={{ fontFamily: latexFontFamily, fontSize: '10pt', marginTop: '8pt', color: '#000' }}>
                                    {section.title}
                                </div>
                                {/* Rule (\hrule) */}
                                <div className="bg-black mb-2" style={{ height: '1px' }}></div>

                                {/* Section Content */}
                                <div className="text-justify" style={{ fontSize: '9pt' }}>
                                    {cleanContent(section.content).split('\n').map((line, i) => {
                                        const trimmed = line.trim();

                                        // Bullet points (\item)
                                        if (trimmed.startsWith('-') || trimmed.startsWith('•') || trimmed.startsWith('+ ') || trimmed.startsWith('* ')) {
                                            const bulletText = trimmed.replace(/^[-•+*]\s*/, '');
                                            return (
                                                <div key={i} className="flex items-start mb-0.5 pl-[18pt] relative leading-[1.2]">
                                                    <span className="absolute left-[4pt] top-0 text-black text-[8pt]">•</span>
                                                    <span dangerouslySetInnerHTML={{ __html: renderMarkdown(bulletText) }} />
                                                </div>
                                            );
                                        }

                                        // Key-Value pairs (e.g. for Skills: "Technical Skills: ...")
                                        // Logic: Line contains ':' and is short enough to be a label-value pair, not a sentence.
                                        if (trimmed.includes(':') && trimmed.length < 150 && !trimmed.endsWith('.')) {
                                            const [key, val] = trimmed.split(/:(.+)/);
                                            if (val) {
                                                return (
                                                    <div key={i} className="mb-1 leading-[1.2]">
                                                        <span className="font-bold">{key}:</span> <span dangerouslySetInnerHTML={{ __html: renderMarkdown(val) }} />
                                                    </div>
                                                );
                                            }
                                        }

                                        // Standard text (e.g. summary or dates)
                                        return <div key={i} className="mb-0.5 leading-[1.2]" dangerouslySetInnerHTML={{ __html: renderMarkdown(line) }} />;
                                    })}
                                </div>
                            </div>
                        ))}
                </div>
            </div>
        </Layout>
    );
};
