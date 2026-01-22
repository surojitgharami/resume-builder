# tests/test_resume_draft.py
"""
Tests for ResumeDraft model validation.
"""
import pytest
from pydantic import ValidationError
from app.models.resume_draft import (
    ResumeDraft, Profile, ExperienceEntry, EducationEntry, 
    ProjectEntry, Skills, AIEnhancementOptions
)


class TestResumeDraftValidation:
    """Test validation rules for ResumeDraft model."""
    
    def test_valid_resume_draft(self):
        """Test that a valid resume draft passes validation."""
        draft = ResumeDraft(
            profile=Profile(
                full_name="John Doe",
                email="john@example.com",
                phone="+1-555-0123",
                summary="Software engineer with 5 years experience"
            ),
            experience=[
                ExperienceEntry(
                    company="Tech Corp",
                    position="Senior Engineer",
                    start_date="2020-01",
                    end_date="Present",
                    achievements=["Led team of 5", "Reduced latency by 40%"]
                )
            ],
            education=[
                EducationEntry(
                    institution="University of California",
                    degree="B.S. Computer Science",
                    graduation_date="2018"
                )
            ],
            skills=Skills(
                languages=["Python", "JavaScript"],
                frameworks=["FastAPI", "React"]
            )
        )
        
        assert draft.profile.full_name == "John Doe"
        assert len(draft.experience) == 1
        assert draft.experience[0].company == "Tech Corp"
    
    def test_missing_name_raises_validation_error(self):
        """Test that missing profile name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ResumeDraft(
                profile=Profile(
                    full_name="",  # Empty name
                    email="john@example.com"
                ),
                experience=[
                    ExperienceEntry(
                        company="Tech Corp",
                        position="Engineer",
                        start_date="2020-01"
                    )
                ]
            )
        
        errors = exc_info.value.errors()
        assert any("full_name" in str(error) for error in errors)
    
    def test_missing_experience_raises_validation_error(self):
        """Test that missing experience raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ResumeDraft(
                profile=Profile(
                    full_name="John Doe",
                    email="john@example.com"
                ),
                experience=[]  # No experience entries
            )
        
        errors = exc_info.value.errors()
        assert any("experience" in str(error) for error in errors)
    
    def test_at_least_one_experience_required(self):
        """Test that at least one experience entry is required."""
        with pytest.raises(ValidationError):
            ResumeDraft(
                profile=Profile(
                    full_name="John Doe",
                    email="john@example.com"
                ),
                experience=[]
            )
    
    def test_experience_validation(self):
        """Test experience entry validation."""
        # Valid experience
        exp = ExperienceEntry(
            company="Tech Corp",
            position="Engineer",
            start_date="2020-01",
            achievements=["Achievement 1", "Achievement 2"]
        )
        assert exp.company == "Tech Corp"
        
        # Too many achievements
        with pytest.raises(ValidationError):
            ExperienceEntry(
                company="Tech Corp",
                position="Engineer",
                start_date="2020-01",
                achievements=["Achievement " + str(i) for i in range(25)]  # Over limit
            )
    
    def test_education_entry_validation(self):
        """Test education entry validation."""
        edu = EducationEntry(
            institution="University of California",
            degree="B.S. Computer Science",
            graduation_date="2018",
            gpa="3.8",
            honors="Cum Laude"
        )
        assert edu.institution == "University of California"
        assert edu.gpa == "3.8"
    
    def test_project_entry_validation(self):
        """Test project entry validation."""
        project = ProjectEntry(
            name="E-Commerce Platform",
            description="Built a scalable e-commerce platform",
            technologies=["Python", "Django", "PostgreSQL"],
            url="https://github.com/user/project"
        )
        assert project.name == "E-Commerce Platform"
        assert len(project.technologies) == 3
    
    def test_skills_validation(self):
        """Test skills validation."""
        skills = Skills(
            languages=["Python", "JavaScript", "Go"],
            frameworks=["FastAPI", "React", "Docker"],
            technical=["REST APIs", "Microservices"],
            tools=["Git", "Jenkins"],
            soft_skills=["Leadership", "Communication"],
            certifications=["AWS Certified", "Google Cloud"]
        )
        assert len(skills.languages) == 3
        assert "FastAPI" in skills.frameworks
    
    def test_ai_enhancement_options(self):
        """Test AI enhancement options."""
        options = AIEnhancementOptions(
            enhance_summary=True,
            enhance_experience=True,
            enhance_projects=False,
            use_job_description=True,
            custom_instructions="Focus on leadership skills"
        )
        assert options.enhance_summary is True
        assert options.enhance_projects is False
        assert options.custom_instructions == "Focus on leadership skills"
    
    def test_resume_draft_with_job_description(self):
        """Test resume draft with job description."""
        draft = ResumeDraft(
            profile=Profile(
                full_name="Jane Smith",
                email="jane@example.com"
            ),
            experience=[
                ExperienceEntry(
                    company="Tech Corp",
                    position="Engineer",
                    start_date="2020-01"
                )
            ],
            job_description="Looking for a senior engineer with Python experience",
            ai_enhancement=AIEnhancementOptions(
                enhance_summary=True,
                use_job_description=True
            )
        )
        assert draft.job_description is not None
        assert draft.ai_enhancement.enhance_summary is True
    
    def test_optional_fields_default_to_empty(self):
        """Test that optional fields default appropriately."""
        draft = ResumeDraft(
            profile=Profile(
                full_name="John Doe",
                email="john@example.com"
            ),
            experience=[
                ExperienceEntry(
                    company="Tech Corp",
                    position="Engineer",
                    start_date="2020-01"
                )
            ]
        )
        
        # Optional fields should have defaults
        assert draft.education == []
        assert draft.projects == []
        assert draft.job_description is None
        assert draft.template_style == "professional"
    
    def test_field_length_validation(self):
        """Test that field length constraints are enforced."""
        # Test max length for company name
        with pytest.raises(ValidationError):
            ExperienceEntry(
                company="A" * 201,  # Over 200 char limit
                position="Engineer",
                start_date="2020-01"
            )
        
        # Test max length for job description
        with pytest.raises(ValidationError):
            ResumeDraft(
                profile=Profile(
                    full_name="John Doe",
                    email="john@example.com"
                ),
                experience=[
                    ExperienceEntry(
                        company="Tech Corp",
                        position="Engineer",
                        start_date="2020-01"
                    )
                ],
                job_description="A" * 10001  # Over 10000 char limit
            )
    
    def test_model_dump_creates_dict(self):
        """Test that model_dump creates a dictionary snapshot."""
        draft = ResumeDraft(
            profile=Profile(
                full_name="John Doe",
                email="john@example.com"
            ),
            experience=[
                ExperienceEntry(
                    company="Tech Corp",
                    position="Engineer",
                    start_date="2020-01"
                )
            ]
        )
        
        snapshot = draft.model_dump()
        assert isinstance(snapshot, dict)
        assert snapshot["profile"]["full_name"] == "John Doe"
        assert len(snapshot["experience"]) == 1
        assert snapshot["experience"][0]["company"] == "Tech Corp"


