// src/pages/ProfileSetup.tsx
/**
 * Comprehensive profile setup page for new users.
 * Multi-step form to collect all professional information.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../contexts/ToastContext';
import {
    createOrUpdateProfile,
    type ProfileCreateRequest,
    type ContactInfo,
    type Experience,
    type Education,
} from '../services/profileApi';

export const ProfileSetup: React.FC = () => {
    const navigate = useNavigate();
    const { accessToken, refresh } = useAuth();
    const { showToast } = useToast();

    const [saving, setSaving] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);

    // Form state
    const [fullName, setFullName] = useState('');
    const [professionalTitle, setProfessionalTitle] = useState('');
    const [contact, setContact] = useState<ContactInfo>({
        email: '',
        phone: '',
        location: '',
        linkedin: '',
        github: '',
    });
    const [summary, setSummary] = useState('');
    const [skills, setSkills] = useState<string[]>([]);
    const [experience, setExperience] = useState<Experience[]>([]);
    const [education, setEducation] = useState<Education[]>([]);

    const [skillInput, setSkillInput] = useState('');

    const steps = ['Contact', 'Summary', 'Experience', 'Education', 'Skills'];

    const handleSave = async () => {
        try {
            setSaving(true);

            // Frontend validation to prevent 422 errors
            if (!fullName?.trim()) {
                showToast('Please enter your full name', 'error');
                setSaving(false);
                return;
            }

            if (!contact.email?.trim()) {
                showToast('Please enter your email address', 'error');
                setSaving(false);
                return;
            }

            // Email format validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(contact.email)) {
                showToast('Please enter a valid email address', 'error');
                setSaving(false);
                return;
            }

            const profileData: ProfileCreateRequest = {
                full_name: fullName,
                professional_title: professionalTitle || undefined,
                contact,
                summary: summary || undefined,
                skills,
                experience,
                education,
            };

            await createOrUpdateProfile(profileData, accessToken, refresh);
            showToast('Profile created successfully!', 'success');
            navigate('/resumes/builder');
        } catch (err) {
            showToast('Failed to save profile', 'error');
        } finally {
            setSaving(false);
        }
    };

    const addExperience = () => {
        setExperience([
            ...experience,
            {
                title: '',
                company: '',
                start_date: '',
                end_date: '',
                is_current: false,
                bullets: [''],
            },
        ]);
    };

    const addEducation = () => {
        setEducation([
            ...education,
            {
                degree: '',
                school: '',
                start_date: '',
                end_date: '',
            },
        ]);
    };

    const addSkill = () => {
        if (skillInput.trim()) {
            setSkills([...skills, skillInput.trim()]);
            setSkillInput('');
        }
    };

    const isStepValid = () => {
        switch (currentStep) {
            case 0: // Contact
                return fullName && contact.email;
            case 1: // Summary
                return true; // Optional
            case 2: // Experience
                return true; // Optional
            case 3: // Education
                return true; // Optional
            case 4: // Skills
                return true; // Optional
            default:
                return true;
        }
    };

    return (
        <Layout>
            <div className="max-w-3xl mx-auto py-8 px-4">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Create Your Profile
                    </h1>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        Let's build your professional profile to create amazing resumes
                    </p>
                </div>

                {/* Progress */}
                <div className="mb-8">
                    <div className="flex justify-between">
                        {steps.map((step, index) => (
                            <div
                                key={step}
                                className={`flex-1 ${index < steps.length - 1 ? 'pr-4' : ''}`}
                            >
                                <div
                                    className={`h-2 rounded-full ${index <= currentStep
                                        ? 'bg-primary-600'
                                        : 'bg-gray-200 dark:bg-gray-700'
                                        }`}
                                />
                                <p
                                    className={`mt-2 text-sm ${index <= currentStep
                                        ? 'text-primary-600 font-medium'
                                        : 'text-gray-500'
                                        }`}
                                >
                                    {step}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>

                <Card>
                    <div className="p-6">
                        {/* Step 0: Contact */}
                        {currentStep === 0 && (
                            <div className="space-y-4">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                    Contact Information
                                </h2>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Full Name *
                                    </label>
                                    <input
                                        type="text"
                                        value={fullName}
                                        onChange={(e) => setFullName(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                        placeholder="John Doe"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Professional Title
                                    </label>
                                    <input
                                        type="text"
                                        value={professionalTitle}
                                        onChange={(e) => setProfessionalTitle(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                        placeholder="Senior Software Engineer"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Email *
                                    </label>
                                    <input
                                        type="email"
                                        value={contact.email}
                                        onChange={(e) => setContact({ ...contact, email: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                        placeholder="john@example.com"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Phone
                                    </label>
                                    <input
                                        type="tel"
                                        value={contact.phone}
                                        onChange={(e) => setContact({ ...contact, phone: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                        placeholder="+1-555-0123"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                        Location
                                    </label>
                                    <input
                                        type="text"
                                        value={contact.location}
                                        onChange={(e) => setContact({ ...contact, location: e.target.value })}
                                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                        placeholder="San Francisco, CA"
                                    />
                                </div>
                            </div>
                        )}

                        {/* Step 1: Summary */}
                        {currentStep === 1 && (
                            <div className="space-y-4">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                    Professional Summary
                                </h2>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    Write a brief overview of your professional background (optional)
                                </p>

                                <textarea
                                    value={summary}
                                    onChange={(e) => setSummary(e.target.value)}
                                    rows={6}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                    placeholder="Experienced software engineer with 5+ years building scalable applications..."
                                />
                            </div>
                        )}

                        {/* Step 2: Experience */}
                        {currentStep === 2 && (
                            <div className="space-y-4">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                    Work Experience
                                </h2>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    Add your work experience (you can skip this and add later)
                                </p>

                                {experience.length === 0 ? (
                                    <div className="text-center py-8">
                                        <p className="text-gray-500 dark:text-gray-400 mb-4">
                                            No experience added yet
                                        </p>
                                        <Button
                                            variant="primary"
                                            onClick={() => {
                                                console.log('[ProfileSetup] Adding first experience entry');
                                                addExperience();
                                            }}
                                        >
                                            + Add Experience
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="space-y-6">
                                        {experience.map((exp, index) => (
                                            <Card key={index}>
                                                <div className="p-4 space-y-4">
                                                    <div className="flex justify-between items-center">
                                                        <h3 className="font-semibold text-gray-900 dark:text-white">
                                                            Experience #{index + 1}
                                                        </h3>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => {
                                                                console.log(`[ProfileSetup] Removing experience #${index}`);
                                                                setExperience(experience.filter((_, i) => i !== index));
                                                            }}
                                                        >
                                                            Remove
                                                        </Button>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-4">
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                                Job Title *
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={exp.title}
                                                                onChange={(e) => {
                                                                    const updated = [...experience];
                                                                    updated[index] = { ...updated[index], title: e.target.value };
                                                                    setExperience(updated);
                                                                }}
                                                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                                                placeholder="Senior Software Engineer"
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                                Company *
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={exp.company}
                                                                onChange={(e) => {
                                                                    const updated = [...experience];
                                                                    updated[index] = { ...updated[index], company: e.target.value };
                                                                    setExperience(updated);
                                                                }}
                                                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                                                placeholder="Tech Corp"
                                                            />
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center">
                                                        <input
                                                            type="checkbox"
                                                            checked={exp.is_current}
                                                            onChange={(e) => {
                                                                const updated = [...experience];
                                                                updated[index] = { ...updated[index], is_current: e.target.checked };
                                                                setExperience(updated);
                                                            }}
                                                            className="mr-2 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                                                        />
                                                        <label className="text-sm text-gray-700 dark:text-gray-300">
                                                            I currently work here
                                                        </label>
                                                    </div>
                                                </div>
                                            </Card>
                                        ))}

                                        <Button
                                            variant="outline"
                                            onClick={() => {
                                                console.log('[ProfileSetup] Adding another experience entry');
                                                addExperience();
                                            }}
                                            className="w-full"
                                        >
                                            + Add Another
                                        </Button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Step 3: Education */}
                        {currentStep === 3 && (
                            <div className="space-y-4">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                    Education
                                </h2>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    Add your education (you can skip this and add later)
                                </p>

                                {education.length === 0 ? (
                                    <div className="text-center py-8">
                                        <p className="text-gray-500 dark:text-gray-400 mb-4">
                                            No education added yet
                                        </p>
                                        <Button
                                            variant="primary"
                                            onClick={() => {
                                                console.log('[ProfileSetup] Adding first education entry');
                                                addEducation();
                                            }}
                                        >
                                            + Add Education
                                        </Button>
                                    </div>
                                ) : (
                                    <div className="space-y-6">
                                        {education.map((edu, index) => (
                                            <Card key={index}>
                                                <div className="p-4 space-y-4">
                                                    <div className="flex justify-between items-center">
                                                        <h3 className="font-semibold text-gray-900 dark:text-white">
                                                            Education #{index + 1}
                                                        </h3>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => {
                                                                console.log(`[ProfileSetup] Removing education #${index}`);
                                                                setEducation(education.filter((_, i) => i !== index));
                                                            }}
                                                        >
                                                            Remove
                                                        </Button>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-4">
                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                                Degree *
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={edu.degree}
                                                                onChange={(e) => {
                                                                    const updated = [...education];
                                                                    updated[index] = { ...updated[index], degree: e.target.value };
                                                                    setEducation(updated);
                                                                }}
                                                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                                                placeholder="Bachelor of Science in Computer Science"
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                                School *
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={edu.school}
                                                                onChange={(e) => {
                                                                    const updated = [...education];
                                                                    updated[index] = { ...updated[index], school: e.target.value };
                                                                    setEducation(updated);
                                                                }}
                                                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                                                placeholder="University of California, Berkeley"
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                                Start Year
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={edu.start_date}
                                                                onChange={(e) => {
                                                                    const updated = [...education];
                                                                    updated[index] = { ...updated[index], start_date: e.target.value };
                                                                    setEducation(updated);
                                                                }}
                                                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                                                placeholder="2016"
                                                            />
                                                        </div>

                                                        <div>
                                                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                                                End Year
                                                            </label>
                                                            <input
                                                                type="text"
                                                                value={edu.end_date}
                                                                onChange={(e) => {
                                                                    const updated = [...education];
                                                                    updated[index] = { ...updated[index], end_date: e.target.value };
                                                                    setEducation(updated);
                                                                }}
                                                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                                                placeholder="2020"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                            </Card>
                                        ))}

                                        <Button
                                            variant="outline"
                                            onClick={() => {
                                                console.log('[ProfileSetup] Adding another education entry');
                                                addEducation();
                                            }}
                                            className="w-full"
                                        >
                                            + Add Another
                                        </Button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Step 4: Skills */}
                        {currentStep === 4 && (
                            <div className="space-y-4">
                                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                    Skills
                                </h2>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    Add your professional skills
                                </p>

                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={skillInput}
                                        onChange={(e) => setSkillInput(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && addSkill()}
                                        className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:bg-gray-800 dark:text-white"
                                        placeholder="e.g., Python, React, AWS"
                                    />
                                    <Button variant="primary" onClick={addSkill}>
                                        Add
                                    </Button>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                    {skills.map((skill, index) => (
                                        <span
                                            key={index}
                                            className="inline-flex items-center gap-2 px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded-full text-sm"
                                        >
                                            {skill}
                                            <button
                                                onClick={() => setSkills(skills.filter((_, i) => i !== index))}
                                                className="text-primary-600 hover:text-primary-800"
                                            >
                                                ✕
                                            </button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Navigation */}
                        <div className="flex justify-between mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                            <Button
                                variant="outline"
                                onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                                disabled={currentStep === 0}
                            >
                                ← Previous
                            </Button>

                            {currentStep === steps.length - 1 ? (
                                <Button
                                    variant="primary"
                                    onClick={handleSave}
                                    disabled={saving || !isStepValid()}
                                >
                                    {saving ? 'Saving...' : 'Complete Setup'}
                                </Button>
                            ) : (
                                <Button
                                    variant="primary"
                                    onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
                                    disabled={!isStepValid()}
                                >
                                    Next →
                                </Button>
                            )}
                        </div>
                    </div>
                </Card>
            </div>
        </Layout>
    );
};
