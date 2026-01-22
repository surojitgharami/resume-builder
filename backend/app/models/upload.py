# app/models/upload.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    CERTIFICATE = "certificate"
    OTHER = "other"


class FileUpload(BaseModel):
    file_id: str
    user_id: str
    filename: str
    file_type: FileType
    file_size: int
    mime_type: str
    s3_key: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
    ocr_text: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    model_config = {
        "use_enum_values": True
    }


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    uploaded_at: datetime
    download_url: Optional[str] = None
    ocr_text: Optional[str] = None
