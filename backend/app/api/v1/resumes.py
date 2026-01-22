# app/api/v1/resumes.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import logging
from datetime import datetime
from pathlib import Path

from app.models.resume import ResumeCreate, ResumeResponse, Resume, HybridResumeCreate
from app.models.user import User
from app.middleware.auth import get_current_active_user
from app.middleware.rate_limit import check_rate_limit
from app.db.mongo import get_database
from app.services.resume_generator import ResumeGeneratorService, get_resume_generator_service
from app.services.llm import get_llm_service
from app.services.embeddings import get_embeddings_service
from app.services.pdf_generator import get_pdf_generator_service, PDFGeneratorService
from app.services.storage import get_storage_service
from app.core.config import settings
from app.core.security import sanitize_input
from app.api.v1.sanitization_middleware import sanitize_resume_sections

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-resume", response_model=ResumeResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_resume(
    request: Request,
    resume_request: ResumeCreate,
    background_tasks: BackgroundTasks,
    use_async: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate a tailored resume based on job description.
    
    Can run synchronously (immediate response) or asynchronously (background task).
    
    Args:
        request: FastAPI request object
        resume_request: Resume generation request
        background_tasks: Background tasks handler
        use_async: Whether to use background task (default: True)
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Resume response (with status PROCESSING if async, COMPLETED if sync)
        
    Raises:
        HTTPException: If generation fails
    """
    # Rate limiting
    await check_rate_limit(
        request,
        "resume_generation",
        max_requests=settings.RATE_LIMIT_RESUME_GENERATION,
        window_seconds=settings.RATE_LIMIT_RESUME_WINDOW
    )
    
    import uuid
    from app.models.resume import Resume, ResumeStatus
    
    try:
        # Create resume record first
        resume_id = str(uuid.uuid4())
        
        resume = Resume(
            resume_id=resume_id,
            user_id=str(current_user.id),
            job_description=resume_request.job_description,
            template_preferences=resume_request.template_preferences,
            format=resume_request.format,
            status=ResumeStatus.PENDING,
            sections=[],
            metadata={
                "use_async": use_async,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        # Save initial resume record
        await db["resumes"].insert_one(resume.model_dump())
        
        # TEMPORARY: Async processing disabled (Celery not configured)
        # Always run synchronously regardless of use_async flag
        if use_async:
            logger.warning(f"Async processing requested but not available. Running synchronously for resume_id={resume_id}")
        
        # Synchronous generation
        llm_service = get_llm_service()
        embeddings_service = get_embeddings_service()
        pdf_service = get_pdf_generator_service()
        storage_service = get_storage_service()
        
        generator_service = get_resume_generator_service(
            db, llm_service, embeddings_service, pdf_service, storage_service
        )
        
        # Generate resume synchronously
        resume = await generator_service.generate_resume(
            user=current_user,
            resume_request=resume_request
        )
        
        # Return completed resume
        return ResumeResponse(
            resume_id=resume.resume_id,
            sections=resume.sections,
            generated_at=resume.generated_at,
            status=resume.status,
            download_url=resume.download_url
        )
        
    except Exception as e:
        logger.error(f"Resume generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume generation failed: {str(e)}"
        )


@router.get("/resumes/list", response_model=List[ResumeResponse])
async def list_resumes(
    limit: int = 10,
    skip: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all resumes for the current user.
    
    Server-side HTML sanitization is applied to all sections before returning.
    
    Args:
        limit: Maximum number of resumes to return
        skip: Number of resumes to skip
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        List of resume responses with sanitized content
    """
    llm_service = get_llm_service()
    embeddings_service = get_embeddings_service()
    pdf_service = get_pdf_generator_service()
    storage_service = get_storage_service()
    
    generator_service = get_resume_generator_service(
        db, llm_service, embeddings_service, pdf_service, storage_service
    )
    
    resumes = await generator_service.get_user_resumes(
        user_id=str(current_user.id),
        limit=limit,
        skip=skip
    )
    
    return [
        ResumeResponse(
            resume_id=resume.resume_id,
            sections=sanitize_resume_sections(resume.sections),
            generated_at=resume.generated_at,
            status=resume.status,
            download_url=resume.download_url
        )
        for resume in resumes
    ]


