# Manual Test Scripts

This directory contains standalone test scripts and test configuration files for manual testing and debugging.

## Test Scripts

### Cassandra Tests
- **cassandra_test.py** - Cassandra database connectivity test
- **test_cassandra_connection.py** - Alternative Cassandra connection test
- **test_cassandra_k8s.sh** - Kubernetes-based Cassandra testing script

### File Upload Tests
- **test_file_upload.py** - Test file upload functionality

## Helm Test Configurations

### Test Value Files
- **test-helm-scenarios.yaml** - Various Helm deployment scenarios
- **test-values-empty-tag.yaml** - Test with empty image tag
- **test-values-no-tag.yaml** - Test with no image tag specified

## Usage

These scripts are intended for:
- Manual testing during development
- Debugging specific components
- Validating Helm chart configurations
- Testing database connections

## Running Manual Tests

```bash
# Run Cassandra test
python tests/manual_tests/cassandra_test.py

# Run Cassandra connection test
python tests/manual_tests/test_cassandra_connection.py

# Run file upload test
python tests/manual_tests/test_file_upload.py

# Test Helm scenarios
helm install test-release helm/airia-test-pod -f tests/manual_tests/test-helm-scenarios.yaml
```

## Note

For automated testing, use the main test suite:
```bash
pytest tests/
python run_tests.py
```
