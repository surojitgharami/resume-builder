# app/services/ai_enhancer_v2.py
"""
AI enhancement service for resume content.
Only enhances existing text - never creates or removes sections.
"""
import logging
from typing import Dict, Any, List, Optional

# Defensive import - AI service is OPTIONAL
try:
    from app.services.llm import LLMService
    LLM_AVAILABLE = True
except Exception as e:
    LLMService = None
    LLM_AVAILABLE = False
    # Logger might not be set up yet, so we'll log later

logger = logging.getLogger(__name__)

if not LLM_AVAILABLE:
    logger.warning("LLMService import failed. AI enhancement features will be disabled.")


class AIEnhancerService:
    """
    Service for AI-enhanced resume content generation.
    
    Design principles:
    - Only enhances existing content (text rewriting)
    - Never creates or removes sections
    - Respects user's structure and data
    - Togglable per section
    """
    
    def __init__(self, llm_service: Optional[Any] = None):
        """
        Initialize AI enhancer service.
        
        Args:
            llm_service: LLM service for content generation (can be None if unavailable)
        """
        self.llm_service = llm_service
        if not llm_service:
            logger.warning("AIEnhancerService initialized without LLM service - all enhancement operations will return original content")
    
    def is_available(self) -> bool:
        """
        Check if AI enhancer service is available.
        
        Returns:
            True if service is ready to use, False otherwise
        """
        try:
            return self.llm_service is not None and self.llm_service.is_available()
        except Exception:
            return False
    
    async def enhance_summary(
        self,
        original_summary: str,
        job_description: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Enhance professional summary with AI.
        
        Args:
            original_summary: Original summary text
            job_description: Optional job description for tailoring
            custom_instructions: Optional custom instructions
            
        Returns:
            Enhanced summary text
        """
        if not original_summary or not original_summary.strip():
            logger.warning("Empty summary provided, returning as-is")
            return original_summary
        
        try:
            prompt = self._build_summary_prompt(original_summary, job_description, custom_instructions)
            enhanced = await self.llm_service.generate_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, 
                temperature=0.7
            )
            
            logger.info(f"Summary enhanced (original={len(original_summary)}, enhanced={len(enhanced)})")
            return enhanced.strip()
            
        except Exception as e:
            logger.error(f"Failed to enhance summary: {e}", exc_info=True)
            # Fallback to original on error
            return original_summary
    
    async def enhance_experience_achievements(
        self,
        achievements: List[str],
        position: str,
        company: str,
        job_description: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> List[str]:
        """
        Enhance experience achievements/bullet points.
        
        Args:
            achievements: Original achievement bullets
            position: Job position
            company: Company name
            job_description: Optional job description for tailoring
            custom_instructions: Optional custom instructions
            
        Returns:
            Enhanced achievement bullets (same count as input)
        """
        if not achievements or len(achievements) == 0:
            logger.warning("Empty achievements list, returning as-is")
            return achievements
        
        try:
            prompt = self._build_achievements_prompt(
                achievements, position, company, job_description, custom_instructions
            )
            enhanced_text = await self.llm_service.generate_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500, 
                temperature=0.7
            )
            
            # Parse bullet points from response
            enhanced_achievements = self._parse_bullet_points(enhanced_text, len(achievements))
            
            logger.info(f"Achievements enhanced (original={len(achievements)}, enhanced={len(enhanced_achievements)})")
            return enhanced_achievements
            
        except Exception as e:
            logger.error(f"Failed to enhance achievements: {e}", exc_info=True)
            # Fallback to original on error
            return achievements
    
    async def enhance_project_description(
        self,
        project_name: str,
        original_description: str,
        technologies: List[str],
        job_description: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Enhance project description.
        
        Args:
            project_name: Project name
            original_description: Original description
            technologies: Technologies used
            job_description: Optional job description for tailoring
            custom_instructions: Optional custom instructions
            
        Returns:
            Enhanced project description
        """
        if not original_description or not original_description.strip():
            logger.warning("Empty project description, returning as-is")
            return original_description
        
        try:
            prompt = self._build_project_prompt(
                project_name, original_description, technologies, job_description, custom_instructions
            )
            enhanced = await self.llm_service.generate_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, 
                temperature=0.7
            )
            
            logger.info(f"Project description enhanced (original={len(original_description)}, enhanced={len(enhanced)})")
            return enhanced.strip()
            
        except Exception as e:
            logger.error(f"Failed to enhance project description: {e}", exc_info=True)
            # Fallback to original on error
            return original_description
    
    def _build_summary_prompt(
        self,
        original: str,
        job_description: Optional[str],
        custom_instructions: Optional[str]
    ) -> str:
        """Build prompt for summary enhancement."""
        prompt = f"""You are a professional resume writer. Enhance the following professional summary to make it more impactful and compelling.

Original Summary:
{original}
"""
        if job_description:
            prompt += f"\nTarget Job Description:\n{job_description[:500]}\n"
            prompt += "\nTailor the summary to align with this job description while keeping the core message."
        
        if custom_instructions:
            prompt += f"\nAdditional Instructions:\n{custom_instructions}\n"
        
        prompt += """
Requirements:
- Keep the same length (2-4 sentences)
- Use action verbs and quantifiable achievements
- Maintain professional tone
- Only enhance the text, do not add new claims

Enhanced Summary:"""
        
        return prompt
    
    def _build_achievements_prompt(
        self,
        achievements: List[str],
        position: str,
        company: str,
        job_description: Optional[str],
        custom_instructions: Optional[str]
    ) -> str:
        """Build prompt for achievements enhancement."""
        achievements_text = "\n".join([f"- {a}" for a in achievements])
        
        prompt = f"""You are a professional resume writer. Enhance the following achievement bullets for a resume.

Position: {position}
Company: {company}

Original Achievements:
{achievements_text}
"""
        if job_description:
            prompt += f"\nTarget Job Description:\n{job_description[:500]}\n"
            prompt += "\nTailor the achievements to align with this job description."
        
        if custom_instructions:
            prompt += f"\nAdditional Instructions:\n{custom_instructions}\n"
        
        prompt += f"""
Requirements:
- Return EXACTLY {len(achievements)} bullet points
- Use strong action verbs (Led, Developed, Implemented, etc.)
- Include quantifiable metrics where possible
- Keep each bullet concise (1-2 lines)
- Only enhance existing achievements, do not invent new ones

Enhanced Achievements (one per line, starting with '-'):"""
        
        return prompt
    
    def _build_project_prompt(
        self,
        project_name: str,
        original: str,
        technologies: List[str],
        job_description: Optional[str],
        custom_instructions: Optional[str]
    ) -> str:
        """Build prompt for project description enhancement."""
        tech_list = ", ".join(technologies) if technologies else "N/A"
        
        prompt = f"""You are a professional resume writer. Enhance the following project description for a resume.

Project Name: {project_name}
Technologies: {tech_list}

Original Description:
{original}
"""
        if job_description:
            prompt += f"\nTarget Job Description:\n{job_description[:500]}\n"
            prompt += "\nTailor the description to highlight relevant aspects for this job."
        
        if custom_instructions:
            prompt += f"\nAdditional Instructions:\n{custom_instructions}\n"
        
        prompt += """
Requirements:
- Keep similar length to original (2-4 sentences)
- Highlight impact and technical complexity
- Use professional, technical language
- Only enhance the description, do not add false information

Enhanced Description:"""
        
        return prompt
    
    def _parse_bullet_points(self, text: str, expected_count: int) -> List[str]:
        """
        Parse bullet points from LLM response.
        
        Args:
            text: LLM response text
            expected_count: Expected number of bullets
            
        Returns:
            List of bullet points
        """
        lines = text.strip().split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove common bullet prefixes
            for prefix in ['- ', '• ', '* ', '→ ', '> ']:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            
            if line:
                bullets.append(line)
        
        # Ensure we have the expected count
        if len(bullets) < expected_count:
            logger.warning(f"Expected {expected_count} bullets, got {len(bullets)}. Padding with originals.")
            # This shouldn't happen with good prompts, but just in case
            return bullets
        elif len(bullets) > expected_count:
            logger.warning(f"Expected {expected_count} bullets, got {len(bullets)}. Truncating.")
            return bullets[:expected_count]
        
        return bullets


def get_ai_enhancer_service(llm_service: Optional[Any] = None) -> Optional[AIEnhancerService]:
    """
    Get AI enhancer service instance.
    
    Args:
        llm_service: Optional LLM service instance
        
    Returns:
        AIEnhancerService if available, None otherwise
    """
    if not LLM_AVAILABLE or llm_service is None:
        logger.info("AI enhancer service not available (LLM service missing or not configured)")
        return None
    return AIEnhancerService(llm_service)