@router.get("/resumes", response_model=List[ResumeResponse])
async def list_resumes_legacy(
    limit: int = 10,
    skip: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all resumes for the current user.
    
    Server-side HTML sanitization is applied to all sections before returning.
    
    Args:
        limit: Maximum number of resumes to return
        skip: Number of resumes to skip
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        List of resume responses with sanitized content
    """
    llm_service = get_llm_service()
    embeddings_service = get_embeddings_service()
    pdf_service = get_pdf_generator_service()
    storage_service = get_storage_service()
    
    generator_service = get_resume_generator_service(
        db, llm_service, embeddings_service, pdf_service, storage_service
    )
    
    resumes = await generator_service.get_user_resumes(
        user_id=str(current_user.id),
        limit=limit,
        skip=skip
    )
    
    return [
        ResumeResponse(
            resume_id=resume.resume_id,
            sections=sanitize_resume_sections(resume.sections),
            generated_at=resume.generated_at,
            status=resume.status,
            download_url=resume.download_url
        )
        for resume in resumes
    ]


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get a specific resume by ID.
    
    Server-side HTML sanitization is applied to all sections before returning.
    
    Args:
        resume_id: Resume ID
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        Resume response with sanitized content
        
    Raises:
        HTTPException: If resume not found
    """
    llm_service = get_llm_service()
    embeddings_service = get_embeddings_service()
    pdf_service = get_pdf_generator_service()
    storage_service = get_storage_service()
    
    generator_service = get_resume_generator_service(
        db, llm_service, embeddings_service, pdf_service, storage_service
    )
    
    resume = await generator_service.get_resume_by_id(
        resume_id=resume_id,
        user_id=str(current_user.id)
    )
    
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Regenerate presigned URL if needed (for PDFs)
    if resume.s3_key and resume.format.value == "pdf":
        try:
            download_url = await storage_service.generate_presigned_url(
                resume.s3_key,
                expiration=7200
            )
            resume.download_url = download_url
        except Exception as e:
            pass  # URL generation is optional
    
    # Sanitize resume sections before returning (defense in depth)
    sanitized_sections = sanitize_resume_sections(resume.sections)
    
    return ResumeResponse(
        resume_id=resume.resume_id,
        sections=sanitized_sections,
        generated_at=resume.generated_at,
        status=resume.status,
        download_url=resume.download_url
    )


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a resume.
    
    Args:
        resume_id: Resume ID
        current_user: Authenticated user
        db: Database connection
        
    Raises:
        HTTPException: If resume not found
    """
    llm_service = get_llm_service()
    embeddings_service = get_embeddings_service()
    pdf_service = get_pdf_generator_service()
    storage_service = get_storage_service()
    
    generator_service = get_resume_generator_service(
        db, llm_service, embeddings_service, pdf_service, storage_service
    )
    
    deleted = await generator_service.delete_resume(
        resume_id=resume_id,
        user_id=str(current_user.id)
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    return None


@router.get("/resumes/{resume_id}/download-pdf")
async def download_resume_pdf(
    resume_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    background_tasks: BackgroundTasks = None
):
    """
    Download resume as PDF.
    
    Behavior depends on PDF_UPLOAD_TO_S3 configuration:
    - If True (default): Uploads PDF to S3 and returns presigned URL (recommended for production)
    - If False: Streams PDF file directly via FileResponse (simpler for development)
    
    Args:
        resume_id: Resume ID
        current_user: Authenticated user
        db: Database connection
        background_tasks: FastAPI background tasks for cleanup
        
    Returns:
        If PDF_UPLOAD_TO_S3=True: JSON with pdf_url (S3 presigned URL)
        If PDF_UPLOAD_TO_S3=False: FileResponse (PDF file download)
        
    Raises:
        HTTPException: If resume not found or PDF generation unavailable
        
    Example (S3 mode):
        GET /api/v1/resumes/abc123/download-pdf
        Response: {"pdf_url": "https://s3.amazonaws.com/...?signature=..."}
        
    Example (Streaming mode):
        GET /api/v1/resumes/abc123/download-pdf
        Response: resume_abc123.pdf (application/pdf binary)
    """
    try:
        # Fetch resume from database
        resume_doc = await db.resumes.find_one({
            "resume_id": resume_id,
            "user_id": str(current_user.id)
        })
        
        if not resume_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Convert to Resume model
        resume = Resume(**resume_doc)
        
        # Get services
        pdf_service = get_pdf_generator_service()
        
        # Check if PDF generation is available
        if not pdf_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "PDF generation unavailable",
                    "message": "Playwright is not installed",
                    "suggestion": "Contact administrator to install: pip install playwright && playwright install chromium"
                }
            )
        
        # Generate PDF filename
        safe_filename = f"resume_{resume_id}.pdf"
        
        # Generate PDF file
        logger.info(f"Generating PDF for resume {resume_id} (mode: {'S3' if settings.PDF_UPLOAD_TO_S3 else 'streaming'})")
        pdf_path = await pdf_service.generate_pdf(resume, filename=safe_filename)
        
        # Verify file exists
        if not Path(pdf_path).exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF generation failed - file not created"
            )
        
        # OPTION 1: Upload to S3 and return presigned URL (recommended for production)
        if settings.PDF_UPLOAD_TO_S3:
            try:
                storage_service = get_storage_service()
                
                # Read PDF file
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Upload to S3/storage
                s3_key = f"resumes/{current_user.id}/{resume_id}/resume.pdf"
                storage_url = await storage_service.upload_file(
                    file_data=pdf_data,
                    object_path=s3_key,
                    content_type="application/pdf"
                )
                
                # Generate presigned URL for download (1 hour expiration)
                try:
                    pdf_url = await storage_service.generate_presigned_url(
                        object_path=s3_key,
                        expiration=3600,  # 1 hour
                        content_disposition=f'attachment; filename="{safe_filename}"'
                    )
                except Exception as presign_error:
                    logger.warning(f"Failed to generate presigned URL: {presign_error}, using storage URL")
                    pdf_url = storage_url
                
                # Update resume document with PDF URL
                await db.resumes.update_one(
                    {"resume_id": resume_id, "user_id": str(current_user.id)},
                    {
                        "$set": {
                            "pdf_url": storage_url,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
                logger.info(f"PDF uploaded to storage for resume {resume_id}")
                
                return {
                    "pdf_url": pdf_url,
                    "resume_id": resume_id,
                    "expires_in": 3600,
                    "storage_type": "s3" if hasattr(storage_service, 'bucket') else "local"
                }
            
            finally:
                # Cleanup temporary file
                try:
                    Path(pdf_path).unlink(missing_ok=True)
                    logger.info(f"Cleaned up temporary PDF file: {pdf_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp PDF: {e}")
        
        # OPTION 2: Stream file directly via FileResponse (simpler, no storage needed)
        else:
            # Schedule cleanup after response is sent
            if background_tasks:
                def cleanup_pdf():
                    try:
                        Path(pdf_path).unlink(missing_ok=True)
                        logger.info(f"Cleaned up PDF file: {pdf_path}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup PDF: {e}")
                
                background_tasks.add_task(cleanup_pdf)
            
            # Return file as download
            logger.info(f"Streaming PDF download: {pdf_path}")
            return FileResponse(
                path=pdf_path,
                media_type="application/pdf",
                filename=safe_filename,
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_filename}"',
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error generating PDF for resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}"
        )


# DEPRECATED: Legacy hybrid resume creation endpoint
@router.post(
    "/resumes/create-from-profile",
    deprecated=True,
    status_code=status.HTTP_410_GONE,
    responses={
        410: {"description": "Endpoint deprecated - use POST /api/v1/resumes instead"}
    }
)
async def create_resume_from_profile(
    request: Request,
    resume_request: HybridResumeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    DEPRECATED: This endpoint has been replaced by POST /api/v1/resumes.
    
    Please use the new production-ready endpoint instead:
    - POST /api/v1/resumes with ResumeDraft model
    - Provides better validation, error handling, and status tracking
    - Supports background processing with status polling
    
    Migration Guide:
    1. Convert your profile data to ResumeDraft format
    2. POST to /api/v1/resumes
    3. Poll GET /api/v1/resumes/{resume_id} for status
    4. Download PDF when status is 'complete'
    
    See API documentation for details: /docs
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "error": "Endpoint deprecated",
            "message": "This endpoint has been replaced. Please use POST /api/v1/resumes instead.",
            "new_endpoint": "/api/v1/resumes",
            "documentation": "/docs#/Resumes%20-%20V2/create_resume_resumes_post",
            "migration_guide": {
                "step_1": "Convert profile data to ResumeDraft format",
                "step_2": "POST to /api/v1/resumes",
                "step_3": "Poll GET /api/v1/resumes/{resume_id} for status",
                "step_4": "Download PDF when status='complete'"
            }
        }
    )


@router.post("/resumes/{resume_id}/regenerate-pdf")
async def regenerate_resume_pdf(
    resume_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Regenerate and store PDF for a resume.
    
    This endpoint regenerates the PDF and updates the stored version in S3.
    Useful for updating PDFs after resume edits.
    
    Args:
        resume_id: Resume ID
        current_user: Authenticated user
        db: Database connection
        
    Returns:
        dict: Success message with PDF URL
        
    Raises:
        HTTPException: If resume not found or PDF generation fails
    """
    try:
        # Fetch resume
        resume_doc = await db.resumes.find_one({
            "resume_id": resume_id,
            "user_id": str(current_user.id)
        })
        
        if not resume_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        resume = Resume(**resume_doc)
        
        # Get services
        pdf_service = get_pdf_generator_service()
        storage_service = get_storage_service()
        
        if not pdf_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF generation unavailable"
            )
        
        # Generate PDF
        safe_filename = f"resume_{resume_id}.pdf"
        pdf_path = await pdf_service.generate_pdf(resume, filename=safe_filename)
        
        try:
            # Read PDF file
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            # Upload to S3
            s3_key = f"resumes/{current_user.id}/{resume_id}/resume.pdf"
            pdf_url = await storage_service.upload_file(
                file_data=pdf_data,
                object_path=s3_key,
                content_type="application/pdf"
            )
            
            # Update resume document with new PDF URL
            await db.resumes.update_one(
                {"resume_id": resume_id, "user_id": str(current_user.id)},
                {
                    "$set": {
                        "pdf_url": pdf_url,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"PDF regenerated and uploaded for resume {resume_id}")
            
            return {
                "message": "PDF regenerated successfully",
                "pdf_url": pdf_url,
                "resume_id": resume_id
            }
        
        finally:
            # Cleanup temporary file
            try:
                Path(pdf_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp PDF: {e}")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error regenerating PDF for resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate PDF: {str(e)}"
        )
