# app/core/health_checks.py
"""
Health checks for external dependencies and services.

Provides runtime validation and helpful error messages for:
- OCR services (Tesseract, Google Vision, AWS Textract, Azure)
- PDF generation (WeasyPrint)
- Vector stores (MongoDB Atlas, Pinecone, Qdrant)
- LLM services (OpenRouter)
- Storage (S3)
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceHealthCheck:
    """Health check results for a service."""
    
    def __init__(self, name: str, available: bool, message: str, details: Optional[Dict] = None):
        self.name = name
        self.available = available
        self.message = message
        self.details = details or {}
        self.checked_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "status": "healthy" if self.available else "unavailable",
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat()
        }


async def check_ocr_service() -> ServiceHealthCheck:
    """Check OCR service availability using the OCR service's built-in health checks."""
    from app.services.ocr import get_ocr_service
    
    try:
        ocr_service = get_ocr_service()
        status_info = ocr_service.get_availability_status()
        
        details = {
            "provider": status_info.get('provider')
        }
        
        if status_info.get('suggestion'):
            details["suggestion"] = status_info['suggestion']
        
        # For tesseract, try to get version info if available
        if status_info['available'] and status_info.get('provider') == 'tesseract':
            try:
                import pytesseract
                version = pytesseract.get_tesseract_version()
                details["version"] = str(version)
            except Exception:
                pass
        
        return ServiceHealthCheck(
            name="OCR",
            available=status_info['available'],
            message=status_info['message'],
            details=details
        )
    except Exception as e:
        logger.exception("Error checking OCR service health")
        return ServiceHealthCheck(
            name="OCR",
            available=False,
            message=f"Error checking OCR service: {str(e)}",
            details={"error": str(e)}
        )


async def check_pdf_generation() -> ServiceHealthCheck:
    """Check PDF generation service availability."""
    from app.core.config import settings
    
    engine = settings.PDF_ENGINE
    
    if not engine or engine == "none":
        return ServiceHealthCheck(
            name="PDF Generation",
            available=False,
            message="PDF generation not configured. Set PDF_ENGINE in environment.",
            details={"engine": "none", "suggestion": "Set PDF_ENGINE to weasyprint"}
        )
    
    if engine == "weasyprint":
        try:
            from weasyprint import HTML
            # Try a simple test
            HTML(string="<p>Test</p>")
            return ServiceHealthCheck(
                name="PDF Generation",
                available=True,
                message="WeasyPrint PDF generation available",
                details={"engine": "weasyprint"}
            )
        except (ImportError, OSError) as e:
            return ServiceHealthCheck(
                name="PDF Generation",
                available=False,
                message="WeasyPrint not available (requires GTK libraries on Windows)",
                details={
                    "engine": "weasyprint",
                    "error": str(e),
                    "suggestion": "Use Docker (Linux) or deploy on Linux server. JSON format is available as fallback."
                }
            )
    
    return ServiceHealthCheck(
        name="PDF Generation",
        available=False,
        message=f"Unknown PDF engine: {engine}",
        details={"engine": engine}
    )


async def check_llm_service() -> ServiceHealthCheck:
    """Check LLM service availability."""
    from app.core.config import settings
    
    api_key = settings.OPENROUTER_API_KEY
    
    if not api_key:
        return ServiceHealthCheck(
            name="LLM",
            available=False,
            message="OpenRouter API key not configured",
            details={"suggestion": "Set OPENROUTER_API_KEY in environment. Get key from: https://openrouter.ai/keys"}
        )
    
    return ServiceHealthCheck(
        name="LLM",
        available=True,
        message=f"OpenRouter LLM configured (model: {settings.LLM_MODEL})",
        details={"model": settings.LLM_MODEL, "provider": "openrouter"}
    )


async def check_embeddings_service() -> ServiceHealthCheck:
    """Check embeddings service availability."""
    from app.core.config import settings
    
    provider = settings.EMBEDDING_PROVIDER
    
    if provider == "openai":
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return ServiceHealthCheck(
                name="Embeddings",
                available=False,
                message="OpenAI API key not configured",
                details={"provider": "openai", "suggestion": "Set OPENAI_API_KEY or use EMBEDDING_PROVIDER=local"}
            )
        return ServiceHealthCheck(
            name="Embeddings",
            available=True,
            message=f"OpenAI embeddings configured (model: {settings.EMBEDDING_MODEL})",
            details={"provider": "openai", "model": settings.EMBEDDING_MODEL}
        )
    
    elif provider == "cohere":
        api_key = getattr(settings, 'COHERE_API_KEY', None)
        if not api_key:
            return ServiceHealthCheck(
                name="Embeddings",
                available=False,
                message="Cohere API key not configured",
                details={"provider": "cohere", "suggestion": "Set COHERE_API_KEY or use EMBEDDING_PROVIDER=local"}
            )
        return ServiceHealthCheck(
            name="Embeddings",
            available=True,
            message="Cohere embeddings configured",
            details={"provider": "cohere"}
        )
    
    elif provider == "local":
        return ServiceHealthCheck(
            name="Embeddings",
            available=True,
            message=f"Local embeddings configured (model: {settings.EMBEDDING_MODEL})",
            details={"provider": "local", "model": settings.EMBEDDING_MODEL, "note": "Downloads model on first use"}
        )
    
    return ServiceHealthCheck(
        name="Embeddings",
        available=False,
        message=f"Unknown embeddings provider: {provider}",
        details={"provider": provider}
    )


