import React, { useState, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { apiRequest } from '../services/api';
import DOMPurify from 'dompurify';

interface ResumeSection {
  title: string;
  content: string;
  order?: number;
}

interface GenerateResumeResponse {
  resume_id: string;
  sections: ResumeSection[];
  generated_at: string;
  download_url?: string;
}

interface UserProfile {
  full_name: string;
  photo_url?: string;
  contact: {
    email: string;
    phone?: string;
    linkedin?: string;
    github?: string;
    website?: string;
  };
}

const getPhotoUrl = (url?: string) => {
  if (!url) return null;
  if (url.startsWith('http')) return url;
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
};

export const GenerateResume: React.FC = () => {
  const [jobDescription, setJobDescription] = useState<string>('');
  const [templateId, setTemplateId] = useState<string>('professional');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [resumeData, setResumeData] = useState<GenerateResumeResponse | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  // JSON Import State
  const [showJsonImport, setShowJsonImport] = useState(false);
  const [jsonInput, setJsonInput] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState(false);

  const { accessToken, refresh } = useAuth();

  // Example JSON
  const EXAMPLE_JSON = {
    "full_name": "Rahul Sharma",
    "phone": "+91-98765-43210",
    "location": "Bengaluru, Karnataka, India",
    "linkedin_url": "https://www.linkedin.com/in/rahul-sharma",
    "github_url": "https://github.com/rahulsharma",
    "portfolio_url": "https://rahulsharma.dev",
    "summary": "Senior Software Engineer with 5+ years of experience in building scalable web applications",
    "skills": ["Python", "JavaScript", "React", "FastAPI", "AWS"],
    "experience": [{
      "company": "Infosys Limited",
      "position": "Senior Software Engineer",
      "start_date": "2020-01",
      "end_date": "2023-06",
      "achievements": ["Improved API performance by 40%", "Led team of 6 engineers"]
    }],
    "education": [{
      "institution": "IIT Kharagpur",
      "degree": "B.Tech Computer Science",
      "graduation_date": "2020",
      "gpa": "8.6/10"
    }],
    "certifications": []
  };

  // Fetch user profile for resume header
  React.useEffect(() => {
    const ctrl = new AbortController();
    let mounted = true;

    if (!accessToken) return;

    (async () => {
      try {
        const profileData = await apiRequest<UserProfile>(
          `/api/v1/profile`,
          { method: 'GET', signal: ctrl.signal },
          accessToken,
          refresh
        );
        if (mounted) setProfile(profileData);
      } catch (err) {
        console.warn('Failed to load profile for resume header:', err);
      }
    })();

    return () => {
      mounted = false;
      ctrl.abort();
    };
  }, [accessToken]);

  const loadExample = () => {
    setJsonInput(JSON.stringify(EXAMPLE_JSON, null, 2));
    setJsonError(null);
  };

  const handleJsonImport = async () => {
    setJsonError(null);
    setImportSuccess(false);

    try {
      let profileData = JSON.parse(jsonInput);

      // Check if full user object, extract profile
      if ('profile' in profileData && typeof profileData.profile === 'object') {
        profileData = profileData.profile;
      }

      // Import via API
      await apiRequest<any>(
        '/api/v1/users/me/profile/import-json',
        {
          method: 'POST',
          body: JSON.stringify(profileData),
        },
        accessToken,
        refresh
      );

      setImportSuccess(true);
      setJsonInput('');
      setShowJsonImport(false);

    } catch (error: any) {
      if (error.message.includes('JSON')) {
        setJsonError('Invalid JSON format. Please check your input.');
      } else {
        setJsonError(error.message || 'Failed to import profile');
      }
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResumeData(null);

    try {
      const payload = {
        job_description: jobDescription,
        template_preferences: {
          tone: templateId,
          bullets_per_section: 3,
          include_skills: true,
          include_projects: true,
        },
        format: 'json',
      };

      const response = await apiRequest<GenerateResumeResponse>(
        '/api/v1/generate-resume?use_async=true',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
        accessToken,
        refresh
      );

      setResumeData(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate resume';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const cleanContent = (content: string): string => {
    if (!content) return '';

    // Split into lines
    let lines = content.split('\n');

    // Filter out conversational filler and redundant headers
    lines = lines.map(line => {
      let trimmed = line.trim();
      // Remove conversational prefixes but keep content
      // Remove "Here is..." up to the colon
      trimmed = trimmed.replace(/^(Here is|Here's|Note:|However,|This section|Given the job description|I've kept|I'm excited).*?:\s*/i, '');
      // Remove "Here is..." if it's the whole line
      trimmed = trimmed.replace(/^(Here is|Here's|Note:|However,|This section|Given the job description|I've kept|I'm excited)[^:]*$/i, '');

      return trimmed;
    }).filter(line => {
      // Remove empty lines
      if (!line) return false;

      // Remove redundant self-headers (e.g. "**Professional Summary:**")
      if (line.match(/^\*\*.*\*\*$/) && lines.length > 5) {
        // Check if it's just a header and we have other content
        return true; // Keep headers for now to be safe, renderMarkdown handles formatting
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
    // Matches: * space, + space, - space, • space
    result = result.replace(/^[*+\-•]\s+/gm, '• ');

    return result;
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Generate Resume</h1>
          <div className="flex gap-3">
            <Link
              to="/dashboard"
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Dashboard
            </Link>
          </div>
        </div>

        {/* Success Message */}
        {importSuccess && (
          <div className="mb-6 rounded-xl bg-green-50 p-4 border border-green-200 animate-fade-in">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-semibold text-green-800">Profile Imported Successfully!</h3>
                <p className="mt-1 text-sm text-green-700">Your profile data has been saved. Now paste a job description to generate a tailored resume.</p>
              </div>
            </div>
          </div>
        )}

        {/* JSON Import Section */}
        {/* JSON Import Section */}
        <div className="bg-white/80 backdrop-blur-sm shadow-lg rounded-2xl p-6 mb-8 border border-gray-100 transition-all duration-300">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600">Quick Import</h2>
              <p className="text-sm text-gray-500 mt-1">
                Already have your profile data?
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowJsonImport(!showJsonImport)}
              className="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-xl hover:bg-indigo-100 transition-colors duration-200"
            >
              {showJsonImport ? 'Hide' : 'Show'} Importer
            </button>
          </div>

          {showJsonImport && (
            <div className="space-y-4 mt-6 p-6 bg-gray-50/50 rounded-2xl border border-gray-200 backdrop-blur-sm animate-fade-in">
              <div className="group">
                <label className="block text-sm font-semibold text-gray-700 mb-2 group-focus-within:text-indigo-600 transition-colors">
                  Paste Your Profile JSON
                </label>
                <textarea
                  className="block w-full rounded-xl border-gray-200 bg-white p-4 font-mono text-xs text-gray-800 shadow-sm transition-all duration-300 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 hover:border-indigo-300 focus:outline-none"
                  rows={12}
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder='{"full_name": "John Doe", ...}'
                  spellCheck={false}
                />
                <p className="mt-2 text-xs text-gray-500 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  Import full user object or just the profile section
                </p>
              </div>

              {jsonError && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-xl animate-shake">
                  <p className="text-sm text-red-700 font-medium">{jsonError}</p>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={loadExample}
                  className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
                >
                  📋 Load Example
                </button>
                <button
                  type="button"
                  onClick={handleJsonImport}
                  disabled={!jsonInput.trim()}
                  className="px-4 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:shadow-none"
                >
                  Import Profile
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setJsonInput('');
                    setJsonError(null);
                  }}
                  className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-red-600 bg-transparent hover:bg-red-50 rounded-xl transition-all"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="bg-white/80 backdrop-blur-sm shadow-xl rounded-2xl p-8 mb-8 border border-gray-100 transition-all duration-300 hover:shadow-2xl">
          <div className="mb-8 group">
            <label htmlFor="jobDescription" className="block text-sm font-semibold text-gray-700 mb-3 group-focus-within:text-indigo-600 transition-colors">
              Job Description
            </label>
            <div className="relative">
              <textarea
                id="jobDescription"
                name="jobDescription"
                rows={8}
                required
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                className="block w-full rounded-xl border-gray-200 bg-gray-50/50 p-4 text-gray-900 shadow-sm transition-all duration-300 focus:bg-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 hover:bg-gray-50 focus:outline-none resize-y text-sm leading-relaxed"
                placeholder="Paste the job description here..."
                disabled={loading}
              />
              <div className="absolute bottom-3 right-3 pointer-events-none opacity-50">
                <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </div>
            </div>
            <p className="mt-2 text-xs text-gray-500 flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              We'll tailor your resume keywords based on this description
            </p>
          </div>

          <div className="mb-8">
            <label htmlFor="templateId" className="block text-sm font-semibold text-gray-700 mb-3">
              Resume Tone
            </label>
            <div className="relative">
              <select
                id="templateId"
                name="templateId"
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                className="block w-full appearance-none rounded-xl border-gray-200 bg-gray-50/50 p-4 pr-10 text-gray-900 shadow-sm transition-all duration-300 focus:bg-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 hover:bg-gray-50 focus:outline-none cursor-pointer text-sm font-medium"
                disabled={loading}
              >
                <option value="professional">👔 Professional (Standard)</option>
                <option value="technical">💻 Technical (Focus on Skills)</option>
                <option value="creative">🎨 Creative (Unique Phrasing)</option>
                <option value="casual">👋 Casual (Modern Startups)</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-gray-500">
                <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-6 rounded-xl bg-red-50 p-4 border border-red-100">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-1 text-sm text-red-700">
                    <p>{error}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="group relative flex w-full justify-center overflow-hidden rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 p-4 text-sm font-semibold text-white shadow-lg transition-all duration-300 hover:scale-[1.01] hover:shadow-xl hover:from-indigo-500 hover:to-purple-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:scale-100"
          >
            <span className="relative flex items-center gap-2">
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating your masterpiece...
                </>
              ) : (
                <>
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                  </svg>
                  Generate Tailored Resume
                </>
              )}
            </span>
          </button>
        </form>

        {resumeData && (
          <div className="bg-white shadow-md rounded-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Generated Resume</h2>
              {resumeData.download_url && (
                <a
                  href={resumeData.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
                >
                  Download PDF
                </a>
              )}
            </div>

            <div className="text-sm text-gray-500 mb-6">
              Resume ID: {resumeData.resume_id}
            </div>

            {/* LaTeX-style A4 Resume Preview */}
            <div className="bg-white text-black shadow-lg rounded-none mx-auto border border-gray-300 overflow-hidden"
              style={{
                width: '210mm',
                minHeight: '297mm',
                padding: '10.16mm 12.7mm',
                fontFamily: '"Latin Modern Roman", "Times New Roman", Times, serif',
                fontSize: '9pt',
                lineHeight: '1.2'
              }}>

              {/* Header with Profile Info */}
              <div className="flex justify-between items-start mb-1">
                <div className="w-2/3">
                  <div style={{ height: '2pt' }}></div>
                  <h1 className="font-bold uppercase mb-1 leading-none" style={{ fontSize: '17.28pt' }}>
                    {profile?.full_name || "YOUR NAME"}
                  </h1>
                  <div style={{ fontSize: '9pt' }}>
                    <div className="mb-0.5">
                      <span className="font-bold">Email: </span>
                      <span className="mr-2">{profile?.contact?.email || "email@example.com"}</span>
                    </div>
                    <div className="mb-0.5">
                      <span className="font-bold">Phone: </span>
                      <span>{profile?.contact?.phone || "123-456-7890"}</span>
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
                      src={`https://ui-avatars.com/api/?name=${encodeURIComponent(profile.full_name || 'User')}&background=e2e8f0&color=64748b&size=256`}
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

              {/* Resume Sections */}
              {resumeData.sections
                .filter(section => section.title.toUpperCase() !== 'CONTACT INFORMATION')
                .sort((a, b) => (a.order || 0) - (b.order || 0))
                .map((section, index) => (
                  <div key={index} className="mb-2">
                    {/* Section Title */}
                    <div className="uppercase font-bold tracking-wide mb-0"
                      style={{ fontSize: '10pt', marginTop: '8pt', color: '#000' }}>
                      {section.title}
                    </div>
                    {/* Horizontal Rule */}
                    <div className="bg-black mb-2" style={{ height: '1px' }}></div>

                    {/* Section Content */}
                    <div className="text-justify" style={{ fontSize: '9pt' }}>
                      {cleanContent(section.content).split('\n').map((line, i) => {
                        const trimmed = line.trim();

                        // Bullet points
                        if (trimmed.startsWith('-') || trimmed.startsWith('•') || trimmed.startsWith('+ ') || trimmed.startsWith('* ')) {
                          const bulletText = trimmed.replace(/^[-•+*]\s*/, '');
                          return (
                            <div key={i} className="flex items-start mb-0.5 pl-[18pt] relative leading-[1.2]">
                              <span className="absolute left-[4pt] top-0 text-black text-[8pt]">•</span>
                              <span dangerouslySetInnerHTML={{ __html: renderMarkdown(bulletText) }} />
                            </div>
                          );
                        }

                        // Key-Value pairs (e.g. "Technical Skills: ...")
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

                        // Standard text
                        return <div key={i} className="mb-0.5 leading-[1.2]" dangerouslySetInnerHTML={{ __html: renderMarkdown(line) }} />;
                      })}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
