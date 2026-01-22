# app/services/pdf_generator.py
"""
PDF Generation Service for AI Resume Builder.

This service provides a unified interface for PDF generation,
supporting multiple engines (Playwright, WeasyPrint).

Default engine: Playwright (production-ready, cross-platform)
Fallback: WeasyPrint (if Playwright unavailable)
"""

import logging
from typing import Optional
from pathlib import Path

# Handle WeasyPrint import safely to avoid startup noise
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

from app.core.config import settings
from app.models.resume import Resume

# Import Playwright service
try:
    from app.services.pdf_playwright import get_pdf_service, PLAYWRIGHT_AVAILABLE
except ImportError as e:
    import logging
    logging.getLogger(__name__).error(f"Failed to import Playwright service: {e}")
    PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFGeneratorService:
    """
    Unified PDF generation service supporting multiple engines.
    
    Engine Priority:
    1. Playwright (default, production-ready)
    2. WeasyPrint (fallback)
    """
    
    def __init__(self):
        # Determine which PDF engine to use
        self.engine = self._select_engine()
        logger.info(f"PDF Generator initialized with engine: {self.engine}")
    
    def _select_engine(self) -> Optional[str]:
        """
        Select the best available PDF engine.
        
        Returns:
            str: Engine name ('playwright', 'weasyprint', or None)
        """
        # Check for explicit engine setting
        preferred_engine = getattr(settings, 'PDF_ENGINE', 'playwright')
        
        # Try Playwright first (recommended)
        if preferred_engine == 'playwright' or preferred_engine is None:
            if PLAYWRIGHT_AVAILABLE:
                return 'playwright'
            else:
                logger.warning("Playwright not available, checking alternatives...")
        
        # Fallback to WeasyPrint
        if preferred_engine == 'weasyprint' or not PLAYWRIGHT_AVAILABLE:
            if WEASYPRINT_AVAILABLE:
                logger.info("Using WeasyPrint for PDF generation")
                return 'weasyprint'
            else:
                logger.debug("WeasyPrint not available")
        
        # No engine available
        logger.warning("No PDF generation engine available! PDF features will be disabled.")
        return None
    
    def is_available(self) -> bool:
        """
        Check if PDF generation is available.
        
        Returns:
            bool: True if any PDF engine is available
        """
        return self.engine is not None
    
    async def generate_pdf(self, resume: Resume, filename: Optional[str] = None) -> str:
        """
        Generate a PDF from resume data.
        
        Args:
            resume: Resume object with sections
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
            
        Raises:
            RuntimeError: If PDF generation fails or no engine available
        """
        if not self.is_available():
            raise RuntimeError(
                "PDF generation is not available. "
                "Install Playwright: pip install playwright && playwright install chromium"
            )
        
        # Generate HTML from resume
        html_content = self._generate_html(resume)
        
        # Generate PDF using selected engine
        if self.engine == 'playwright':
            return await self._playwright_generate(html_content, filename)
        elif self.engine == 'weasyprint':
            return await self._weasyprint_generate(html_content, filename)
        else:
            raise RuntimeError("No PDF engine configured")
    
    async def generate_pdf_from_html(self, html_content: str, filename: Optional[str] = None) -> str:
        """
        Generate a PDF from HTML content.
        
        Args:
            html_content: HTML string
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
        """
        if not self.is_available():
            raise RuntimeError("PDF generation is not available")
        
        if self.engine == 'playwright':
            return await self._playwright_generate(html_content, filename)
        elif self.engine == 'weasyprint':
            return await self._weasyprint_generate(html_content, filename)
        else:
            raise RuntimeError("No PDF engine configured")
    
    async def _playwright_generate(self, html_content: str, filename: Optional[str] = None) -> str:
        """
        Generate PDF using Playwright.
        
        Args:
            html_content: HTML string
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
        """
        try:
            pdf_service = get_pdf_service()
            pdf_path = await pdf_service.generate_pdf_from_html(html_content, filename)
            logger.info(f"PDF generated successfully using Playwright: {pdf_path}")
            return pdf_path
        except Exception as e:
            logger.error(f"Playwright PDF generation failed: {str(e)}")
            raise RuntimeError(f"PDF generation failed: {str(e)}") from e
    
    async def _weasyprint_generate(self, html_content: str, filename: Optional[str] = None) -> str:
        """
        Generate PDF using WeasyPrint (fallback).
        
        Args:
            html_content: HTML string
            filename: Optional custom filename
            
        Returns:
            str: Path to generated PDF file
        """
        import uuid
        
        try:
            if not filename:
                filename = f"resume_{uuid.uuid4().hex}.pdf"
            elif not filename.endswith('.pdf'):
                filename = f"{filename}.pdf"
            
            # Create temp directory if it doesn't exist
            temp_dir = Path("temp_pdfs")
            temp_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = temp_dir / filename
            
            # Generate PDF
            from weasyprint import HTML
            html = HTML(string=html_content)
            html.write_pdf(str(pdf_path))
            
            logger.info(f"Successfully generated PDF using WeasyPrint: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {e}")
            raise RuntimeError(f"PDF generation failed: {str(e)}") from e
    
    def _generate_html(self, resume: Resume) -> str:
        """Generate HTML content for the resume."""
        sections_html = ""
        
        for section in sorted(resume.sections, key=lambda s: s.order):
            sections_html += f"""
            <div class="section">
                <h2 class="section-title">{self._escape_html(section.title)}</h2>
                <div class="section-content">
                    {self._format_content(section.content)}
                </div>
            </div>
            """
        
        color_scheme = resume.template_preferences.color_scheme or "blue"
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Resume</title>
        </head>
        <body class="resume-{color_scheme}">
            <div class="container">
                {sections_html}
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_css(self, resume: Resume) -> str:
        """Generate CSS styling for the resume."""
        font_family = resume.template_preferences.font_family or "Arial"
        color_scheme = resume.template_preferences.color_scheme or "blue"
        
        # Color schemes
        colors = {
            "blue": {"primary": "#2563eb", "secondary": "#1e40af", "accent": "#dbeafe"},
            "green": {"primary": "#059669", "secondary": "#047857", "accent": "#d1fae5"},
            "purple": {"primary": "#7c3aed", "secondary": "#6d28d9", "accent": "#ede9fe"},
            "red": {"primary": "#dc2626", "secondary": "#b91c1c", "accent": "#fee2e2"},
            "gray": {"primary": "#4b5563", "secondary": "#374151", "accent": "#f3f4f6"},
        }
        
        scheme = colors.get(color_scheme, colors["blue"])
        
        css = f"""
        @page {{
            size: letter;
            margin: 0.75in;
        }}
        
        body {{
            font-family: {font_family}, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #1f2937;
            margin: 0;
            padding: 0;
        }}
        
        .container {{
            max-width: 100%;
        }}
        
        .section {{
            margin-bottom: 1.5em;
            page-break-inside: avoid;
        }}
        
        .section-title {{
            font-size: 14pt;
            font-weight: bold;
            color: {scheme['primary']};
            border-bottom: 2px solid {scheme['primary']};
            padding-bottom: 0.25em;
            margin-bottom: 0.5em;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .section-content {{
            margin-top: 0.5em;
        }}
        
        .section-content p {{
            margin: 0.5em 0;
        }}
        
        .section-content ul {{
            margin: 0.5em 0;
            padding-left: 1.5em;
        }}
        
        .section-content li {{
            margin: 0.25em 0;
        }}
        
        h3 {{
            font-size: 12pt;
            font-weight: bold;
            color: {scheme['secondary']};
            margin: 0.75em 0 0.25em 0;
        }}
        
        h4 {{
            font-size: 11pt;
            font-weight: bold;
            color: #4b5563;
            margin: 0.5em 0 0.25em 0;
        }}
        
        .date {{
            color: #6b7280;
            font-style: italic;
        }}
        
        a {{
            color: {scheme['primary']};
            text-decoration: none;
        }}
        
        strong {{
            font-weight: 600;
            color: #111827;
        }}
        """
        
        return css
    
    def _format_content(self, content: str) -> str:
        """Format plain text content to HTML with proper line breaks and lists."""
        lines = content.split('\n')
        formatted_lines = []
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                formatted_lines.append('<br>')
                continue
            
            # Check if line is a bullet point
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                if not in_list:
                    formatted_lines.append('<ul>')
                    in_list = True
                # Remove bullet and add list item
                cleaned_line = line[1:].strip()
                formatted_lines.append(f'<li>{self._escape_html(cleaned_line)}</li>')
            else:
                if in_list:
                    formatted_lines.append('</ul>')
                    in_list = False
                formatted_lines.append(f'<p>{self._escape_html(line)}</p>')
        
        if in_list:
            formatted_lines.append('</ul>')
        
        return '\n'.join(formatted_lines)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


# Global PDF generator service instance
pdf_generator_service = PDFGeneratorService()


def get_pdf_generator_service() -> PDFGeneratorService:
    """Dependency to get PDF generator service instance."""
    return pdf_generator_service
