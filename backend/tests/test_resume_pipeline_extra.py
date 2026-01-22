"""
Additional tests for resume pipeline failure scenarios.

Tests AI-unavailable scenario and PDF generation failures.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.resume_pipeline import ResumePipeline, ResumeStatus, ResumePipelineError
from app.models.resume_draft import ResumeDraft, ResumeProfile, Experience, AIEnhancementOptions


def valid_resume_draft() -> ResumeDraft:
    """Helper to create a valid resume draft for testing."""
    return ResumeDraft(
        profile=ResumeProfile(
            full_name="John Doe",
            email="john@example.com",
            phone="555-1234",
            summary="Experienced developer"
        ),
        experience=[
            Experience(
                company="Tech Corp",
                position="Senior Developer",
                start_date="2020-01",
                end_date="2024-01",
                achievements=["Built scalable systems", "Led team of 5"]
            )
        ],
        education=[],
        skills=[],
        projects=[],
        ai_enhancement=AIEnhancementOptions(
            enhance_summary=False,
            enhance_experience=False,
            enhance_projects=False
        ),
        job_description="Senior developer position"
    )


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=AsyncMock())
    return db


@pytest.fixture
def mock_html_renderer():
    """Mock HTML renderer service."""
    renderer = MagicMock()
    renderer.render_resume = MagicMock(return_value="<html>Resume</html>")
    return renderer


@pytest.fixture
def mock_pdf_service():
    """Mock PDF service that succeeds."""
    service = MagicMock()
    service.generate_pdf_from_html = AsyncMock(return_value="/tmp/resume.pdf")
    service.cleanup_file = MagicMock()
    service.is_available = MagicMock(return_value=True)
    return service


@pytest.fixture
def failing_pdf_service():
    """Mock PDF service that always fails."""
    service = MagicMock()
    service.generate_pdf_from_html = AsyncMock(
        side_effect=Exception("PDF generation failed")
    )
    service.is_available = MagicMock(return_value=True)
    return service


@pytest.fixture
def mock_storage():
    """Mock S3 storage service."""
    storage = MagicMock()
    storage.upload_file = AsyncMock()
    storage.get_presigned_url = AsyncMock(
        return_value="https://s3.amazonaws.com/bucket/resume.pdf"
    )
    return storage


@pytest.mark.asyncio
async def test_resume_generation_without_ai_service(
    mock_db, mock_html_renderer, mock_pdf_service, mock_storage
):
    """
    Test that resume pipeline works without AI enhancer.
    
    Verifies that generation completes successfully when ai_enhancer=None.
    """
    # Create pipeline with ai_enhancer=None
    pipeline = ResumePipeline(
        db=mock_db,
        html_renderer=mock_html_renderer,
        pdf_service=mock_pdf_service,
        storage_service=mock_storage,
        ai_enhancer=None  # AI disabled
    )
    
    draft = valid_resume_draft()
    result = await pipeline.generate_resume("user123", draft)
    
    # Should complete successfully
    assert result["status"] in (ResumeStatus.COMPLETE, "complete")
    assert "resume_id" in result
    assert "download_url" in result
    
    # Verify HTML was rendered
    mock_html_renderer.render_resume.assert_called_once()
    
    # Verify PDF was generated
    mock_pdf_service.generate_pdf_from_html.assert_called_once()
    
    # Verify upload occurred
    mock_storage.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_pdf_generation_failure_marks_error(
    mock_db, mock_html_renderer, failing_pdf_service, mock_storage
):
    """
    Test that PDF generation failure sets status=error in database.
    
    Verifies error handling and database state when PDF generation fails.
    """
    pipeline = ResumePipeline(
        db=mock_db,
        html_renderer=mock_html_renderer,
        pdf_service=failing_pdf_service,
        storage_service=mock_storage,
        ai_enhancer=None
    )
    
    draft = valid_resume_draft()
    
    # Should raise ResumePipelineError
    with pytest.raises(ResumePipelineError):
        await pipeline.generate_resume("user123", draft)
    
    # Verify update_one was called to mark error
    # Note: Access the resumes collection mock
    resumes_collection = mock_db["resumes"]
    
    # Should have called update_one to set error status
    update_calls = [
        call for call in resumes_collection.update_one.call_args_list
        if call[0][1].get("$set", {}).get("status") == "error"
    ]
    
    assert len(update_calls) > 0, "Should have updated status to error"
    
    # Verify error details were set
    error_update = update_calls[0][0][1]["$set"]
    assert "error_message" in error_update
    assert "error_code" in error_update


@pytest.mark.asyncio
async def test_validation_error_raised_for_missing_name(
    mock_db, mock_html_renderer, mock_pdf_service, mock_storage
):
    """
    Test that validation fails when full_name is missing.
    
    Verifies ValidationError is raised with helpful message.
    """
    from app.services.resume_pipeline import ValidationError
    
    pipeline = ResumePipeline(
        db=mock_db,
        html_renderer=mock_html_renderer,
        pdf_service=mock_pdf_service,
        storage_service=mock_storage,
        ai_enhancer=None
    )
    
    # Create draft with missing name
    draft = valid_resume_draft()
    draft.profile.full_name = ""
    
    with pytest.raises(ValidationError) as exc_info:
        await pipeline.generate_resume("user123", draft)
    
    assert "full_name" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_validation_error_raised_for_no_experience(
    mock_db, mock_html_renderer, mock_pdf_service, mock_storage
):
    """
    Test that validation fails when no experience entries exist.
    
    Verifies ValidationError is raised with helpful message.
    """
    from app.services.resume_pipeline import ValidationError
    
    pipeline = ResumePipeline(
        db=mock_db,
        html_renderer=mock_html_renderer,
        pdf_service=mock_pdf_service,
        storage_service=mock_storage,
        ai_enhancer=None
    )
    
    # Create draft with no experience
    draft = valid_resume_draft()
    draft.experience = []
    
    with pytest.raises(ValidationError) as exc_info:
        await pipeline.generate_resume("user123", draft)
    
    assert "experience" in str(exc_info.value).lower()
