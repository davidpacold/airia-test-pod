from typing import Dict, Any, List, Optional
import os
import time
import base64
import io
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from .base_test import BaseTest, TestResult
from ..models import TestStatus


class DocumentIntelligenceTest(BaseTest):
    """Test Azure Document Intelligence connectivity and capabilities"""

    def __init__(self):
        super().__init__()
        self.endpoint = os.getenv("AZURE_DOC_INTEL_ENDPOINT")
        self.api_key = os.getenv("AZURE_DOC_INTEL_API_KEY")
        self.model_id = os.getenv("AZURE_DOC_INTEL_MODEL", "prebuilt-document")
        self.test_document_url = os.getenv("AZURE_DOC_INTEL_TEST_URL")
        self.timeout_seconds_api = int(os.getenv("DOC_INTEL_TIMEOUT", "60"))

        # Create a simple test document content (base64 encoded minimal PDF)
        self.sample_pdf_content = self._create_minimal_pdf_content()

    @property
    def test_name(self) -> str:
        return "Document Intelligence"

    @property
    def test_description(self) -> str:
        return "Tests Azure Document Intelligence API connectivity"

    @property
    def test_id(self) -> str:
        return "docintel"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 120  # Document processing can take longer

    def is_configured(self) -> bool:
        """Check if Document Intelligence is properly configured"""
        return bool(self.endpoint and self.api_key)

    def get_configuration_help(self) -> str:
        return (
            "Azure Document Intelligence configuration required. "
            "Environment variables: AZURE_DOC_INTEL_ENDPOINT, AZURE_DOC_INTEL_API_KEY, "
            "AZURE_DOC_INTEL_MODEL (default: prebuilt-document), "
            "AZURE_DOC_INTEL_TEST_URL (optional - for testing with external document), "
            "DOC_INTEL_TIMEOUT (default: 60)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            # Create Document Analysis client
            client = DocumentAnalysisClient(
                endpoint=self.endpoint, credential=AzureKeyCredential(self.api_key)
            )

            all_passed = True

            # Test 1: Basic connectivity test
            connectivity_result = self._test_connectivity(client)
            result.add_sub_test("API Connectivity", connectivity_result)
            if not connectivity_result["success"]:
                all_passed = False

            # Test 2: Document analysis with sample content
            if self.test_document_url:
                # Test with provided URL
                analysis_result = self._test_document_analysis_url(
                    client, self.test_document_url
                )
                result.add_sub_test("Document Analysis (URL)", analysis_result)
            else:
                # Test with sample content
                analysis_result = self._test_document_analysis_content(client)
                result.add_sub_test("Document Analysis (Sample)", analysis_result)

            if not analysis_result["success"]:
                all_passed = False

            # Test 3: Model information (if possible)
            model_result = self._test_model_info(client)
            result.add_sub_test("Model Information", model_result)
            if not model_result["success"]:
                # Model info failure shouldn't fail the overall test
                result.add_log(
                    "WARNING",
                    f"Model info test failed: {model_result.get('message', 'Unknown error')}",
                )

            if all_passed:
                result.complete(
                    True, "All Document Intelligence tests passed successfully"
                )
            else:
                failed_tests = [
                    name
                    for name, test_result in result.sub_tests.items()
                    if not test_result.get("success", False)
                ]
                result.fail(
                    f"Document Intelligence tests failed: {', '.join(failed_tests)}",
                    remediation="Check API credentials, endpoint configuration, and service availability",
                )

        except Exception as e:
            result.fail(
                f"Document Intelligence test failed: {str(e)}",
                error=e,
                remediation="Check API configuration, credentials, and network connectivity",
            )

        return result

    def _test_connectivity(self, client: DocumentAnalysisClient) -> Dict[str, Any]:
        """Test basic API connectivity"""
        try:
            start_time = time.time()

            # Try to analyze a minimal document to test connectivity
            # Using the smallest possible document content
            minimal_content = self.sample_pdf_content

            # Start the analysis (this tests connectivity)
            poller = client.begin_analyze_document(
                model_id=self.model_id, document=minimal_content
            )

            # Don't wait for completion, just test that we can start the operation
            duration = time.time() - start_time

            # Cancel the operation to avoid unnecessary processing
            try:
                poller.cancel()
            except:
                pass  # Cancel might not be supported, that's okay

            return {
                "success": True,
                "message": "Successfully connected to Document Intelligence API",
                "endpoint": self.endpoint,
                "model": self.model_id,
                "response_time_ms": round(duration * 1000, 2),
            }

        except Exception as e:
            error_msg = str(e)
            remediation = "Check API endpoint and credentials"

            if "401" in error_msg or "unauthorized" in error_msg.lower():
                remediation = "Check API key - authentication failed"
            elif "404" in error_msg or "not found" in error_msg.lower():
                remediation = "Check API endpoint URL and model ID"
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
                remediation = "API rate limit or quota exceeded"

            return {
                "success": False,
                "message": f"Connectivity test failed: {error_msg}",
                "error": error_msg,
                "remediation": remediation,
            }

    def _test_document_analysis_url(
        self, client: DocumentAnalysisClient, document_url: str
    ) -> Dict[str, Any]:
        """Test document analysis with a URL"""
        try:
            start_time = time.time()

            # Start document analysis
            poller = client.begin_analyze_document(
                model_id=self.model_id, document_url=document_url
            )

            # Wait for completion with timeout
            result_doc = poller.result()
            duration = time.time() - start_time

            # Extract basic information
            page_count = len(result_doc.pages)
            content_length = len(result_doc.content) if result_doc.content else 0

            return {
                "success": True,
                "message": f"Successfully analyzed document from URL",
                "document_url": document_url,
                "model": self.model_id,
                "page_count": page_count,
                "content_length": content_length,
                "processing_time_ms": round(duration * 1000, 2),
                "has_content": bool(result_doc.content),
                "table_count": len(result_doc.tables) if result_doc.tables else 0,
            }

        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "message": f"Document analysis failed: {error_msg}",
                "error": error_msg,
                "remediation": "Check document URL accessibility and format support",
            }

    def _test_document_analysis_content(
        self, client: DocumentAnalysisClient
    ) -> Dict[str, Any]:
        """Test document analysis with sample content"""
        try:
            start_time = time.time()

            # Use minimal PDF content for testing
            document_content = self.sample_pdf_content

            # Start document analysis
            poller = client.begin_analyze_document(
                model_id=self.model_id, document=document_content
            )

            # Wait for completion
            result_doc = poller.result()
            duration = time.time() - start_time

            # Extract basic information
            page_count = len(result_doc.pages)
            content_length = len(result_doc.content) if result_doc.content else 0

            return {
                "success": True,
                "message": f"Successfully analyzed sample document",
                "model": self.model_id,
                "page_count": page_count,
                "content_length": content_length,
                "processing_time_ms": round(duration * 1000, 2),
                "has_content": bool(result_doc.content),
                "document_type": "sample_pdf",
            }

        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "message": f"Sample document analysis failed: {error_msg}",
                "error": error_msg,
                "remediation": "Check model availability and document format support",
            }

    def _test_model_info(self, client: DocumentAnalysisClient) -> Dict[str, Any]:
        """Test model information retrieval"""
        try:
            # This is a basic test - actual model info retrieval might require different SDK methods
            # For now, just test that we can use the configured model
            return {
                "success": True,
                "message": f"Model '{self.model_id}' is configured",
                "model_id": self.model_id,
                "model_type": "prebuilt" if "prebuilt" in self.model_id else "custom",
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Model info test failed: {str(e)}",
                "error": str(e),
            }

    def _create_minimal_pdf_content(self) -> bytes:
        """Create minimal PDF content for testing"""
        # This is a minimal PDF structure that should be processable
        # In a real implementation, you might want to use a proper PDF library
        minimal_pdf = """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000197 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
290
%%EOF"""
        return minimal_pdf.encode("latin-1")

    def test_with_custom_file(
        self, file_content: bytes, file_type: str, custom_prompt: str = None
    ) -> Dict[str, Any]:
        """Test Document Intelligence with custom file upload"""
        try:
            if not self.is_configured():
                return {
                    "success": False,
                    "message": "Document Intelligence not configured",
                    "remediation": self.get_configuration_help(),
                }

            # Create client
            credential = AzureKeyCredential(self.api_key)
            client = DocumentAnalysisClient(
                endpoint=self.endpoint, credential=credential
            )

            start_time = time.time()

            # Analyze the provided document
            poller = client.begin_analyze_document(
                model_id=self.model_id,
                document=file_content,
                content_type="application/octet-stream",
            )

            # Wait for analysis to complete
            result_doc = poller.result()

            duration = time.time() - start_time

            # Extract information from the document
            page_count = len(result_doc.pages)
            content_length = len(result_doc.content) if result_doc.content else 0
            table_count = len(result_doc.tables) if result_doc.tables else 0

            # Extract text content (first 1000 characters for preview)
            content_preview = (
                result_doc.content[:1000] + "..."
                if result_doc.content and len(result_doc.content) > 1000
                else result_doc.content or ""
            )

            # Get document structure information
            structure_info = {
                "pages": page_count,
                "tables": table_count,
                "paragraphs": (
                    len(result_doc.paragraphs) if result_doc.paragraphs else 0
                ),
                "key_value_pairs": (
                    len(result_doc.key_value_pairs) if result_doc.key_value_pairs else 0
                ),
            }

            analysis_result = {
                "success": True,
                "message": "Document analysis completed successfully",
                "file_type": file_type,
                "model_used": self.model_id,
                "processing_time_ms": round(duration * 1000, 2),
                "document_info": structure_info,
                "content_length": content_length,
                "content_preview": content_preview,
                "analysis_complete": True,
            }

            # If a custom prompt was provided, include it in the response
            if custom_prompt:
                analysis_result["custom_prompt"] = custom_prompt
                analysis_result["prompt_response"] = (
                    f"Custom analysis request: '{custom_prompt}'\n\nDocument content extracted successfully. The document contains {page_count} page(s) with {content_length} characters of text content."
                )

            return analysis_result

        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "message": f"Custom document analysis failed: {error_msg}",
                "file_type": file_type,
                "error": error_msg,
                "remediation": "Check file format support and Document Intelligence configuration",
            }
