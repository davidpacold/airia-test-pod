#!/usr/bin/env python3
"""
Test script to verify file upload functionality for the AI test pod.
This script tests various file upload scenarios with different file types.
"""

import base64
import io
import json
import os
import tempfile
from pathlib import Path

import requests


def create_test_files():
    """Create various test files for upload testing."""
    test_files = {}

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="test_uploads_")

    # Create text file
    text_file = Path(temp_dir) / "test.txt"
    text_file.write_text("This is a test file for upload testing.\nIt contains multiple lines.\n")
    test_files["text"] = str(text_file)

    # Create JSON file
    json_file = Path(temp_dir) / "test.json"
    json_file.write_text(json.dumps({"test": "data", "number": 123}, indent=2))
    test_files["json"] = str(json_file)

    # Create Markdown file
    md_file = Path(temp_dir) / "test.md"
    md_file.write_text("# Test Document\n\nThis is a **markdown** file with *formatting*.\n")
    test_files["markdown"] = str(md_file)

    # Create CSV file
    csv_file = Path(temp_dir) / "test.csv"
    csv_file.write_text("name,age,city\nJohn,30,NYC\nJane,25,LA\n")
    test_files["csv"] = str(csv_file)

    # Create a simple PNG image (1x1 pixel, red)
    png_file = Path(temp_dir) / "test.png"
    # PNG header + IHDR + pixel data + IEND
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    png_file.write_bytes(png_data)
    test_files["png"] = str(png_file)

    # Create a simple PDF
    pdf_file = Path(temp_dir) / "test.pdf"
    # Minimal PDF with "Hello World"
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000351 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
445
%%EOF"""
    pdf_file.write_bytes(pdf_content)
    test_files["pdf"] = str(pdf_file)

    return test_files, temp_dir


def test_file_upload(base_url, auth_token, endpoint, file_path, file_type):
    """Test file upload to a specific endpoint."""
    print(f"\nTesting {file_type} upload to {endpoint}...")

    headers = {
        "Cookie": f"access_token=Bearer {auth_token}"
    }

    with open(file_path, "rb") as f:
        files = {
            "file": (Path(file_path).name, f, f"application/{file_type}")
        }
        data = {
            "prompt": f"Test prompt for {file_type} file upload"
        }

        try:
            response = requests.post(
                f"{base_url}{endpoint}",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                print(f"✅ {file_type} upload successful!")
                result = response.json()
                if "success" in result:
                    print(f"   Success: {result.get('success')}")
                if "model" in result:
                    print(f"   Model: {result.get('model')}")
                if "response_time_ms" in result:
                    print(f"   Response time: {result.get('response_time_ms')}ms")
            else:
                print(f"❌ {file_type} upload failed!")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:500]}")

        except Exception as e:
            print(f"❌ Error uploading {file_type}: {str(e)}")

    return response.status_code == 200


def main():
    """Main test function."""
    # Configuration
    BASE_URL = os.getenv("TEST_POD_URL", "http://localhost:8000")
    USERNAME = os.getenv("TEST_POD_USER", "admin")
    PASSWORD = os.getenv("TEST_POD_PASS", "admin")

    print(f"Testing file uploads for: {BASE_URL}")
    print("=" * 60)

    # Step 1: Login to get auth token
    print("\n1. Authenticating...")
    login_response = requests.post(
        f"{BASE_URL}/token",
        data={
            "username": USERNAME,
            "password": PASSWORD,
            "grant_type": "password"
        }
    )

    if login_response.status_code != 200:
        print(f"❌ Authentication failed: {login_response.text}")
        return 1

    auth_token = login_response.json()["access_token"]
    print("✅ Authentication successful!")

    # Step 2: Create test files
    print("\n2. Creating test files...")
    test_files, temp_dir = create_test_files()
    print(f"✅ Created test files in: {temp_dir}")

    # Step 3: Test file uploads to different endpoints
    print("\n3. Testing file uploads...")

    test_cases = [
        # OpenAI endpoint tests
        ("openai", "/api/tests/openai/custom", ["text", "json", "markdown", "pdf", "png"]),
        # Document Intelligence endpoint tests
        ("docintel", "/api/tests/docintel/custom", ["pdf", "png"]),
        # Embeddings endpoint tests
        ("embeddings", "/api/tests/embeddings/custom", ["text", "json", "markdown", "csv", "pdf"]),
    ]

    results = []
    for test_name, endpoint, file_types in test_cases:
        print(f"\n--- Testing {test_name} endpoint ---")
        for file_type in file_types:
            if file_type in test_files:
                success = test_file_upload(
                    BASE_URL,
                    auth_token,
                    endpoint,
                    test_files[file_type],
                    file_type
                )
                results.append((test_name, file_type, success))

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, _, success in results if success)
    failed = len(results) - passed

    for test_name, file_type, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {file_type}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)
    print(f"\n✅ Cleaned up temporary files")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())