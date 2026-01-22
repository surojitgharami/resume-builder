# app/services/llm.py
import logging
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenRouter LLM API."""
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.api_url = settings.OPENROUTER_URL
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.max_concurrency = settings.OPENROUTER_MAX_CONCURRENCY
    
    def is_available(self) -> bool:
        """
        Check if LLM service is available and configured.
        
        Returns:
            True if service is ready to use, False otherwise
        """
        try:
            return bool(self.api_key and self.api_url and self.model)
        except Exception:
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (overrides default)
            max_tokens: Maximum tokens to generate (overrides default)
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
            
        Raises:
            Exception: If API call fails
        """
        if not self.api_key:
            raise Exception("OpenRouter API key not configured")
        
        # Prepare messages
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        formatted_messages.extend(messages)
        
        # Prepare request payload
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://resume-builder.app",  # Optional
                        "X-Title": "AI Resume Builder"  # Optional
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract completion
                completion = data['choices'][0]['message']['content']
                logger.info(f"LLM completion generated successfully")
                return completion
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise Exception(f"LLM generation failed: {str(e)}")
    
    async def generate_resume_section(
        self,
        section_name: str,
        job_description: str,
        user_data: Dict[str, Any],
        tone: str = "professional",
        context: Optional[str] = None
    ) -> str:
        """
        Generate a specific resume section tailored to a job description.
        
        Args:
            section_name: Name of the section (e.g., "Summary", "Experience")
            job_description: Target job description
            user_data: User's profile data
            tone: Writing tone (professional, technical, creative, casual)
            context: Optional additional context from RAG
            
        Returns:
            Generated section content
        """
        system_prompt = f"""You are an expert resume writer specializing in creating compelling, ATS-friendly resume content.
Your task is to write resume sections that are:
- Tailored to the specific job description
- Professional and impactful
- Quantifiable with metrics where possible
- Free of clichés and buzzwords
- Written in {tone} tone
- Formatted with bullet points where appropriate"""

        user_prompt = f"""Write the {section_name} section for a resume targeting this job:

JOB DESCRIPTION:
{job_description}

USER PROFILE DATA:
{json.dumps(user_data, indent=2)}
"""

        if context:
            user_prompt += f"\n\nADDITIONAL CONTEXT:\n{context}"
        
        user_prompt += f"""

Please write the {section_name} section that best matches the job requirements while highlighting the candidate's relevant experience and skills. Use bullet points for experience items. Keep it concise and impactful."""
        
        messages = [{"role": "user", "content": user_prompt}]
        
        return await self.generate_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=800
        )
    
    async def extract_resume_data(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract structured data from unstructured resume text using LLM.
        
        Args:
            resume_text: Raw resume text from OCR or file
            
        Returns:
            Structured resume data as dictionary
        """
        system_prompt = """You are an expert at extracting structured information from resumes.
Extract and organize the information into a structured JSON format."""

        user_prompt = f"""Extract all relevant information from this resume and format it as JSON with these fields:
- full_name
- contact (email, phone, location, linkedin, github, portfolio)
- summary
- skills (array of strings)
- experience (array with: title, company, location, start_date, end_date, description, achievements)
- education (array with: degree, institution, location, graduation_date, gpa, honors)
- certifications (array with: name, issuer, date, credential_id)
- projects (array with: name, description, technologies, link)

RESUME TEXT:
{resume_text}

Return only valid JSON, no other text."""
        
        messages = [{"role": "user", "content": user_prompt}]
        
        response = await self.generate_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.0,
            max_tokens=2000
        )
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            return data
        except Exception as e:
            logger.error(f"Failed to parse extracted resume data: {e}")
            raise Exception(f"Failed to parse resume data: {str(e)}")



# Global LLM service instance (may be None if not configured)
llm_service = None

try:
    llm_service = LLMService()
    if not llm_service.is_available():
        logger.warning("LLM service not properly configured (missing API key or URL). AI features will be disabled.")
        llm_service = None
    else:
        logger.info("LLM service initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize LLM service: {e}. AI features will be disabled.")
    llm_service = None


def get_llm_service() -> Optional[LLMService]:
    """
    Dependency to get LLM service instance.
    
    Returns:
        LLMService instance if available, None otherwise
    """
    return llm_service

