# app/services/ai_enhancer.py
"""
AI Enhancement Service for hybrid resume builder.

Provides AI-powered content enhancement including:
- Professional summary enhancement
- Experience bullet point improvement
- Skills suggestion based on experience
- Content tailoring to job descriptions
"""

import logging
from typing import List, Optional, Dict
import asyncio

from app.core.config import settings
from app.services.llm_client import LLMClient
from app.models.profile import Experience, Project

logger = logging.getLogger(__name__)


class AIEnhancementService:
    """Service for AI-powered content enhancement."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    async def enhance_summary(
        self,
        original_summary: str,
        job_description: Optional[str] = None,
        tone: str = "professional"
    ) -> str:
        """
        Enhance professional summary with AI.
        
        Args:
            original_summary: User's original summary
            job_description: Optional job description for tailoring
            tone: Desired tone (professional, technical, creative, casual)
            
        Returns:
            Enhanced summary
        """
        try:
            prompt = self._build_summary_prompt(original_summary, job_description, tone)
            
            enhanced = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=300,
                temperature=0.7
            )
            
            logger.info("Successfully enhanced professional summary")
            return enhanced.strip()
            
        except Exception as e:
            logger.error(f"Failed to enhance summary: {e}")
            # Return original on failure
            return original_summary
    
    async def enhance_experience_bullets(
        self,
        bullets: List[str],
        job_description: Optional[str] = None,
        tone: str = "professional"
    ) -> List[str]:
        """
        Enhance experience bullet points with AI.
        
        Improves clarity, adds metrics, uses action verbs.
        
        Args:
            bullets: Original bullet points
            job_description: Optional job description for tailoring
            tone: Desired tone
            
        Returns:
            Enhanced bullet points
        """
        try:
            if not bullets:
                return bullets
            
            prompt = self._build_bullets_prompt(bullets, job_description, tone)
            
            enhanced = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=500,
                temperature=0.6
            )
            
            # Parse enhanced bullets (one per line)
            enhanced_bullets = [
                line.strip().lstrip('•-*').strip()
                for line in enhanced.strip().split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            
            # Ensure we return same number of bullets
            if len(enhanced_bullets) != len(bullets):
                logger.warning(f"Bullet count mismatch: {len(enhanced_bullets)} vs {len(bullets)}")
                # Pad or truncate
                while len(enhanced_bullets) < len(bullets):
                    enhanced_bullets.append(bullets[len(enhanced_bullets)])
                enhanced_bullets = enhanced_bullets[:len(bullets)]
            
            logger.info(f"Successfully enhanced {len(bullets)} bullet points")
            return enhanced_bullets
            
        except Exception as e:
            logger.error(f"Failed to enhance bullets: {e}")
            return bullets
    
    async def enhance_project_description(
        self,
        project_name: str,
        description: str,
        technologies: List[str],
        highlights: List[str],
        job_description: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Enhance project description and highlights.
        
        Args:
            project_name: Project name
            description: Original description
            technologies: Technologies used
            highlights: Original highlights
            job_description: Optional job description
            
        Returns:
            Dict with enhanced description and highlights
        """
        try:
            prompt = self._build_project_prompt(
                project_name, description, technologies, highlights, job_description
            )
            
            enhanced = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=400,
                temperature=0.6
            )
            
            # Parse response (expecting description followed by highlights)
            lines = [l.strip() for l in enhanced.strip().split('\n') if l.strip()]
            
            enhanced_desc = description
            enhanced_highlights = highlights
            
            # Simple parsing: first line is description, rest are highlights
            if lines:
                enhanced_desc = lines[0].strip()
                enhanced_highlights = [
                    line.lstrip('•-*').strip()
                    for line in lines[1:]
                    if line and not line.startswith('#')
                ]
            
            logger.info(f"Successfully enhanced project: {project_name}")
            return {
                "description": enhanced_desc,
                "highlights": enhanced_highlights or highlights
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance project: {e}")
            return {"description": description, "highlights": highlights}
    
    async def suggest_skills(
        self,
        experience: List[Experience],
        job_description: Optional[str] = None,
        existing_skills: List[str] = []
    ) -> List[str]:
        """
        Suggest additional skills based on experience and job description.
        
        Args:
            experience: User's work experience
            job_description: Optional job description
            existing_skills: Skills user already listed
            
        Returns:
            List of suggested skills (not including existing ones)
        """
        try:
            prompt = self._build_skills_prompt(experience, job_description, existing_skills)
            
            suggested = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=200,
                temperature=0.5
            )
            
            # Parse skills (comma-separated or line-separated)
            skills = []
            for line in suggested.strip().split('\n'):
                line = line.strip().lstrip('•-*').strip()
                if ',' in line:
                    skills.extend([s.strip() for s in line.split(',')])
                elif line and not line.startswith('#'):
                    skills.append(line)
            
            # Remove duplicates and existing skills
            existing_lower = [s.lower() for s in existing_skills]
            new_skills = [
                s for s in skills
                if s and s.lower() not in existing_lower
            ]
            
            logger.info(f"Suggested {len(new_skills)} new skills")
            return new_skills[:10]  # Limit to 10 suggestions
            
        except Exception as e:
            logger.error(f"Failed to suggest skills: {e}")
            return []
    
    async def tailor_content(
        self,
        content: str,
        job_description: str,
        content_type: str = "general"
    ) -> str:
        """
        Tailor content to match job description.
        
        Args:
            content: Original content
            job_description: Job description to tailor to
            content_type: Type of content (summary, bullet, project, etc.)
            
        Returns:
            Tailored content
        """
        try:
            prompt = f"""Tailor the following {content_type} to better match this job description.
Keep the core facts accurate but emphasize relevant skills and experience.

Job Description:
{job_description[:500]}

Original {content_type}:
{content}

Tailored {content_type}:"""
            
            tailored = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=300,
                temperature=0.6
            )
            
            logger.info(f"Successfully tailored {content_type}")
            return tailored.strip()
            
        except Exception as e:
            logger.error(f"Failed to tailor content: {e}")
            return content
    
    # Private helper methods for building prompts
    
    def _build_summary_prompt(
        self,
        summary: str,
        job_description: Optional[str],
        tone: str
    ) -> str:
        """Build prompt for summary enhancement."""
        base_prompt = f"""Enhance this professional summary to be more impactful and {tone}.
Use strong action verbs, quantify achievements where possible, and make it compelling.
Keep it concise (2-3 sentences).

Original summary:
{summary}

Enhanced summary:"""
        
        if job_description:
            base_prompt = f"""Enhance this professional summary to be more impactful and {tone}.
Tailor it to match the job description below.
Use strong action verbs, quantify achievements where possible, and make it compelling.
Keep it concise (2-3 sentences).

Job Description:
{job_description[:300]}...

Original summary:
{summary}

Enhanced summary:"""
        
        return base_prompt
    
    def _build_bullets_prompt(
        self,
        bullets: List[str],
        job_description: Optional[str],
        tone: str
    ) -> str:
        """Build prompt for bullet enhancement."""
        bullets_text = '\n'.join(f"• {b}" for b in bullets)
        
        base_prompt = f"""Enhance these resume bullet points to be more impactful and {tone}.
Rules:
- Start with strong action verbs
- Add metrics/numbers where possible
- Be specific and concrete
- Keep each bullet to 1-2 lines
- Return exactly {len(bullets)} bullets

Original bullets:
{bullets_text}

Enhanced bullets:"""
        
        if job_description:
            base_prompt = f"""Enhance these resume bullet points to be more impactful and {tone}.
Tailor them to match the job description below.
Rules:
- Start with strong action verbs
- Add metrics/numbers where possible
- Highlight skills mentioned in job description
- Be specific and concrete
- Keep each bullet to 1-2 lines
- Return exactly {len(bullets)} bullets

Job Description:
{job_description[:300]}...

Original bullets:
{bullets_text}

Enhanced bullets:"""
        
        return base_prompt
    
    def _build_project_prompt(
        self,
        name: str,
        description: str,
        technologies: List[str],
        highlights: List[str],
        job_description: Optional[str]
    ) -> str:
        """Build prompt for project enhancement."""
        tech_str = ', '.join(technologies)
        highlights_str = '\n'.join(f"• {h}" for h in highlights)
        
        prompt = f"""Enhance this project description and highlights to be more impressive.

Project: {name}
Technologies: {tech_str}

Original description:
{description}

Original highlights:
{highlights_str}

Provide:
1. Enhanced description (1-2 sentences)
2. Enhanced highlights (one per line, starting with •)

Enhanced version:"""
        
        if job_description:
            prompt = f"""Enhance this project description and highlights to be more impressive.
Tailor it to match the job description below.

Job Description:
{job_description[:200]}...

Project: {name}
Technologies: {tech_str}

Original description:
{description}

Original highlights:
{highlights_str}

Provide:
1. Enhanced description (1-2 sentences)
2. Enhanced highlights (one per line, starting with •)

Enhanced version:"""
        
        return prompt
    
    def _build_skills_prompt(
        self,
        experience: List[Experience],
        job_description: Optional[str],
        existing_skills: List[str]
    ) -> str:
        """Build prompt for skills suggestion."""
        exp_summary = '\n'.join([
            f"• {exp.title} at {exp.company}"
            for exp in experience[:3]  # Limit to recent 3
        ])
        
        existing_str = ', '.join(existing_skills)
        
        prompt = f"""Based on this work experience, suggest 5-10 additional relevant skills.
Do not include skills already listed.

Work Experience:
{exp_summary}

Already listed skills:
{existing_str}

Suggested additional skills (one per line):"""
        
        if job_description:
            prompt = f"""Based on this work experience and job description, suggest 5-10 additional relevant skills.
Focus on skills mentioned in the job description that match the experience.
Do not include skills already listed.

Job Description:
{job_description[:300]}...

Work Experience:
{exp_summary}

Already listed skills:
{existing_str}

Suggested additional skills (one per line):"""
        
        return prompt


# Singleton instance
_ai_enhancer = None


def get_ai_enhancer() -> AIEnhancementService:
    """Get AI enhancement service instance."""
    global _ai_enhancer
    if _ai_enhancer is None:
        _ai_enhancer = AIEnhancementService()
    return _ai_enhancer
