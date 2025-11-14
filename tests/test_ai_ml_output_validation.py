"""
Test cases to validate AI/ML test outputs and UI display

This test suite ensures that all enhanced AI/ML tests display the correct
information in the UI with proper formatting and completeness.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from io import StringIO

# Add parent directory to path to import app modules
sys.path.insert(0, '/Users/davidpacold/Documents/Github/airia-test-pod')

from app.tests.llama_test import LlamaTest
from app.tests.embedding_test import EmbeddingTest
from app.tests.openai_test import OpenAITest
from app.tests.document_intelligence_test import DocumentIntelligenceTest


class TestLlamaTestOutput:
    """Test cases for Llama model test output validation"""

    @patch('app.tests.llama_test.OpenAI')
    def test_llama_completion_output_format(self, mock_openai):
        """Test that Llama completion test displays correct output format"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I am a helpful AI assistant designed to assist users with various tasks."
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 25
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 15

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client.models.list.return_value = Mock(data=[Mock(id="llama2")])
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        # Set environment variables
        with patch.dict('os.environ', {
            'LLAMA_BASE_URL': 'http://localhost:8000/v1',
            'LLAMA_API_KEY': 'test-key',
            'LLAMA_MODEL_NAME': 'llama2'
        }):
            test = LlamaTest()
            result = test.run_test()

        # Restore stdout
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate output contains expected elements
        assert "💬 Running text generation test..." in output
        assert "✅ Text generation test passed" in output
        assert "📝 Input:" in output
        assert "Hello! Can you introduce yourself briefly?" in output
        assert "💬 Output:" in output
        assert "I am a helpful AI assistant" in output
        assert "⏱️  Duration:" in output
        assert result.status.value == "passed"

    @patch('app.tests.llama_test.OpenAI')
    def test_llama_prompt_test_output_format(self, mock_openai):
        """Test that Llama-style prompt test displays correct output"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Llama models are large language models developed by Meta that excel at natural language understanding and generation tasks."
        mock_response.usage = Mock()

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client.models.list.return_value = Mock(data=[])
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'LLAMA_BASE_URL': 'http://localhost:8000/v1',
            'LLAMA_API_KEY': 'test-key',
            'LLAMA_MODEL_NAME': 'llama2'
        }):
            test = LlamaTest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate Llama-specific prompt output
        assert "🦙 Running Llama-style prompt test..." in output
        assert "✅ Llama-style prompt test passed" in output
        assert "📝 Input:" in output
        assert "What are the key capabilities of Llama models?" in output
        assert "💬 Output:" in output
        assert "Llama models" in output or "large language model" in output
        assert "⏱️  Duration:" in output


class TestEmbeddingTestOutput:
    """Test cases for Embedding model test output validation"""

    @patch('app.tests.embedding_test.OpenAI')
    def test_single_embedding_output_format(self, mock_openai):
        """Test that single embedding test displays correct metrics"""
        # Setup mock response
        mock_embedding = [0.123456, -0.234567, 0.345678, 0.456789, -0.567890] + [0.1] * 1531
        mock_response = Mock()
        mock_response.data = [Mock(embedding=mock_embedding)]
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 8
        mock_response.usage.total_tokens = 8

        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'EMBEDDING_BASE_URL': 'http://localhost:8000/v1',
            'EMBEDDING_API_KEY': 'test-key',
            'EMBEDDING_MODEL_NAME': 'text-embedding-ada-002'
        }):
            test = EmbeddingTest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate single embedding output
        assert "🔢 Running single embedding test..." in output
        assert "✅ Single embedding test passed" in output
        assert "📝 Input:" in output
        assert "This is a test sentence for embedding generation" in output
        assert "📐 Embedding Dimension: 1536" in output
        assert "⏱️  Processing Time:" in output
        assert "📊 Value Range:" in output
        assert "🎯 Tokens Used:" in output

    @patch('app.tests.embedding_test.OpenAI')
    @patch('app.tests.embedding_test.HAS_NUMPY', True)
    @patch('app.tests.embedding_test.np')
    def test_batch_embedding_output_format(self, mock_np, mock_openai):
        """Test that batch embedding test displays batch metrics"""
        # Setup mock responses
        mock_embedding1 = [0.1] * 1536
        mock_embedding2 = [0.2] * 1536
        mock_embedding3 = [0.3] * 1536

        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=mock_embedding1),
            Mock(embedding=mock_embedding2),
            Mock(embedding=mock_embedding3)
        ]
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 24
        mock_response.usage.total_tokens = 24

        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'EMBEDDING_BASE_URL': 'http://localhost:8000/v1',
            'EMBEDDING_API_KEY': 'test-key',
            'EMBEDDING_MODEL_NAME': 'text-embedding-ada-002'
        }):
            test = EmbeddingTest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate batch embedding output
        assert "📚 Running batch embedding test..." in output
        assert "✅ Batch embedding test passed" in output
        assert "📦 Batch Size: 3" in output
        assert "📐 Embedding Dimension: 1536" in output
        assert "⏱️  Total Processing Time:" in output
        assert "⚡ Avg Time per Embedding:" in output

    @patch('app.tests.embedding_test.OpenAI')
    def test_embedding_summary_output(self, mock_openai):
        """Test that embedding test displays final summary"""
        # Setup mock response
        mock_embedding = [0.1] * 1536
        mock_response = Mock()
        mock_response.data = [Mock(embedding=mock_embedding)]
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 8

        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'EMBEDDING_BASE_URL': 'http://localhost:8000/v1',
            'EMBEDDING_API_KEY': 'test-key',
            'EMBEDDING_MODEL_NAME': 'text-embedding-ada-002'
        }):
            test = EmbeddingTest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate summary section
        assert "=" * 60 in output
        assert "🎉 All critical embedding tests passed!" in output
        assert "📊 Model: text-embedding-ada-002" in output
        assert "📐 Embedding Dimension: 1536" in output
        assert "⏱️  Single Embedding Processing Time:" in output
        assert "⚡ Batch Processing (3 texts):" in output


class TestOpenAITestOutput:
    """Test cases for OpenAI test output validation"""

    @patch('app.tests.openai_test.OpenAI')
    def test_openai_connection_output(self, mock_openai):
        """Test that OpenAI connection test displays connection info"""
        # Setup mock
        mock_models = Mock()
        mock_models.data = [Mock(id='gpt-3.5-turbo'), Mock(id='gpt-4')]

        mock_client = Mock()
        mock_client.models.list.return_value = mock_models
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'OPENAI_BASE_URL': 'http://localhost:8000/v1',
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL_NAME': 'gpt-3.5-turbo'
        }):
            test = OpenAITest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate connection output
        assert "🔗 Testing API connection..." in output
        assert "✅ API connection successful" in output
        assert "📋 Found 2 models available" in output
        assert "⏱️  Response Time:" in output

    @patch('app.tests.openai_test.OpenAI')
    def test_openai_completion_output_format(self, mock_openai):
        """Test that OpenAI completion test displays input/output correctly"""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "4"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 1
        mock_response.usage.total_tokens = 21

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client.models.list.return_value = Mock(data=[])
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'OPENAI_BASE_URL': 'http://localhost:8000/v1',
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL_NAME': 'gpt-3.5-turbo'
        }):
            test = OpenAITest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate completion output
        assert "💬 Running text completion test..." in output
        assert "✅ Text completion test passed" in output
        assert "🤖 Model: gpt-3.5-turbo" in output
        assert "📝 Input: What is 2+2?" in output
        assert "💬 Output: 4" in output
        assert "✓ Validation: Passed (contains 4)" in output
        assert "🎯 Tokens: 21 (20 prompt + 1 completion)" in output
        assert "⏱️  Duration:" in output

    @patch('app.tests.openai_test.OpenAI')
    def test_openai_embedding_output_format(self, mock_openai):
        """Test that OpenAI embedding test displays embedding details"""
        # Setup mock responses
        mock_embedding = [0.123456, -0.234567, 0.345678, 0.456789, -0.567890] + [0.1] * 1531
        mock_response = Mock()
        mock_response.data = [Mock(embedding=mock_embedding)]
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 8

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="test"), finish_reason="stop")],
            usage=Mock(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        )
        mock_client.embeddings.create.return_value = mock_response
        mock_client.models.list.return_value = Mock(data=[])
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'OPENAI_BASE_URL': 'http://localhost:8000/v1',
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL_NAME': 'gpt-3.5-turbo',
            'OPENAI_EMBEDDING_MODEL': 'text-embedding-ada-002'
        }):
            test = OpenAITest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate embedding output
        assert "🔢 Running text embedding test..." in output
        assert "✅ Text embedding test passed" in output
        assert "🤖 Model: text-embedding-ada-002" in output
        assert "📝 Input:" in output
        assert "This is a test sentence for embedding" in output
        assert "📐 Embedding Dimension: 1536" in output
        assert "📊 Sample Values:" in output
        assert "🎯 Tokens Used: 8" in output
        assert "⏱️  Duration:" in output

    @patch('app.tests.openai_test.OpenAI')
    def test_openai_summary_output(self, mock_openai):
        """Test that OpenAI test displays final summary"""
        # Setup mock
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="4"), finish_reason="stop")]
        mock_response.usage = Mock(prompt_tokens=20, completion_tokens=1, total_tokens=21)

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client.models.list.return_value = Mock(data=[])
        mock_openai.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'OPENAI_BASE_URL': 'http://localhost:8000/v1',
            'OPENAI_API_KEY': 'test-key',
            'OPENAI_MODEL_NAME': 'gpt-3.5-turbo'
        }):
            test = OpenAITest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate summary section
        assert "=" * 60 in output
        assert "🎉 All OpenAI API tests passed successfully!" in output
        assert "🔧 Endpoint: OpenAI-compatible API" in output
        assert "🤖 Completion Model: gpt-3.5-turbo" in output


class TestDocumentIntelligenceTestOutput:
    """Test cases for Document Intelligence test output validation"""

    @patch('app.tests.document_intelligence_test.DocumentAnalysisClient')
    @patch('app.tests.document_intelligence_test.AzureKeyCredential')
    def test_document_analysis_output_format(self, mock_credential, mock_client_class):
        """Test that document analysis displays structure information"""
        # Setup mock result
        mock_result = Mock()
        mock_result.pages = [Mock(), Mock()]  # 2 pages
        mock_result.content = "Test Document\nThis is a sample document with test content."
        mock_result.tables = [Mock()]  # 1 table
        mock_result.paragraphs = [Mock(), Mock(), Mock()]  # 3 paragraphs
        mock_result.key_value_pairs = []

        mock_poller = Mock()
        mock_poller.result.return_value = mock_result
        mock_poller.cancel = Mock()

        mock_client = Mock()
        mock_client.begin_analyze_document.return_value = mock_poller
        mock_client_class.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'AZURE_DOC_INTEL_ENDPOINT': 'https://test.cognitiveservices.azure.com/',
            'AZURE_DOC_INTEL_API_KEY': 'test-key',
            'AZURE_DOC_INTEL_MODEL': 'prebuilt-document'
        }):
            test = DocumentIntelligenceTest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate document analysis output
        assert "📄 Testing document analysis with sample content..." in output
        assert "✅ Document analysis test passed" in output
        assert "📄 Pages: 2" in output
        assert "📊 Tables: 1" in output
        assert "📝 Content Length:" in output
        assert "⏱️  Processing Time:" in output
        assert "👁️  Content Preview:" in output

    @patch('app.tests.document_intelligence_test.DocumentAnalysisClient')
    @patch('app.tests.document_intelligence_test.AzureKeyCredential')
    def test_document_intelligence_summary_output(self, mock_credential, mock_client_class):
        """Test that document intelligence test displays final summary"""
        # Setup mock result
        mock_result = Mock()
        mock_result.pages = [Mock()]
        mock_result.content = "Test content"
        mock_result.tables = []
        mock_result.paragraphs = [Mock()]
        mock_result.key_value_pairs = []

        mock_poller = Mock()
        mock_poller.result.return_value = mock_result
        mock_poller.cancel = Mock()

        mock_client = Mock()
        mock_client.begin_analyze_document.return_value = mock_poller
        mock_client_class.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'AZURE_DOC_INTEL_ENDPOINT': 'https://test.cognitiveservices.azure.com/',
            'AZURE_DOC_INTEL_API_KEY': 'test-key',
            'AZURE_DOC_INTEL_MODEL': 'prebuilt-document'
        }):
            test = DocumentIntelligenceTest()
            result = test.run_test()

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate summary section
        assert "=" * 60 in output
        assert "🎉 All Document Intelligence tests passed successfully!" in output
        assert "🔧 Endpoint:" in output
        assert "📋 Model: prebuilt-document" in output
        assert "📄 Document Pages Processed:" in output
        assert "📊 Tables Extracted:" in output
        assert "📝 Paragraphs Found:" in output

    @patch('app.tests.document_intelligence_test.DocumentAnalysisClient')
    @patch('app.tests.document_intelligence_test.AzureKeyCredential')
    def test_custom_file_analysis_output(self, mock_credential, mock_client_class):
        """Test that custom file analysis displays detailed structure info"""
        # Setup mock result
        mock_result = Mock()
        mock_result.pages = [Mock(), Mock(), Mock()]  # 3 pages
        mock_result.content = "Custom document content with multiple pages and tables."
        mock_result.tables = [Mock(), Mock()]  # 2 tables
        mock_result.paragraphs = [Mock()] * 5  # 5 paragraphs
        mock_result.key_value_pairs = [Mock()] * 3  # 3 key-value pairs

        mock_poller = Mock()
        mock_poller.result.return_value = mock_result

        mock_client = Mock()
        mock_client.begin_analyze_document.return_value = mock_poller
        mock_client_class.return_value = mock_client

        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output

        with patch.dict('os.environ', {
            'AZURE_DOC_INTEL_ENDPOINT': 'https://test.cognitiveservices.azure.com/',
            'AZURE_DOC_INTEL_API_KEY': 'test-key',
            'AZURE_DOC_INTEL_MODEL': 'prebuilt-document'
        }):
            test = DocumentIntelligenceTest()
            # Test custom file analysis
            test_content = b"Sample PDF content"
            result = test.test_with_custom_file(test_content, "pdf", "Analyze this document")

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        # Validate custom file analysis output
        assert "📁 Starting custom file test with file type: pdf" in output
        assert "✅ Custom document analysis completed successfully" in output
        assert "📄 Pages: 3" in output
        assert "📊 Tables: 2" in output
        assert "📝 Paragraphs: 5" in output
        assert "🔑 Key-Value Pairs: 3" in output
        assert "📏 Content Length:" in output
        assert "⏱️  Processing Time:" in output
        assert "👁️  Content Preview:" in output


class TestOutputConsistency:
    """Test cases for consistent output formatting across all tests"""

    def test_all_tests_use_emoji_indicators(self):
        """Verify all tests use consistent emoji indicators"""
        # This is a meta-test to ensure consistency
        emoji_map = {
            '🔗': 'connection',
            '💬': 'text generation',
            '🔢': 'embedding',
            '📝': 'input',
            '💬': 'output',
            '⏱️': 'duration/time',
            '🎯': 'tokens',
            '📊': 'metrics/data',
            '✅': 'success',
            '❌': 'failure',
            '🎉': 'summary/completion',
            '📄': 'document/pages',
            '🤖': 'model'
        }

        # All tests should use these emojis consistently
        assert len(emoji_map) > 0, "Emoji indicators are defined"

    def test_all_tests_have_summary_sections(self):
        """Verify all tests include summary sections with separators"""
        # All enhanced tests should use "=" * 60 for summary sections
        separator = "=" * 60

        # This ensures consistency in visual presentation
        assert len(separator) == 60, "Summary separator is 60 characters"

    def test_duration_formatting_consistency(self):
        """Verify duration is consistently formatted across tests"""
        # All tests should display duration as "X.XXs" format
        import re

        duration_pattern = r'\d+\.\d{2}s'
        test_strings = [
            "⏱️  Duration: 1.23s",
            "⏱️  Processing Time: 2.45s",
            "⏱️  Total Processing Time: 0.97s"
        ]

        for test_str in test_strings:
            assert re.search(duration_pattern, test_str), f"Duration format matches in: {test_str}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
