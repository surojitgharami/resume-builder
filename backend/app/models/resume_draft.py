# app/models/resume_draft.py
"""
Production-ready resume draft models with structured validation.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ExperienceEntry(BaseModel):
    """Single work experience entry."""
    company: str = Field(..., min_length=1, max_length=200, description="Company name")
    position: str = Field(..., min_length=1, max_length=200, description="Job title/position")
    start_date: str = Field(..., description="Start date (YYYY-MM or YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date or 'Present'")
    location: Optional[str] = Field(None, max_length=200, description="Job location")
    description: Optional[str] = Field(None, max_length=2000, description="Job description")
    achievements: List[str] = Field(default_factory=list, description="Key achievements/responsibilities")
    
    @field_validator('achievements')
    @classmethod
    def validate_achievements(cls, v):
        """Ensure achievements list is reasonable size."""
        if len(v) > 20:
            raise ValueError("Maximum 20 achievements per experience entry")
        return v


class EducationEntry(BaseModel):
    """Single education entry."""
    institution: str = Field(..., min_length=1, max_length=200, description="School/University name")
    degree: str = Field(..., min_length=1, max_length=200, description="Degree type and field")
    graduation_date: Optional[str] = Field(None, description="Graduation date (YYYY-MM or YYYY)")
    gpa: Optional[str] = Field(None, max_length=20, description="GPA or grade")
    honors: Optional[str] = Field(None, max_length=500, description="Honors, awards, distinctions")
    relevant_coursework: List[str] = Field(default_factory=list, description="Relevant courses")


class ProjectEntry(BaseModel):
    """Single project entry."""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(..., min_length=1, max_length=2000, description="Project description")
    technologies: List[str] = Field(default_factory=list, description="Technologies used")
    url: Optional[str] = Field(None, max_length=500, description="Project URL or repository")
    date: Optional[str] = Field(None, description="Project date or duration")


class Profile(BaseModel):
    """User profile information for resume."""
    full_name: str = Field(..., min_length=1, max_length=200, description="Full name")
    email: str = Field(..., max_length=200, description="Email address")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    location: Optional[str] = Field(None, max_length=200, description="City, State/Country")
    linkedin: Optional[str] = Field(None, max_length=500, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, max_length=500, description="GitHub profile URL")
    website: Optional[str] = Field(None, max_length=500, description="Personal website")
    summary: Optional[str] = Field(None, max_length=2000, description="Professional summary")
    
    # Extended fields for full template support
    awards: List[str] = Field(default_factory=list, description="Awards and Achievements")
    languages: List[str] = Field(default_factory=list, description="Spoken languages")
    interests: List[str] = Field(default_factory=list, description="Interests and Hobbies")


class Skills(BaseModel):
    """Skills section with categorization."""
    technical: List[str] = Field(default_factory=list, description="Technical skills")
    languages: List[str] = Field(default_factory=list, description="Programming languages")
    frameworks: List[str] = Field(default_factory=list, description="Frameworks and libraries")
    tools: List[str] = Field(default_factory=list, description="Tools and platforms")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills")
    certifications: List[str] = Field(default_factory=list, description="Certifications")


class AIEnhancementOptions(BaseModel):
    """Per-section AI enhancement toggles."""
    enhance_summary: bool = Field(default=False, description="Enhance professional summary")
    enhance_experience: bool = Field(default=False, description="Enhance experience bullets")
    enhance_projects: bool = Field(default=False, description="Enhance project descriptions")
    enhance_skills: bool = Field(default=False, description="Enhance skills presentation")
    
    # Global AI settings
    use_job_description: bool = Field(default=False, description="Tailor to job description")
    custom_instructions: Optional[str] = Field(None, max_length=1000, description="Custom AI instructions")


class ResumeDraft(BaseModel):
    """
    Production-ready resume draft model.
    
    Validation rules:
    - name is required
    - all nested fields are validated
    """
    profile: Profile = Field(..., description="User profile information")
    experience: List[ExperienceEntry] = Field(default_factory=list, description="Work experience (optional)")
    education: List[EducationEntry] = Field(default_factory=list, description="Education history")
    skills: Optional[Skills] = Field(None, description="Skills and certifications")
    projects: List[ProjectEntry] = Field(default_factory=list, description="Projects")
    
    # Optional metadata
    job_description: Optional[str] = Field(None, max_length=10000, description="Target job description for tailoring")
    ai_enhancement: AIEnhancementOptions = Field(default_factory=AIEnhancementOptions, description="AI enhancement settings")
    template_style: str = Field(default="professional", description="Template style: professional, modern, creative")
    
    @model_validator(mode='after')
    def validate_draft(self):
        """Cross-field validation."""
        # Ensure profile has name
        if not self.profile.full_name or not self.profile.full_name.strip():
            raise ValueError("Profile full_name is required")
        
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile": {
                    "full_name": "John Doe",
                    "email": "john.doe@example.com",
                    "phone": "+1-555-0123",
                    "location": "San Francisco, CA",
                    "summary": "Experienced software engineer with 5+ years in backend development"
                },
                "experience": [
                    {
                        "company": "Tech Corp",
                        "position": "Senior Software Engineer",
                        "start_date": "2020-01",
                        "end_date": "Present",
                        "achievements": [
                            "Led migration to microservices architecture",
                            "Reduced API latency by 40%"
                        ]
                    }
                ],
                "education": [
                    {
                        "institution": "University of California",
                        "degree": "B.S. Computer Science",
                        "graduation_date": "2018"
                    }
                ],
                "skills": {
                    "languages": ["Python", "JavaScript", "Go"],
                    "frameworks": ["FastAPI", "React", "Docker"]
                }
            }
        }


class ResumeStatus(str, Enum):
    """Resume processing status."""
    DRAFT = "draft"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class PDFMetadata(BaseModel):
    """PDF file metadata."""
    s3_key: str = Field(..., description="S3 object key")
    url: str = Field(..., description="Download URL")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    file_size: Optional[int] = Field(None, description="File size in bytes")


class ResumeDocument(BaseModel):
    """
    Resume document stored in database.
    
    Tracks full lifecycle: draft → processing → complete/error
    """
    resume_id: str = Field(..., description="Unique resume ID")
    user_id: str = Field(..., description="User ID")
    
    # Snapshot at creation time
    snapshot: Dict[str, Any] = Field(..., description="Frozen snapshot of input data")
    
    # Processing state
    status: ResumeStatus = Field(default=ResumeStatus.DRAFT, description="Current status")
    
    # Generated content (populated during processing)
    html_content: Optional[str] = Field(None, description="Rendered HTML content")
    pdf: Optional[PDFMetadata] = Field(None, description="PDF metadata (when complete)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Detailed error message")
    error_code: Optional[str] = Field(None, description="Error code for debugging")
    retry_count: int = Field(default=0, description="Number of retries")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = True


class ResumeCreateResponse(BaseModel):
    """Response when creating a new resume."""
    resume_id: str = Field(..., description="Unique resume ID")
    status: ResumeStatus = Field(..., description="Current processing status")
    created_at: datetime = Field(..., description="Creation timestamp")
    message: str = Field(default="Resume generation started", description="Status message")


class ResumeStatusResponse(BaseModel):
    """Response for resume status check."""
    resume_id: str
    status: ResumeStatus
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    class Config:
        use_enum_values = True
