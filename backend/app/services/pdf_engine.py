# app/services/pdf_engine.py
"""
PDF engine helper. Prefer Playwright; fall back to WeasyPrint if available.
Expose a simple API:
- get_preferred_engine() -> "playwright"|"weasyprint"|None
- is_available() -> bool
- render_html_to_pdf_bytes(html: str) -> bytes   # raises exceptions on failure
"""

import logging
from typing import Optional

logger = logging.getLogger("app.services.pdf_engine")

# Safe imports
_PLAYWRIGHT_AVAILABLE = False
_WEASYPRINT_AVAILABLE = False

try:
    # Playwright sync API import
    from playwright.sync_api import sync_playwright  # type: ignore
    _PLAYWRIGHT_AVAILABLE = True
except Exception as e:
    logger.debug("Playwright import failed: %s", e)
    _PLAYWRIGHT_AVAILABLE = False

try:
    import weasyprint  # type: ignore
    _WEASYPRINT_AVAILABLE = True
except Exception as e:
    # Quietly fail if WeasyPrint is not installed (expected in many envs)
    logger.debug("WeasyPrint import failed (optional): %s", e)
    _WEASYPRINT_AVAILABLE = False


def get_preferred_engine() -> Optional[str]:
    if _PLAYWRIGHT_AVAILABLE:
        return "playwright"
    if _WEASYPRINT_AVAILABLE:
        return "weasyprint"
    return None


def is_available() -> bool:
    return get_preferred_engine() is not None


def render_html_to_pdf_bytes(html: str, timeout_seconds: int = 30) -> bytes:
    """
    Render HTML to PDF bytes using the preferred engine.
    Raise RuntimeError on failure.
    """
    engine = get_preferred_engine()
    if engine is None:
        raise RuntimeError("No PDF engine available")

    if engine == "playwright":
        try:
            # Use sync playwright to produce PDF bytes
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.set_content(html, timeout=timeout_seconds * 1000)
                # produce pdf into bytes by writing to a temporary file
                # playwright's page.pdf only writes to disk, so we use bytes via file read
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as tmp:
                    tmp_path = tmp.name
                
                page.pdf(path=tmp_path, format="A4")
                browser.close()
                
                # Read bytes and cleanup
                with open(tmp_path, "rb") as f:
                    data = f.read()
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return data
        except Exception as e:
            logger.exception("Playwright PDF render failed: %s", e)
            raise RuntimeError(f"Playwright PDF render failed: {e}") from e

    if engine == "weasyprint":
        try:
            # simple usage of weasyprint
            from weasyprint import HTML  # type: ignore
            pdf = HTML(string=html).write_pdf()
            return pdf
        except Exception as e:
            logger.exception("WeasyPrint PDF render failed: %s", e)
            raise RuntimeError(f"WeasyPrint PDF render failed: {e}") from e

    raise RuntimeError("Unsupported PDF engine")
