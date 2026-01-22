# app/services/optional_imports.py
"""
Safe imports for optional dependencies.
These dependencies are not required for core functionality.
"""
import logging

logger = logging.getLogger("app.services.optional_imports")


def try_import_llm():
    """Try to import LLM client. Returns None if unavailable."""
    try:
        from app.services.llm import LLMService
        return LLMService
    except Exception as e:
        logger.warning("LLMClient unavailable: %s. AI enhancements will be disabled.", e)
        return None


def try_import_pinecone():
    """Try to import Pinecone. Returns None if unavailable."""
    try:
        import pinecone  # type: ignore
        return pinecone
    except Exception as e:
        logger.info("Pinecone unavailable: %s (optional).", e)
        return None


def try_import_qdrant():
    """Try to import Qdrant client. Returns None if unavailable."""
    try:
        import qdrant_client  # type: ignore
        return qdrant_client
    except Exception as e:
        logger.info("Qdrant unavailable: %s (optional).", e)
        return None
