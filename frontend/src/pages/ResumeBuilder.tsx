import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import { apiRequest } from '../services/api';

// Interfaces matching Backend ResumeDraft
interface ResumeDraft {
  profile: {
    full_name: string;
    email: string;
    phone: string;
    location: string;
    linkedin: string;
    github: string;
    website: string;
    summary: string;
    awards: string[];     // New
    languages: string[];  // New
    interests: string[];  // New
  };
  experience: Array<{
    company: string;
    position: string;
    start_date: string;
    end_date: string;
    location: string;
    achievements: string[];
  }>;
  education: Array<{
    institution: string;
    degree: string;
    graduation_date: string;
    gpa: string;
    relevant_coursework: string[];
  }>;
  skills: {
    technical: string[];
    languages: string[]; // Programming langs
    soft_skills: string[];
    frameworks: string[];
    tools: string[];
  };
  projects: Array<{
    name: string;
    description: string;
    technologies: string[];
    url: string;
  }>;
  job_description: string;
  ai_enhancement: {
    enhance_summary: boolean;
    enhance_experience: boolean;
    enhance_projects: boolean;
    custom_instructions: string;
  };
  template_style: string;
}

const initialDraft: ResumeDraft = {
  profile: {
    full_name: '', email: '', phone: '', location: '', linkedin: '', github: '', website: '', summary: '',
    awards: [], languages: [], interests: []
  },
  experience: [],
  education: [],
  skills: { technical: [], languages: [], soft_skills: [], frameworks: [], tools: [] },
  projects: [],
  job_description: '',
  ai_enhancement: { enhance_summary: true, enhance_experience: true, enhance_projects: false, custom_instructions: '' },
  template_style: 'professional'
};

