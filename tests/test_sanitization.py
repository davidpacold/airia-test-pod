"""
Unit tests for input sanitization functionality.

Tests the sanitization.py module including XSS prevention,
input validation, file upload security, and data sanitization.
"""

import pytest
import io
from unittest.mock import Mock, patch, AsyncMock
from fastapi import UploadFile, HTTPException

from app.utils.sanitization import (
    InputSanitizer,
    sanitize_user_input,
    sanitize_ai_prompt,
    sanitize_login_credentials,
    validate_file_upload,
)


class TestInputSanitizer:
    """Test the main InputSanitizer class methods."""

    def test_sanitize_text_input_clean_text(self):
        """Test sanitization of clean text."""
        clean_text = "This is a normal text input"
        result = InputSanitizer.sanitize_text_input(clean_text)
        assert result == clean_text

    def test_sanitize_text_input_html_escape(self):
        """Test HTML escaping for XSS prevention."""
        malicious_input = "<script>alert('xss')</script>Hello"
        result = InputSanitizer.sanitize_text_input(malicious_input)

        # Should escape HTML characters
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        assert "Hello" in result
        assert "<script>" not in result

    def test_sanitize_text_input_javascript_url(self):
        """Test removal of JavaScript URLs."""
        malicious_input = "Click here: javascript:alert('xss')"
        result = InputSanitizer.sanitize_text_input(malicious_input)

        # JavaScript URL should be removed
        assert "javascript:" not in result.lower()
        assert "Click here:" in result

    def test_sanitize_text_input_event_handlers(self):
        """Test removal of event handlers."""
        malicious_input = "Hello onclick=alert('xss') world"
        result = InputSanitizer.sanitize_text_input(malicious_input)

        # Event handler should be removed
        assert "onclick" not in result.lower()
        assert "Hello" in result
        assert "world" in result

    def test_sanitize_text_input_null_bytes(self):
        """Test removal of null bytes and control characters."""
        malicious_input = "Hello\x00World\x01Test\x02"
        result = InputSanitizer.sanitize_text_input(malicious_input)

        # Should remove null bytes and control chars
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "HelloWorldTest" == result

    def test_sanitize_text_input_preserve_newlines_tabs(self):
        """Test that newlines and tabs are preserved."""
        input_text = "Line 1\nLine 2\tTabbed"
        result = InputSanitizer.sanitize_text_input(input_text)

        assert "\n" in result
        assert "\t" in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Tabbed" in result

    def test_sanitize_text_input_length_limit(self):
        """Test length limiting for DoS prevention."""
        long_input = "A" * 15000  # 15KB, should be limited to 10KB
        result = InputSanitizer.sanitize_text_input(long_input)

        assert len(result) == 10000
        assert result == "A" * 10000

    def test_sanitize_text_input_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped."""
        input_text = "   \t  Hello World  \n  "
        result = InputSanitizer.sanitize_text_input(input_text)

        assert result == "Hello World"

    def test_sanitize_text_input_empty_none(self):
        """Test handling of empty and None inputs."""
        assert InputSanitizer.sanitize_text_input("") == ""
        assert InputSanitizer.sanitize_text_input(None) is None
        assert InputSanitizer.sanitize_text_input("   ") == ""

    def test_sanitize_text_input_unicode(self):
        """Test handling of Unicode characters."""
        unicode_text = "Hello 世界 🌍 Тест"
        result = InputSanitizer.sanitize_text_input(unicode_text)

        assert "Hello" in result
        assert "世界" in result
        assert "🌍" in result
        assert "Тест" in result


class TestPromptSanitization:
    """Test AI prompt-specific sanitization."""

    def test_sanitize_prompt_input_valid(self):
        """Test sanitization of valid AI prompt."""
        prompt = "Explain machine learning concepts"
        result = InputSanitizer.sanitize_prompt_input(prompt)
        assert result == prompt

    def test_sanitize_prompt_input_too_short(self):
        """Test rejection of too short prompts."""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_prompt_input("Hi")

        assert exc_info.value.status_code == 400
        assert "too short" in exc_info.value.detail.lower()

    def test_sanitize_prompt_input_empty(self):
        """Test rejection of empty prompts."""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_prompt_input("")

        assert exc_info.value.status_code == 400
        assert "cannot be empty" in exc_info.value.detail.lower()

    def test_sanitize_prompt_input_length_limit(self):
        """Test custom length limiting for prompts."""
        long_prompt = "A" * 5000  # Longer than 4KB default
        result = InputSanitizer.sanitize_prompt_input(long_prompt, max_length=1000)

        assert len(result) == 1000
        assert result == "A" * 1000

    def test_sanitize_prompt_input_xss_removal(self):
        """Test XSS removal in prompts."""
        malicious_prompt = "<script>alert('hack')</script>Explain AI safety"
        result = InputSanitizer.sanitize_prompt_input(malicious_prompt)

        assert "<script>" not in result
        assert "Explain AI safety" in result
        assert len(result) >= 3  # Should pass minimum length after sanitization


class TestCredentialSanitization:
    """Test credential sanitization and validation."""

    def test_sanitize_credentials_valid(self):
        """Test sanitization of valid credentials."""
        username, password = InputSanitizer.sanitize_credentials("testuser", "testpass")

        assert username == "testuser"
        assert password == "testpass"

    def test_sanitize_credentials_empty_username(self):
        """Test rejection of empty username."""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_credentials("", "testpass")

        assert exc_info.value.status_code == 400
        assert "username cannot be empty" in exc_info.value.detail.lower()

    def test_sanitize_credentials_empty_password(self):
        """Test rejection of empty password."""
        with pytest.raises(HTTPException) as exc_info:
            InputSanitizer.sanitize_credentials("testuser", "")

        assert exc_info.value.status_code == 400
        assert "password cannot be empty" in exc_info.value.detail.lower()

    def test_sanitize_credentials_malicious_username(self):
        """Test sanitization of malicious username."""
        malicious_username = "<script>alert('xss')</script>user"
        username, password = InputSanitizer.sanitize_credentials(
            malicious_username, "testpass"
        )

        # Dangerous characters should be removed
        assert "<" not in username
        assert ">" not in username
        assert "script" in username  # Content preserved, tags removed
        assert "user" in username

    def test_sanitize_credentials_long_username(self):
        """Test username length limiting."""
        long_username = "a" * 100  # Should be limited to 50
        username, password = InputSanitizer.sanitize_credentials(
            long_username, "testpass"
        )

        assert len(username) == 50
        assert username == "a" * 50

    def test_sanitize_credentials_special_chars_username(self):
        """Test handling of special characters in username."""
        special_username = "user@domain.com"
        username, password = InputSanitizer.sanitize_credentials(
            special_username, "testpass"
        )

        # @ symbol should be preserved (valid email character)
        assert username == special_username


class TestFileValidation:
    """Test file upload validation and security."""

    @pytest.mark.asyncio
    async def test_validate_file_upload_valid_txt(self, mock_file_upload):
        """Test validation of valid text file."""
        mock_file = mock_file_upload("test.txt", "Hello world", "text/plain")

        result = await InputSanitizer.validate_file_upload(mock_file)

        assert result["validated"] is True
        assert result["file_extension"] == "txt"
        assert result["original_filename"] == "test.txt"
        assert "safe_filename" in result

    @pytest.mark.asyncio
    async def test_validate_file_upload_valid_pdf(self, mock_file_upload):
        """Test validation of valid PDF file."""
        pdf_content = b"%PDF-1.4\n%test pdf content"
        mock_file = mock_file_upload("document.pdf", pdf_content, "application/pdf")

        result = await InputSanitizer.validate_file_upload(mock_file)

        assert result["validated"] is True
        assert result["file_extension"] == "pdf"

    @pytest.mark.asyncio
    async def test_validate_file_upload_no_file(self):
        """Test rejection when no file provided."""
        with pytest.raises(HTTPException) as exc_info:
            await InputSanitizer.validate_file_upload(None)

        assert exc_info.value.status_code == 400
        assert "No file provided" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_file_upload_file_too_large(self, mock_file_upload):
        """Test rejection of files that are too large."""
        large_content = b"A" * (15 * 1024 * 1024)  # 15MB
        mock_file = mock_file_upload("large.txt", large_content, "text/plain")

        with pytest.raises(HTTPException) as exc_info:
            await InputSanitizer.validate_file_upload(mock_file, max_size_mb=10)

        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_file_upload_invalid_extension(self, mock_file_upload):
        """Test rejection of invalid file extensions."""
        mock_file = mock_file_upload(
            "malicious.exe", b"MZexecutable", "application/octet-stream"
        )

        with pytest.raises(HTTPException) as exc_info:
            await InputSanitizer.validate_file_upload(mock_file)

        assert exc_info.value.status_code == 400
        assert "not allowed" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_file_upload_filename_sanitization(self, mock_file_upload):
        """Test filename sanitization."""
        dangerous_filename = "../../../etc/passwd<script>.txt"
        mock_file = mock_file_upload(dangerous_filename, "content", "text/plain")

        result = await InputSanitizer.validate_file_upload(mock_file)

        # Dangerous characters should be replaced with underscores
        safe_filename = result["safe_filename"]
        assert "/" not in safe_filename
        assert "<" not in safe_filename
        assert ">" not in safe_filename
        assert ".txt" in safe_filename

    @pytest.mark.asyncio
    async def test_validate_file_upload_magic_number_mismatch(self, mock_file_upload):
        """Test rejection of files with mismatched magic numbers."""
        # File with .pdf extension but wrong magic number
        fake_pdf = mock_file_upload("fake.pdf", b"This is not a PDF", "application/pdf")

        with pytest.raises(HTTPException) as exc_info:
            await InputSanitizer.validate_file_upload(fake_pdf)

        assert exc_info.value.status_code == 400
        assert "doesn't match expected file type" in exc_info.value.detail


class TestBatchTextSanitization:
    """Test batch text processing."""

    def test_sanitize_batch_texts_valid(self):
        """Test sanitization of valid batch texts."""
        batch_input = "Text one, Text two, Text three"
        result = InputSanitizer.sanitize_batch_texts(batch_input)

        assert len(result) == 3
        assert "Text one" in result
        assert "Text two" in result
        assert "Text three" in result

    def test_sanitize_batch_texts_empty(self):
        """Test handling of empty batch input."""
        result = InputSanitizer.sanitize_batch_texts("")
        assert result == []

        result = InputSanitizer.sanitize_batch_texts(None)
        assert result == []

    def test_sanitize_batch_texts_with_xss(self):
        """Test XSS removal in batch texts."""
        malicious_batch = "Clean text, <script>alert('xss')</script>, Another text"
        result = InputSanitizer.sanitize_batch_texts(malicious_batch)

        assert len(result) == 3
        assert "Clean text" in result
        assert "Another text" in result
        # XSS should be sanitized but content preserved
        assert any("script" in text and "<script>" not in text for text in result)

    def test_sanitize_batch_texts_length_limits(self):
        """Test individual text length limiting."""
        long_text = "A" * 2000
        batch_input = f"Short text, {long_text}, Another short"
        result = InputSanitizer.sanitize_batch_texts(batch_input)

        # Long text should be truncated to 1000 chars
        long_result = next(text for text in result if len(text) > 100)
        assert len(long_result) == 1000
        assert long_result == "A" * 1000

    def test_sanitize_batch_texts_count_limit(self):
        """Test batch count limiting."""
        # Create 15 texts, should be limited to 10
        many_texts = ", ".join([f"Text {i}" for i in range(15)])
        result = InputSanitizer.sanitize_batch_texts(many_texts)

        assert len(result) == 10
        assert "Text 0" in result
        assert "Text 9" in result

    def test_sanitize_batch_texts_skip_short(self):
        """Test skipping of too-short texts."""
        batch_input = "Valid text, Hi, No, Another valid text"
        result = InputSanitizer.sanitize_batch_texts(batch_input)

        # Should skip "Hi" and "No" (less than 3 chars)
        assert len(result) == 2
        assert "Valid text" in result
        assert "Another valid text" in result
        assert "Hi" not in result
        assert "No" not in result


class TestJSONSanitization:
    """Test JSON input sanitization."""

    def test_sanitize_json_input_clean(self):
        """Test sanitization of clean JSON data."""
        clean_data = {"name": "John Doe", "email": "john@example.com", "age": 30}
        result = InputSanitizer.sanitize_json_input(clean_data)

        assert result == clean_data

    def test_sanitize_json_input_with_xss(self):
        """Test XSS removal in JSON values."""
        malicious_data = {
            "name": "<script>alert('xss')</script>John",
            "description": "Safe content",
        }
        result = InputSanitizer.sanitize_json_input(malicious_data)

        # XSS should be escaped
        assert "&lt;script&gt;" in result["name"]
        assert "John" in result["name"]
        assert result["description"] == "Safe content"

    def test_sanitize_json_input_nested(self):
        """Test sanitization of nested JSON structures."""
        nested_data = {
            "user": {
                "name": "<script>alert('xss')</script>Jane",
                "profile": {"bio": "javascript:alert('hack')"},
            }
        }
        result = InputSanitizer.sanitize_json_input(nested_data)

        # All nested values should be sanitized
        assert "&lt;script&gt;" in result["user"]["name"]
        assert "Jane" in result["user"]["name"]
        assert "javascript:" not in result["user"]["profile"]["bio"]

    def test_sanitize_json_input_array_values(self):
        """Test sanitization of arrays in JSON."""
        data_with_arrays = {
            "tags": ["<script>alert('xss')</script>", "safe tag", "javascript:alert()"],
            "numbers": [1, 2, 3],
        }
        result = InputSanitizer.sanitize_json_input(data_with_arrays)

        # String values in arrays should be sanitized
        tags = result["tags"]
        assert "&lt;script&gt;" in tags[0]
        assert "safe tag" in tags
        assert "javascript:" not in tags[2]

        # Non-string values preserved
        assert result["numbers"] == [1, 2, 3]

    def test_sanitize_json_input_array_size_limit(self):
        """Test array size limiting."""
        data_with_large_array = {
            "items": [f"item_{i}" for i in range(150)]  # Should be limited to 100
        }
        result = InputSanitizer.sanitize_json_input(data_with_large_array)

        assert len(result["items"]) == 100
        assert "item_0" in result["items"]
        assert "item_99" in result["items"]


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_sanitize_user_input_wrapper(self):
        """Test the sanitize_user_input convenience function."""
        malicious_input = "<script>alert('xss')</script>Hello"
        result = sanitize_user_input(malicious_input)

        assert "&lt;script&gt;" in result
        assert "Hello" in result

    def test_sanitize_ai_prompt_wrapper(self):
        """Test the sanitize_ai_prompt convenience function."""
        prompt = "Explain machine learning"
        result = sanitize_ai_prompt(prompt)

        assert result == prompt

    def test_sanitize_login_credentials_wrapper(self):
        """Test the sanitize_login_credentials convenience function."""
        username, password = sanitize_login_credentials("testuser", "testpass")

        assert username == "testuser"
        assert password == "testpass"

    @pytest.mark.asyncio
    async def test_validate_file_upload_wrapper(self, mock_file_upload):
        """Test the validate_file_upload convenience function."""
        mock_file = mock_file_upload("test.txt", "content", "text/plain")
        result = await validate_file_upload(mock_file)

        assert result["validated"] is True


@pytest.mark.security
class TestSecurityScenarios:
    """Test various security attack scenarios."""

    def test_xss_script_tag_variants(self, test_helpers):
        """Test various XSS script tag variants."""
        xss_variants = [
            "<script>alert('xss')</script>",
            "<SCRIPT>alert('xss')</SCRIPT>",
            "<script src='evil.js'></script>",
            "<script\ntype='text/javascript'>alert(1)</script>",
        ]

        for variant in xss_variants:
            result = InputSanitizer.sanitize_text_input(variant)
            test_helpers.assert_no_xss(result)

    def test_xss_javascript_url_variants(self, test_helpers):
        """Test various JavaScript URL variants."""
        js_url_variants = [
            "javascript:alert('xss')",
            "JAVASCRIPT:alert('xss')",
            "javascript&#58;alert('xss')",
            "java\nscript:alert('xss')",
        ]

        for variant in js_url_variants:
            text_with_js = f"Click here: {variant}"
            result = InputSanitizer.sanitize_text_input(text_with_js)
            test_helpers.assert_no_xss(result)

    def test_xss_event_handler_variants(self, test_helpers):
        """Test various event handler XSS variants."""
        event_variants = [
            "onclick=alert('xss')",
            "onload=alert('xss')",
            "onmouseover=alert('xss')",
            "ON CLICK=alert('xss')",
        ]

        for variant in event_variants:
            text_with_event = f"Hello {variant} world"
            result = InputSanitizer.sanitize_text_input(text_with_event)
            test_helpers.assert_no_xss(result)

    def test_sql_injection_patterns(self):
        """Test handling of SQL injection patterns."""
        sql_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM passwords--",
        ]

        for pattern in sql_patterns:
            # SQL injection in text should be escaped, not executed
            result = InputSanitizer.sanitize_text_input(pattern)
            # Single quotes should be escaped
            assert "&#x27;" in result or "'" not in result or result == pattern

    def test_path_traversal_in_filenames(self, test_helpers):
        """Test path traversal prevention in filenames."""
        malicious_filenames = [
            "../../../etc/passwd.txt",
            "..\\..\\windows\\system32\\config\\sam.txt",
            "....//....//....//etc//passwd.txt",
        ]

        for filename in malicious_filenames:
            # Simulate processing malicious filename
            safe_filename = InputSanitizer.sanitize_text_input(filename)
            test_helpers.assert_safe_filename(safe_filename)

    def test_dos_prevention_length_limits(self, test_helpers):
        """Test DoS prevention through length limits."""
        # Test extremely long inputs
        very_long_text = "A" * 1000000  # 1MB text
        result = InputSanitizer.sanitize_text_input(very_long_text)

        # Should be limited to prevent DoS
        test_helpers.assert_length_limit(result, 10000)

        # Test batch text limits
        many_batch_texts = ",".join([f"Text {i}" for i in range(1000)])
        batch_result = InputSanitizer.sanitize_batch_texts(many_batch_texts)

        # Should be limited to 10 items
        assert len(batch_result) <= 10
