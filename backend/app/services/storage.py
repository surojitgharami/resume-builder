# app/services/storage.py
"""
Storage service with S3 and local filesystem support.

This module provides a factory pattern to select between:
- S3StorageService: Production storage (AWS S3, Cloudflare R2, etc.)
- LocalStorageService: Development storage (local filesystem)

The factory automatically selects based on configuration:
- USE_LOCAL_STORAGE=true → Local storage
- USE_LOCAL_STORAGE=false + valid S3 credentials → S3 storage
- No S3 credentials → Falls back to local storage with warning

Usage:
    storage = get_storage_service()
    await storage.upload_file(data, "path/file.pdf")
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, BinaryIO, Union
import logging
from datetime import timedelta
import mimetypes

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """Service for interacting with S3-compatible storage."""
    
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=f"https://{settings.S3_ENDPOINT}" if settings.S3_USE_SSL else f"http://{settings.S3_ENDPOINT}",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )
        self.bucket = settings.S3_BUCKET
        
    async def upload_file(
        self,
        file_data: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3.
        
        Args:
            file_data: File data as binary stream
            object_key: S3 object key (path)
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
            
        Returns:
            S3 object key
            
        Raises:
            Exception: If upload fails
        """
        try:
            extra_args = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
            else:
                # Guess content type from filename
                content_type, _ = mimetypes.guess_type(object_key)
                if content_type:
                    extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.client.upload_fileobj(
                file_data,
                self.bucket,
                object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Successfully uploaded file to S3: {object_key}")
            return object_key
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise Exception(f"S3 upload failed: {str(e)}")
    
    async def download_file(self, object_key: str) -> bytes:
        """
        Download a file from S3.
        
        Args:
            object_key: S3 object key
            
        Returns:
            File content as bytes
            
        Raises:
            Exception: If download fails
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            content = response['Body'].read()
            logger.info(f"Successfully downloaded file from S3: {object_key}")
            return content
            
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise Exception(f"S3 download failed: {str(e)}")
    
    async def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            object_key: S3 object key
            
        Returns:
            True if successful
            
        Raises:
            Exception: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Successfully deleted file from S3: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise Exception(f"S3 deletion failed: {str(e)}")
    
    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        method: str = 'get_object',
        content_disposition: Optional[str] = None
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file.
        
        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            method: S3 method ('get_object' for download, 'put_object' for upload)
            content_disposition: Optional Content-Disposition header value
            
        Returns:
            Presigned URL
            
        Raises:
            Exception: If URL generation fails
        """
        try:
            params = {'Bucket': self.bucket, 'Key': object_key}
            
            # Add Content-Disposition if provided
            if content_disposition:
                params['ResponseContentDisposition'] = content_disposition
            
            url = self.client.generate_presigned_url(
                method,
                Params=params,
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {object_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise Exception(f"Presigned URL generation failed: {str(e)}")
    
    async def file_exists(self, object_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            object_key: S3 object key
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError:
            return False
    
    async def get_file_metadata(self, object_key: str) -> dict:
        """
        Get metadata for a file in S3.
        
        Args:
            object_key: S3 object key
            
        Returns:
            Dictionary with file metadata
            
        Raises:
            Exception: If metadata retrieval fails
        """
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise Exception(f"Failed to get metadata: {str(e)}")


# Storage service factory

_storage_service: Optional[Union[S3StorageService, 'LocalStorageService']] = None
_storage_initialized = False


def _is_s3_configured() -> bool:
    """
    Check if S3 credentials are properly configured.
    
    Returns:
        bool: True if S3 can be used, False otherwise
    """
    # Check if essential S3 settings are present
    if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
        logger.warning("S3 credentials not configured (S3_ACCESS_KEY or S3_SECRET_KEY missing)")
        return False
    
    if not settings.S3_BUCKET:
        logger.warning("S3 bucket not configured (S3_BUCKET missing)")
        return False
    
    if not settings.S3_ENDPOINT:
        logger.warning("S3 endpoint not configured (S3_ENDPOINT missing)")
        return False
    
    return True


def _initialize_storage_service() -> Union[S3StorageService, 'LocalStorageService']:
    """
    Initialize storage service based on configuration.
    
    Priority:
    1. If USE_LOCAL_STORAGE=true: Always use local storage
    2. If S3 credentials configured: Try S3 storage
    3. Fallback: Local storage with warning
    
    Returns:
        Storage service instance (S3 or Local)
    """
    # Check if local storage is explicitly requested
    use_local = getattr(settings, 'USE_LOCAL_STORAGE', False)
    
    if use_local:
        logger.info("Using local filesystem storage (USE_LOCAL_STORAGE=true)")
        from app.services.local_storage import LocalStorageService
        return LocalStorageService()
    
    # Try to use S3 if configured
    if _is_s3_configured():
        try:
            logger.info("Attempting to initialize S3 storage...")
            s3_service = S3StorageService()
            
            # Test S3 connection by listing bucket (doesn't require listing permissions)
            try:
                s3_service.client.head_bucket(Bucket=settings.S3_BUCKET)
                logger.info(f"✓ S3 storage initialized successfully (bucket: {settings.S3_BUCKET})")
                return s3_service
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if error_code == '403':
                    # Forbidden - credentials might be valid but no bucket access
                    logger.warning(f"S3 bucket access forbidden (403). Check bucket permissions.")
                    logger.info("Using S3 storage anyway (credentials appear valid)")
                    return s3_service
                elif error_code == '404':
                    logger.error(f"S3 bucket not found: {settings.S3_BUCKET}")
                    logger.warning("Falling back to local storage")
                else:
                    logger.error(f"S3 connection test failed: {e}")
                    logger.warning("Falling back to local storage")
            except NoCredentialsError:
                logger.error("S3 credentials are invalid")
                logger.warning("Falling back to local storage")
        
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage: {e}")
            logger.warning("Falling back to local storage")
    else:
        logger.warning("S3 not configured. Using local storage fallback.")
        logger.warning("For production, set: S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET, S3_ENDPOINT")
    
    # Fallback to local storage
    logger.info("Using local filesystem storage")
    from app.services.local_storage import LocalStorageService
    return LocalStorageService()


def get_storage_service() -> Union[S3StorageService, 'LocalStorageService']:
    """
    Get storage service instance (S3 or Local).
    
    This is a factory function that returns the appropriate storage service
    based on configuration. The service is initialized once and reused.
    
    Returns:
        Storage service instance with methods:
        - upload_file(file_data, object_path, content_type, metadata)
        - download_file(object_path)
        - delete_file(object_path)
        - file_exists(object_path)
        - get_file_metadata(object_path)
        - generate_presigned_url(object_path, expiration)
    
    Example:
        storage = get_storage_service()
        url = await storage.upload_file(pdf_data, "resumes/user123/resume.pdf")
    """
    global _storage_service, _storage_initialized
    
    if not _storage_initialized:
        _storage_service = _initialize_storage_service()
        _storage_initialized = True
    
    return _storage_service


def is_using_s3() -> bool:
    """
    Check if currently using S3 storage.
    
    Returns:
        bool: True if using S3, False if using local storage
    """
    service = get_storage_service()
    return isinstance(service, S3StorageService)


def get_storage_info() -> dict:
    """
    Get information about current storage configuration.
    
    Returns:
        dict: Storage type, bucket/directory, and status
    """
    service = get_storage_service()
    
    if isinstance(service, S3StorageService):
        return {
            "type": "s3",
            "bucket": service.bucket,
            "endpoint": settings.S3_ENDPOINT,
            "region": settings.S3_REGION,
            "configured": True
        }
    else:
        return {
            "type": "local",
            "directory": str(service.storage_dir.absolute()),
            "configured": True
        }


# Backwards compatibility
storage_service = None  # Deprecated: use get_storage_service() instead
