// src/services/profileApi.ts
/**
 * Profile API client for managing user profiles.
 * 
 * Provides methods for CRUD operations on user profiles including:
 * - Creating/updating profiles
 * - Fetching profiles
 * - Checking profile existence
 */

import { apiRequest } from './api';

export interface ContactInfo {
    email: string;
    phone?: string;
    location?: string;
    linkedin?: string;
    github?: string;
    portfolio?: string;
    website?: string;
}

export interface Experience {
    title: string;
    company: string;
    location?: string;
    start_date: string;
    end_date?: string;
    is_current: boolean;
    bullets: string[];
    description?: string;
}

export interface Education {
    degree: string;
    school: string;
    location?: string;
    start_date: string;
    end_date: string;
    gpa?: string;
    honors?: string;
    relevant_coursework?: string[];
    achievements?: string[];
}

export interface Project {
    name: string;
    description: string;
    technologies: string[];
    link?: string;
    highlights: string[];
    start_date?: string;
    end_date?: string;
}

export interface Certification {
    name: string;
    issuer: string;
    date_obtained: string;
    expiry_date?: string;
    credential_id?: string;
    credential_url?: string;
}

export interface UserProfile {
    user_id: string;
    full_name: string;
    professional_title?: string;
    contact: ContactInfo;
    summary?: string;
    skills: string[];
    experience: Experience[];
    education: Education[];
    projects: Project[];
    certifications: Certification[];
    languages: string[];
    volunteer_work: string[];
    awards: string[];
    publications: string[];
    created_at: string;
    updated_at: string;
}

export interface ProfileCreateRequest {
    full_name: string;
    professional_title?: string;
    contact: ContactInfo;
    summary?: string;
    skills?: string[];
    experience?: Experience[];
    education?: Education[];
    projects?: Project[];
    certifications?: Certification[];
    languages?: string[];
    volunteer_work?: string[];
    awards?: string[];
    publications?: string[];
}

export interface ProfileExistsResponse {
    exists: boolean;
    completed: boolean;
}

/**
 * Create or update user profile
 */
export const createOrUpdateProfile = async (
    profileData: ProfileCreateRequest,
    accessToken: string | null,
    refresh: () => Promise<void>
): Promise<UserProfile> => {
    return apiRequest<UserProfile>(
        '/api/v1/profile',
        {
            method: 'POST',
            body: JSON.stringify(profileData),
        },
        accessToken,
        refresh
    );
};

/**
 * Get current user's profile
 */
export const getProfile = async (
    accessToken: string | null,
    refresh: () => Promise<void>
): Promise<UserProfile> => {
    return apiRequest<UserProfile>(
        '/api/v1/profile',
        { method: 'GET' },
        accessToken,
        refresh
    );
};

/**
 * Partially update profile
 */
export const updateProfile = async (
    updates: Partial<ProfileCreateRequest>,
    accessToken: string | null,
    refresh: () => Promise<void>
): Promise<UserProfile> => {
    return apiRequest<UserProfile>(
        '/api/v1/profile',
        {
            method: 'PATCH',
            body: JSON.stringify(updates),
        },
        accessToken,
        refresh
    );
};

/**
 * Delete user profile
 */
export const deleteProfile = async (
    accessToken: string | null,
    refresh: () => Promise<void>
): Promise<void> => {
    return apiRequest<void>(
        '/api/v1/profile',
        { method: 'DELETE' },
        accessToken,
        refresh
    );
};

/**
 * Check if user has a profile
 */
export const checkProfileExists = async (
    accessToken: string | null,
    refresh: () => Promise<void>
): Promise<ProfileExistsResponse> => {
    return apiRequest<ProfileExistsResponse>(
        '/api/v1/profile/exists',
        { method: 'GET' },
        accessToken,
        refresh
    );
};
