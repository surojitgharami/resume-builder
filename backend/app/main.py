# app/main.py
# CRITICAL: Fix for Python 3.13 on Windows - Must be set BEFORE any asyncio operations
# Forced reload trigger 3
import sys
import asyncio
if sys.platform == 'win32' and sys.version_info >= (3, 13):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uuid
import os

from app.core.config import settings
from app.core.logging import setup_logging, set_request_id
from app.core.metrics import PrometheusMiddleware, metrics_endpoint
from app.api.v1 import auth

# Initialize structured logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    enable_sentry=bool(settings.SENTRY_DSN and settings.SENTRY_DSN.strip()),
    sentry_dsn=settings.SENTRY_DSN
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="AI Resume Builder API",
    version="1.0.0",
    description="Production-ready AI-powered resume builder using Llama 3.3-70B",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Mount local storage for development/local mode
if settings.ENVIRONMENT == "development" or getattr(settings, 'USE_LOCAL_STORAGE', False):
    os.makedirs("local_storage", exist_ok=True)
    app.mount("/local_storage", StaticFiles(directory="local_storage"), name="local_storage")
    logger.info("Mounted /local_storage for serving uploaded files")

# Configure CORS - MUST be added before other middleware
# This ensures CORS headers are sent with ALL responses, including errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600  # Cache preflight requests for 1 hour
)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)


@app.middleware("http")
async def ensure_cors_headers(request: Request, call_next):
    """
    Ensure CORS headers are added to ALL responses, including errors.
    This middleware runs AFTER CORSMiddleware but ensures headers are present.
    """
    # Handle preflight requests
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response
    
    response = await call_next(request)
    
    # Get origin from request
    origin = request.headers.get("origin")
    
    # Check if origin is allowed
    if origin and origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request for tracing."""
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    try:
        response = await call_next(request)
    except HTTPException:
        # Re-raise FastAPI exceptions so default handler deals with them
        raise
    except Exception as exc:
        # Handle client disconnects gracefully
        if isinstance(exc, RuntimeError) and str(exc) == "No response returned.":
            logger.warning(f"Client disconnected during request processing {request.url}")
            return JSONResponse(status_code=499, content={"detail": "Client Closed Request"})

        # Handle any other unhandled exceptions
        logger.exception(f"Unhandled exception in middleware for {request.url}: {exc}")
        

        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
        # Still add security headers to error response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
    
    # Add security headers to successful responses
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "ai-resume-builder"
    }


# Metrics endpoint
@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format
    """
    return metrics_endpoint()


# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# Import other routers
from app.api.v1 import register, resumes, resumes_v2, upload, ingest, profile, users

app.include_router(register.router, prefix="/api/v1", tags=["Registration"])
app.include_router(resumes.router, prefix="/api/v1", tags=["Resumes - Legacy"])
app.include_router(resumes_v2.router, prefix="/api/v1", tags=["Resumes - V2"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])


@app.on_event("startup")
async def startup_event():
    """
    Initialize resources on application startup.
    
    CRITICAL: MongoDB Atlas connection is REQUIRED.
    Application will fail to start if MongoDB is not accessible.
    """
    logger.info("=" * 60)
    logger.info("AI Resume Builder API - Starting Up")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
    
    # Initialize MongoDB Atlas connection (REQUIRED - will raise exception on failure)
    from app.db.mongo import connect_to_mongo, create_indexes
    
    logger.info("Initializing MongoDB Atlas connection (required)...")
    try:
        await connect_to_mongo()
        logger.info("✓ MongoDB Atlas connection established")
    except Exception as e:
        logger.critical("✗ MongoDB Atlas connection FAILED")
        logger.critical(f"Error: {str(e)}")
        logger.critical("=" * 60)
        logger.critical("APPLICATION STARTUP ABORTED")
        logger.critical("=" * 60)
        # Re-raise to stop application startup
        raise RuntimeError("Cannot start application without MongoDB Atlas") from e
    
    # Create database indexes (required for proper operation)
    logger.info("Creating database indexes...")
    try:
        await create_indexes()
        logger.info("✓ Database indexes created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create indexes: {e}")
        logger.error("Application will start but database operations may fail")
        # Don't fail startup for index creation - they might already exist
    
    # Initialize Redis connection for rate limiting (optional)
    from app.middleware.rate_limit import rate_limiter
    logger.info("Connecting to Redis for rate limiting (optional)...")
    redis_connected = await rate_limiter.connect()
    if redis_connected:
        logger.info("✓ Connected to Redis for rate limiting")
    else:
        logger.warning("⚠ Using in-memory rate limiting (Redis unavailable)")
        logger.warning("  For production, configure Redis using REDIS_URL environment variable")
    
    logger.info("=" * 60)
    logger.info("✓ Application startup complete")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Application shutting down")
    
    # Close database connections
    from app.db.mongo import close_mongo_connection
    await close_mongo_connection()
    
    # Close Redis connections
    from app.middleware.rate_limit import rate_limiter
    try:
        await rate_limiter.close()
    except Exception as e:
        logger.warning(f"Failed to close Redis connection: {e}")
    
    # Close Playwright browser
    try:
        from app.services.pdf_playwright import cleanup_playwright_service
        await cleanup_playwright_service()
    except Exception as e:
        logger.warning(f"Failed to close Playwright browser: {e}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
