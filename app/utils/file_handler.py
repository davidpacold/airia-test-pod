"""
Centralized file upload handling utilities.

This module provides standardized file processing logic to eliminate
duplication across endpoints and ensure consistent file handling.
"""

import base64
from typing import Optional, Dict, Any, List, Tuple
from fastapi import UploadFile
from dataclasses import dataclass

from ..exceptions import ValidationError, ErrorCode


@dataclass
class ProcessedFile:
    """Container for processed file information."""
    content: Any  # Can be str (text/base64) or bytes
    file_type: str
    extension: str
    size_bytes: int
    encoding: Optional[str] = None
    
    
class FileUploadHandler:
    """Centralized file processing logic for all endpoints."""
    
    # Supported file types by category
    TEXT_EXTENSIONS = {'txt', 'md', 'json', 'csv', 'log'}
    IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'}
    DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'pptx'}
    
    # File type categories for different use cases
    AI_MODEL_TYPES = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | {'pdf'}
    DOCUMENT_INTEL_TYPES = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS
    EMBEDDING_TYPES = TEXT_EXTENSIONS | {'pdf'}
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        Extract file extension from filename.
        
        Args:
            filename: The uploaded file's name
            
        Returns:
            Lowercase file extension without the dot
        """
        if not filename or '.' not in filename:
            return ''
        return filename.lower().split('.')[-1]
    
    @staticmethod
    async def validate_file_size(file: UploadFile, max_size_mb: int = 25) -> int:
        """
        Validate file size and return size in bytes.
        
        Args:
            file: The uploaded file
            max_size_mb: Maximum allowed size in megabytes
            
        Returns:
            File size in bytes
            
        Raises:
            ValidationError: If file exceeds size limit
        """
        # Get file size
        await file.seek(0, 2)  # Seek to end
        file_size = await file.tell()
        await file.seek(0)  # Reset to beginning
        
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValidationError(
                message=f"File too large (max {max_size_mb}MB)",
                error_code=ErrorCode.FILE_INVALID,
                field_name="file",
                provided_value=f"{file_size} bytes",
                remediation=f"Please upload a file smaller than {max_size_mb}MB"
            )
        
        return file_size
    
    @staticmethod
    def validate_file_type(extension: str, allowed_types: set) -> None:
        """
        Validate file extension against allowed types.
        
        Args:
            extension: File extension to validate
            allowed_types: Set of allowed file extensions
            
        Raises:
            ValidationError: If file type is not allowed
        """
        if not extension or extension not in allowed_types:
            allowed_list = ", ".join(sorted(allowed_types))
            raise ValidationError(
                message=f"File type not allowed. Supported types: {allowed_list}",
                error_code=ErrorCode.FILE_INVALID,
                field_name="file",
                provided_value=extension or "unknown",
                remediation=f"Please upload a file with one of these extensions: {allowed_list}"
            )
    
    @staticmethod
    async def process_text_file(content: bytes, extension: str) -> Tuple[str, str]:
        """
        Process text-based files.
        
        Args:
            content: Raw file content
            extension: File extension
            
        Returns:
            Tuple of (processed_content, file_type)
            
        Raises:
            ValidationError: If file cannot be decoded as UTF-8
        """
        try:
            text_content = content.decode('utf-8')
            return text_content, 'text'
        except UnicodeDecodeError:
            raise ValidationError(
                message="Text file must be UTF-8 encoded",
                error_code=ErrorCode.FILE_INVALID,
                field_name="file",
                remediation="Please ensure your text file is saved with UTF-8 encoding"
            )
    
    @staticmethod
    async def process_pdf_file(content: bytes) -> Tuple[str, str]:
        """
        Process PDF files by extracting text content.
        
        Args:
            content: Raw PDF content
            
        Returns:
            Tuple of (extracted_text, file_type)
            
        Raises:
            ValidationError: If PDF processing fails
        """
        try:
            from ..utils.file_processors import process_pdf
            text_content = process_pdf(content)
            return text_content, 'pdf'
        except Exception as e:
            raise ValidationError(
                message=f"Failed to process PDF: {str(e)}",
                error_code=ErrorCode.FILE_INVALID,
                field_name="file",
                remediation="Please ensure the PDF is not corrupted and try again"
            )
    
    @staticmethod
    async def process_image_file(content: bytes, extension: str) -> Tuple[str, str]:
        """
        Process image files by encoding as base64.
        
        Args:
            content: Raw image content
            extension: Image file extension
            
        Returns:
            Tuple of (base64_content, file_type)
            
        Raises:
            ValidationError: If image processing fails
        """
        try:
            base64_content = base64.b64encode(content).decode('utf-8')
            return base64_content, extension
        except Exception as e:
            raise ValidationError(
                message=f"Failed to process image: {str(e)}",
                error_code=ErrorCode.FILE_INVALID,
                field_name="file",
                remediation="Please ensure the image file is not corrupted and try again"
            )
    
    @classmethod
    async def process_upload(
        cls, 
        file: UploadFile, 
        allowed_types: set,
        max_size_mb: int = 25
    ) -> ProcessedFile:
        """
        Process uploaded file with validation and content extraction.
        
        Args:
            file: The uploaded file
            allowed_types: Set of allowed file extensions
            max_size_mb: Maximum file size in MB
            
        Returns:
            ProcessedFile object with processed content and metadata
            
        Raises:
            ValidationError: If file validation or processing fails
        """
        if not file:
            raise ValidationError(
                message="No file provided",
                error_code=ErrorCode.FILE_INVALID,
                field_name="file",
                remediation="Please select a file to upload"
            )
        
        # Extract file extension
        extension = cls.get_file_extension(file.filename or "")
        
        # Validate file type
        cls.validate_file_type(extension, allowed_types)
        
        # Validate file size
        file_size = await cls.validate_file_size(file, max_size_mb)
        
        # Read file content
        content = await file.read()
        await file.seek(0)  # Reset for potential future reads
        
        # Process based on file type
        processed_content = None
        file_type = None
        encoding = None
        
        if extension in cls.TEXT_EXTENSIONS:
            processed_content, file_type = await cls.process_text_file(content, extension)
            encoding = 'utf-8'
        elif extension == 'pdf':
            processed_content, file_type = await cls.process_pdf_file(content)
            encoding = 'utf-8'
        elif extension in cls.IMAGE_EXTENSIONS:
            processed_content, file_type = await cls.process_image_file(content, extension)
            encoding = 'base64'
        else:
            # For document types that don't need processing, return raw content
            processed_content = content
            file_type = extension
        
        return ProcessedFile(
            content=processed_content,
            file_type=file_type,
            extension=extension,
            size_bytes=file_size,
            encoding=encoding
        )
    
    @classmethod
    async def process_ai_model_upload(cls, file: Optional[UploadFile]) -> Optional[ProcessedFile]:
        """
        Process file upload for AI model endpoints (OpenAI, Llama).
        
        Args:
            file: Optional uploaded file
            
        Returns:
            ProcessedFile if file provided, None otherwise
        """
        if not file:
            return None
            
        return await cls.process_upload(
            file=file,
            allowed_types=cls.AI_MODEL_TYPES,
            max_size_mb=25
        )
    
    @classmethod 
    async def process_document_intel_upload(cls, file: UploadFile) -> ProcessedFile:
        """
        Process file upload for Document Intelligence endpoint.
        
        Args:
            file: Required uploaded file
            
        Returns:
            ProcessedFile with processed content
        """
        return await cls.process_upload(
            file=file,
            allowed_types=cls.DOCUMENT_INTEL_TYPES,
            max_size_mb=25
        )
    
    @classmethod
    async def process_embedding_upload(cls, file: Optional[UploadFile]) -> Optional[ProcessedFile]:
        """
        Process file upload for embedding endpoint.
        
        Args:
            file: Optional uploaded file
            
        Returns:
            ProcessedFile if file provided, None otherwise
        """
        if not file:
            return None
            
        return await cls.process_upload(
            file=file,
            allowed_types=cls.EMBEDDING_TYPES,
            max_size_mb=25
        )