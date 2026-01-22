# app/workers/worker_services.py
"""
Service factory for Celery workers.

Provides thread-safe service instances for worker processes.
Services are created per-worker-process (not per-task) for efficiency.
"""
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.llm import LLMService
from app.services.embeddings import EmbeddingsService
from app.services.pdf_generator import PDFGeneratorService
from app.services.storage import S3StorageService
from app.services.ocr import OCRService
from app.workers.celery_app import get_worker_db

logger = logging.getLogger(__name__)

# Global service instances (per worker process)
_llm_service: Optional[LLMService] = None
_embeddings_service: Optional[EmbeddingsService] = None
_pdf_service: Optional[PDFGeneratorService] = None
_storage_service: Optional[S3StorageService] = None
_ocr_service: Optional[OCRService] = None


def get_worker_llm_service() -> LLMService:
    """
    Get LLM service instance for worker.
    
    Creates one instance per worker process (thread-safe).
    """
    global _llm_service
    
    if _llm_service is None:
        from app.services.llm import llm_service
        _llm_service = llm_service
        logger.info("Initialized LLM service for worker")
    
    return _llm_service


def get_worker_embeddings_service() -> EmbeddingsService:
    """
    Get embeddings service instance for worker.
    
    Creates one instance per worker process (thread-safe).
    """
    global _embeddings_service
    
    if _embeddings_service is None:
        from app.services.embeddings import embeddings_service
        _embeddings_service = embeddings_service
        logger.info("Initialized embeddings service for worker")
    
    return _embeddings_service


def get_worker_pdf_service() -> PDFGeneratorService:
    """
    Get PDF generator service instance for worker.
    
    Creates one instance per worker process (thread-safe).
    """
    global _pdf_service
    
    if _pdf_service is None:
        from app.services.pdf_generator import pdf_generator_service
        _pdf_service = pdf_generator_service
        logger.info("Initialized PDF service for worker")
    
    return _pdf_service


def get_worker_storage_service() -> S3StorageService:
    """
    Get storage service instance for worker.
    
    Creates one instance per worker process (thread-safe).
    """
    global _storage_service
    
    if _storage_service is None:
        from app.services.storage import storage_service
        _storage_service = storage_service
        logger.info("Initialized storage service for worker")
    
    return _storage_service


def get_worker_ocr_service() -> OCRService:
    """
    Get OCR service instance for worker.
    
    Creates one instance per worker process (thread-safe).
    """
    global _ocr_service
    
    if _ocr_service is None:
        from app.services.ocr import ocr_service
        _ocr_service = ocr_service
        logger.info("Initialized OCR service for worker")
    
    return _ocr_service


def reset_worker_services():
    """
    Reset all worker services.
    
    Useful for testing or worker process recycling.
    """
    global _llm_service, _embeddings_service, _pdf_service, _storage_service, _ocr_service
    
    _llm_service = None
    _embeddings_service = None
    _pdf_service = None
    _storage_service = None
    _ocr_service = None
    
    logger.info("Reset all worker services")
