# app/models/profile.py
"""
User profile models for hybrid resume builder.

This module defines the data models for user profiles including:
- Contact information
- Work experience
- Education
- Skills and projects
- Certifications

Design decisions:
- Profile is stored separately from resumes (reusable)
- Each resume snapshots the profile at creation time
- Users can have one profile, many resumes
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class ContactInfo(BaseModel):
    """User contact information."""
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None  # City, State or City, Country
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None


class Experience(BaseModel):
    """Work experience entry."""
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    start_date: str = Field(..., description="Format: YYYY-MM or 'Present'")
    end_date: Optional[str] = Field(None, description="Format: YYYY-MM or None if current")
    is_current: bool = False
    bullets: List[str] = Field(default_factory=list, max_length=10)
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "location": "San Francisco, CA",
                "start_date": "2020-01",
                "end_date": "2023-06",
                "is_current": False,
                "bullets": [
                    "Led team of 5 engineers in developing microservices architecture",
                    "Improved system performance by 40% through optimization",
                    "Mentored junior developers and conducted code reviews"
                ]
            }
        }


class Education(BaseModel):
    """Education entry."""
    degree: str = Field(..., min_length=1, max_length=200)
    school: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    start_date: str = Field(..., description="Format: YYYY")
    end_date: str = Field(..., description="Format: YYYY")
    gpa: Optional[str] = None
    honors: Optional[str] = None  # e.g., "Summa Cum Laude"
    relevant_coursework: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "degree": "Bachelor of Science in Computer Science",
                "school": "University of California, Berkeley",
                "location": "Berkeley, CA",
                "start_date": "2016",
                "end_date": "2020",
                "gpa": "3.8/4.0",
                "honors": "Magna Cum Laude",
                "achievements": ["Dean's List (4 semesters)", "CS Department Award"]
            }
        }


class Project(BaseModel):
    """Project entry."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None  # GitHub, demo, etc.
    highlights: List[str] = Field(default_factory=list, max_length=5)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "AI Resume Builder",
                "description": "Full-stack web application for generating AI-powered resumes",
                "technologies": ["FastAPI", "React", "MongoDB", "OpenAI"],
                "link": "https://github.com/user/resume-builder",
                "highlights": [
                    "Built scalable backend with 99.9% uptime",
                    "Implemented real-time PDF generation",
                    "Integrated AI for content enhancement"
                ]
            }
        }


class Certification(BaseModel):
    """Certification or license."""
    name: str = Field(..., min_length=1, max_length=200)
    issuer: str = Field(..., min_length=1, max_length=200)
    date_obtained: str = Field(..., description="Format: YYYY-MM")
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None


class UserProfile(BaseModel):
    """
    Complete user profile for resume generation.
    
    This model represents all the user's professional information
    that can be used to generate multiple tailored resumes.
    """
    user_id: str
    full_name: str = Field(..., min_length=1, max_length=100)
    photo_url: Optional[str] = None
    professional_title: Optional[str] = Field(None, max_length=200)  # e.g., "Senior Software Engineer"
    contact: ContactInfo
    summary: Optional[str] = Field(None, max_length=1000)  # Professional summary/objective
    
    # Professional experience
    experience: List[Experience] = Field(default_factory=list)
    
    # Education
    education: List[Education] = Field(default_factory=list)
    
    # Skills (categorized or flat list)
    skills: List[str] = Field(default_factory=list)
    
    # Projects
    projects: List[Project] = Field(default_factory=list)
    
    # Certifications
    certifications: List[Certification] = Field(default_factory=list)
    
    # Additional sections (flexible)
    languages: List[str] = Field(default_factory=list)  # e.g., ["English (Native)", "Spanish (Fluent)"]
    volunteer_work: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    publications: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "full_name": "John Doe",
                "professional_title": "Senior Full-Stack Developer",
                "contact": {
                    "email": "john.doe@example.com",
                    "phone": "+1-555-0123",
                    "location": "San Francisco, CA",
                    "linkedin": "linkedin.com/in/johndoe",
                    "github": "github.com/johndoe"
                },
                "summary": "Experienced software engineer with 5+ years building scalable web applications...",
                "skills": ["Python", "JavaScript", "React", "FastAPI", "MongoDB", "AWS"],
                "experience": [],
                "education": []
            }
        }


class ProfileCreate(BaseModel):
    """Request model for creating a user profile."""
    full_name: str = Field(..., min_length=1, max_length=100)
    professional_title: Optional[str] = None
    contact: ContactInfo
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    volunteer_work: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    publications: List[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    """Request model for updating a user profile (all fields optional)."""
    full_name: Optional[str] = None
    photo_url: Optional[str] = None
    professional_title: Optional[str] = None
    contact: Optional[ContactInfo] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Experience]] = None
    education: Optional[List[Education]] = None
    projects: Optional[List[Project]] = None
    certifications: Optional[List[Certification]] = None
    languages: Optional[List[str]] = None
    volunteer_work: Optional[List[str]] = None
    awards: Optional[List[str]] = None
    publications: Optional[List[str]] = None


class ProfileResponse(BaseModel):
    """Response model for user profile."""
    user_id: str
    full_name: str
    photo_url: Optional[str] = None
    professional_title: Optional[str]
    contact: ContactInfo
    summary: Optional[str]
    skills: List[str]
    experience: List[Experience]
    education: List[Education]
    projects: List[Project]
    certifications: List[Certification]
    languages: List[str]
    volunteer_work: List[str]
    awards: List[str]
    publications: List[str]
    created_at: datetime
    updated_at: datetime
