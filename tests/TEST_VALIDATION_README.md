# AI/ML Test Output Validation

This directory contains test cases to validate that all AI/ML tests display the correct output in the UI with proper formatting and completeness.

## Overview

The test suite `test_ai_ml_output_validation.py` validates the enhanced output for:
- **Llama Model Tests** - Text generation and Llama-specific prompts
- **Embedding Tests** - Single and batch embeddings with similarity validation
- **OpenAI Tests** - Completion, embedding, and connection tests
- **Document Intelligence Tests** - Document analysis and structure extraction

## Running the Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-mock
```

### Run All Validation Tests

```bash
# From the project root
pytest tests/test_ai_ml_output_validation.py -v

# Run with coverage
pytest tests/test_ai_ml_output_validation.py -v --cov=app/tests --cov-report=html
```

### Run Specific Test Classes

```bash
# Test only Llama output validation
pytest tests/test_ai_ml_output_validation.py::TestLlamaTestOutput -v

# Test only Embedding output validation
pytest tests/test_ai_ml_output_validation.py::TestEmbeddingTestOutput -v

# Test only OpenAI output validation
pytest tests/test_ai_ml_output_validation.py::TestOpenAITestOutput -v

# Test only Document Intelligence output validation
pytest tests/test_ai_ml_output_validation.py::TestDocumentIntelligenceTestOutput -v

# Test output consistency across all tests
pytest tests/test_ai_ml_output_validation.py::TestOutputConsistency -v
```

## What These Tests Validate

### 1. Llama Model Test Output

✅ **Text Generation Output:**
- Displays input prompt
- Shows model response (preview)
- Includes duration metrics
- Uses consistent emoji indicators

✅ **Llama-Style Prompt Output:**
- Shows Llama-specific questions
- Displays model responses mentioning "Llama"
- Includes timing information

**Example Expected Output:**
```
💬 Running text generation test...
✅ Text generation test passed
   📝 Input: Hello! Can you introduce yourself briefly?
   💬 Output: I am a helpful AI assistant designed to...
   ⏱️  Duration: 2.27s
```

### 2. Embedding Test Output

✅ **Single Embedding Output:**
- Shows input text
- Displays embedding dimensions (e.g., 1536)
- Shows value range (min/max)
- Includes token usage
- Displays processing time

✅ **Batch Embedding Output:**
- Shows batch size
- Displays average time per embedding
- Shows total processing time

✅ **Summary Section:**
- Model name
- Embedding dimensions
- Processing times
- Uses separator lines (60 '=' characters)

**Example Expected Output:**
```
🔢 Running single embedding test...
✅ Single embedding test passed
   📝 Input: 'This is a test sentence for embedding generation.'
   📐 Embedding Dimension: 1536
   ⏱️  Processing Time: 0.342s
   📊 Value Range: [-0.015234, 0.023456]
   🎯 Tokens Used: 12
```

### 3. OpenAI Test Output

✅ **Connection Test:**
- Shows number of models found
- Displays response time

✅ **Completion Test:**
- Shows model name
- Displays input prompt
- Shows model output
- Includes validation status (e.g., "contains 4")
- Token breakdown (prompt + completion + total)
- Duration

✅ **Embedding Test:**
- Model name
- Input text
- Embedding dimensions
- Sample values (first 5)
- Token usage

✅ **Summary Section:**
- Endpoint type (Azure vs OpenAI-compatible)
- Completion and embedding models

**Example Expected Output:**
```
💬 Running text completion test...
✅ Text completion test passed
   🤖 Model: gpt-3.5-turbo
   📝 Input: What is 2+2? Answer with just the number.
   💬 Output: 4
   ✓ Validation: Passed (contains 4)
   🎯 Tokens: 21 (20 prompt + 1 completion)
   ⏱️  Duration: 1.23s
```

### 4. Document Intelligence Test Output

✅ **Document Analysis:**
- Number of pages
- Table count
- Content length
- Processing time
- Content preview (first 100 chars)

✅ **Custom File Analysis:**
- All above metrics plus:
- Paragraph count
- Key-value pairs extracted

✅ **Summary Section:**
- Endpoint URL
- Model name
- Document structure statistics

**Example Expected Output:**
```
✅ Document analysis test passed
   📄 Pages: 2
   📊 Tables: 1
   📝 Content Length: 523 characters
   ⏱️  Processing Time: 4.23s
   👁️  Content Preview: Test Document This is a sample...
