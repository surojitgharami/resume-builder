# tests/test_models.py
import pytest
from pydantic import ValidationError
from app.models.user import UserCreate, User, UserProfile
from app.models.resume import ResumeCreate, Resume, ResumeSection, TemplatePreferences
from app.models.upload import FileUpload, FileType


def test_user_create_validation():
    """Test user creation validation."""
    # Valid user
    user = UserCreate(
        email="test@example.com",
        password="SecurePass123",
        full_name="Test User"
    )
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"


def test_user_create_invalid_password():
    """Test user creation with invalid password."""
    # Too short
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="short",
            full_name="Test User"
        )
    
    # No uppercase
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="lowercase123",
            full_name="Test User"
        )
    
    # No lowercase
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="UPPERCASE123",
            full_name="Test User"
        )
    
    # No digit
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password="NoDigitsHere",
            full_name="Test User"
        )


def test_user_create_invalid_email():
    """Test user creation with invalid email."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="not-an-email",
            password="SecurePass123",
            full_name="Test User"
        )


def test_resume_create_validation():
    """Test resume creation validation."""
    resume = ResumeCreate(
        job_description="Software Engineer position requiring Python and FastAPI experience",
        template_preferences=TemplatePreferences(tone="technical"),
        format="json"
    )
    assert resume.job_description is not None
    assert resume.template_preferences.tone == "technical"


def test_resume_create_job_description_length():
    """Test resume creation with invalid job description length."""
    # Too short
    with pytest.raises(ValidationError):
        ResumeCreate(
            job_description="Short",
            template_preferences=TemplatePreferences()
        )
    
    # Too long (over 10000 chars)
    with pytest.raises(ValidationError):
        ResumeCreate(
            job_description="x" * 10001,
            template_preferences=TemplatePreferences()
        )


def test_template_preferences_validation():
    """Test template preferences validation."""
    # Valid
    prefs = TemplatePreferences(
        tone="professional",
        bullets_per_section=5,
        include_skills=True
    )
    assert prefs.bullets_per_section == 5
    
    # Invalid bullets count (too few)
    with pytest.raises(ValidationError):
        TemplatePreferences(bullets_per_section=0)
    
    # Invalid bullets count (too many)
    with pytest.raises(ValidationError):
        TemplatePreferences(bullets_per_section=11)


def test_file_upload_model():
    """Test file upload model."""
    from datetime import datetime
    
    upload = FileUpload(
        file_id="test-123",
        user_id="user-456",
        filename="resume.pdf",
        file_type=FileType.RESUME,
        file_size=1024000,
        mime_type="application/pdf",
        s3_key="uploads/user-456/resume/test-123.pdf",
        processed=True
    )
    
    assert upload.file_id == "test-123"
    assert upload.file_type == FileType.RESUME
    assert upload.file_size == 1024000


def test_user_profile_model():
    """Test user profile model."""
    profile = UserProfile(
        full_name="John Doe",
        phone="+1234567890",
        location="San Francisco, CA",
        skills=["Python", "FastAPI", "React"],
        experience=[
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "start_date": "2020-01",
                "end_date": "2023-12"
            }
        ],
        education=[
            {
                "degree": "BS Computer Science",
                "institution": "University",
                "graduation_date": "2020"
            }
        ]
    )
    
    assert profile.full_name == "John Doe"
    assert len(profile.skills) == 3
    assert len(profile.experience) == 1
    assert len(profile.education) == 1


def test_resume_section_model():
    """Test resume section model."""
    section = ResumeSection(
        title="Professional Experience",
        content="• Developed scalable APIs\n• Improved performance by 50%",
        order=3,
        metadata={"generated_by": "llm"}
    )
    
    assert section.title == "Professional Experience"
    assert section.order == 3
    assert section.metadata["generated_by"] == "llm"
