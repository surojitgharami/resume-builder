# app/services/ocr.py
import logging
from typing import Optional
from io import BytesIO
from PIL import Image
import pdf2image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except (ImportError, OSError) as e:
    TESSERACT_AVAILABLE = False
    import warnings
    warnings.warn(f"Tesseract not available: {e}. OCR will be disabled.")

from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRServiceUnavailable(Exception):
    """Exception raised when OCR service is not available or misconfigured."""
    
    def __init__(self, message: str, provider: str = None, suggestion: str = None):
        self.message = message
        self.provider = provider
        self.suggestion = suggestion
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert exception to dictionary for API responses."""
        result = {"error": "OCR service unavailable", "message": self.message}
        if self.provider:
            result["provider"] = self.provider
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


class OCRService:
    """Service for extracting text from images and PDFs using OCR."""
    
    def __init__(self):
        self.provider = settings.OCR_PROVIDER
        self._availability_checked = False
        self._availability_error = None
        
        if self.provider == "tesseract" and not TESSERACT_AVAILABLE:
            logger.warning("Tesseract not available, OCR will be disabled")
            self.provider = None
            self._availability_error = OCRServiceUnavailable(
                message="Tesseract OCR is not installed or binary not found",
                provider="tesseract",
                suggestion="Install Tesseract: https://github.com/tesseract-ocr/tesseract or set OCR_PROVIDER=none to disable"
            )
    
    def _check_provider_availability(self):
        """Check if the configured OCR provider is available and properly configured."""
        if self._availability_checked:
            if self._availability_error:
                raise self._availability_error
            return
        
        self._availability_checked = True
        
        if not self.provider or self.provider == "none":
            self._availability_error = OCRServiceUnavailable(
                message="No OCR provider configured",
                provider="none",
                suggestion="Set OCR_PROVIDER environment variable to: tesseract, google_vision, aws_textract, or azure_vision"
            )
            raise self._availability_error
        
        if self.provider == "tesseract":
            if not TESSERACT_AVAILABLE:
                self._availability_error = OCRServiceUnavailable(
                    message="Tesseract OCR is not installed or binary not found",
                    provider="tesseract",
                    suggestion="Install Tesseract: https://github.com/tesseract-ocr/tesseract or use a different OCR_PROVIDER"
                )
                raise self._availability_error
            
            # Verify tesseract binary is actually executable
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                self._availability_error = OCRServiceUnavailable(
                    message=f"Tesseract binary check failed: {str(e)}",
                    provider="tesseract",
                    suggestion="Ensure Tesseract is installed and in PATH, or set OCR_PROVIDER to a different service"
                )
                raise self._availability_error
        
        elif self.provider == "google_vision":
            if not settings.GOOGLE_VISION_CREDENTIALS:
                self._availability_error = OCRServiceUnavailable(
                    message="Google Vision API credentials not configured",
                    provider="google_vision",
                    suggestion="Set GOOGLE_VISION_CREDENTIALS environment variable with path to credentials JSON file"
                )
                raise self._availability_error
        
        elif self.provider == "aws_textract":
            if not settings.AWS_TEXTRACT_REGION:
                self._availability_error = OCRServiceUnavailable(
                    message="AWS Textract region not configured",
                    provider="aws_textract",
                    suggestion="Set AWS_TEXTRACT_REGION and ensure AWS credentials are configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
                )
                raise self._availability_error
        
        elif self.provider == "azure_vision":
            if not settings.AZURE_VISION_KEY or not settings.AZURE_VISION_ENDPOINT:
                self._availability_error = OCRServiceUnavailable(
                    message="Azure Vision API credentials not fully configured",
                    provider="azure_vision",
                    suggestion="Set both AZURE_VISION_KEY and AZURE_VISION_ENDPOINT environment variables"
                )
                raise self._availability_error
        
        else:
            self._availability_error = OCRServiceUnavailable(
                message=f"Unknown OCR provider: {self.provider}",
                provider=self.provider,
                suggestion="Valid providers are: tesseract, google_vision, aws_textract, azure_vision"
            )
            raise self._availability_error
    
    def is_available(self) -> bool:
        """Check if OCR service is available without raising an exception."""
        try:
            self._check_provider_availability()
            return True
        except OCRServiceUnavailable:
            return False
    
    def get_availability_status(self) -> dict:
        """Get detailed availability status information."""
        try:
            self._check_provider_availability()
            return {
                "available": True,
                "provider": self.provider,
                "message": f"OCR service is available using {self.provider}"
            }
        except OCRServiceUnavailable as e:
            return {
                "available": False,
                "provider": e.provider,
                "message": e.message,
                "suggestion": e.suggestion
            }
    
    async def extract_text_from_image(self, image_data: bytes) -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            image_data: Image file as bytes
            
        Returns:
            Extracted text
            
        Raises:
            OCRServiceUnavailable: If OCR service is not available or misconfigured
            Exception: If OCR processing fails
        """
        # Check provider availability first
        self._check_provider_availability()
        
        if self.provider == "tesseract":
            return await self._tesseract_extract_image(image_data)
        elif self.provider == "google_vision":
            return await self._google_vision_extract(image_data)
        elif self.provider == "aws_textract":
            return await self._aws_textract_extract(image_data)
        elif self.provider == "azure_vision":
            return await self._azure_vision_extract(image_data)
        else:
            raise OCRServiceUnavailable(
                message="No OCR provider configured",
                suggestion="Set OCR_PROVIDER environment variable"
            )
    
    async def extract_text_from_pdf(self, pdf_data: bytes) -> str:
        """
        Extract text from a PDF using OCR.
        Converts PDF pages to images first, then applies OCR.
        
        Args:
            pdf_data: PDF file as bytes
            
        Returns:
            Extracted text from all pages
            
        Raises:
            OCRServiceUnavailable: If OCR service is not available or misconfigured
            Exception: If OCR processing fails
        """
        # Check provider availability first
        self._check_provider_availability()
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_bytes(pdf_data)
            
            all_text = []
            for i, image in enumerate(images):
                logger.info(f"Processing PDF page {i + 1}/{len(images)}")
                
                # Convert PIL Image to bytes
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Extract text from image
                text = await self.extract_text_from_image(img_bytes)
                all_text.append(text)
            
            return "\n\n--- Page Break ---\n\n".join(all_text)
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise Exception(f"PDF OCR failed: {str(e)}")
    
    async def _tesseract_extract_image(self, image_data: bytes) -> str:
        """Extract text using Tesseract OCR."""
        try:
            image = Image.open(BytesIO(image_data))
            text = pytesseract.image_to_string(image)
            logger.info("Successfully extracted text using Tesseract")
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            raise Exception(f"Tesseract OCR failed: {str(e)}")
    
    async def _google_vision_extract(self, image_data: bytes) -> str:
        """Extract text using Google Cloud Vision API."""
        try:
            from google.cloud import vision
            
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=image_data)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                return texts[0].description
            return ""
            
        except Exception as e:
            logger.error(f"Google Vision OCR failed: {e}")
            raise Exception(f"Google Vision OCR failed: {str(e)}")
    
    async def _aws_textract_extract(self, image_data: bytes) -> str:
        """Extract text using AWS Textract."""
        try:
            import boto3
            
            textract = boto3.client(
                'textract',
                region_name=settings.AWS_TEXTRACT_REGION
            )
            
            response = textract.detect_document_text(
                Document={'Bytes': image_data}
            )
            
            text_lines = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f"AWS Textract OCR failed: {e}")
            raise Exception(f"AWS Textract OCR failed: {str(e)}")
    
    async def _azure_vision_extract(self, image_data: bytes) -> str:
        """Extract text using Azure Computer Vision."""
        try:
            from azure.cognitiveservices.vision.computervision import ComputerVisionClient
            from msrest.authentication import CognitiveServicesCredentials
            
            credentials = CognitiveServicesCredentials(settings.AZURE_VISION_KEY)
            client = ComputerVisionClient(settings.AZURE_VISION_ENDPOINT, credentials)
            
            # Call API
            read_response = client.read_in_stream(BytesIO(image_data), raw=True)
            operation_location = read_response.headers["Operation-Location"]
            operation_id = operation_location.split("/")[-1]
            
            # Wait for result
            import time
            while True:
                result = client.get_read_result(operation_id)
                if result.status.lower() not in ['notstarted', 'running']:
                    break
                time.sleep(1)
            
            # Extract text
            text_lines = []
            if result.status.lower() == 'succeeded':
                for text_result in result.analyze_result.read_results:
                    for line in text_result.lines:
                        text_lines.append(line.text)
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            logger.error(f"Azure Vision OCR failed: {e}")
            raise Exception(f"Azure Vision OCR failed: {str(e)}")


# Global OCR service instance
ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    """Dependency to get OCR service instance."""
    return ocr_service
