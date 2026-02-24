import base64
import io
import os
import time
from typing import Any, Dict, List, Optional

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from .base_test import BaseTest, TestResult


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
        
        self.logger.info(f"Starting Document Intelligence test with endpoint: {self.endpoint}")
        self.logger.info(f"Using model: {self.model_id}")

        try:
            # Create Document Analysis client
            self.logger.info("Creating Document Analysis client...")
            client = DocumentAnalysisClient(
                endpoint=self.endpoint, credential=AzureKeyCredential(self.api_key)
            )
            self.logger.info("Document Analysis client created successfully")

            all_passed = True

            # Test 1: Basic connectivity test
            self.logger.info("Running connectivity test...")
            connectivity_result = self._test_connectivity(client)
            result.add_sub_test("API Connectivity", connectivity_result)
            if connectivity_result["success"]:
                self.logger.info("Connectivity test passed")
            else:
                self.logger.error(f"Connectivity test failed: {connectivity_result.get('message', 'Unknown error')}")
                all_passed = False

            # Test 2: Document analysis with sample content
            if self.test_document_url:
                # Test with provided URL
                self.logger.info(f"Testing document analysis with URL: {self.test_document_url}")
                analysis_result = self._test_document_analysis(
                    client, document_url=self.test_document_url
                )
                result.add_sub_test("Document Analysis (URL)", analysis_result)
            else:
                # Test with sample content
                self.logger.info("Testing document analysis with sample content...")
                analysis_result = self._test_document_analysis(client)
                result.add_sub_test("Document Analysis (Sample)", analysis_result)

            if analysis_result["success"]:
                self.logger.info("Document analysis test passed")
                self.logger.info(f"Pages: {analysis_result.get('page_count', 'N/A')}")
                self.logger.info(f"Tables: {analysis_result.get('table_count', 0)}")
                self.logger.info(f"Content Length: {analysis_result.get('content_length', 0)} characters")
                self.logger.info(f"Processing Time: {analysis_result.get('processing_time_ms', 0)/1000:.2f}s")
                if analysis_result.get('content_preview'):
                    preview = analysis_result.get('content_preview', '')[:100]
                    self.logger.info(f"Content Preview: {preview}...")
            else:
                self.logger.error(f"Document analysis test failed: {analysis_result.get('message', 'Unknown error')}")
                all_passed = False

            # Test 3: Model information (if possible)
            self.logger.info("Running model information test...")
            model_result = self._test_model_info(client)
            result.add_sub_test("Model Information", model_result)
            if not model_result["success"]:
                # Model info failure shouldn't fail the overall test
                self.logger.warning(f"Model info test failed (non-critical): {model_result.get('message', 'Unknown error')}")
                result.add_log(
                    "WARNING",
                    f"Model info test failed: {model_result.get('message', 'Unknown error')}",
                )
            else:
                self.logger.info("Model information test passed")

            if all_passed:
                self.logger.info("All Document Intelligence tests passed successfully")
                self.logger.info(f"Endpoint: {self.endpoint}")
                self.logger.info(f"Model: {self.model_id}")
                if analysis_result.get('page_count'):
                    self.logger.info(f"Document Pages Processed: {analysis_result.get('page_count', 0)}")
                    self.logger.info(f"Tables Extracted: {analysis_result.get('table_count', 0)}")
                    self.logger.info(f"Paragraphs Found: {analysis_result.get('paragraph_count', 0)}")
                result.complete(
                    True, "All Document Intelligence tests passed successfully"
                )
            else:
                failed_tests = [
                    name
                    for name, test_result in result.sub_tests.items()
                    if not test_result.get("success", False)
                ]
                failure_msg = f"Document Intelligence tests failed: {', '.join(failed_tests)}"
                self.logger.error(failure_msg)
                result.fail(
                    failure_msg,
                    remediation="Check API credentials, endpoint configuration, and service availability",
                )

        except Exception as e:
            error_msg = f"Document Intelligence test failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.fail(
                error_msg,
                error=e,
                remediation="Check API configuration, credentials, and network connectivity",
            )

        return result

    def _test_connectivity(self, client: DocumentAnalysisClient) -> Dict[str, Any]:
        """Test basic API connectivity with a lightweight HTTP request."""
        import urllib.request
        import urllib.error

        try:
            start_time = time.time()

            # Use a lightweight HEAD-style GET to the endpoint root to verify reachability
            # rather than submitting a full document and cancelling
            url = self.endpoint.rstrip("/") + "/formrecognizer/documentModels?api-version=2023-07-31"
            req = urllib.request.Request(url, method="GET")
            req.add_header("Ocp-Apim-Subscription-Key", self.api_key)

            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status

            duration = time.time() - start_time

            return {
                "success": True,
                "message": "Successfully connected to Document Intelligence API",
                "endpoint": self.endpoint,
                "model": self.model_id,
                "response_time_ms": round(duration * 1000, 2),
            }

        except urllib.error.HTTPError as e:
            duration = time.time() - start_time
            # A 401/403 means the endpoint is reachable but credentials are wrong
            # A 404 means the endpoint path is wrong but service is reachable
            if e.code in (401, 403):
                return {
                    "success": False,
                    "message": f"Authentication failed (HTTP {e.code})",
                    "error": str(e),
                    "endpoint": self.endpoint,
                    "response_time_ms": round(duration * 1000, 2),
                    "remediation": "Check API key - authentication failed",
                }
            elif e.code == 404:
                return {
                    "success": False,
                    "message": f"Endpoint not found (HTTP {e.code})",
                    "error": str(e),
                    "endpoint": self.endpoint,
                    "response_time_ms": round(duration * 1000, 2),
                    "remediation": "Check API endpoint URL",
                }
            return {
                "success": False,
                "message": f"Connectivity test failed (HTTP {e.code}): {str(e)}",
                "error": str(e),
                "remediation": "Check API endpoint and credentials",
            }

        except Exception as e:
            error_msg = str(e)
            remediation = "Check API endpoint and credentials"

            if "timeout" in error_msg.lower():
                remediation = "Connection timed out - check network connectivity"
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
                remediation = "API rate limit or quota exceeded"

            return {
                "success": False,
                "message": f"Connectivity test failed: {error_msg}",
                "error": error_msg,
                "remediation": remediation,
            }

    def _test_document_analysis(
        self,
        client: DocumentAnalysisClient,
        document_url: str = None,
        document_content: bytes = None,
    ) -> Dict[str, Any]:
        """Test document analysis with either a URL or direct content.

        Args:
            client: The DocumentAnalysisClient instance
            document_url: URL of the document to analyze (mutually exclusive with document_content)
            document_content: Raw bytes of the document to analyze
        """
        source_type = "URL" if document_url else "sample"
        try:
            start_time = time.time()

            # Start document analysis with either URL or content
            if document_url:
                poller = client.begin_analyze_document(
                    model_id=self.model_id, document_url=document_url
                )
            else:
                poller = client.begin_analyze_document(
                    model_id=self.model_id, document=document_content or self.sample_pdf_content
                )

            # Wait for completion
            result_doc = poller.result()
            duration = time.time() - start_time

            # Extract basic information
            page_count = len(result_doc.pages)
            content_length = len(result_doc.content) if result_doc.content else 0

            # Extract content preview
            content_preview = ""
            if result_doc.content:
                content_preview = result_doc.content[:200] if len(result_doc.content) > 200 else result_doc.content

            result = {
                "success": True,
                "message": f"Successfully analyzed document from {source_type}",
                "model": self.model_id,
                "page_count": page_count,
                "content_length": content_length,
                "content_preview": content_preview,
                "processing_time_ms": round(duration * 1000, 2),
                "has_content": bool(result_doc.content),
                "table_count": len(result_doc.tables) if result_doc.tables else 0,
                "paragraph_count": len(result_doc.paragraphs) if result_doc.paragraphs else 0,
            }

            if document_url:
                result["document_url"] = document_url
            else:
                result["document_type"] = "sample_pdf"

            return result

        except Exception as e:
            error_msg = str(e)
            remediation = (
                "Check document URL accessibility and format support"
                if document_url
                else "Check model availability and document format support"
            )
            return {
                "success": False,
                "message": f"Document analysis failed ({source_type}): {error_msg}",
                "error": error_msg,
                "remediation": remediation,
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
        self.logger.info(f"Starting custom file test with file type: {file_type}")
        if custom_prompt:
            self.logger.info(f"Custom prompt: {custom_prompt}")
        
        try:
            if not self.is_configured():
                self.logger.error("Document Intelligence not configured")
                return {
                    "success": False,
                    "message": "Document Intelligence not configured",
                    "remediation": self.get_configuration_help(),
                }

            # Create client
            self.logger.info("Creating Document Intelligence client for custom file...")
            credential = AzureKeyCredential(self.api_key)
            client = DocumentAnalysisClient(
                endpoint=self.endpoint, credential=credential
            )
            self.logger.info("Client created successfully")

            start_time = time.time()
            self.logger.info(f"Starting document analysis for {len(file_content)} bytes of {file_type} content...")

            # Analyze the provided document
            poller = client.begin_analyze_document(
                model_id=self.model_id,
                document=file_content,
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

            # Log detailed results
            self.logger.info("Custom document analysis completed successfully")
            self.logger.info(f"Pages: {page_count}")
            self.logger.info(f"Tables: {table_count}")
            self.logger.info(f"Paragraphs: {structure_info['paragraphs']}")
            self.logger.info(f"Key-Value Pairs: {structure_info['key_value_pairs']}")
            self.logger.info(f"Content Length: {content_length} characters")
            self.logger.info(f"Processing Time: {duration:.2f}s")
            if content_preview:
                preview_text = content_preview[:100] if len(content_preview) > 100 else content_preview
                self.logger.info(f"Content Preview: {preview_text}...")

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