class TestExperienceEntry:
    """Test ExperienceEntry specific validation."""
    
    def test_experience_with_achievements(self):
        """Test experience entry with achievements."""
        exp = ExperienceEntry(
            company="Tech Corp",
            position="Engineer",
            start_date="2020-01",
            end_date="2022-12",
            location="San Francisco, CA",
            description="Worked on backend services",
            achievements=["Built API", "Optimized queries"]
        )
        assert len(exp.achievements) == 2
    
    def test_experience_without_end_date(self):
        """Test experience entry without end date (current job)."""
        exp = ExperienceEntry(
            company="Tech Corp",
            position="Engineer",
            start_date="2020-01",
            end_date=None
        )
        assert exp.end_date is None


class TestProfileValidation:
    """Test Profile specific validation."""
    
    def test_profile_with_all_fields(self):
        """Test profile with all optional fields."""
        profile = Profile(
            full_name="John Doe",
            email="john@example.com",
            phone="+1-555-0123",
            location="San Francisco, CA",
            linkedin="https://linkedin.com/in/johndoe",
            github="https://github.com/johndoe",
            website="https://johndoe.com",
            summary="Experienced engineer"
        )
        assert profile.full_name == "John Doe"
        assert profile.linkedin is not None
    
    def test_profile_minimal_required(self):
        """Test profile with only required fields."""
        profile = Profile(
            full_name="John Doe",
            email="john@example.com"
        )
        assert profile.phone is None
        assert profile.summary is None
