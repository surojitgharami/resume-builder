# app/api/v1/resumes_v2.py
"""
Production-ready resume generation API endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging

from app.models.resume_draft import (
    ResumeDraft, ResumeCreateResponse, ResumeStatusResponse, 
    ResumeStatus, ResumeDocument
)
from app.models.user import User
from app.middleware.auth import get_current_active_user
from app.db.mongo import get_database
from app.services.resume_pipeline import ResumePipeline, ValidationError, ResumePipelineError
from app.services.html_renderer import get_html_renderer_service
from app.services.pdf_playwright import get_playwright_pdf_service
from app.services.storage import get_storage_service
from app.services.llm import get_llm_service
from app.services.ai_enhancer_v2 import get_ai_enhancer_service
from app.core.config import settings
from pydantic import ValidationError as PydanticValidationError

# Import unified PDF engine
from app.services.pdf_engine import is_available as pdf_engine_available, get_preferred_engine

router = APIRouter()
logger = logging.getLogger(__name__)


def get_resume_pipeline(db: AsyncIOMotorDatabase = Depends(get_database)) -> ResumePipeline:
    """
    Dependency to get resume pipeline instance with optional AI.
    
    AI services are optional - if unavailable, pipeline works without AI enhancement.
    
    Args:
        db: Database connection
        
    Returns:
        ResumePipeline instance
        
    Raises:
        HTTPException 503: If PDF generation engine is not available
    """
    # CRITICAL: Fail-fast check for PDF engine availability
    if not pdf_engine_available():
        engine = get_preferred_engine()  # Will be None
        logger.error("PDF generation engine unavailable (no Playwright or WeasyPrint).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "PDF engine unavailable",
                "message": "PDF generation engine is not available. Please install Playwright or WeasyPrint.",
                "instructions": "Run: pip install playwright && python -m playwright install --with-deps"
            }
        )
    
    logger.info(f"PDF engine available: {get_preferred_engine()}")
    
    html_renderer = get_html_renderer_service()
    pdf_service = get_playwright_pdf_service()
    storage_service = get_storage_service()
    
    # Try to initialize AI enhancer (optional)
    ai_enhancer = None
    try:
        llm_service = get_llm_service()
        if llm_service and llm_service.is_available():
            ai_enhancer = get_ai_enhancer_service(llm_service)
            if ai_enhancer and ai_enhancer.is_available():
                logger.info("AI enhancer service initialized successfully")
            else:
                logger.warning("AI enhancer service not available")
                ai_enhancer = None
        else:
            logger.warning("LLM service not available. Resume generation will work without AI.")
    except Exception as e:
        logger.warning(f"Failed to initialize AI enhancer: {e}. Resume generation will work without AI.")
        ai_enhancer = None
    
    return ResumePipeline(
        db=db,
        html_renderer=html_renderer,
        pdf_service=pdf_service,
        storage_service=storage_service,
        ai_enhancer=ai_enhancer  # Can be None
    )


async def _run_resume_generation_background(
    user_id: str,
    resume_draft: ResumeDraft,
    pipeline: ResumePipeline
):
    """
    Background task for resume generation.
    
    Args:
        user_id: User ID
        resume_draft: Resume draft data
        pipeline: Resume pipeline instance
    """
    try:
        await pipeline.generate_resume(user_id, resume_draft)
    except Exception as e:
        logger.error(f"Background resume generation failed for user_id={user_id}: {e}", exc_info=True)


@router.post(
    "/resumes",
    response_model=ResumeCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Resume generation started"},
        422: {"description": "Validation error - missing required fields"}
    }
)
async def create_resume(
    resume_draft: ResumeDraft,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    pipeline: ResumePipeline = Depends(get_resume_pipeline)
):
    """
    Create a new resume from structured data.
    
    **Validation Requirements:**
    - `profile.full_name` is required
    - At least one `experience` entry is required
    
    **Processing Flow:**
    1. Validate input (422 if validation fails)
    2. Save draft with snapshot
    3. Process in background (AI enhancement, HTML render, PDF generation, S3 upload)
    4. Return immediately with `resume_id` and `status=processing`
    
    **AI Enhancement:**
    - Optional per-section enhancement (summary, experience, projects)
    - AI only rewrites text, never creates/removes sections
    - Toggle via `ai_enhancement` field
    
    **Error Handling:**
    - Validation errors return 422 with detailed messages
    - Processing errors set status=error in database
    - Check status with GET /resumes/{resume_id}
    
    Args:
        resume_draft: Resume draft data (validated by Pydantic)
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        pipeline: Resume generation pipeline
        
    Returns:
        ResumeCreateResponse with resume_id and status=processing
        
    Raises:
        HTTPException 422: If validation fails
    """
    try:
        user_id = str(current_user.id)
        
        # Validate draft early (defensive)
        try:
            pipeline._validate_draft(resume_draft)
        except ValidationError as e:
            logger.warning(f"Validation error for user_id={user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "Validation failed", "message": str(e)}
            ) from e
        
        # Generate resume_id and persist draft early
        import uuid
        from datetime import datetime
        
        resume_id = str(uuid.uuid4())
        snapshot = resume_draft.model_dump()
        
        document = ResumeDocument(
            resume_id=resume_id,
            user_id=user_id,
            snapshot=snapshot,
            status=ResumeStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Get database from pipeline
        db = pipeline.db
        
        # FEATURE: Automatically update user profile with latest data from this draft
        # This satisfies "save all information in mongo db" requirement
        try:
            # Construct profile update payload
            # We map ResumeDraft fields back to UserProfile structure
            profile_update = {
                "profile.full_name": resume_draft.profile.full_name,
                "profile.phone": resume_draft.profile.phone,
                "profile.location": resume_draft.profile.location,
                "profile.linkedin_url": resume_draft.profile.linkedin,
                "profile.github_url": resume_draft.profile.github,
                "profile.portfolio_url": resume_draft.profile.website,
                "profile.summary": resume_draft.profile.summary,
                "profile.skills": getattr(resume_draft.skills, 'technical', []) if resume_draft.skills else [],
                "profile.experience": [exp.model_dump() for exp in resume_draft.experience],
                "profile.education": [edu.model_dump() for edu in resume_draft.education],
                "profile.projects": [proj.model_dump() for proj in resume_draft.projects],
                
                # Extended fields
                "profile.awards": resume_draft.profile.awards,
                "profile.languages": resume_draft.profile.languages,
                "profile.interests": resume_draft.profile.interests,
            }
            
            # Remove None values
            profile_update = {k: v for k, v in profile_update.items() if v is not None}
            
            await db["users"].update_one(
                {"_id": current_user.id},
                {"$set": profile_update}
            )
            logger.info(f"Updated user profile from resume draft for user_id={user_id}")
            
        except Exception as e:
            # Non-blocking error - log and continue with generation
            logger.warning(f"Failed to auto-update profile from draft: {e}")

        await db["resumes"].insert_one(document.model_dump())
        logger.info(f"Created resume draft: resume_id={resume_id}, user_id={user_id}")
        
        # Update background task to use existing resume_id
        # Replace the task with one that uses the pre-created resume
        background_tasks.add_task(
            _process_existing_resume,
            resume_id,
            user_id,
            resume_draft,
            pipeline
        )
        
        return ResumeCreateResponse(
            resume_id=resume_id,
            status=ResumeStatus.PROCESSING,
            created_at=document.created_at,
            message="Resume generation started. Check status with GET /resumes/{resume_id}"
        )
        
    except ValidationError as e:
        # Custom validation errors from pipeline
        logger.warning(f"Validation error for user_id={current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation failed",
                "message": str(e)
            }
        )
    except PydanticValidationError as e:
        # Pydantic model validation errors
        logger.warning(f"Pydantic validation error for user_id={current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation failed",
                "details": e.errors()
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error creating resume for user_id={current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the resume"
        )


async def _process_existing_resume(
    resume_id: str,
    user_id: str,
    resume_draft: ResumeDraft,
    pipeline: ResumePipeline
):
    """
    Process existing resume draft in background.
    
    Args:
        resume_id: Pre-created resume ID
        user_id: User ID
        resume_draft: Resume draft data
        pipeline: Resume pipeline instance
    """
    try:
        # Update status to processing
        await pipeline._update_status(resume_id, ResumeStatus.PROCESSING)
        
        # Continue with the rest of the pipeline
        from app.core.metrics import get_metrics_tracker
        
        metrics = get_metrics_tracker(resume_id)
        
        try:
            snapshot = resume_draft.model_dump()
            
            # AI enhancement (optional)
            enhanced_snapshot = snapshot.copy()
            if resume_draft.ai_enhancement.enhance_summary or \
               resume_draft.ai_enhancement.enhance_experience or \
               resume_draft.ai_enhancement.enhance_projects:
                
                with metrics.track_stage('ai_enhancement'):
                    enhanced_snapshot = await pipeline._apply_ai_enhancement(
                        snapshot, resume_draft.ai_enhancement, resume_draft.job_description, metrics
                    )
            
            # Render HTML
            with metrics.track_stage('html_render'):
                html_content = pipeline.html_renderer.render_resume(enhanced_snapshot)
                await pipeline._save_html(resume_id, html_content)
            
            # Generate PDF
            with metrics.track_stage('pdf_generation'):
                pdf_bytes = await pipeline._generate_pdf_with_retry(html_content, resume_id, metrics)
                metrics.record_pdf_size(len(pdf_bytes))
            
            # Upload to S3
            with metrics.track_stage('upload'):
                pdf_metadata = await pipeline._upload_pdf(resume_id, user_id, pdf_bytes, metrics)
            
            # Complete
            await pipeline._complete_resume(resume_id, pdf_metadata)
            metrics.record_success()
            
        except Exception as e:
            error_msg = f"Resume generation failed: {str(e)}"
            
            # DEBUG: Write error to file for inspection
            try:
                with open("last_error.txt", "w") as f:
                    f.write(error_msg)
            except:
                pass

            logger.error(f"Error processing resume_id={resume_id}: {e}", exc_info=True)
            await pipeline._mark_error(resume_id, error_msg, 'processing_error')
            metrics.record_failure('processing_error', str(e))
            
    except Exception as e:
        logger.error(f"Critical error in background task for resume_id={resume_id}: {e}", exc_info=True)


@router.get(
    "/resumes/{resume_id}",
    response_model=ResumeStatusResponse,
    responses={
        200: {"description": "Resume status retrieved"},
        404: {"description": "Resume not found"}
    }
)
async def get_resume_status(
    resume_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get resume generation status and download URL.
    
    **Status Flow:**
    - `draft`: Initial state after creation
    - `processing`: Generation in progress
    - `complete`: Generation complete, PDF available
    - `error`: Generation failed (see error_message)
    
    Args:
        resume_id: Resume ID
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        ResumeStatusResponse with status and download URL (if complete)
        
    Raises:
        HTTPException 404: If resume not found or not owned by user
    """
    try:
        resume_doc = await db["resumes"].find_one({
            "resume_id": resume_id,
            "user_id": str(current_user.id)
        })
        
        if not resume_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        response = ResumeStatusResponse(
            resume_id=resume_doc["resume_id"],
            status=ResumeStatus(resume_doc["status"]),
            created_at=resume_doc["created_at"],
            updated_at=resume_doc["updated_at"],
            completed_at=resume_doc.get("completed_at"),
            download_url=resume_doc.get("pdf", {}).get("url") if resume_doc.get("pdf") else None,
            error_message=resume_doc.get("error_message"),
            error_code=resume_doc.get("error_code")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resume status for resume_id={resume_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume status"
        )


@router.get(
    "/resumes",
    response_model=list[ResumeStatusResponse],
    responses={
        200: {"description": "List of user's resumes"}
    }
)
async def list_user_resumes(
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    limit: int = 20,
    skip: int = 0
):
    """
    List all resumes for the current user.
    
    Args:
        current_user: Authenticated user
        db: Database connection
        limit: Maximum number of resumes to return
        skip: Number of resumes to skip
        
    Returns:
        List of ResumeStatusResponse
    """
    try:
        cursor = db["resumes"].find(
            {"user_id": str(current_user.id)}
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        resumes = []
        async for resume_doc in cursor:
            resumes.append(ResumeStatusResponse(
                resume_id=resume_doc["resume_id"],
                status=ResumeStatus(resume_doc["status"]),
                created_at=resume_doc["created_at"],
                updated_at=resume_doc["updated_at"],
                completed_at=resume_doc.get("completed_at"),
                download_url=resume_doc.get("pdf", {}).get("url") if resume_doc.get("pdf") else None,
                error_message=resume_doc.get("error_message"),
                error_code=resume_doc.get("error_code")
            ))
        
        return resumes
        
    except Exception as e:
        logger.error(f"Failed to list resumes for user_id={current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes"
        )
