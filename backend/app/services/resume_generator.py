# app/services/resume_generator.py
import logging
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.resume import Resume, ResumeCreate, ResumeSection, ResumeStatus, TemplatePreferences
from app.models.user import User
from app.services.llm import LLMService
from app.services.rag import RAGService
from app.services.embeddings import EmbeddingsService
from app.services.pdf_generator import PDFGeneratorService
from app.services.storage import S3StorageService
from io import BytesIO

logger = logging.getLogger(__name__)


class ResumeGeneratorService:
    """Service for generating tailored resumes using LLM and RAG."""
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        llm_service: LLMService,
        embeddings_service: EmbeddingsService,
        pdf_service: PDFGeneratorService,
        storage_service: S3StorageService
    ):
        self.db = db
        self.llm_service = llm_service
        self.embeddings_service = embeddings_service
        self.pdf_service = pdf_service
        self.storage_service = storage_service
        self.resumes_collection = db["resumes"]
    
    async def generate_resume(
        self,
        user: User,
        resume_request: ResumeCreate
    ) -> Resume:
        """
        Generate a complete resume tailored to a job description.
        
        Args:
            user: User object
            resume_request: Resume generation request
            
        Returns:
            Generated Resume object
        """
        resume_id = str(uuid.uuid4())
        
        # Create initial resume record
        resume = Resume(
            resume_id=resume_id,
            user_id=str(user.id),
            job_description=resume_request.job_description,
            template_preferences=resume_request.template_preferences,
            format=resume_request.format,
            status=ResumeStatus.PROCESSING,
            sections=[],
            metadata={}
        )
        
        try:
            # Save initial resume
            await self.resumes_collection.insert_one(resume.model_dump())
            
            # Get relevant context from RAG if enabled
            context = None
            if resume_request.use_rag:
                context = await self._get_rag_context(
                    str(user.id),
                    resume_request.job_description
                )
            
            # Generate resume sections
            sections = await self._generate_sections(
                user=user,
                job_description=resume_request.job_description,
                template_preferences=resume_request.template_preferences,
                context=context,
                custom_instructions=resume_request.custom_instructions
            )
            
            resume.sections = sections
            resume.status = ResumeStatus.COMPLETED
            resume.completed_at = datetime.utcnow()
            
            # Generate PDF if requested
            if resume_request.format.value == "pdf":
                pdf_bytes = await self.pdf_service.generate_pdf(resume)
                
                # Upload to S3
                s3_key = f"resumes/{str(user.id)}/{resume_id}.pdf"
                await self.storage_service.upload_file(
                    BytesIO(pdf_bytes),
                    s3_key,
                    content_type="application/pdf",
                    metadata={
                        "user_id": str(user.id),
                        "resume_id": resume_id
                    }
                )
                
                # Generate presigned URL
                download_url = await self.storage_service.generate_presigned_url(
                    s3_key,
                    expiration=7200  # 2 hours
                )
                
                resume.s3_key = s3_key
                resume.download_url = download_url
            
            # Update resume in database
            await self.resumes_collection.update_one(
                {"resume_id": resume_id},
                {"$set": resume.model_dump()}
            )
            
            logger.info(f"Successfully generated resume {resume_id} for user {user.id}")
            return resume
            
        except Exception as e:
            logger.error(f"Resume generation failed: {e}")
            
            # Update resume status to failed
            resume.status = ResumeStatus.FAILED
            resume.error_message = str(e)
            
            await self.resumes_collection.update_one(
                {"resume_id": resume_id},
                {"$set": {"status": resume.status.value, "error_message": resume.error_message}}
            )
            
            raise Exception(f"Resume generation failed: {str(e)}")
    
    async def _generate_sections(
        self,
        user: User,
        job_description: str,
        template_preferences: TemplatePreferences,
        context: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> List[ResumeSection]:
        """Generate all resume sections."""
        sections = []
        
        # Define section order and names
        section_configs = [
            {"name": "Contact Information", "order": 0},
            {"name": "Professional Summary", "order": 1},
            {"name": "Skills", "order": 2},
            {"name": "Professional Experience", "order": 3},
            {"name": "Education", "order": 4},
        ]
        
        if template_preferences.include_projects:
            section_configs.append({"name": "Projects", "order": 5})
        
        if template_preferences.include_certifications:
            section_configs.append({"name": "Certifications", "order": 6})
        
        # Prepare user data
        user_data = self._prepare_user_data(user)
        
        # Add custom instructions to context if provided
        full_context = context or ""
        if custom_instructions:
            full_context = f"{full_context}\n\nCUSTOM INSTRUCTIONS:\n{custom_instructions}"
        
        # Generate each section
        for config in section_configs:
            try:
                content = await self._generate_section_content(
                    section_name=config["name"],
                    job_description=job_description,
                    user_data=user_data,
                    tone=template_preferences.tone,
                    context=full_context if full_context else None,
                    template_preferences=template_preferences
                )
                
                section = ResumeSection(
                    title=config["name"],
                    content=content,
                    order=config["order"]
                )
                
                sections.append(section)
                
            except Exception as e:
                logger.error(f"Failed to generate section {config['name']}: {e}")
                # Add empty section as fallback
                sections.append(ResumeSection(
                    title=config["name"],
                    content=f"[Section generation failed: {str(e)}]",
                    order=config["order"]
                ))
        
        return sections
    
    async def _generate_section_content(
        self,
        section_name: str,
        job_description: str,
        user_data: Dict[str, Any],
        tone: str,
        context: Optional[str] = None,
        template_preferences: TemplatePreferences = None
    ) -> str:
        """Generate content for a specific section."""
        
        if section_name == "Contact Information":
            return self._format_contact_info(user_data)
        
        elif section_name == "Skills":
            return await self._generate_skills_section(
                job_description,
                user_data,
                tone,
                context
            )
        
        else:
            # Use LLM for other sections
            return await self.llm_service.generate_resume_section(
                section_name=section_name,
                job_description=job_description,
                user_data=user_data,
                tone=tone,
                context=context
            )
    
    def _format_contact_info(self, user_data: Dict[str, Any]) -> str:
        """Format contact information section."""
        profile = user_data.get("profile", {})
        
        lines = [profile.get("full_name", "")]
        
        if profile.get("email"):
            lines.append(f"Email: {profile['email']}")
        
        if profile.get("phone"):
            lines.append(f"Phone: {profile['phone']}")
        
        if profile.get("location"):
            lines.append(f"Location: {profile['location']}")
        
        links = []
        if profile.get("linkedin_url"):
            links.append(f"LinkedIn: {profile['linkedin_url']}")
        if profile.get("github_url"):
            links.append(f"GitHub: {profile['github_url']}")
        if profile.get("portfolio_url"):
            links.append(f"Portfolio: {profile['portfolio_url']}")
        
        if links:
            lines.append(" | ".join(links))
        
        return "\n".join(lines)
    
    async def _generate_skills_section(
        self,
        job_description: str,
        user_data: Dict[str, Any],
        tone: str,
        context: Optional[str] = None
    ) -> str:
        """Generate skills section with categorization."""
        profile = user_data.get("profile", {})
        all_skills = profile.get("skills", [])
        
        if not all_skills:
            return "Skills to be added"
        
        # Use LLM to categorize and prioritize skills based on job description
        prompt = f"""Given this job description and list of skills, organize the skills into relevant categories and prioritize them based on job requirements.

JOB DESCRIPTION:
{job_description}

SKILLS:
{', '.join(all_skills)}

Format the output as categorized bullet points (e.g., Programming Languages, Frameworks, Tools, etc.). Only include categories that are relevant."""
        
        messages = [{"role": "user", "content": prompt}]
        
        return await self.llm_service.generate_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=400
        )
    
    async def _get_rag_context(
        self,
        user_id: str,
        job_description: str,
        top_k: int = 5
    ) -> str:
        """Get relevant context from RAG system."""
        try:
            rag_service = RAGService(self.db, self.embeddings_service)
            
            # Search for relevant documents
            results = await rag_service.search_similar(
                user_id=user_id,
                query=job_description,
                top_k=top_k
            )
            
            if not results:
                return None
            
            # Combine relevant context
            context_parts = []
            for result in results:
                context_parts.append(result.get("content", ""))
            
            context = "\n\n".join(context_parts)
            logger.info(f"Retrieved {len(results)} relevant documents from RAG")
            return context
            
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return None
    
    def _prepare_user_data(self, user: User) -> Dict[str, Any]:
        """Prepare user data for LLM consumption."""
        return {
            "email": user.email,
            "profile": user.profile.model_dump()
        }
    
    async def get_user_resumes(
        self,
        user_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Resume]:
        """
        Get all resumes for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of resumes to return
            skip: Number of resumes to skip
            
        Returns:
            List of Resume objects
        """
        cursor = self.resumes_collection.find(
            {"user_id": user_id}
        ).sort("generated_at", -1).skip(skip).limit(limit)
        
        resumes = await cursor.to_list(length=limit)
        return [Resume(**resume) for resume in resumes]
    
    async def get_resume_by_id(
        self,
        resume_id: str,
        user_id: str
    ) -> Optional[Resume]:
        """
        Get a specific resume by ID.
        
        Args:
            resume_id: Resume ID
            user_id: User ID for authorization
            
        Returns:
            Resume object or None
        """
        resume_data = await self.resumes_collection.find_one({
            "resume_id": resume_id,
            "user_id": user_id
        })
        
        if resume_data:
            return Resume(**resume_data)
        return None
    
    async def delete_resume(
        self,
        resume_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a resume.
        
        Args:
            resume_id: Resume ID
            user_id: User ID for authorization
            
        Returns:
            True if deleted successfully
        """
        resume = await self.get_resume_by_id(resume_id, user_id)
        
        if not resume:
            return False
        
        # Delete from S3 if exists
        if resume.s3_key:
            try:
                await self.storage_service.delete_file(resume.s3_key)
            except Exception as e:
                logger.warning(f"Failed to delete S3 file: {e}")
        
        # Delete from database
        result = await self.resumes_collection.delete_one({
            "resume_id": resume_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0


def get_resume_generator_service(
    db: AsyncIOMotorDatabase,
    llm_service: LLMService,
    embeddings_service: EmbeddingsService,
    pdf_service: PDFGeneratorService,
    storage_service: S3StorageService
) -> ResumeGeneratorService:
    """Dependency to get resume generator service instance."""
    return ResumeGeneratorService(
        db, llm_service, embeddings_service, pdf_service, storage_service
    )
