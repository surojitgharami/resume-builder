import React, { useState, FormEvent } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiRequest } from '../services/api';
import { useNavigate } from 'react-router-dom';

interface ImportResponse {
    message: string;
    format_detected: 'simple' | 'detailed';
    profiles_updated: string[];
}

const SIMPLE_EXAMPLE = {
    "full_name": "John Doe",
    "phone": "555-1234",
    "location": "San Francisco, CA",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "github_url": "https://github.com/johndoe",
    "portfolio_url": "https://johndoe.com",
    "summary": "Experienced software engineer with 5+ years building scalable web applications...",
    "skills": ["Python", "JavaScript", "React", "FastAPI", "MongoDB", "AWS"],
    "experience": [
        {
            "company": "Tech Corp",
            "position": "Senior Software Engineer",
            "start_date": "2020-01",
            "end_date": "2023-06",
            "location": "San Francisco, CA",
            "description": "Led development of microservices architecture",
            "achievements": [
                "Improved system performance by 40%",
                "Led team of 5 engineers",
                "Implemented CI/CD pipeline"
            ]
        }
    ],
    "education": [
        {
            "institution": "University of California, Berkeley",
            "degree": "BS Computer Science",
            "graduation_date": "2020",
            "gpa": "3.8",
            "honors": "Magna Cum Laude",
            "relevant_coursework": ["Data Structures", "Algorithms", "Machine Learning"]
        }
    ],
    "certifications": []
};

const DETAILED_EXAMPLE = {
    "full_name": "John Doe",
    "professional_title": "Senior Software Engineer",
    "contact": {
        "email": "john@example.com",
        "phone": "555-1234",
        "location": "San Francisco, CA",
        "linkedin": "https://linkedin.com/in/johndoe",
        "github": "https://github.com/johndoe",
        "portfolio": "https://johndoe.com"
    },
    "summary": "Experienced software engineer with 5+ years building scalable web applications...",
    "skills": ["Python", "JavaScript", "React", "FastAPI", "MongoDB", "AWS"],
    "experience": [
        {
            "title": "Senior Software Engineer",
            "company": "Tech Corp",
            "location": "San Francisco, CA",
            "start_date": "2020-01",
            "end_date": "2023-06",
            "is_current": false,
            "bullets": [
                "Improved system performance by 40%",
                "Led team of 5 engineers"
            ],
            "description": "Led development of microservices architecture"
        }
    ],
    "education": [
        {
            "degree": "BS Computer Science",
            "school": "University of California, Berkeley",
            "location": "Berkeley, CA",
            "start_date": "2016",
            "end_date": "2020",
            "gpa": "3.8",
            "honors": "Magna Cum Laude",
            "relevant_coursework": ["Data Structures", "Algorithms"],
            "achievements": []
        }
    ],
    "projects": [],
    "certifications": [],
    "languages": [],
    "volunteer_work": [],
    "awards": [],
    "publications": []
};

