# app/services/pdf_playwright.py
"""
Playwright-based PDF generation service for AI Resume Builder.

This service uses Playwright's Chromium browser to generate high-quality PDFs
from HTML content. It's production-ready and works on Windows, Linux, Docker,
and cloud platforms like Render.

Key Features:
- Async/await for non-blocking operations
- Automatic browser lifecycle management
- Unique temporary file names (prevents conflicts)
- Automatic cleanup on success and failure
- A4 format with professional styling
- Secure file handling
"""

import asyncio
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# Fix for Windows + Python 3.13 asyncio event loop issue with Playwright
# This resolves the NotImplementedError when creating subprocesses
if sys.platform == 'win32':
    # Set the event loop policy to use ProactorEventLoop instead of SelectorEventLoop
    # This is required for subprocess operations on Windows with Python 3.8+
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Define dummy types when Playwright not available
    Browser = None
    Page = None

logger = logging.getLogger(__name__)

# Global browser instance (reused across requests for performance)
_browser: Optional[Browser] = None
_browser_lock = asyncio.Lock()


class PDFGenerationError(Exception):
    """Exception raised when PDF generation fails."""
    pass


class PlaywrightPDFService:
    """
    Production-ready PDF generation service using Playwright.
    
    Usage:
        service = PlaywrightPDFService()
        pdf_path = await service.generate_pdf_from_html(html_content, filename="resume.pdf")
    """
    
    def __init__(self, temp_dir: str = "temp_pdfs"):
        """
        Initialize PDF service.
        
        Args:
            temp_dir: Directory for temporary PDF files (default: temp_pdfs)
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Playwright PDF service initialized. Temp dir: {self.temp_dir}")
    
    async def _ensure_browser(self) -> Browser:
        """
        Ensure browser instance is running (lazy initialization).
        
        Uses singleton pattern with async lock to prevent multiple browser instances.
        
        Returns:
            Browser: Running Playwright browser instance
            
        Raises:
            RuntimeError: If Playwright is not installed
        """
        global _browser
        
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright is not installed. "
                "Install with: pip install playwright && playwright install chromium"
            )
        
        async with _browser_lock:
            if _browser is None or not _browser.is_connected():
                logger.info("Starting Playwright Chromium browser...")
                playwright = await async_playwright().start()
                _browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920x1080',
                    ]
                )
                logger.info("✓ Chromium browser started successfully")
        
        return _browser
    
    async def generate_pdf_from_html(
        self,
        html_content: str,
        filename: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate PDF from HTML content using Playwright.
        
        Args:
            html_content: HTML string to convert to PDF
            filename: Optional custom filename (default: auto-generated UUID)
            options: Optional PDF generation options (margins, format, etc.)
            
        Returns:
            str: Path to generated PDF file
            
        Raises:
            RuntimeError: If PDF generation fails
            
        Example:
            html = "<html><body><h1>Resume</h1></body></html>"
            pdf_path = await service.generate_pdf_from_html(html, "john_doe_resume.pdf")
        """
        # Generate unique filename if not provided
        if not filename:
            filename = f"resume_{uuid.uuid4().hex}.pdf"
        elif not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        pdf_path = self.temp_dir / filename
        
        # Default PDF options (A4 format, professional margins)
        pdf_options = {
            "path": str(pdf_path),
            "format": "A4",
            "print_background": True,
            "margin": {
                "top": "20mm",
                "right": "20mm",
                "bottom": "20mm",
                "left": "20mm"
            },
            "prefer_css_page_size": False,
        }
        
        # Merge custom options
        if options:
            pdf_options.update(options)
        
        page: Optional[Page] = None
        
        try:
            logger.info(f"Generating PDF: {filename}")
            
            # Get browser instance
            browser = await self._ensure_browser()
            
            # Create new page
            page = await browser.new_page()
            
            # Set viewport for consistent rendering
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Load HTML content
            await page.set_content(html_content, wait_until="networkidle")
            
            # Wait for any fonts or images to load
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.5)  # Additional buffer for rendering
            
            # Generate PDF
            await page.pdf(**pdf_options)
            
            logger.info(f"✓ PDF generated successfully: {pdf_path}")
            return str(pdf_path)
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            loop_type = str(type(asyncio.get_running_loop()))
            logger.error(f"Failed to generate PDF: {tb} Loop: {loop_type}")
            
            # Clean up failed PDF file
            if pdf_path.exists():
                pdf_path.unlink()
            
            raise RuntimeError(f"PDF generation failed: {str(e)} | Loop: {loop_type} | Trace: {tb}") from e
        
        finally:
            # Always close the page to prevent memory leaks
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Failed to close page: {e}")
    
    async def generate_pdf_from_url(
        self,
        url: str,
        filename: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate PDF from URL using Playwright.
        
        Args:
            url: URL to convert to PDF
            filename: Optional custom filename
            options: Optional PDF generation options
            
        Returns:
            str: Path to generated PDF file
        """
        if not filename:
            filename = f"resume_{uuid.uuid4().hex}.pdf"
        elif not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        pdf_path = self.temp_dir / filename
        
        pdf_options = {
            "path": str(pdf_path),
            "format": "A4",
            "print_background": True,
            "margin": {
                "top": "20mm",
                "right": "20mm",
                "bottom": "20mm",
                "left": "20mm"
            }
        }
        
        if options:
            pdf_options.update(options)
        
        page: Optional[Page] = None
        
        try:
            logger.info(f"Generating PDF from URL: {url}")
            
            browser = await self._ensure_browser()
            page = await browser.new_page()
            
            # Navigate to URL
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.5)
            
            # Generate PDF
            await page.pdf(**pdf_options)
            
            logger.info(f"✓ PDF generated from URL: {pdf_path}")
            return str(pdf_path)
        
        except Exception as e:
            logger.error(f"Failed to generate PDF from URL: {str(e)}")
            
            if pdf_path.exists():
                pdf_path.unlink()
            
            raise RuntimeError(f"PDF generation from URL failed: {str(e)}") from e
        
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Failed to close page: {e}")
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Delete a temporary PDF file.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            bool: True if deleted, False if file not found or error
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
            return False
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary PDF files.
        
        Args:
            max_age_hours: Maximum age of files to keep (default: 24 hours)
            
        Returns:
            int: Number of files deleted
        """
        import time
        
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for pdf_file in self.temp_dir.glob("*.pdf"):
                file_age = current_time - pdf_file.stat().st_mtime
                
                if file_age > max_age_seconds:
                    pdf_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {pdf_file.name}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old PDF files")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return deleted_count
    
    @staticmethod
    async def close_browser():
        """
        Close the global browser instance.
        
        Should be called on application shutdown.
        """
        global _browser
        
        if _browser:
            try:
                await _browser.close()
                logger.info("Playwright browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                _browser = None
    
    @staticmethod
    def is_available() -> bool:
        """
        Check if Playwright is available.
        
        Returns:
            bool: True if Playwright is installed
        """
        return PLAYWRIGHT_AVAILABLE


# Default HTML template for testing
DEFAULT_RESUME_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume</title>
    <style>
        @page {
            size: A4;
            margin: 0;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: white;
            padding: 20mm;
        }
        h1 {
            font-size: 32px;
            color: #2c3e50;
            margin-bottom: 10px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            font-size: 20px;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }
        h3 {
            font-size: 16px;
            color: #34495e;
            margin-top: 15px;
            margin-bottom: 5px;
        }
        p {
            margin-bottom: 10px;
        }
        .contact-info {
            margin-bottom: 20px;
            color: #7f8c8d;
        }
        .section {
            margin-bottom: 25px;
        }
        .experience-item, .education-item {
            margin-bottom: 15px;
        }
        .job-title {
            font-weight: bold;
            color: #2c3e50;
        }
        .company {
            color: #3498db;
        }
        .date {
            color: #95a5a6;
            font-style: italic;
        }
        ul {
            margin-left: 20px;
            margin-top: 5px;
        }
        li {
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
    {content}
</body>
</html>
"""


# Singleton instance
_pdf_service: Optional[PlaywrightPDFService] = None


def get_pdf_service() -> PlaywrightPDFService:
    """
    Get or create the singleton PDF service instance.
    
    Returns:
        PlaywrightPDFService: Singleton service instance
    """
    global _pdf_service
    
    if _pdf_service is None:
        _pdf_service = PlaywrightPDFService()
    
    return _pdf_service


# Alias for compatibility
def get_playwright_pdf_service() -> PlaywrightPDFService:
    """
    Alias for get_pdf_service() for backward compatibility.
    
    Returns:
        PlaywrightPDFService: Singleton service instance
    """
    return get_pdf_service()


async def cleanup_playwright_service():
    """
    Cleanup function to close the global browser instance.
    Should be called on application shutdown.
    """
    global _browser
    
    if _browser is not None:
        try:
            await _browser.close()
            logger.info("Playwright browser closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Playwright browser: {e}")
        finally:
            _browser = None