export const ResumeBuilder: React.FC = () => {
  const navigate = useNavigate();
  const { accessToken, refresh } = useAuth();
  const { showToast } = useToast();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [formData, setFormData] = useState<ResumeDraft>(initialDraft);

  // JSON Import State
  const [showJsonImport, setShowJsonImport] = useState(false);
  const [jsonInput, setJsonInput] = useState('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState(false);

  // Example JSON Template
  const EXAMPLE_JSON = {
    "full_name": "Rahul Sharma",
    "professional_title": "Senior Software Engineer",
    "contact": {
      "email": "rahul.sharma@gmail.com",
      "phone": "+91-98765-43210",
      "location": "Bengaluru, Karnataka, India",
      "linkedin": "https://www.linkedin.com/in/rahul-sharma",
      "github": "https://github.com/rahulsharma",
      "portfolio": "https://rahulsharma.dev"
    },
    "summary": "Senior Software Engineer with 5+ years of experience in building scalable web applications using modern JavaScript frameworks and Python-based backend systems. Strong experience in system design, cloud deployment, and mentoring junior developers.",
    "skills": [
      "Python",
      "JavaScript",
      "TypeScript",
      "React",
      "Next.js",
      "FastAPI",
      "Node.js",
      "MongoDB",
      "PostgreSQL",
      "AWS",
      "Docker",
      "Git"
    ],
    "experience": [
      {
        "title": "Senior Software Engineer",
        "company": "Infosys Limited",
        "location": "Bengaluru, Karnataka, India",
        "start_date": "2020-01",
        "end_date": "2023-06",
        "is_current": false,
        "bullets": [
          "Improved backend API performance by 40% through database indexing and caching",
          "Led a team of 6 engineers in an Agile environment",
          "Designed and implemented REST APIs using FastAPI and PostgreSQL",
          "Deployed applications on AWS using Docker and CI/CD pipelines"
        ],
        "description": "Worked on enterprise-scale applications for international clients, focusing on backend architecture and cloud deployment."
      }
    ],
    "education": [
      {
        "degree": "Bachelor of Technology (B.Tech) in Computer Science and Engineering",
        "school": "Indian Institute of Technology, Kharagpur",
        "location": "Kharagpur, West Bengal, India",
        "start_date": "2016-08",
        "end_date": "2020-07",
        "gpa": "8.6/10",
        "honors": "First Class with Distinction",
        "relevant_coursework": [
          "Data Structures and Algorithms",
          "Database Management Systems",
          "Operating Systems",
          "Computer Networks",
          "Software Engineering"
        ],
        "achievements": [
          "Final year project awarded Best Project in department"
        ]
      }
    ],
    "projects": [
      {
        "name": "E-Commerce Backend Platform",
        "description": "Developed a scalable e-commerce backend with authentication, order management, and payment integration.",
        "technologies": [
          "FastAPI",
          "PostgreSQL",
          "Redis",
          "Docker",
          "AWS"
        ],
        "link": "https://github.com/rahulsharma/ecommerce-backend"
      }
    ],
    "certifications": [
      {
        "name": "AWS Certified Solutions Architect – Associate",
        "issuer": "Amazon Web Services",
        "date_obtained": "2022-09",
        "credential_url": "https://aws.amazon.com/verification"
      }
    ],
    "languages": [
      {
        "name": "English",
        "proficiency": "Professional"
      },
      {
        "name": "Hindi",
        "proficiency": "Native"
      }
    ],
    "volunteer_work": [],
    "awards": [],
    "publications": []
  };

  const loadExample = () => {
    setJsonInput(JSON.stringify(EXAMPLE_JSON, null, 2));
    setJsonError(null);
  };

  // JSON Import Handler
  const handleJsonImport = async () => {
    setJsonError(null);

    try {
      let profileData = JSON.parse(jsonInput);

      // Check if full user object, extract profile
      if ('profile' in profileData && typeof profileData.profile === 'object') {
        profileData = profileData.profile;
      }

      // Import via API to sanitize and store
      await apiRequest<any>(
        '/api/v1/users/me/profile/import-json',
        {
          method: 'POST',
          body: JSON.stringify(profileData),
        },
        accessToken,
        refresh
      );

      showToast('Profile imported successfully!', 'success');

      // Reload the profile data
      const userProfile = await apiRequest<any>('/api/v1/profile', { method: 'GET' }, accessToken, refresh);

      if (userProfile) {
        const p = userProfile.profile || {};
        const contact = p.contact || {};

        setFormData(prev => ({
          ...prev,
          profile: {
            ...prev.profile,
            full_name: p.full_name || '',
            email: contact.email || '',
            phone: contact.phone || '',
            location: contact.location || '',
            linkedin: contact.linkedin || '',
            github: contact.github || '',
            website: contact.website || contact.portfolio || '',
            summary: p.summary || '',
            awards: p.awards || [],
            languages: p.languages || [],
            interests: p.interests || []
          },
          experience: (p.experience || []).map((e: any) => ({
            company: e.company || '',
            position: e.title || '',
            start_date: e.start_date || '',
            end_date: e.end_date || '',
            location: e.location || '',
            achievements: e.bullets || []
          })),
          education: (p.education || []).map((e: any) => ({
            institution: e.school || '',
            degree: e.degree || '',
            graduation_date: e.end_date || '',
            gpa: e.gpa || '',
            relevant_coursework: []
          })),
          skills: {
            technical: p.skills || [],
            languages: [],
            soft_skills: [],
            frameworks: [],
            tools: []
          },
          projects: (p.projects || []).map((pr: any) => ({
            name: pr.name || '',
            description: pr.description || '',
            technologies: pr.technologies || [],
            url: pr.link || ''
          }))
        }));
      }
      setImportSuccess(true);
      setJsonInput('');
      setShowJsonImport(false);

      // Enable quick generate mode after successful import
      setStep(1); // Reset to step 1 to show quick generate option

    } catch (error: any) {
      if (error.message.includes('JSON')) {
        setJsonError('Invalid JSON format. Please check your input.');
      } else {
        setJsonError(error.message || 'Failed to import profile');
      }
    }
  };

  // Initial Data Load
  useEffect(() => {
    const loadProfile = async () => {
      if (!accessToken) return;
      try {
        // Fetch user profile to pre-fill
        const userProfile = await apiRequest<any>('/api/v1/profile', { method: 'GET' }, accessToken, refresh);

        // Map API profile to our Draft structure
        if (userProfile) {
          const p = userProfile.profile || {};
          const contact = p.contact || {};

          setFormData(prev => ({
            ...prev,
            profile: {
              ...prev.profile,
              full_name: p.full_name || '',
              email: contact.email || '',
              phone: contact.phone || '',
              location: contact.location || '',
              linkedin: contact.linkedin || '',
              github: contact.github || '',
              website: contact.website || contact.portfolio || '',
              summary: p.summary || '',
              awards: p.awards || [],
              languages: p.languages || [],
              interests: p.interests || []
            },
            // Map other arrays if they exist in source
            experience: (p.experience || []).map((e: any) => ({
              company: e.company || '',
              position: e.title || '', // Map title -> position
              start_date: e.start_date || '',
              end_date: e.end_date || '',
              location: e.location || '',
              achievements: e.bullets || []
            })),
            education: (p.education || []).map((e: any) => ({
              institution: e.school || '',
              degree: e.degree || '',
              graduation_date: e.end_date || '',
              gpa: e.gpa || '',
              relevant_coursework: []
            })),
            skills: {
              technical: p.skills || [], // Assuming flat array in DB profile for now
              languages: [],
              soft_skills: [],
              frameworks: [],
              tools: []
            },
            projects: (p.projects || []).map((pr: any) => ({
              name: pr.name || '',
              description: pr.description || '',
              technologies: pr.technologies || [],
              url: pr.link || ''
            }))
          }));
        }
      } catch (error) {
        console.warn("Could not load existing profile, starting fresh.");
      } finally {
        setInitializing(false);
      }
    };
    loadProfile();
  }, [accessToken]);

  const handleChange = (section: keyof ResumeDraft, field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section] as any,
        [field]: value
      }
    }));
  };

  const handleArrayChange = (section: string, index: number, field: string, value: any) => {
    setFormData(prev => {
      const list = [...(prev as any)[section]];
      list[index] = { ...list[index], [field]: value };
      return { ...prev, [section]: list };
    });
  };

  const addItem = (section: 'experience' | 'education' | 'projects') => {
    setFormData(prev => {
      const newItem = section === 'experience' ? { company: '', position: '', start_date: '', end_date: '', achievements: [] }
        : section === 'education' ? { institution: '', degree: '', graduation_date: '', gpa: '', relevant_coursework: [] }
          : { name: '', description: '', technologies: [], url: '' };
      return { ...prev, [section]: [...prev[section], newItem] };
    });
  };

  const removeItem = (section: 'experience' | 'education' | 'projects', index: number) => {
    setFormData(prev => ({
      ...prev,
      [section]: prev[section].filter((_, i) => i !== index)
    }));
  };

  // Helper for string lists (Skills, Awards, etc)
  const handleStringListChange = (path: string[], value: string) => {
    const list = value.split(',').map(s => s.trim()).filter(s => s);
    // path example: ['profile', 'awards'] or ['skills', 'technical']
    if (path.length === 2) {
      setFormData(prev => ({
        ...prev,
        [path[0]]: {
          ...(prev as any)[path[0]],
          [path[1]]: list
        }
      }));
    }
  };

  const handleGenerate = async () => {
    try {
      setLoading(true);

      // Validate required fields
      if (!formData.profile.full_name || !formData.profile.full_name.trim()) {
        showToast('Please provide your full name in the profile', 'error');
        setLoading(false);
        return;
      }

      // Validate experience entries if any exist
      for (let i = 0; i < formData.experience.length; i++) {
        const exp = formData.experience[i];
        if (!exp.company || !exp.company.trim()) {
          showToast(`Experience entry ${i + 1}: Company name is required`, 'error');
          setLoading(false);
          return;
        }
        if (!exp.position || !exp.position.trim()) {
          showToast(`Experience entry ${i + 1}: Position is required`, 'error');
          setLoading(false);
          return;
        }
      }

      // Clean up empty fields if necessary
      // The ResumeDraft expects specific structure, strict validation
      const payload = {
        ...formData,
        // Ensure array fields initialized
        profile: { ...formData.profile },
        experience: formData.experience,
        education: formData.education,
        projects: formData.projects,
        skills: formData.skills
      };

      const response = await apiRequest<{ resume_id: string; status: string }>(
        '/api/v1/resumes',
        {
          method: 'POST',
          body: JSON.stringify(payload)
        },
        accessToken,
        refresh
      );

      showToast('Resume generation started! Redirecting...', 'success');
      setTimeout(() => navigate(`/resumes/${response.resume_id}`), 1000);

    } catch (error: any) {
      showToast(error.message || 'Failed to generate resume', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (initializing) return <Layout><div className="py-20 flex justify-center"><LoadingSpinner size="lg" /></div></Layout>;

  // Step Rendering Helpers
  const renderNav = () => (
    <div className="flex justify-between items-center mb-8">
      <h1 className="text-2xl font-bold dark:text-white">Unified Resume Builder</h1>
      <div className="flex gap-2 text-sm font-medium">
        {[1, 2, 3, 4, 5].map(s => (
          <div key={s} className={`w-8 h-8 rounded-full flex items-center justify-center ${step === s ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
            {s}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <Layout>
      <div className="max-w-5xl mx-auto pb-20">
        {renderNav()}

        {/* STEP 1: HEADER & JD */}
        {step === 1 && (
          <div className="space-y-6 animate-fade-in">
            {/* JSON Import Section */}
            <Card>
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h2 className="text-xl font-bold dark:text-white">Quick Import from JSON</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      Already have your profile data? Paste it here to auto-fill all fields instantly.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowJsonImport(!showJsonImport)}
                    className="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-md hover:bg-indigo-100"
                  >
                    {showJsonImport ? 'Hide' : 'Show'} JSON Import
                  </button>
                </div>

                {showJsonImport && (
                  <div className="space-y-4 mt-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Paste Your Profile JSON
                      </label>
                      <textarea
                        className="w-full p-3 border rounded-lg dark:bg-gray-800 dark:text-white dark:border-gray-600 font-mono text-xs"
                        rows={12}
                        value={jsonInput}
                        onChange={(e) => setJsonInput(e.target.value)}
                        placeholder='{"full_name": "John Doe", "phone": "555-1234", ...}'
                        spellCheck={false}
                      />
                      <p className="mt-2 text-xs text-gray-500">
                        💡 You can paste either just the profile object or the complete user object (we'll extract it automatically)
                      </p>
                    </div>

                    {jsonError && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-sm text-red-700">{jsonError}</p>
                      </div>
                    )}

                    <div className="flex gap-3">
                      <Button
                        variant="secondary"
                        onClick={loadExample}
                      >
                        📋 Load Example
                      </Button>
                      <Button
                        variant="primary"
                        onClick={handleJsonImport}
                        disabled={!jsonInput.trim()}
                      >
                        Import & Auto-Fill Form
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setJsonInput('');
                          setJsonError(null);
                        }}
                      >
                        Clear
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Quick Generate Option (shows after successful JSON import) */}
            {importSuccess && (
              <Card>
                <div className="p-6 space-y-6">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                    <h3 className="text-lg font-semibold text-green-900 mb-2">✅ Profile Imported Successfully!</h3>
                    <p className="text-sm text-green-700">Your profile data has been saved. You can now generate a resume directly or continue with the detailed form.</p>
                  </div>

                  <h2 className="text-xl font-bold dark:text-white border-b pb-2">Quick Generate Resume</h2>
                  <p className="text-sm text-gray-500">Skip the form and generate your resume directly using your imported profile.</p>

                  <div>
                    <label className="block text-sm font-medium mb-2 dark:text-gray-300">Job Description (Optional)</label>
                    <textarea
                      className="w-full p-3 border rounded-lg dark:bg-gray-800 dark:text-white dark:border-gray-600 focus:ring-2 focus:ring-primary-500"
                      rows={6}
                      placeholder="Paste the job description to tailor your resume..."
                      value={formData.job_description}
                      onChange={e => setFormData({ ...formData, job_description: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 dark:text-gray-300">AI Enhancement</label>
                    <div className="space-y-2">
                      <label className="flex items-center space-x-3 p-3 border rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.ai_enhancement.enhance_summary}
                          onChange={e => setFormData(p => ({ ...p, ai_enhancement: { ...p.ai_enhancement, enhance_summary: e.target.checked } }))}
                          className="w-5 h-5 text-primary-600"
                        />
                        <span className="dark:text-white font-medium">✨ Enhance Summary with AI</span>
                      </label>
                      <label className="flex items-center space-x-3 p-3 border rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={formData.ai_enhancement.enhance_experience}
                          onChange={e => setFormData(p => ({ ...p, ai_enhancement: { ...p.ai_enhancement, enhance_experience: e.target.checked } }))}
                          className="w-5 h-5 text-primary-600"
                        />
                        <span className="dark:text-white font-medium">✨ Enhance Experience Bullets</span>
                      </label>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <Button
                      variant="primary"
                      size="lg"
                      onClick={handleGenerate}
                      isLoading={loading}
                      className="flex-1"
                    >
                      {loading ? 'Generating Resume...' : '🚀 Generate Resume Now'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setImportSuccess(false)}
                      className="px-6"
                    >
                      Use Detailed Form Instead
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            <Card>
              <div className="p-6 space-y-4">
                <h2 className="text-xl font-bold dark:text-white border-b pb-2">Target Job</h2>
                <p className="text-sm text-gray-500">Paste the job description here. The AI will use this to tailor your resume.</p>
                <textarea
                  className="w-full p-3 border rounded-lg dark:bg-gray-800 dark:text-white dark:border-gray-600 focus:ring-2 focus:ring-primary-500"
                  rows={6}
                  placeholder="Paste Job Description..."
                  value={formData.job_description}
                  onChange={e => setFormData({ ...formData, job_description: e.target.value })}
                />
              </div>
            </Card>
            <Card>
              <div className="p-6 space-y-4">
                <h2 className="text-xl font-bold dark:text-white border-b pb-2">Personal Details</h2>
                <div className="grid grid-cols-2 gap-4">
                  <Input label="Full Name" value={formData.profile.full_name} onChange={e => handleChange('profile', 'full_name', e.target.value)} />
                  <Input label="Email" value={formData.profile.email} onChange={e => handleChange('profile', 'email', e.target.value)} />
                  <Input label="Phone" value={formData.profile.phone} onChange={e => handleChange('profile', 'phone', e.target.value)} />
                  <Input label="Location" value={formData.profile.location} onChange={e => handleChange('profile', 'location', e.target.value)} />
                  <Input label="LinkedIn" value={formData.profile.linkedin} onChange={e => handleChange('profile', 'linkedin', e.target.value)} />
                  <Input label="GitHub" value={formData.profile.github} onChange={e => handleChange('profile', 'github', e.target.value)} />
                  <Input label="Portfolio / Website" value={formData.profile.website} onChange={e => handleChange('profile', 'website', e.target.value)} />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 dark:text-gray-300">Professional Summary</label>
                  <textarea
                    className="w-full p-2 border rounded-lg dark:bg-gray-800 dark:text-white dark:border-gray-600"
                    rows={4}
                    value={formData.profile.summary}
                    onChange={e => handleChange('profile', 'summary', e.target.value)}
                  />
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* STEP 2: EXPERIENCE */}
        {step === 2 && (
          <div className="space-y-6 animate-fade-in">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold dark:text-white border-b pb-4 mb-4">Work Experience</h2>
                {formData.experience.map((exp, i) => (
                  <div key={i} className="mb-6 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800/50 relative">
                    <button onClick={() => removeItem('experience', i)} className="absolute top-2 right-2 text-red-500 hover:text-red-700">✕</button>
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <Input label="Company" value={exp.company} onChange={e => handleArrayChange('experience', i, 'company', e.target.value)} />
                      <Input label="Position" value={exp.position} onChange={e => handleArrayChange('experience', i, 'position', e.target.value)} />
                      <Input label="Start Date" value={exp.start_date} placeholder="YYYY-MM" onChange={e => handleArrayChange('experience', i, 'start_date', e.target.value)} />
                      <Input label="End Date" value={exp.end_date} placeholder="YYYY-MM or Present" onChange={e => handleArrayChange('experience', i, 'end_date', e.target.value)} />
                    </div>
                    <label className="block text-sm font-medium mb-1 dark:text-gray-300">Achievements (One per line)</label>
                    <textarea
                      className="w-full p-2 border rounded dark:bg-gray-800 dark:text-white dark:border-gray-600"
                      rows={4}
                      value={exp.achievements.join('\n')}
                      onChange={e => handleArrayChange('experience', i, 'achievements', e.target.value.split('\n'))}
                      placeholder="- Increased revenue by 20%..."
                    />
                  </div>
                ))}
                <Button variant="outline" onClick={() => addItem('experience')}>+ Add Experience</Button>
              </div>
            </Card>
          </div>
        )}

        {/* STEP 3: EDUCATION & PROJECTS */}
        {step === 3 && (
          <div className="space-y-6 animate-fade-in">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold dark:text-white border-b pb-4 mb-4">Education</h2>
                {formData.education.map((edu, i) => (
                  <div key={i} className="mb-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800/50 relative">
                    <button onClick={() => removeItem('education', i)} className="absolute top-2 right-2 text-red-500 hover:text-red-700">✕</button>
                    <div className="grid grid-cols-2 gap-4">
                      <Input label="Institution" value={edu.institution} onChange={e => handleArrayChange('education', i, 'institution', e.target.value)} />
                      <Input label="Degree" value={edu.degree} onChange={e => handleArrayChange('education', i, 'degree', e.target.value)} />
                      <Input label="Graduation Date" value={edu.graduation_date} onChange={e => handleArrayChange('education', i, 'graduation_date', e.target.value)} />
                      <Input label="GPA / Score" value={edu.gpa} onChange={e => handleArrayChange('education', i, 'gpa', e.target.value)} />
                    </div>
                  </div>
                ))}
                <Button variant="outline" onClick={() => addItem('education')}>+ Add Education</Button>
              </div>
            </Card>
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold dark:text-white border-b pb-4 mb-4">Projects</h2>
                {formData.projects.map((proj, i) => (
                  <div key={i} className="mb-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800/50 relative">
                    <button onClick={() => removeItem('projects', i)} className="absolute top-2 right-2 text-red-500 hover:text-red-700">✕</button>
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <Input label="Project Name" value={proj.name} onChange={e => handleArrayChange('projects', i, 'name', e.target.value)} />
                      <Input label="Link / URL" value={proj.url} onChange={e => handleArrayChange('projects', i, 'url', e.target.value)} />
                    </div>
                    <div className="mb-3">
                      <label className="block text-sm font-medium mb-1 dark:text-gray-300">Technologies (comma separated)</label>
                      <input className="w-full p-2 border rounded dark:bg-gray-800 dark:text-white"
                        value={proj.technologies.join(', ')}
                        onChange={e => handleArrayChange('projects', i, 'technologies', e.target.value.split(',').map((s: string) => s.trim()))}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 dark:text-gray-300">Description</label>
                      <textarea className="w-full p-2 border rounded dark:bg-gray-800 dark:text-white"
                        rows={2} value={proj.description}
                        onChange={e => handleArrayChange('projects', i, 'description', e.target.value)}
                      />
                    </div>
                  </div>
                ))}
                <Button variant="outline" onClick={() => addItem('projects')}>+ Add Project</Button>
              </div>
            </Card>
          </div>
        )}

        {/* STEP 4: SKILLS & EXTRAS */}
        {step === 4 && (
          <div className="space-y-6 animate-fade-in">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold dark:text-white border-b pb-4 mb-4">Skills</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block font-bold mb-1 dark:text-white">Technical Skills (Comma separated)</label>
                    <textarea className="w-full p-3 border rounded dark:bg-gray-800 dark:text-white" rows={3}
                      value={formData.skills.technical.join(', ')}
                      onChange={e => handleStringListChange(['skills', 'technical'], e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block font-bold mb-1 dark:text-white">Soft Skills / Behavioral</label>
                    <textarea className="w-full p-3 border rounded dark:bg-gray-800 dark:text-white" rows={2}
                      value={formData.skills.soft_skills.join(', ')}
                      onChange={e => handleStringListChange(['skills', 'soft_skills'], e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold dark:text-white border-b pb-4 mb-4">Additional Info</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block font-bold mb-1 dark:text-white">Awards & Achievements (Comma separated)</label>
                    <textarea className="w-full p-2 border rounded dark:bg-gray-800 dark:text-white" rows={2}
                      value={formData.profile.awards.join(', ')}
                      onChange={e => handleStringListChange(['profile', 'awards'], e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block font-bold mb-1 dark:text-white">Languages Known</label>
                    <input className="w-full p-2 border rounded dark:bg-gray-800 dark:text-white"
                      value={formData.profile.languages.join(', ')}
                      onChange={e => handleStringListChange(['profile', 'languages'], e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block font-bold mb-1 dark:text-white">Interests</label>
                    <input className="w-full p-2 border rounded dark:bg-gray-800 dark:text-white"
                      value={formData.profile.interests.join(', ')}
                      onChange={e => handleStringListChange(['profile', 'interests'], e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* STEP 5: REVIEW & GENERATE */}
        {step === 5 && (
          <div className="space-y-6 animate-fade-in">
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold dark:text-white border-b pb-4 mb-4">AI & Generation Settings</h2>
                <div className="grid grid-cols-1 gap-4">
                  <label className="flex items-center space-x-3 p-3 border rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer">
                    <input type="checkbox" checked={formData.ai_enhancement.enhance_summary}
                      onChange={e => setFormData(p => ({ ...p, ai_enhancement: { ...p.ai_enhancement, enhance_summary: e.target.checked } }))}
                      className="w-5 h-5 text-primary-600"
                    />
                    <span className="dark:text-white font-medium">✨ Enhance Summary with AI</span>
                  </label>
                  <label className="flex items-center space-x-3 p-3 border rounded hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer">
                    <input type="checkbox" checked={formData.ai_enhancement.enhance_experience}
                      onChange={e => setFormData(p => ({ ...p, ai_enhancement: { ...p.ai_enhancement, enhance_experience: e.target.checked } }))}
                      className="w-5 h-5 text-primary-600"
                    />
                    <span className="dark:text-white font-medium">✨ Enhance Experience Bullets</span>
                  </label>
                </div>
                <div className="mt-4">
                  <label className="block font-bold mb-2 dark:text-white">Additional Instructions for AI</label>
                  <textarea className="w-full p-3 border rounded dark:bg-gray-800 dark:text-white"
                    placeholder="e.g. 'Focus on leadership' or 'Use more technical jargon'"
                    value={formData.ai_enhancement.custom_instructions}
                    onChange={e => setFormData(p => ({ ...p, ai_enhancement: { ...p.ai_enhancement, custom_instructions: e.target.value } }))}
                  />
                </div>
              </div>
            </Card>

            <div className="text-center p-8">
              <h3 className="text-2xl font-bold mb-4 dark:text-white">Ready to Build?</h3>
              <p className="mb-6 text-gray-600 dark:text-gray-300">
                This will save your profile updates and generate a tailored PDF resume.
              </p>
              <Button size="lg" variant="primary" onClick={handleGenerate} isLoading={loading} className="px-12 py-4 text-lg">
                {loading ? 'Generating...' : '🚀 Generate Resume'}
              </Button>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t p-4 flex justify-between max-w-5xl mx-auto w-full z-10">
          <Button variant="ghost" disabled={step === 1} onClick={() => setStep(s => s - 1)}>
            Back
          </Button>
          {step < 5 ? (
            <Button variant="primary" onClick={() => setStep(s => s + 1)}>
              Next Step →
            </Button>
          ) : (
            <div />
          )}
        </div>
        <div className="h-20"></div> {/* Spacer for fixed footer */}
      </div>
    </Layout>
  );
};
