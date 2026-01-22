# tests/test_services.py
import pytest
from app.services.llm import LLMService
from app.services.embeddings import EmbeddingsService
from app.services.pdf_generator import PDFGeneratorService
from app.models.resume import Resume, ResumeSection, TemplatePreferences, ResumeFormat, ResumeStatus
from datetime import datetime


def test_llm_service_initialization():
    """Test LLM service can be initialized."""
    service = LLMService()
    assert service.model == "meta-llama/llama-3.3-70b-instruct"
    assert service.temperature == 0.1
    assert service.max_tokens == 1200


def test_embeddings_service_initialization():
    """Test embeddings service can be initialized."""
    service = EmbeddingsService()
    assert service.provider in ["openai", "cohere", "local"]
    assert service.dimensions > 0


def test_pdf_generator_initialization():
    """Test PDF generator service can be initialized."""
    service = PDFGeneratorService()
    assert service.engine in ["weasyprint", None]


def test_resume_section_creation():
    """Test resume section model."""
    section = ResumeSection(
        title="Professional Summary",
        content="Experienced software engineer...",
        order=1
    )
    assert section.title == "Professional Summary"
    assert section.order == 1


def test_resume_model_validation():
    """Test resume model validation."""
    resume = Resume(
        resume_id="test-123",
        user_id="user-456",
        job_description="Software Engineer position",
        template_preferences=TemplatePreferences(),
        format=ResumeFormat.JSON,
        status=ResumeStatus.PENDING,
        sections=[]
    )
    
    assert resume.resume_id == "test-123"
    assert resume.status == ResumeStatus.PENDING
    assert resume.format == ResumeFormat.JSON
    assert len(resume.sections) == 0


def test_template_preferences_defaults():
    """Test template preferences default values."""
    prefs = TemplatePreferences()
    assert prefs.tone == "professional"
    assert prefs.bullets_per_section == 3
    assert prefs.include_skills is True
    assert prefs.include_projects is True


def test_pdf_html_generation():
    """Test PDF HTML generation."""
    service = PDFGeneratorService()
    
    resume = Resume(
        resume_id="test-123",
        user_id="user-456",
        job_description="Test job",
        template_preferences=TemplatePreferences(color_scheme="blue"),
        format=ResumeFormat.PDF,
        status=ResumeStatus.COMPLETED,
        sections=[
            ResumeSection(title="Summary", content="Test summary", order=0),
            ResumeSection(title="Experience", content="Test experience", order=1)
        ]
    )
    
    html = service._generate_html(resume)
    assert "Summary" in html
    assert "Experience" in html
    assert "resume-blue" in html


def test_pdf_css_generation():
    """Test PDF CSS generation."""
    service = PDFGeneratorService()
    
    resume = Resume(
        resume_id="test-123",
        user_id="user-456",
        job_description="Test job",
        template_preferences=TemplatePreferences(
            color_scheme="purple",
            font_family="Helvetica"
        ),
        format=ResumeFormat.PDF,
        status=ResumeStatus.COMPLETED,
        sections=[]
    )
    
    css = service._generate_css(resume)
    assert "Helvetica" in css
    assert "#7c3aed" in css  # Purple color


def test_html_escape():
    """Test HTML escaping."""
    service = PDFGeneratorService()
    
    escaped = service._escape_html("<script>alert('xss')</script>")
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_content_formatting():
    """Test content formatting with bullets."""
    service = PDFGeneratorService()
    
    content = """
- First bullet point
- Second bullet point
Regular paragraph
• Another bullet with different marker
"""
    
    formatted = service._format_content(content)
    assert "<ul>" in formatted
    assert "<li>" in formatted
    assert "</ul>" in formatted
    assert "<p>" in formatted