async def check_storage_service() -> ServiceHealthCheck:
    """Check S3 storage service availability."""
    from app.core.config import settings
    
    if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
        return ServiceHealthCheck(
            name="Storage",
            available=False,
            message="S3 credentials not configured",
            details={"suggestion": "Set S3_ACCESS_KEY and S3_SECRET_KEY in environment"}
        )
    
    return ServiceHealthCheck(
        name="Storage",
        available=True,
        message=f"S3 storage configured (bucket: {settings.S3_BUCKET})",
        details={"bucket": settings.S3_BUCKET, "endpoint": settings.S3_ENDPOINT}
    )


async def check_vector_store() -> ServiceHealthCheck:
    """Check vector store availability."""
    from app.core.config import settings
    
    provider = settings.VECTOR_STORE_PROVIDER
    
    if provider == "mongodb_atlas":
        return ServiceHealthCheck(
            name="Vector Store",
            available=True,
            message="MongoDB Atlas Vector Search configured",
            details={"provider": "mongodb_atlas", "note": "Ensure vector index is created in Atlas UI"}
        )
    
    elif provider == "pinecone":
        api_key = getattr(settings, 'PINECONE_API_KEY', None)
        if not api_key:
            return ServiceHealthCheck(
                name="Vector Store",
                available=False,
                message="Pinecone API key not configured",
                details={"provider": "pinecone", "suggestion": "Set PINECONE_API_KEY and PINECONE_ENVIRONMENT"}
            )
        return ServiceHealthCheck(
            name="Vector Store",
            available=True,
            message="Pinecone configured",
            details={"provider": "pinecone"}
        )
    
    elif provider == "qdrant":
        url = getattr(settings, 'QDRANT_URL', 'http://localhost:6333')
        return ServiceHealthCheck(
            name="Vector Store",
            available=True,
            message="Qdrant configured",
            details={"provider": "qdrant", "url": url}
        )
    
    return ServiceHealthCheck(
        name="Vector Store",
        available=False,
        message=f"Unknown vector store provider: {provider}",
        details={"provider": provider}
    )


async def check_database() -> ServiceHealthCheck:
    """Check MongoDB database availability."""
    try:
        from app.db.mongo import get_database
        db = await anext(get_database())
        
        # Try to ping database
        await db.command("ping")
        
        return ServiceHealthCheck(
            name="Database",
            available=True,
            message="MongoDB connected",
            details={"status": "connected"}
        )
    except Exception as e:
        return ServiceHealthCheck(
            name="Database",
            available=False,
            message="MongoDB connection failed",
            details={"error": str(e), "suggestion": "Check MONGO_URI in environment"}
        )


async def check_redis() -> ServiceHealthCheck:
    """Check Redis availability."""
    from app.core.config import settings
    
    if not settings.REDIS_URL:
        return ServiceHealthCheck(
            name="Redis",
            available=False,
            message="Redis not configured (using in-memory fallback)",
            details={"suggestion": "Set REDIS_URL for distributed rate limiting", "impact": "Rate limiting will use in-memory fallback"}
        )
    
    try:
        import redis.asyncio as redis
        client = redis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.close()
        
        return ServiceHealthCheck(
            name="Redis",
            available=True,
            message="Redis connected",
            details={"url": settings.REDIS_URL.split('@')[-1] if '@' in settings.REDIS_URL else settings.REDIS_URL}
        )
    except Exception as e:
        return ServiceHealthCheck(
            name="Redis",
            available=False,
            message="Redis connection failed (using in-memory fallback)",
            details={"error": str(e), "impact": "Rate limiting will use in-memory fallback"}
        )


async def get_all_health_checks() -> Dict[str, ServiceHealthCheck]:
    """
    Run all health checks and return results.
    
    Returns:
        Dictionary of service name to health check result
    """
    checks = {}
    
    # Required services
    checks["database"] = await check_database()
    checks["llm"] = await check_llm_service()
    checks["embeddings"] = await check_embeddings_service()
    checks["storage"] = await check_storage_service()
    
    # Optional services
    checks["ocr"] = await check_ocr_service()
    checks["pdf_generation"] = await check_pdf_generation()
    checks["vector_store"] = await check_vector_store()
    checks["redis"] = await check_redis()
    
    return checks


async def get_health_summary() -> Dict[str, Any]:
    """
    Get summary of all health checks.
    
    Returns:
        Dictionary with overall health status and individual checks
    """
    checks = await get_all_health_checks()
    
    # Count available services
    total = len(checks)
    available = sum(1 for check in checks.values() if check.available)
    
    # Determine overall status
    required_services = ["database", "llm", "embeddings", "storage"]
    required_available = all(checks[svc].available for svc in required_services if svc in checks)
    
    overall_status = "healthy" if required_available else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {name: check.to_dict() for name, check in checks.items()},
        "summary": {
            "total_services": total,
            "available_services": available,
            "unavailable_services": total - available,
            "required_services_ok": required_available
        }
    }