```

## Test Coverage

The validation tests cover:

### Output Format Tests (70% of tests)
- ✅ Correct emoji usage
- ✅ Proper indentation (3 spaces for details)
- ✅ Metric formatting (decimal places, units)
- ✅ Text truncation (preview lengths)

### Content Validation Tests (20% of tests)
- ✅ All expected fields present
- ✅ Values within expected ranges
- ✅ Proper data types

### Consistency Tests (10% of tests)
- ✅ Emoji indicators used consistently
- ✅ Duration format (X.XXs)
- ✅ Summary sections use 60-char separators
- ✅ Success/failure indicators

## Expected Test Results

When all tests pass, you should see:

```
tests/test_ai_ml_output_validation.py::TestLlamaTestOutput::test_llama_completion_output_format PASSED
tests/test_ai_ml_output_validation.py::TestLlamaTestOutput::test_llama_prompt_test_output_format PASSED
tests/test_ai_ml_output_validation.py::TestEmbeddingTestOutput::test_single_embedding_output_format PASSED
tests/test_ai_ml_output_validation.py::TestEmbeddingTestOutput::test_batch_embedding_output_format PASSED
tests/test_ai_ml_output_validation.py::TestEmbeddingTestOutput::test_embedding_summary_output PASSED
tests/test_ai_ml_output_validation.py::TestOpenAITestOutput::test_openai_connection_output PASSED
tests/test_ai_ml_output_validation.py::TestOpenAITestOutput::test_openai_completion_output_format PASSED
tests/test_ai_ml_output_validation.py::TestOpenAITestOutput::test_openai_embedding_output_format PASSED
tests/test_ai_ml_output_validation.py::TestOpenAITestOutput::test_openai_summary_output PASSED
tests/test_ai_ml_output_validation.py::TestDocumentIntelligenceTestOutput::test_document_analysis_output_format PASSED
tests/test_ai_ml_output_validation.py::TestDocumentIntelligenceTestOutput::test_document_intelligence_summary_output PASSED
tests/test_ai_ml_output_validation.py::TestDocumentIntelligenceTestOutput::test_custom_file_analysis_output PASSED
tests/test_ai_ml_output_validation.py::TestOutputConsistency::test_all_tests_use_emoji_indicators PASSED
tests/test_ai_ml_output_validation.py::TestOutputConsistency::test_all_tests_have_summary_sections PASSED
tests/test_ai_ml_output_validation.py::TestOutputConsistency::test_duration_formatting_consistency PASSED

============================== 15 passed in X.XXs ===============================
```

## Troubleshooting

### Common Issues

**Issue: Import errors**
```bash
# Solution: Ensure you're running from project root
cd /Users/davidpacold/Documents/Github/airia-test-pod
pytest tests/test_ai_ml_output_validation.py -v
```

**Issue: Mock not working**
```bash
# Solution: Install pytest-mock
pip install pytest-mock
```

**Issue: Tests fail due to output format changes**
- Check if the actual test files have been modified
- Update the validation tests to match new format
- Ensure emoji indicators are still consistent

## Adding New Tests

To add validation for a new AI/ML test:

1. **Create a new test class:**
```python
class TestNewAITestOutput:
    """Test cases for new AI test output validation"""
```

2. **Add output format test:**
```python
@patch('app.tests.new_test.SomeClient')
def test_new_ai_output_format(self, mock_client):
    # Setup mocks
    # Capture stdout
    # Run test
    # Validate output contains expected elements
```

3. **Add to consistency tests if needed:**
```python
def test_new_ai_uses_consistent_emojis(self):
    # Validate emoji usage
```

## Output Standards

All AI/ML tests should follow these standards:

### Emoji Indicators
- 🔗 Connection/API tests
- 💬 Text generation/completion
- 🔢 Embeddings
- 📝 Input data
- 💬 Output/response
- ⏱️  Duration/time
- 🎯 Tokens
- 📊 Metrics/statistics
- ✅ Success
- ❌ Failure
- 🎉 Summary/completion
- 📄 Documents/pages
- 🤖 Model name

### Formatting Rules
1. **Indentation:** 3 spaces for detail lines
2. **Duration:** Always format as `X.XXs` (2 decimal places + 's')
3. **Summary:** Use `"=" * 60` separator lines
4. **Preview:** Truncate long text with `...`
   - Prompts: 80 chars max
   - Responses: 100 chars max
   - Content: 100 chars max

### Required Sections
1. **Test announcement:** e.g., "💬 Running text completion test..."
2. **Success/failure:** e.g., "✅ Text completion test passed"
3. **Details:** Model, input, output, metrics
4. **Summary (if all pass):** Final statistics with separators

## Continuous Integration

These tests can be integrated into CI/CD:

```yaml
# .github/workflows/test-ai-ml-output.yml
name: AI/ML Output Validation

on: [push, pull_request]

jobs:
  validate-output:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pytest pytest-mock
      - name: Run output validation tests
        run: |
          pytest tests/test_ai_ml_output_validation.py -v
```

## Contributing

When modifying AI/ML test output:

1. Update the corresponding test in `test_ai_ml_output_validation.py`
2. Run validation tests to ensure format consistency
3. Document any new emoji indicators or formatting rules
4. Ensure backward compatibility where possible

## License

Same as parent project.
