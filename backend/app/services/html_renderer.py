# app/services/html_renderer.py
"""
HTML rendering service using Jinja2 templates.
"""
import logging
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


class HTMLRendererService:
    """Service for rendering HTML from resume data using Jinja2 templates."""
    
    def __init__(self, template_dir: str = None):
        """
        Initialize HTML renderer with template directory.
        
        Args:
            template_dir: Path to template directory. Defaults to app/templates
        """
        if template_dir is None:
            # Default to app/templates directory
            app_dir = Path(__file__).parent.parent
            template_dir = str(app_dir / "templates")
        
        self.template_dir = template_dir
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        logger.info(f"HTML renderer initialized with template_dir={template_dir}")
    
    def render_resume(self, snapshot: Dict[str, Any], template_name: str = "resume_template.html") -> str:
        """
        Render resume HTML from snapshot data.
        
        Args:
            snapshot: Resume data snapshot (ResumeDraft as dict)
            template_name: Template file name
            
        Returns:
            Rendered HTML string
            
        Raises:
            Exception: If rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            
            # Extract fields from snapshot
            profile_data = snapshot.get('profile', {})
            
            # ADAPTER: Transform flat profile (ResumeDraft) to nested structure (Legacy Template)
            # The template expects profile.contact.email, etc.
            # But ResumeDraft has profile.email directly.
            profile_wrapper = {
                "full_name": profile_data.get("full_name"),
                "summary": profile_data.get("summary"),
                "awards": profile_data.get("awards", []),
                "languages": profile_data.get("languages", []),
                "interests": profile_data.get("interests", []),
                "contact": {
                    "email": profile_data.get("email"),
                    "phone": profile_data.get("phone"),
                    "location": profile_data.get("location"),
                    "linkedin": profile_data.get("linkedin"),
                    "github": profile_data.get("github"),
                    "website": profile_data.get("website"),  # Website/Portfolio
                    "portfolio": profile_data.get("website") # Alias for compatibility
                }
            }
            
            experience = snapshot.get('experience', [])
            education = snapshot.get('education', [])
            skills = snapshot.get('skills', {})
            projects = snapshot.get('projects', [])
            
            # DEBUG logging
            logger.info(f"Rendering resume with profile keys: {list(profile_wrapper.keys())}")
            if 'contact' in profile_wrapper:
                 logger.info(f"Contact keys: {list(profile_wrapper['contact'].keys())}")
            else:
                 logger.error("CRITICAL: 'contact' key MISSING from profile_wrapper")
            
            # Render template
            html_content = template.render(
                profile=profile_wrapper,
                experience=experience,
                education=education,
                skills=skills,
                projects=projects
            )
            
            logger.info(f"Successfully rendered resume HTML (length={len(html_content)})")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to render HTML: {e}", exc_info=True)
            raise Exception(f"HTML rendering failed: {str(e)}")


def get_html_renderer_service() -> HTMLRendererService:
    """Get singleton HTML renderer service instance."""
    if not hasattr(get_html_renderer_service, '_instance'):
        get_html_renderer_service._instance = HTMLRendererService()
    return get_html_renderer_service._instance
