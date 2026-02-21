# Airia Infrastructure Test Pod

## What This Is
A Kubernetes-native infrastructure validation tool. Customers deploy this via Helm chart (OCI registry) before installing the Airia platform. It tests connectivity to databases, storage, AI services, and Kubernetes resources, providing a web dashboard with pass/fail results and remediation guidance.

## Tech Stack
- Python 3.11, FastAPI, Uvicorn, Jinja2 templates
- Pydantic Settings for configuration
- passlib/bcrypt + python-jose for JWT auth
- Docker multi-stage build, Helm 3 chart
- Published to ghcr.io/davidpacold/airia-test-pod (OCI)

## Key Directories
- `app/` - FastAPI application
  - `app/main.py` - Routes and endpoints
  - `app/config.py` - Pydantic Settings (env var config, cached)
  - `app/auth.py` - JWT authentication with bcrypt
  - `app/tests/` - Infrastructure test classes (BaseTest -> individual tests)
  - `app/tests/base_test.py` - BaseTest ABC + TestSuite + TestResult
  - `app/tests/test_runner.py` - TestRunner singleton (thread-safe)
- `helm/airia-test-pod/` - Helm chart (Chart.yaml, values.yaml, templates/)
- `templates/` - Jinja2 HTML templates (dashboard, login)
- `static/` - CSS/JS assets
- `scripts/upgrade.sh` - OCI-based upgrade helper

## Running Locally
```bash
pip install -r requirements.txt
SECURE_COOKIES=false uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
# Open http://localhost:8080 (login: admin/changeme)
```

## How Tests Work
Each test inherits from `BaseTest` (app/tests/base_test.py). Tests are registered in `TestRunner._register_tests()`. The `execute()` method handles timeout enforcement (ThreadPoolExecutor), retry logic, and error handling. Tests run concurrently when using "Run All". Results are stored in the TestRunner singleton with thread-safe locking.

## Release Workflow
- Version is tracked in: Chart.yaml, app/main.py, app/config.py
- `.github/workflows/release.yml` builds Docker image + Helm chart
- Published to OCI registry: `oci://ghcr.io/davidpacold/airia-test-pod/charts`
- Triggered by tag push (`git tag v1.0.X && git push origin v1.0.X`)

## Conventions
- Test classes: one per service, inherit BaseTest, implement run_test()
- Config: use Pydantic Settings native env loading (no manual os.getenv in config.py)
- Secrets: never log, always from env vars / K8s secrets
- Endpoints: auth required via Depends(require_auth)
- Thread safety: use self._lock for shared state in TestRunner
