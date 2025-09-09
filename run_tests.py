#!/usr/bin/env python3
"""
Test runner script for local development.

This script provides an easy way to run tests locally with various options.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n🔄 {description}")
    print("=" * (len(description) + 3))
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for airia-test-pod")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--security", action="store_true", help="Run security scans")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--pattern", help="Run tests matching pattern")
    
    args = parser.parse_args()
    
    # Default to unit tests if no specific option is chosen
    if not any([args.unit, args.integration, args.coverage, args.security, args.quality, args.all]):
        args.unit = True
    
    success_count = 0
    total_count = 0
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Install dependencies check
    print("🔍 Checking dependencies...")
    try:
        import pytest
        import coverage
    except ImportError:
        print("❌ Missing required packages. Please run:")
        print("   pip install -r requirements-dev.txt")
        sys.exit(1)
    
    if args.unit or args.all:
        total_count += 1
        pytest_cmd = "python -m pytest tests/ --ignore=tests/integration"
        
        if args.verbose:
            pytest_cmd += " -v"
        if args.fast:
            pytest_cmd += " -m 'not slow'"
        if args.pattern:
            pytest_cmd += f" -k '{args.pattern}'"
            
        pytest_cmd += " --tb=short"
        
        if run_command(pytest_cmd, "Running Unit Tests"):
            success_count += 1
            print("✅ Unit tests passed")
        else:
            print("❌ Unit tests failed")
    
    if args.integration or args.all:
        total_count += 1
        
        # Check if integration testing is enabled
        integration_enabled = os.environ.get("INTEGRATION_TESTS_ENABLED", "0") == "1"
        if not integration_enabled:
            print("⚠️  Integration tests require INTEGRATION_TESTS_ENABLED=1")
            print("   To run integration tests:")
            print("   1. Start services: docker-compose -f docker-compose.test.yml up -d")
            print("   2. Run tests: INTEGRATION_TESTS_ENABLED=1 python run_tests.py --integration")
            success_count += 1  # Don't fail if not enabled
        else:
            pytest_cmd = "python -m pytest tests/integration/"
            
            if args.verbose:
                pytest_cmd += " -v"
            if args.fast:
                pytest_cmd += " -m 'not slow'"
            if args.pattern:
                pytest_cmd += f" -k '{args.pattern}'"
                
            pytest_cmd += " --tb=short"
            
            if run_command(pytest_cmd, "Running Integration Tests"):
                success_count += 1
                print("✅ Integration tests passed")
            else:
                print("❌ Integration tests failed")
    
    if args.coverage or args.all:
        total_count += 1
        coverage_cmd = ("python -m pytest tests/ "
                       "--cov=app "
                       "--cov-report=html:htmlcov "
                       "--cov-report=term-missing "
                       "--cov-fail-under=80")
        
        if args.verbose:
            coverage_cmd += " -v"
        if args.fast:
            coverage_cmd += " -m 'not slow'"
            
        if run_command(coverage_cmd, "Running Tests with Coverage"):
            success_count += 1
            print("✅ Coverage tests passed")
            print("📊 Coverage report generated in htmlcov/index.html")
        else:
            print("❌ Coverage tests failed")
    
    if args.quality or args.all:
        quality_checks = [
            ("python -m black --check app/ tests/", "Black code formatting check"),
            ("python -m isort --check-only app/ tests/", "Import sorting check"),
            ("python -m flake8 app/ tests/", "Flake8 linting"),
            ("python -m mypy app/ --ignore-missing-imports", "Type checking"),
        ]
        
        for cmd, description in quality_checks:
            total_count += 1
            if run_command(cmd, description):
                success_count += 1
                print(f"✅ {description} passed")
            else:
                print(f"❌ {description} failed")
    
    if args.security or args.all:
        security_checks = [
            ("python -m safety check", "Safety vulnerability check"),
            ("python -m bandit -r app/", "Bandit security analysis"),
            ("python -m pip_audit", "pip-audit dependency check"),
        ]
        
        for cmd, description in security_checks:
            total_count += 1
            # Security checks are informational, don't fail on them
            try:
                if run_command(cmd, description):
                    success_count += 1
                    print(f"✅ {description} completed")
                else:
                    success_count += 1  # Count as success even if issues found
                    print(f"⚠️  {description} found issues (review required)")
            except:
                success_count += 1
                print(f"⚠️  {description} completed with warnings")
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 10)
    print(f"Completed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("✅ All checks passed!")
        sys.exit(0)
    else:
        print("❌ Some checks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()