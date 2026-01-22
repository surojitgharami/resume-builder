# app/services/resume_pipeline.py
"""
Production-ready resume generation pipeline with proper sequencing and error handling.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.resume_draft import (
    ResumeDraft, ResumeDocument, ResumeStatus, PDFMetadata, AIEnhancementOptions
)
from app.services.html_renderer import HTMLRendererService
from app.services.pdf_playwright import PlaywrightPDFService, PDFGenerationError
from app.services.storage import S3StorageService
from app.services.ai_enhancer_v2 import AIEnhancerService
from app.core.metrics import get_metrics_tracker, ResumeGenerationMetrics

logger = logging.getLogger(__name__)


class ResumePipelineError(Exception):
    """Base exception for resume pipeline errors."""
    pass


class ValidationError(ResumePipelineError):
    """Validation error."""
    pass


class ResumePipeline:
    """
    Production-safe resume generation pipeline.
    
    Pipeline stages:
    1. Validation (422 for missing required fields)
    2. Save draft with snapshot
    3. AI enhancement (optional, per-section)
    4. Set status=processing
    5. Render HTML from snapshot
    6. Generate PDF with Playwright (2x retry)
    7. Upload to S3
    8. Update status=complete with PDF metadata
    
    Error handling:
    - Any failure sets status=error with detailed error message
    - Uploads only happen after PDF generation
    - Metadata persisted only after successful upload
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        html_renderer: HTMLRendererService,
        pdf_service: PlaywrightPDFService,
        storage_service: S3StorageService,
        ai_enhancer: Optional[AIEnhancerService] = None
    ):
        """
        Initialize resume pipeline.
        
        Args:
            db: MongoDB database connection
            html_renderer: HTML rendering service
            pdf_service: PDF generation service
            storage_service: S3 storage service
            ai_enhancer: Optional AI enhancement service
        """
        self.db = db
        self.html_renderer = html_renderer
        self.pdf_service = pdf_service
        self.storage_service = storage_service
        self.ai_enhancer = ai_enhancer
        self.resumes_collection = db["resumes"]
        logger.info("ResumePipeline initialized")
    
    async def generate_resume(
        self,
        user_id: str,
        resume_draft: ResumeDraft
    ) -> Dict[str, Any]:
        """
        Generate resume from draft data.
        
        Args:
            user_id: User ID
            resume_draft: Validated resume draft
            
        Returns:
            Dict with resume_id and status
            
        Raises:
            ValidationError: If validation fails
            ResumePipelineError: If generation fails
        """
        resume_id = str(uuid.uuid4())
        metrics = get_metrics_tracker(resume_id)
        
        try:
            # Stage 1: Validation (already done by Pydantic, but double-check)
            with metrics.track_stage('validation'):
                self._validate_draft(resume_draft)
            
            # Stage 2: Save draft with snapshot
            with metrics.track_stage('snapshot_persist'):
                snapshot = resume_draft.model_dump()
                await self._save_draft(resume_id, user_id, snapshot)
            
            # Stage 3: AI enhancement (optional)
            enhanced_snapshot = snapshot.copy()
            if resume_draft.ai_enhancement.enhance_summary or \
               resume_draft.ai_enhancement.enhance_experience or \
               resume_draft.ai_enhancement.enhance_projects:
                
                with metrics.track_stage('ai_enhancement'):
                    enhanced_snapshot = await self._apply_ai_enhancement(
                        snapshot, resume_draft.ai_enhancement, resume_draft.job_description, metrics
                    )
            
            # Stage 4: Update status to processing
            await self._update_status(resume_id, ResumeStatus.PROCESSING)
            
            # Stage 5: Render HTML from snapshot
            with metrics.track_stage('html_render'):
                html_content = self.html_renderer.render_resume(enhanced_snapshot)
                await self._save_html(resume_id, html_content)
            
            # Stage 6: Generate PDF with retry
            with metrics.track_stage('pdf_generation'):
                pdf_bytes = await self._generate_pdf_with_retry(html_content, resume_id, metrics)
                metrics.record_pdf_size(len(pdf_bytes))
            
            # Stage 7: Upload to S3
            with metrics.track_stage('upload'):
                pdf_metadata = await self._upload_pdf(resume_id, user_id, pdf_bytes, metrics)
            
            # Stage 8: Update status to complete with PDF metadata
            await self._complete_resume(resume_id, pdf_metadata)
            
            metrics.record_success()
            
            return {
                "resume_id": resume_id,
                "status": ResumeStatus.COMPLETE,
                "download_url": pdf_metadata.url
            }
            
        except ValidationError as e:
            logger.error(f"Validation error for resume_id={resume_id}: {e}")
            metrics.record_failure('validation_error', str(e))
            raise
            
        except PDFGenerationError as e:
            error_msg = f"PDF generation failed: {str(e)}"
            await self._mark_error(resume_id, error_msg, 'pdf_error')
            metrics.record_failure('pdf_error', str(e))
            raise ResumePipelineError(error_msg)
            
        except Exception as e:
            error_msg = f"Resume generation failed: {str(e)}"
            logger.error(f"Unexpected error for resume_id={resume_id}: {e}", exc_info=True)
            await self._mark_error(resume_id, error_msg, 'unknown')
            metrics.record_failure('unknown', str(e))
            raise ResumePipelineError(error_msg)
    
    def _validate_draft(self, draft: ResumeDraft):
        """
        Validate resume draft with clear, specific error messages.
        
        Args:
            draft: Resume draft to validate
            
        Raises:
            ValidationError: If validation fails with specific message
        """
        # Name validation
        if not draft.profile.full_name or not draft.profile.full_name.strip():
            raise ValidationError(
                "Profile full_name is required and cannot be empty. "
                "Please provide your full name in the profile section."
            )
        
        # Validate each experience entry (if any provided)
        for idx, exp in enumerate(draft.experience):
            if not exp.company or not exp.company.strip():
                raise ValidationError(
                    f"Experience entry {idx + 1}: Company name is required and cannot be empty."
                )
            if not exp.position or not exp.position.strip():
                raise ValidationError(
                    f"Experience entry {idx + 1}: Position/title is required and cannot be empty."
                )
        
        logger.info(f"Draft validation passed: name={draft.profile.full_name}, experiences={len(draft.experience)}")
    
    async def _save_draft(self, resume_id: str, user_id: str, snapshot: Dict[str, Any]):
        """Save initial draft with snapshot."""
        document = ResumeDocument(
            resume_id=resume_id,
            user_id=user_id,
            snapshot=snapshot,
            status=ResumeStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.resumes_collection.insert_one(document.model_dump())
        logger.info(f"Saved draft for resume_id={resume_id}")
    
    async def _apply_ai_enhancement(
        self,
        snapshot: Dict[str, Any],
        ai_options: AIEnhancementOptions,
        job_description: Optional[str],
        metrics: ResumeGenerationMetrics
    ) -> Dict[str, Any]:
        """
        Apply AI enhancement to snapshot (per-section, togglable).
        
        Args:
            snapshot: Original snapshot
            ai_options: AI enhancement options
            job_description: Optional job description
            metrics: Metrics tracker
            
        Returns:
            Enhanced snapshot
        """
        if not self.ai_enhancer:
            logger.warning("AI enhancer not available, skipping enhancement")
            return snapshot
        
        enhanced = snapshot.copy()
        
        # Enhance summary
        if ai_options.enhance_summary and enhanced.get('profile', {}).get('summary'):
            start_time = datetime.utcnow()
            try:
                original_summary = enhanced['profile']['summary']
                enhanced['profile']['summary'] = await self.ai_enhancer.enhance_summary(
                    original_summary, job_description, ai_options.custom_instructions
                )
                duration = (datetime.utcnow() - start_time).total_seconds()
                metrics.record_ai_enhancement('summary', duration, True)
            except Exception as e:
                logger.error(f"Failed to enhance summary: {e}")
                duration = (datetime.utcnow() - start_time).total_seconds()
                metrics.record_ai_enhancement('summary', duration, False)
        
        # Enhance experience achievements
        if ai_options.enhance_experience and enhanced.get('experience'):
            for i, exp in enumerate(enhanced['experience']):
                if exp.get('achievements') and len(exp['achievements']) > 0:
                    start_time = datetime.utcnow()
                    try:
                        exp['achievements'] = await self.ai_enhancer.enhance_experience_achievements(
                            exp['achievements'],
                            exp.get('position', ''),
                            exp.get('company', ''),
                            job_description,
                            ai_options.custom_instructions
                        )
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        metrics.record_ai_enhancement('experience', duration, True)
                    except Exception as e:
                        logger.error(f"Failed to enhance experience {i}: {e}")
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        metrics.record_ai_enhancement('experience', duration, False)
        
        # Enhance projects
        if ai_options.enhance_projects and enhanced.get('projects'):
            for i, project in enumerate(enhanced['projects']):
                if project.get('description'):
                    start_time = datetime.utcnow()
                    try:
                        project['description'] = await self.ai_enhancer.enhance_project_description(
                            project.get('name', ''),
                            project['description'],
                            project.get('technologies', []),
                            job_description,
                            ai_options.custom_instructions
                        )
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        metrics.record_ai_enhancement('projects', duration, True)
                    except Exception as e:
                        logger.error(f"Failed to enhance project {i}: {e}")
                        duration = (datetime.utcnow() - start_time).total_seconds()
                        metrics.record_ai_enhancement('projects', duration, False)
        
        return enhanced
    
    async def _update_status(self, resume_id: str, status: ResumeStatus):
        """Update resume status."""
        await self.resumes_collection.update_one(
            {"resume_id": resume_id},
            {
                "$set": {
                    "status": status.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.info(f"Updated resume_id={resume_id} status={status.value}")
    
    async def _save_html(self, resume_id: str, html_content: str):
        """Save rendered HTML content."""
        await self.resumes_collection.update_one(
            {"resume_id": resume_id},
            {
                "$set": {
                    "html_content": html_content,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.info(f"Saved HTML for resume_id={resume_id} (length={len(html_content)})")
    
    async def _generate_pdf_with_retry(
        self,
        html_content: str,
        resume_id: str,
        metrics: ResumeGenerationMetrics
    ) -> bytes:
        """
        Generate PDF with automatic retry (handled by Playwright service).
        
        Args:
            html_content: HTML content to render
            resume_id: Resume ID for logging
            metrics: Metrics tracker
            
        Returns:
            PDF bytes
            
        Raises:
            PDFGenerationError: If generation fails after retries
        """
        try:
            # Service returns path to temp file
            pdf_path_str = await self.pdf_service.generate_pdf_from_html(html_content)
            
            try:
                # Read bytes from file
                with open(pdf_path_str, "rb") as f:
                    pdf_bytes = f.read()
                
                # Cleanup temp file
                self.pdf_service.cleanup_file(pdf_path_str)
                
                metrics.record_pdf_attempt(success=True, retry=False)
                return pdf_bytes
                
            except Exception as read_err:
                 # Cleanup if read fails
                 self.pdf_service.cleanup_file(pdf_path_str)
                 raise read_err

        except Exception as e:
            metrics.record_pdf_attempt(success=False, retry=False)
            raise PDFGenerationError(f"PDF generation failed: {str(e)}")
    
    async def _upload_pdf(
        self,
        resume_id: str,
        user_id: str,
        pdf_bytes: bytes,
        metrics: ResumeGenerationMetrics
    ) -> PDFMetadata:
        """
        Upload PDF to S3.
        
        Args:
            resume_id: Resume ID
            user_id: User ID
            pdf_bytes: PDF bytes
            metrics: Metrics tracker
            
        Returns:
            PDF metadata
            
        Raises:
            Exception: If upload fails
        """
        start_time = datetime.utcnow()
        try:
            s3_key = f"resumes/{user_id}/{resume_id}.pdf"
            await self.storage_service.upload_file(
                BytesIO(pdf_bytes),
                s3_key,
                content_type="application/pdf"
            )
            
            download_url = await self.storage_service.generate_presigned_url(s3_key, expiration=3600 * 24 * 7)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics.record_s3_upload(duration, True)
            
            metadata = PDFMetadata(
                s3_key=s3_key,
                url=download_url,
                uploaded_at=datetime.utcnow(),
                file_size=len(pdf_bytes)
            )
            
            logger.info(f"Uploaded PDF for resume_id={resume_id} to s3_key={s3_key}")
            return metadata
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            error_type = type(e).__name__
            metrics.record_s3_upload(duration, False, error_type)
            logger.error(f"Failed to upload PDF for resume_id={resume_id}: {e}", exc_info=True)
            raise
    
    async def _complete_resume(self, resume_id: str, pdf_metadata: PDFMetadata):
        """Mark resume as complete with PDF metadata."""
        await self.resumes_collection.update_one(
            {"resume_id": resume_id},
            {
                "$set": {
                    "status": ResumeStatus.COMPLETE.value,
                    "pdf": pdf_metadata.model_dump(),
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.info(f"Marked resume_id={resume_id} as complete")
    
    async def _mark_error(self, resume_id: str, error_message: str, error_code: str):
        """Mark resume as error with details."""
        await self.resumes_collection.update_one(
            {"resume_id": resume_id},
            {
                "$set": {
                    "status": ResumeStatus.ERROR.value,
                    "error_message": error_message,
                    "error_code": error_code,
                    "updated_at": datetime.utcnow()
                },
                "$inc": {"retry_count": 1}
            }
        )
        logger.error(f"Marked resume_id={resume_id} as error: {error_message}")
