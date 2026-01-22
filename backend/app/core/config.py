# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import List, Optional, Union
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses pydantic-settings for validation and type conversion.
    """
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Security - JWT
    JWT_SECRET: str = "change-this-secret-key-in-production"
    JWT_ALGO: str = "HS256"  # Use RS256 in production
    RS_PRIVATE_KEY: Optional[str] = None
    RS_PUBLIC_KEY: Optional[str] = None
    RS_KID: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 300  # 5 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS - Can be a comma-separated string or list
    CORS_ORIGINS: Union[List[str], str] = "http://localhost:3000,http://localhost:5173"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            # Split by comma and strip whitespace AND trailing slashes
            return [origin.strip().rstrip('/') for origin in v.split(',') if origin.strip()]
        elif isinstance(v, list):
             # Ensure list items are also clean
            return [origin.strip().rstrip('/') for origin in v if isinstance(origin, str) and origin.strip()]
        return v
    
    # Database - MongoDB Atlas (REQUIRED)
    # No default value - MUST be provided via environment variable
    MONGO_URI: str = Field(..., description="MongoDB Atlas connection string (required)")
    MONGO_DB_NAME: str = "resume_builder"
    MONGO_MIN_POOL_SIZE: int = 10
    MONGO_MAX_POOL_SIZE: int = 100
    
    @field_validator('MONGO_URI')
    @classmethod
    def validate_mongo_uri(cls, v: str) -> str:
        """
        Validate MongoDB URI to prevent localhost fallbacks.
        Enforce MongoDB Atlas usage only.
        """
        if not v:
            raise ValueError("MONGO_URI is required and cannot be empty")
        
        # Block localhost URLs in production only
        v_lower = v.lower()
        if cls.__name__ == 'Settings':  # Check if we're in Settings class context
            from os import getenv
            environment = getenv('ENVIRONMENT', 'development')
            
            # Allow localhost only in development
            if environment == 'production' and any(host in v_lower for host in ['localhost', '127.0.0.1', '0.0.0.0']):
                raise ValueError(
                    "localhost MongoDB connections are not allowed in production. "
                    "Use MongoDB Atlas connection string: "
                    "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>"
                )
        
        # Enforce mongodb:// or mongodb+srv:// protocol
        if not (v.startswith('mongodb://') or v.startswith('mongodb+srv://')):
            raise ValueError(
                "MONGO_URI must start with 'mongodb://' or 'mongodb+srv://'. "
                "For Atlas, use: mongodb+srv://<username>:<password>@<cluster>.mongodb.net/"
            )
        
        # Recommend Atlas SRV format
        if v.startswith('mongodb://') and 'mongodb.net' not in v:
            import warnings
            warnings.warn(
                "Using mongodb:// protocol. For MongoDB Atlas, mongodb+srv:// is recommended.",
                UserWarning
            )
        
        return v
    
    # OpenRouter LLM
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MAX_CONCURRENCY: int = 5
    LLM_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1200
    
    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"  # openai, cohere, local
    OPENAI_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 768
    
    # Vector Store
    VECTOR_STORE_PROVIDER: str = "mongodb_atlas"  # mongodb_atlas, pinecone, weaviate, qdrant
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    WEAVIATE_URL: Optional[str] = None
    WEAVIATE_API_KEY: Optional[str] = None
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: Optional[str] = None
    
    # Object Storage - S3 / Local
    # Set USE_LOCAL_STORAGE=true for development without S3 credentials
    USE_LOCAL_STORAGE: bool = False
    
    # S3 Configuration (optional if USE_LOCAL_STORAGE=true)
    S3_ENDPOINT: str = "s3.amazonaws.com"
    S3_BUCKET: str = "resume-builder-storage"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-west-2"
    S3_USE_SSL: bool = True
    
    # OCR Service
    OCR_PROVIDER: str = "tesseract"  # tesseract, google_vision, aws_textract, azure_vision
    GOOGLE_VISION_CREDENTIALS: Optional[str] = None
    AWS_TEXTRACT_REGION: Optional[str] = None
    AZURE_VISION_ENDPOINT: Optional[str] = None
    AZURE_VISION_KEY: Optional[str] = None
    
    # PDF Generation
    PDF_ENGINE: str = "playwright"  # playwright (recommended), weasyprint, wkhtmltopdf
    PDF_UPLOAD_TO_S3: bool = True  # Upload PDFs to S3 (False = stream via FileResponse)
    
    # Redis (optional - for rate limiting and caching)
    REDIS_URL: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Celery Task Queue
    # CELERY_BROKER_URL: Broker URL (defaults to REDIS_URL if not set)
    # CELERY_TASK_ALWAYS_EAGER: Execute tasks synchronously (True for dev without Redis)
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_ALWAYS_EAGER: bool = False  # Set to True for dev without Redis
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW: int = 900  # 15 minutes
    RATE_LIMIT_RESUME_GENERATION: int = 10
    RATE_LIMIT_RESUME_WINDOW: int = 3600  # 1 hour
    
    # Observability
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_EXTENSIONS: Union[List[str], str] = ".pdf,.png,.jpg,.jpeg,.docx"
    
    @field_validator('ALLOWED_UPLOAD_EXTENSIONS', mode='before')
    @classmethod
    def parse_allowed_extensions(cls, v):
        """Parse ALLOWED_UPLOAD_EXTENSIONS from comma-separated string or list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency function to get settings instance.
    Useful for FastAPI dependency injection.
    """
    return settings
