"""
Input sanitization utilities for preventing XSS and other security vulnerabilities.

This module provides utilities to sanitize user inputs across the application,
preventing common security vulnerabilities like XSS, injection attacks, and
malicious file uploads.
"""

import html
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile

# Try to import python-magic, fallback to basic validation
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


class InputSanitizer:
    """Centralized input sanitization utilities"""

    # Allowed HTML tags for rich text (if needed)
    ALLOWED_HTML_TAGS = []  # Start with none - plain text only

    # Dangerous patterns to remove/escape
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript URLs
        r"vbscript:",  # VBScript URLs
        r"on\w+\s*=",  # Event handlers (onclick, onload, etc.)
        r"<iframe[^>]*>.*?</iframe>",  # Iframes
        r"<object[^>]*>.*?</object>",  # Object tags
        r"<embed[^>]*>.*?</embed>",  # Embed tags
    ]

    # File type validation using magic numbers
    ALLOWED_FILE_SIGNATURES = {
        "pdf": [b"%PDF"],
        "txt": [b"", b"\xff\xfe", b"\xfe\xff"],  # Plain text, UTF-16 LE/BE
        "docx": [b"PK\x03\x04"],  # Office documents (ZIP-based)
        "xlsx": [b"PK\x03\x04"],
        "pptx": [b"PK\x03\x04"],
        "png": [b"\x89PNG\r\n\x1a\n"],
        "jpg": [b"\xff\xd8\xff"],
        "jpeg": [b"\xff\xd8\xff"],
        "gif": [b"GIF8"],
    }

    @staticmethod
    def sanitize_text_input(text: str) -> str:
        """
        Sanitize text input to prevent XSS and other attacks.

        Args:
            text: Raw text input from user

        Returns:
            Sanitized text safe for processing and display
        """
        if not text:
            return text

        # HTML escape to prevent XSS
        sanitized = html.escape(text, quote=True)

        # Remove dangerous patterns
        for pattern in InputSanitizer.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Remove null bytes and control characters (except newlines and tabs)
        sanitized = "".join(
            char for char in sanitized if ord(char) >= 32 or char in "\n\t\r"
        )

        # Limit length to prevent DoS
        if len(sanitized) > 10000:  # 10KB limit for text inputs
            sanitized = sanitized[:10000]

        return sanitized.strip()

    @staticmethod
    def sanitize_prompt_input(prompt: str, max_length: int = 4000) -> str:
        """
        Sanitize AI prompt input with specific rules for prompts.

        Args:
            prompt: User's AI prompt
            max_length: Maximum allowed length

        Returns:
            Sanitized prompt
        """
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        # Basic sanitization
        sanitized = InputSanitizer.sanitize_text_input(prompt)

        # Apply prompt-specific length limits
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        # Ensure minimum viable prompt
        if len(sanitized.strip()) < 3:
            raise HTTPException(
                status_code=400, detail="Prompt too short (minimum 3 characters)"
            )

        return sanitized

    @staticmethod
    def sanitize_credentials(username: str, password: str) -> tuple[str, str]:
        """
        Sanitize login credentials.

        Args:
            username: Username input
            password: Password input

        Returns:
            Tuple of (sanitized_username, sanitized_password)
        """
        # Username sanitization - more restrictive
        if not username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")

        # Remove dangerous characters from username
        sanitized_username = re.sub(r'[<>"\';\\]', "", username)
        sanitized_username = sanitized_username.strip()[:50]  # Limit username length

        if not sanitized_username:
            raise HTTPException(status_code=400, detail="Invalid username format")

        # Password - don't modify but validate
        if not password or len(password) < 1:
            raise HTTPException(status_code=400, detail="Password cannot be empty")

        return sanitized_username, password

    @staticmethod
    async def validate_file_upload(
        file: UploadFile, max_size_mb: int = 10
    ) -> Dict[str, Any]:
        """
        Validate and sanitize file uploads.

        Args:
            file: Uploaded file
            max_size_mb: Maximum file size in MB

        Returns:
            Dictionary with file validation info
        """
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        # Read first chunk to check file signature
        file_content = await file.read(1024)  # Read first 1KB
        await file.seek(0)  # Reset file pointer

        # Check file size - read all content to get size
        # (FastAPI UploadFile doesn't support seek with whence parameter)
        all_content = await file.read()
        file_size = len(all_content)
        await file.seek(0)  # Reset to beginning

        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=413, detail=f"File too large. Maximum size: {max_size_mb}MB"
            )

        # Validate file extension
        filename = file.filename or ""
        file_ext = filename.split(".")[-1].lower() if "." in filename else ""

        if not file_ext or file_ext not in InputSanitizer.ALLOWED_FILE_SIGNATURES:
            allowed_types = ", ".join(InputSanitizer.ALLOWED_FILE_SIGNATURES.keys())
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Supported types: {allowed_types}",
            )

        # Validate file signature (magic numbers)
        file_valid = False
        for signature in InputSanitizer.ALLOWED_FILE_SIGNATURES[file_ext]:
            if file_content.startswith(signature):
                file_valid = True
                break

        if not file_valid and file_ext != "txt":  # Text files can be empty
            raise HTTPException(
                status_code=400, detail="File content doesn't match expected file type"
            )

        # Sanitize filename
        safe_filename = re.sub(r"[^\w\-_\.]", "_", filename)
        safe_filename = safe_filename[:100]  # Limit filename length

        return {
            "original_filename": filename,
            "safe_filename": safe_filename,
            "file_extension": file_ext,
            "file_size": file_size,
            "content_type": file.content_type,
            "validated": True,
        }

    @staticmethod
    def sanitize_batch_texts(batch_texts: Optional[str]) -> List[str]:
        """
        Sanitize comma-separated batch text inputs.

        Args:
            batch_texts: Comma-separated text strings

        Returns:
            List of sanitized text strings
        """
        if not batch_texts:
            return []

        # Split by comma and sanitize each
        texts = [text.strip() for text in batch_texts.split(",")]
        sanitized_texts = []

        for text in texts:
            if text:  # Skip empty strings
                sanitized = InputSanitizer.sanitize_text_input(text)
                if sanitized and len(sanitized) >= 3:  # Minimum viable text
                    sanitized_texts.append(
                        sanitized[:1000]
                    )  # Limit individual text length

        return sanitized_texts[:10]  # Limit to 10 batch items

    @staticmethod
    def sanitize_json_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize JSON input data.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            safe_key = InputSanitizer.sanitize_text_input(str(key))

            # Sanitize value based on type
            if isinstance(value, str):
                sanitized[safe_key] = InputSanitizer.sanitize_text_input(value)
            elif isinstance(value, dict):
                sanitized[safe_key] = InputSanitizer.sanitize_json_input(value)
            elif isinstance(value, list):
                sanitized[safe_key] = [
                    (
                        InputSanitizer.sanitize_text_input(str(item))
                        if isinstance(item, str)
                        else item
                    )
                    for item in value[:100]  # Limit array size
                ]
            else:
                sanitized[safe_key] = value

        return sanitized


# Convenience functions for common operations
def sanitize_user_input(text: str) -> str:
    """Convenience function for basic text sanitization"""
    return InputSanitizer.sanitize_text_input(text)


def sanitize_ai_prompt(prompt: str) -> str:
    """Convenience function for AI prompt sanitization"""
    return InputSanitizer.sanitize_prompt_input(prompt)


def sanitize_login_credentials(username: str, password: str) -> tuple[str, str]:
    """Convenience function for credential sanitization"""
    return InputSanitizer.sanitize_credentials(username, password)


async def validate_file_upload(
    file: UploadFile, max_size_mb: int = 10
) -> Dict[str, Any]:
    """Convenience function for file validation"""
    return await InputSanitizer.validate_file_upload(file, max_size_mb)
