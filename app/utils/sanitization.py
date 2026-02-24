"""
Input sanitization utilities for preventing XSS and other security vulnerabilities.

This module provides utilities to sanitize user inputs across the application,
preventing common security vulnerabilities like XSS and injection attacks.
"""

import html
import re

from fastapi import HTTPException


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

        # Remove dangerous patterns first (before escaping, so regexes can match raw HTML)
        sanitized = text
        for pattern in InputSanitizer.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        # HTML escape to prevent XSS
        sanitized = html.escape(sanitized, quote=True)

        # Remove null bytes and control characters (except newlines and tabs)
        sanitized = "".join(
            char for char in sanitized if ord(char) >= 32 or char in "\n\t\r"
        )

        # Limit length to prevent DoS
        if len(sanitized) > 10000:  # 10KB limit for text inputs
            sanitized = sanitized[:10000]

        return sanitized.strip()

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


# Convenience functions for common operations
def sanitize_user_input(text: str) -> str:
    """Convenience function for basic text sanitization"""
    return InputSanitizer.sanitize_text_input(text)


def sanitize_login_credentials(username: str, password: str) -> tuple[str, str]:
    """Convenience function for credential sanitization"""
    return InputSanitizer.sanitize_credentials(username, password)
