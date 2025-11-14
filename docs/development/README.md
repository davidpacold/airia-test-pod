# Development Documentation

This directory contains development guides, project history, and reference materials for contributors.

## Available Documents

### [Cleanup Summary](cleanup-summary.md)
History of repository cleanup including:
- Files deleted and why
- Files relocated
- Benefits of cleanup
- How to regenerate build artifacts

### [Reorganization Plan](reorganization-plan.md)
Repository structure improvements including:
- Current issues identified
- Proposed structure
- Implementation steps
- Benefits and rationale

## Development Setup

### Prerequisites
- Python 3.9+
- Docker
- Kubernetes (for K8s testing)
- Helm (for chart development)

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python run_tests.py

# Run application locally
python app/main.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Run manual tests
python tests/manual_tests/cassandra_test.py
```

## Contributing

When contributing to the project:

1. **Follow the structure** - Keep documentation organized
2. **Update tests** - Add tests for new features
3. **Document changes** - Update relevant docs and CHANGELOG
4. **Clean commits** - Write clear commit messages
5. **Test locally** - Run tests before committing

## Related Resources

- [Main README](../../README.md)
- [Operations Guide](../operations/)
- [Deployment Guide](../deployment/)
- [Manual Tests](../../tests/manual_tests/)