export const ProfileJsonInput: React.FC = () => {
    const [jsonInput, setJsonInput] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<ImportResponse | null>(null);
    const [validationError, setValidationError] = useState<string | null>(null);

    const { accessToken, refresh, logout } = useAuth();
    const navigate = useNavigate();

    const validateJson = (input: string): boolean => {
        if (!input.trim()) {
            setValidationError('JSON input cannot be empty');
            return false;
        }

        try {
            JSON.parse(input);
            setValidationError(null);
            return true;
        } catch (e) {
            setValidationError(`Invalid JSON: ${e instanceof Error ? e.message : 'Unknown error'}`);
            return false;
        }
    };

    const handleJsonChange = (value: string) => {
        setJsonInput(value);
        if (value.trim()) {
            validateJson(value);
        } else {
            setValidationError(null);
        }
    };

    const loadExample = (type: 'simple' | 'detailed') => {
        const example = type === 'simple' ? SIMPLE_EXAMPLE : DETAILED_EXAMPLE;
        const formatted = JSON.stringify(example, null, 2);
        setJsonInput(formatted);
        setValidationError(null);
        setError(null);
        setSuccess(null);
    };

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(null);

        if (!validateJson(jsonInput)) {
            setLoading(false);
            return;
        }

        try {
            const profileData = JSON.parse(jsonInput);

            const response = await apiRequest<ImportResponse>(
                '/api/v1/users/me/profile/import-json',
                {
                    method: 'POST',
                    body: JSON.stringify(profileData),
                },
                accessToken,
                refresh
            );

            setSuccess(response);
            setJsonInput('');
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to import profile';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-5xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Import Profile from JSON</h1>
                        <p className="mt-2 text-sm text-gray-600">
                            Paste your complete profile information as JSON. Supports both simple and detailed formats.
                        </p>
                    </div>
                    <button
                        onClick={logout}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                    >
                        Logout
                    </button>
                </div>

                {/* Example Buttons */}
                <div className="mb-6 flex gap-4">
                    <button
                        type="button"
                        onClick={() => loadExample('simple')}
                        className="px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-md hover:bg-indigo-100"
                    >
                        Load Simple Format Example
                    </button>
                    <button
                        type="button"
                        onClick={() => loadExample('detailed')}
                        className="px-4 py-2 text-sm font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded-md hover:bg-purple-100"
                    >
                        Load Detailed Format Example
                    </button>
                    <button
                        type="button"
                        onClick={() => navigate('/generate-resume')}
                        className="px-4 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-md hover:bg-green-100"
                    >
                        Go to Resume Generator
                    </button>
                </div>

                {/* Success Message */}
                {success && (
                    <div className="mb-6 rounded-md bg-green-50 p-4 border border-green-200">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <h3 className="text-sm font-medium text-green-800">Profile Imported Successfully!</h3>
                                <div className="mt-2 text-sm text-green-700">
                                    <p><strong>Format detected:</strong> {success.format_detected}</p>
                                    <p><strong>Profiles updated:</strong> {success.profiles_updated.join(', ')}</p>
                                    <p className="mt-2">You can now generate resumes using your profile data.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="mb-6 rounded-md bg-red-50 p-4 border border-red-200">
                        <div className="flex">
                            <div className="ml-3">
                                <h3 className="text-sm font-medium text-red-800">Import Failed</h3>
                                <div className="mt-2 text-sm text-red-700">
                                    <p>{error}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Form */}
                <form onSubmit={handleSubmit} className="bg-white shadow-md rounded-lg p-6">
                    <div className="mb-6">
                        <label htmlFor="jsonInput" className="block text-sm font-medium text-gray-700 mb-2">
                            Profile JSON
                        </label>
                        <textarea
                            id="jsonInput"
                            name="jsonInput"
                            rows={20}
                            required
                            value={jsonInput}
                            onChange={(e) => handleJsonChange(e.target.value)}
                            className={`shadow-sm block w-full sm:text-sm rounded-md p-3 border font-mono text-xs ${validationError
                                ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                                : 'border-gray-300 focus:ring-indigo-500 focus:border-indigo-500'
                                }`}
                            placeholder='Paste your profile JSON here or click "Load Example" above...'
                            disabled={loading}
                            spellCheck={false}
                        />
                        {validationError && (
                            <p className="mt-2 text-sm text-red-600">{validationError}</p>
                        )}
                        <p className="mt-2 text-sm text-gray-500">
                            Paste your complete profile as JSON. The system will automatically detect the format.
                        </p>
                    </div>

                    <div className="flex gap-4">
                        <button
                            type="submit"
                            disabled={loading || !!validationError}
                            className="flex-1 flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Importing Profile...' : 'Import Profile'}
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                setJsonInput('');
                                setError(null);
                                setSuccess(null);
                                setValidationError(null);
                            }}
                            disabled={loading}
                            className="px-6 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                        >
                            Clear
                        </button>
                    </div>
                </form>

                {/* Format Information */}
                <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h2 className="text-lg font-semibold text-blue-900 mb-4">Supported Formats</h2>

                    <div className="space-y-4">
                        <div className="bg-blue-100 border border-blue-300 rounded p-3">
                            <h3 className="text-sm font-medium text-blue-900 mb-2">💡 Pro Tip</h3>
                            <p className="text-sm text-blue-800">
                                You can paste either:
                            </p>
                            <ul className="list-disc list-inside text-sm text-blue-800 mt-2 space-y-1">
                                <li>Just the <code className="bg-blue-200 px-1 rounded">profile</code> object</li>
                                <li>The complete user object (we'll extract the profile automatically)</li>
                            </ul>
                        </div>

                        <div>
                            <h3 className="text-sm font-medium text-blue-800 mb-2">Simple Format</h3>
                            <p className="text-sm text-blue-700">
                                Flat structure with fields like <code className="bg-blue-100 px-1 rounded">linkedin_url</code>, <code className="bg-blue-100 px-1 rounded">github_url</code>, etc.
                                Best for quick imports and basic profiles.
                            </p>
                        </div>

                        <div>
                            <h3 className="text-sm font-medium text-blue-800 mb-2">Detailed Format</h3>
                            <p className="text-sm text-blue-700">
                                Nested structure with <code className="bg-blue-100 px-1 rounded">contact</code> object and additional fields like
                                <code className="bg-blue-100 px-1 rounded">projects</code>, <code className="bg-blue-100 px-1 rounded">certifications</code>, etc.
                                Provides more comprehensive profile data.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
