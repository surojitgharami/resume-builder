# app/models/resume.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ResumeStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"  # Added to match resume_draft.py and database status


class ResumeFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    PDF = "pdf"


class TemplatePreferences(BaseModel):
    tone: str = "professional"  # professional, technical, creative, casual
    bullets_per_section: int = Field(default=3, ge=1, le=10)
    include_skills: bool = True
    include_projects: bool = True
    include_certifications: bool = True
    color_scheme: Optional[str] = "blue"
    font_family: Optional[str] = "Arial"


class ResumeSection(BaseModel):
    title: str
    content: str
    order: int = 0
    metadata: Optional[Dict[str, Any]] = {}
    ai_enhanced: bool = False  # NEW: Track if this section was AI-enhanced
    original_content: Optional[str] = None  # NEW: Store original before AI enhancement


class ResumeCreate(BaseModel):
    """
    Request model for creating a resume.
    
    Supports both legacy (AI-only) and hybrid (manual + AI) approaches.
    """
    # Legacy AI-only fields (optional now)
    job_description: Optional[str] = Field(None, max_length=10000)
    
    # NEW: Hybrid approach fields
    use_profile_data: bool = True  # Use user's profile data
    use_ai_enhancement: bool = False  # Apply AI enhancement to profile data
    sections_to_enhance: List[str] = Field(default_factory=list)  # Which sections to enhance
    
    # Common fields
    template_preferences: TemplatePreferences = Field(default_factory=TemplatePreferences)
    format: ResumeFormat = ResumeFormat.JSON
    use_rag: bool = True
    custom_instructions: Optional[str] = None


class Resume(BaseModel):
    """
    Enhanced resume model supporting hybrid manual + AI approach.
    
    Design decisions:
    - Snapshots user profile at creation time (historical accuracy)
    - Tracks which sections were AI-enhanced
    - Stores both original and enhanced content
    """
    resume_id: str
    user_id: str
    
    # Legacy field (optional now)
    job_description: Optional[str] = None
    
    # NEW: Profile snapshot (frozen at creation time)
    profile_snapshot: Optional[Dict[str, Any]] = None  # UserProfile as dict
    
    # NEW: AI enhancement tracking
    ai_enhanced_sections: Dict[str, bool] = Field(default_factory=dict)  # section_id -> enhanced
    manual_edits: Dict[str, str] = Field(default_factory=dict)  # section_id -> edited_content
    
    # Existing fields
    template_preferences: TemplatePreferences = Field(default_factory=TemplatePreferences)  # Made optional with default
    sections: List[ResumeSection] = []
    format: ResumeFormat = ResumeFormat.JSON  # Made optional with default
    status: ResumeStatus = ResumeStatus.PENDING
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    s3_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

    model_config = {
        "use_enum_values": True
    }


class ResumeResponse(BaseModel):
    resume_id: str
    sections: List[ResumeSection]
    generated_at: datetime
    status: ResumeStatus
    download_url: Optional[str] = None
    job_description: Optional[str] = None
    ai_enhanced_sections: Dict[str, bool] = Field(default_factory=dict)

    model_config = {
        "use_enum_values": True
    }


# NEW: Hybrid resume creation models

class HybridResumeCreate(BaseModel):
    """
    Create a resume using profile data with optional AI enhancement.
    
    This is the preferred method for the hybrid approach.
    """
    job_description: Optional[str] = Field(None, max_length=10000, description="Optional: for AI tailoring")
    use_ai_enhancement: bool = Field(default=False, description="Apply AI to enhance content")
    enhance_summary: bool = Field(default=True, description="Enhance professional summary")
    enhance_experience: bool = Field(default=True, description="Enhance experience bullets")
    enhance_projects: bool = Field(default=False, description="Enhance project descriptions")
    template_preferences: TemplatePreferences = Field(default_factory=TemplatePreferences)
    custom_instructions: Optional[str] = Field(None, description="Additional instructions for AI")


class SectionUpdateRequest(BaseModel):
    """Request to update a specific resume section."""
    section_title: str
    new_content: str
    apply_ai_enhancement: bool = False
