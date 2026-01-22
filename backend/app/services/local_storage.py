# app/services/local_storage.py
"""
Local filesystem storage service for development.

This service provides S3-compatible storage interface using local filesystem,
allowing development without AWS credentials. Files are stored in local_storage/
directory with the same structure as S3.

Usage:
    - Development: Set USE_LOCAL_STORAGE=true in .env
    - Production: Use S3StorageService with proper credentials

Features:
    - Drop-in replacement for S3StorageService
    - Same interface (upload, download, delete, exists)
    - Persistent storage across restarts
    - No cloud credentials needed
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LocalStorageService:
    """
    Local filesystem storage service mimicking S3 interface.
    
    Files are stored in: local_storage/{object_path}
    Metadata is stored in: local_storage/.metadata/{object_path}.meta
    """
    
    def __init__(self, storage_dir: str = "local_storage"):
        """
        Initialize local storage service.
        
        Args:
            storage_dir: Base directory for file storage (default: local_storage)
        """
        self.storage_dir = Path(storage_dir)
        self.metadata_dir = self.storage_dir / ".metadata"
        
        # Create directories if they don't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        self.bucket = "local"  # Mimics S3 bucket name
        
        logger.info(f"Local storage initialized at: {self.storage_dir.absolute()}")
    
    async def upload_file(
        self,
        file_data: bytes,
        object_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload file to local storage.
        
        Args:
            file_data: File content as bytes
            object_path: Path where file should be stored (e.g., "resumes/user123/file.pdf")
            content_type: MIME type of file
            metadata: Optional metadata dictionary
            
        Returns:
            str: Local URL to the file (e.g., "/local_storage/resumes/user123/file.pdf")
            
        Raises:
            Exception: If file write fails
        """
        try:
            # Create full path
            file_path = self.storage_dir / object_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'wb') as f:
                if isinstance(file_data, bytes):
                    f.write(file_data)
                else:
                    # Handle file-like objects
                    shutil.copyfileobj(file_data, f)
            
            # Store metadata if provided
            if metadata or content_type:
                meta_path = self.metadata_dir / f"{object_path}.meta"
                meta_path.parent.mkdir(parents=True, exist_ok=True)
                
                meta_info = {
                    "content_type": content_type,
                    "metadata": metadata or {},
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "size": file_path.stat().st_size
                }
                
                import json
                with open(meta_path, 'w') as f:
                    json.dump(meta_info, f, indent=2)
            
            # Return local URL (mimics S3 URL structure)
            local_url = f"/local_storage/{object_path}"
            logger.info(f"File uploaded to local storage: {object_path}")
            
            return local_url
        
        except Exception as e:
            logger.error(f"Failed to upload file to local storage: {object_path}, error: {e}")
            raise Exception(f"Local storage upload failed: {str(e)}") from e
    
    async def download_file(self, object_path: str) -> bytes:
        """
        Download file from local storage.
        
        Args:
            object_path: Path to file
            
        Returns:
            bytes: File content
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            file_path = self.storage_dir / object_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found in local storage: {object_path}")
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logger.info(f"File downloaded from local storage: {object_path}")
            return content
        
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download file from local storage: {object_path}, error: {e}")
            raise Exception(f"Local storage download failed: {str(e)}") from e
    
    async def delete_file(self, object_path: str) -> bool:
        """
        Delete file from local storage.
        
        Args:
            object_path: Path to file
            
        Returns:
            bool: True if deleted, False if file didn't exist
        """
        try:
            file_path = self.storage_dir / object_path
            meta_path = self.metadata_dir / f"{object_path}.meta"
            
            deleted = False
            
            # Delete file
            if file_path.exists():
                file_path.unlink()
                deleted = True
            
            # Delete metadata
            if meta_path.exists():
                meta_path.unlink()
            
            if deleted:
                logger.info(f"File deleted from local storage: {object_path}")
            
            return deleted
        
        except Exception as e:
            logger.error(f"Failed to delete file from local storage: {object_path}, error: {e}")
            return False
    
    async def file_exists(self, object_path: str) -> bool:
        """
        Check if file exists in local storage.
        
        Args:
            object_path: Path to file
            
        Returns:
            bool: True if file exists
        """
        file_path = self.storage_dir / object_path
        return file_path.exists()
    
    async def get_file_metadata(self, object_path: str) -> Dict[str, Any]:
        """
        Get file metadata.
        
        Args:
            object_path: Path to file
            
        Returns:
            dict: Metadata including size, content_type, etc.
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.storage_dir / object_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {object_path}")
        
        # Load stored metadata if available
        meta_path = self.metadata_dir / f"{object_path}.meta"
        if meta_path.exists():
            import json
            with open(meta_path, 'r') as f:
                return json.load(f)
        
        # Return basic metadata from file stats
        stats = file_path.stat()
        return {
            "size": stats.st_size,
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "content_type": "application/octet-stream"
        }
    
    async def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 3600,
        content_disposition: Optional[str] = None
    ) -> str:
        """
        Generate a presigned URL (local equivalent).
        
        For local storage, this just returns the local URL.
        In a real deployment with a web server, you'd generate a temporary token.
        
        Args:
            object_path: Path to file
            expiration: Expiration time in seconds (ignored for local)
            content_disposition: Content-Disposition header (ignored for local)
            
        Returns:
            str: Local URL to file
        """
        if not await self.file_exists(object_path):
            raise FileNotFoundError(f"File not found: {object_path}")
        
        # In local development, return direct path
        # In production with local storage, implement token-based access
        return f"/local_storage/{object_path}"
    
    async def list_files(self, prefix: str = "") -> list:
        """
        List files with given prefix.
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            list: List of file paths
        """
        try:
            prefix_path = self.storage_dir / prefix if prefix else self.storage_dir
            
            if not prefix_path.exists():
                return []
            
            files = []
            for file_path in prefix_path.rglob("*"):
                if file_path.is_file() and ".metadata" not in str(file_path):
                    rel_path = file_path.relative_to(self.storage_dir)
                    files.append(str(rel_path))
            
            return sorted(files)
        
        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []
    
    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """
        Clean up old files from local storage.
        
        Args:
            max_age_days: Maximum age of files to keep
            
        Returns:
            int: Number of files deleted
        """
        import time
        
        deleted_count = 0
        max_age_seconds = max_age_days * 24 * 3600
        current_time = time.time()
        
        try:
            for file_path in self.storage_dir.rglob("*"):
                if file_path.is_file() and ".metadata" not in str(file_path):
                    file_age = current_time - file_path.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        deleted_count += 1
                        
                        # Also delete metadata
                        rel_path = file_path.relative_to(self.storage_dir)
                        meta_path = self.metadata_dir / f"{rel_path}.meta"
                        if meta_path.exists():
                            meta_path.unlink()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files from local storage")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return deleted_count


# Singleton instance
_local_storage_service: Optional[LocalStorageService] = None


def get_local_storage_service() -> LocalStorageService:
    """
    Get or create singleton local storage service.
    
    Returns:
        LocalStorageService: Singleton instance
    """
    global _local_storage_service
    
    if _local_storage_service is None:
        _local_storage_service = LocalStorageService()
    
    return _local_storage_service
