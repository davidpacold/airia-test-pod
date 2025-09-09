"""
File processing utilities for custom AI testing
Handles PDF text extraction and image processing
"""
from typing import Optional
import io
import base64
from PyPDF2 import PdfReader
from PIL import Image


def process_pdf(pdf_content: bytes) -> str:
    """
    Extract text content from PDF file
    
    Args:
        pdf_content: Raw PDF file bytes
        
    Returns:
        Extracted text content from PDF
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        # Create a PDF reader from bytes
        pdf_stream = io.BytesIO(pdf_content)
        reader = PdfReader(pdf_stream)
        
        # Extract text from all pages
        text_content = []
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text.strip():  # Only add pages with actual text
                    text_content.append(f"--- Page {page_num} ---\n{page_text}")
            except Exception as e:
                text_content.append(f"--- Page {page_num} ---\n[Error extracting text: {str(e)}]")
        
        if not text_content:
            return "[PDF contains no extractable text content]"
        
        full_text = "\n\n".join(text_content)
        
        # Add PDF metadata if available
        metadata_info = []
        if reader.metadata:
            if reader.metadata.get('/Title'):
                metadata_info.append(f"Title: {reader.metadata['/Title']}")
            if reader.metadata.get('/Author'):
                metadata_info.append(f"Author: {reader.metadata['/Author']}")
            if reader.metadata.get('/Subject'):
                metadata_info.append(f"Subject: {reader.metadata['/Subject']}")
        
        if metadata_info:
            metadata_str = "PDF Metadata:\n" + "\n".join(metadata_info) + "\n\n"
            full_text = metadata_str + full_text
        
        # Add document summary
        page_count = len(reader.pages)
        summary = f"PDF Document Summary:\n- Total Pages: {page_count}\n- Content Type: Text extraction\n\n"
        
        return summary + full_text
        
    except Exception as e:
        raise Exception(f"PDF processing failed: {str(e)}")


def process_image(image_content: bytes, file_extension: str) -> tuple[str, str]:
    """
    Process image file for AI model input
    
    Args:
        image_content: Raw image file bytes
        file_extension: File extension (jpg, jpeg, png)
        
    Returns:
        Tuple of (base64_encoded_image, image_info_text)
        
    Raises:
        Exception: If image processing fails
    """
    try:
        # Validate and get image info using PIL
        image_stream = io.BytesIO(image_content)
        with Image.open(image_stream) as img:
            # Get image information
            width, height = img.size
            mode = img.mode
            format_name = img.format
            
            # Create image info text
            image_info = f"""Image Information:
- Format: {format_name or file_extension.upper()}
- Dimensions: {width} x {height} pixels
- Color Mode: {mode}
- File Size: {len(image_content):,} bytes ({len(image_content) / (1024*1024):.2f} MB)
"""
        
        # Encode image as base64 for AI model
        base64_encoded = base64.b64encode(image_content).decode('utf-8')
        
        return base64_encoded, image_info
        
    except Exception as e:
        raise Exception(f"Image processing failed: {str(e)}")


def validate_file_size(content: bytes, max_size_mb: int = 25) -> None:
    """
    Validate file size limits
    
    Args:
        content: File content bytes
        max_size_mb: Maximum size in megabytes
        
    Raises:
        ValueError: If file exceeds size limit
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        actual_size_mb = len(content) / (1024 * 1024)
        raise ValueError(f"File too large: {actual_size_mb:.1f}MB (max: {max_size_mb}MB)")


def get_file_type_description(file_extension: str) -> str:
    """
    Get human-readable description of file type
    
    Args:
        file_extension: File extension
        
    Returns:
        Description of file type
    """
    descriptions = {
        'txt': 'Plain Text File',
        'md': 'Markdown File',
        'json': 'JSON Data File',
        'csv': 'CSV Data File',
        'log': 'Log File',
        'pdf': 'PDF Document',
        'jpg': 'JPEG Image',
        'jpeg': 'JPEG Image',
        'png': 'PNG Image'
    }
    return descriptions.get(file_extension.lower(), f"{file_extension.upper()} File")