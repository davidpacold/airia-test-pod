# Airia Test Pod v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the test pod into a production-grade, 16-card infrastructure validation tool with standardized tests, 6 AI provider cards, DNS testing, security hardening, and a polished UI with dark mode.

**Architecture:** FastAPI + Jinja2 templates, per-provider AI test classes inheriting from BaseAIProviderTest, all test inputs standardized (fixed prompts, bundled test image), Helm chart with proper secret management. Simplify code wherever possible — fewer abstractions, less duplication, direct implementations.

**Tech Stack:** Python 3.11, FastAPI, OpenAI SDK, Anthropic SDK, google-generativeai, mistralai, boto3 (Bedrock), dnspython, Pydantic Settings, Helm 3

**Design Doc:** `docs/plans/2026-02-24-v2-production-readiness-design.md`

---

## Phase 1: Security & Correctness Fixes

### Task 1: Self-host axios and add CSP header

**Files:**
- Create: `static/vendor/axios.min.js`
- Modify: `templates/dashboard.html:8`
- Modify: `app/main.py:40-63`

**Step 1:** Download axios to static/vendor/

```bash
mkdir -p static/vendor
curl -o static/vendor/axios.min.js https://unpkg.com/axios@1.7.9/dist/axios.min.js
```

**Step 2:** Update dashboard.html line 8 — change CDN src to `/static/vendor/axios.min.js`

**Step 3:** Add CSP header in main.py security middleware:

```python
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)
```

**Step 4:** Test locally, verify no CSP console errors

**Step 5:** Commit: `security: self-host axios and add Content-Security-Policy header`

---

### Task 2: Add XSS escaping to all dynamic content rendering

**Files:**
- Modify: `templates/dashboard.html`

**Step 1:** Add `esc()` helper at top of script block:

```javascript
function esc(str) {
    if (str == null) return '';
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(String(str)));
    return d.innerHTML;
}
```

**Step 2:** Wrap ALL server-returned data in `esc()` before DOM insertion: `result.message`, `result.model`, `log.message`, `test.endpoint`, `st.message`, `st.remediation`, notification `title`/`message`/`details`, etc.

Do NOT escape locally-defined values (statusIcon, statusClass, numeric computations).

**Step 3:** Fix double-escaped `\\n` — replace with `<br>` in error display strings.

**Step 4:** Commit: `security: escape all dynamic content to prevent XSS`

---

### Task 3: Fix authentication security

**Files:**
- Modify: `app/auth.py:24-40`
- Modify: `app/main.py`

**Step 1:** In auth.py — add `threading.Lock` for hash cache, use `hmac.compare_digest` for username, always call verify_password regardless of username match.

**Step 2:** In main.py — add simple in-memory rate limiter (10 attempts/minute per IP) for `/login` and `/token`. Use a dict + threading.Lock, prune old entries on each check.

**Step 3:** Commit: `security: fix timing side-channel, add rate limiting on auth`

---

### Task 4: Fix thread safety in TestRunner

**Files:**
- Modify: `app/tests/test_runner.py`

**Step 1:** In every method that reads `self.test_results` (`get_test_status`, `get_test_logs`, `get_remediation_suggestions`, `get_test_summary`): acquire `self._lock`, copy the dict, release lock, then process the copy.

**Step 2:** Commit: `fix: thread-safe locking on all TestRunner dict reads`

---

### Task 5: Remove custom prompt/upload system and dead code

**Files:**
- Modify: `app/main.py` (remove custom test endpoints)
- Delete: `app/utils/file_handler.py`, `app/utils/file_processors.py`
- Delete: `app/tests/llama_test.py`
- Delete: `templates/index.html`
- Modify: `app/tests/test_runner.py` (remove llama registration)
- Modify: `app/models.py` (remove unused TestResult/TestSuiteResult)
- Modify: `app/utils/sanitization.py` (remove sanitize_ai_prompt, simplify)

**Step 1:** Remove all `POST /api/tests/*/custom` endpoints from main.py. Remove File/Form/UploadFile imports. Remove file_handler and sanitize_ai_prompt imports.

**Step 2:** Delete dead files. Remove llama from test_runner. Remove unused Pydantic models.

**Step 3:** Simplify `app/utils/sanitization.py` — keep only `sanitize_login_credentials()` and `sanitize_user_input()`. Remove file upload validation code.

**Step 4:** Verify app starts.

**Step 5:** Commit: `refactor: remove custom prompt/upload system and dead code`

---

### Task 6: Fix Helm secrets and health probes

**Files:**
- Modify: `helm/airia-test-pod/templates/NOTES.txt`
- Modify: `helm/airia-test-pod/templates/deployment.yaml`
- Modify: `helm/airia-test-pod/templates/secrets.yaml`

**Step 1:** NOTES.txt — remove plain-text password, show kubectl command instead.

**Step 2:** deployment.yaml — change OpenAI API key from literal `value:` to `secretKeyRef`. Change readiness probe from `/health/live` to `/health/ready`.

**Step 3:** Commit: `security: fix NOTES.txt password leak, secret injection, readiness probe`

---

### Task 7: Fix is_configured() for all tests

**Files:**
- Modify: test files as needed

**Step 1:** Ensure every test's `is_configured()` returns `False` when the test has only default/empty values. The Helm chart already gates env var injection behind `enabled: true`, so absent env vars = unconfigured.

**Step 2:** Commit: `fix: is_configured() returns False for unconfigured tests`

---

## Phase 2: New AI Provider Tests + DNS

### Task 8: Add new Python dependencies

**Files:**
- Modify: `requirements.txt`

Add: `anthropic==0.42.0`, `google-generativeai==0.8.4`, `mistralai==1.6.0`, `dnspython==2.7.0`

Commit: `deps: add anthropic, google-generativeai, mistralai, dnspython`

---

### Task 9: Bundle test image for vision tests

**Files:**
- Create: `static/test-assets/test-image.png`

Generate a simple ~50KB image using Pillow with labeled shapes (square, circle, triangle). Any vision model should be able to describe it.

Commit: `feat: add bundled test image for vision model testing`

---

### Task 10: Create BaseAIProviderTest base class

**Files:**
- Create: `app/tests/ai_provider_base.py`

Shared base class with:
- Standardized constants: `CHAT_PROMPT`, `EMBEDDING_INPUT`, `VISION_PROMPT`
- `load_test_image_base64()` helper
- `run_test()` that calls `_test_chat()`, `_test_embedding()`, `_test_vision()` based on `_supports_*` flags
- Subclasses only implement provider-specific client creation and API calls

Keep it simple — no over-abstraction. Each provider still owns its full API call logic.

Commit: `feat: add BaseAIProviderTest with standardized test inputs`

---

### Task 11: Implement AzureOpenAITest (chat + embedding + vision)

**Files:**
- Create: `app/tests/azure_openai_test.py`

Uses `openai.AzureOpenAI` client. Three sub-tests:
- Chat: send fixed prompt to `chatDeployment`, validate response
- Embedding: send fixed text to `embeddingDeployment`, report dimensions
- Vision: send bundled image to `visionDeployment`, validate description

Env vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, `AZURE_OPENAI_VISION_DEPLOYMENT`

Commit: `feat: add Azure OpenAI test with chat, embedding, and vision`

---

### Task 12: Implement BedrockTest (chat + embedding + vision)

**Files:**
- Create: `app/tests/bedrock_test.py`

Uses `boto3.client('bedrock-runtime')`. Chat via Converse API, embeddings via InvokeModel, vision via Converse with image.

Env vars: `BEDROCK_REGION`, `BEDROCK_ACCESS_KEY_ID`, `BEDROCK_SECRET_ACCESS_KEY`, `BEDROCK_CHAT_MODEL_ID`, `BEDROCK_EMBEDDING_MODEL_ID`, `BEDROCK_VISION_MODEL_ID`

Commit: `feat: add AWS Bedrock test with chat, embedding, and vision`

---

### Task 13: Implement simple provider tests (OpenAI, Anthropic, Gemini, Mistral)

**Files:**
- Create: `app/tests/openai_direct_test.py`
- Create: `app/tests/anthropic_test.py`
- Create: `app/tests/gemini_test.py`
- Create: `app/tests/mistral_test.py`

Each is simple: inherit BaseAIProviderTest, set `_supports_chat = True`, implement `_test_chat()` using the provider's SDK. API key validation + single chat completion.

- OpenAI: `openai.OpenAI(api_key=...)` — env: `OPENAI_DIRECT_API_KEY`, `OPENAI_DIRECT_MODEL`
- Anthropic: `anthropic.Anthropic(api_key=...)` — env: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- Gemini: `google.generativeai` — env: `GEMINI_API_KEY`, `GEMINI_MODEL`
- Mistral: `mistralai.Mistral(api_key=...)` — env: `MISTRAL_API_KEY`, `MISTRAL_MODEL`

Commit: `feat: add OpenAI, Anthropic, Gemini, and Mistral provider tests`

---

### Task 14: Implement DNS Resolution test

**Files:**
- Create: `app/tests/dns_test.py`
- Modify: `app/main.py` (add ad-hoc resolve endpoint)

DNS test with:
- `is_configured()` based on `DNS_TEST_HOSTNAMES` env var
- `resolve_hostname(hostname)` method using `socket.getaddrinfo()`
- Reports IPs, latency per hostname
- Ad-hoc `POST /api/tests/dns/resolve` endpoint for user-entered hostnames (validated: alphanumeric + dots + hyphens only, max 253 chars)

Commit: `feat: add DNS resolution test with ad-hoc hostname lookup`

---

### Task 15: Register all new tests, remove old ones

**Files:**
- Modify: `app/tests/test_runner.py`
- Delete: `app/tests/openai_test.py`, `app/tests/embedding_test.py`
- Modify: `app/main.py` (remove old test-specific endpoints, keep generic ones)

Update `_register_tests()` with all 16 tests. Remove old openai_test.py and embedding_test.py. Simplify main.py to only have generic endpoints: `POST /api/tests/run-all`, `POST /api/tests/{test_id}`, `GET /api/tests/status`, plus the DNS/SSL ad-hoc endpoints.

Commit: `feat: register all 16 tests, remove old test implementations`

---

### Task 16: Update Helm chart for all new providers

**Files:**
- Modify: `helm/airia-test-pod/values.yaml`
- Modify: `helm/airia-test-pod/templates/configmap.yaml`
- Modify: `helm/airia-test-pod/templates/secrets.yaml`
- Modify: `helm/airia-test-pod/templates/deployment.yaml`
- Modify: `helm/airia-test-pod/templates/NOTES.txt`

Add config sections for: azureOpenai, bedrock, openai, anthropic, gemini, mistral, dns. Each gated by `enabled: true`. Non-sensitive values in configmap, credentials in secrets. Follow existing patterns.

Commit: `feat: update Helm chart with all 16 test provider configurations`

---

## Phase 3: Production Hardening

### Task 17: Add startup validation and graceful shutdown

**Files:**
- Modify: `app/main.py`

Add `lifespan` context manager: startup validates config and logs version. Shutdown signals test runner to stop and waits up to 30s for in-progress tests.

Commit: `feat: add startup validation and graceful shutdown`

---

### Task 18: Fix logging — replace all print() with logger

**Files:**
- Modify: `app/main.py` (configure logging at startup)
- Modify: `app/tests/test_runner.py` (remove basicConfig)
- Modify: `app/exceptions/handlers.py` (remove print calls)
- Modify: all test files that use print()

Move `logging.basicConfig()` to lifespan startup. Replace every `print()` in production code with `logger.info()` or `logger.error()`. Remove emoji from log messages.

Commit: `fix: structured logging, replace all print() with logger`

---

### Task 19: Consolidate os.getenv into Pydantic Settings

**Files:**
- Modify: `app/config.py`
- Modify: `app/exceptions/handlers.py`

Add `debug: bool = False` to Settings. Replace `os.getenv("DEBUG")` in handlers.py with `get_settings().debug`.

Commit: `refactor: consolidate os.getenv into Pydantic Settings`

---

### Task 20: Fix PostgreSQL connection reuse and Cassandra issues

**Files:**
- Modify: `app/tests/postgres_test_v2.py`
- Modify: `app/tests/cassandra_test.py`

PostgreSQL: open one connection in `run_test()`, pass to all sub-tests, close in finally block.
Cassandra: replace bare `except:` with `except Exception:`.

Commit: `fix: PostgreSQL connection reuse, Cassandra bare except`

---

### Task 21: Clean up SSL test dead code

**Files:**
- Modify: `app/tests/ssl_test.py`

Remove 3 unused methods (`_check_certificate_expiration`, `_check_hostname_match`, `_check_certificate_signature`). Fix the no-op `_check_certificate_signature_from_info` — either implement or remove.

Commit: `fix: remove dead SSL test methods`

---

### Task 22: Helm hardening

**Files:**
- Modify: `helm/airia-test-pod/values.yaml` (enable readOnlyRootFilesystem)
- Modify: `helm/airia-test-pod/templates/deployment.yaml` (emptyDir /tmp, fix timestamp)
- Modify: `helm/airia-test-pod/templates/pre-upgrade-job.yaml` (namespace, pin image)

Commit: `fix: Helm hardening - readOnlyFS, pin images, fix namespace`

---

## Phase 4: UI Redesign

### Task 23: Extract inline JS to static/dashboard.js

**Files:**
- Create: `static/dashboard.js`
- Modify: `templates/dashboard.html`

Move ~2000 lines of inline JS to external file. Pass template variables via small `window.APP_CONFIG` data block.

Commit: `refactor: extract inline JavaScript to static/dashboard.js`

---

### Task 24: Simplify and deduplicate formatter functions

**Files:**
- Modify: `static/dashboard.js`

Create `buildTestHeader(result, label)` and `buildSubTests(subTests)` helpers. Each formatter becomes 5-15 lines of test-specific details + shared helpers. Remove duplicate functions (`toggleDocumentContent`), dead code (`showLoadingState`), unused variables.

Commit: `refactor: simplify formatters with shared helpers, remove dead code`

---

### Task 25: Update dashboard HTML for 16 test cards

**Files:**
- Modify: `templates/dashboard.html`

Update test grid with all 16 cards grouped by category. Add DNS hostname input and SSL URL input fields. Remove all old custom prompt forms and file upload UI.

Commit: `feat: update dashboard with 16 test cards`

---

### Task 26: Add dark mode and SVG icon system

**Files:**
- Modify: `static/style.css`
- Modify: `templates/dashboard.html`

Add SVG icon sprite (5-6 icons: check-circle, x-circle, alert-triangle, check, x). Add `@media (prefers-color-scheme: dark)` with inverted tokens. Consolidate ~90 CSS color tokens to ~20. Remove duplicate selectors and stale comments.

Commit: `feat: dark mode, SVG icons, CSS cleanup`

---

### Task 27: Accessibility and responsiveness

**Files:**
- Modify: `templates/dashboard.html`, `templates/login.html`, `static/style.css`

Fix focus rings (login.html). Add aria-labels to Run Test buttons. Add aria-live to status badges. Add mobile breakpoints for header, notifications, grid. Remove static "READY" badge. Fix version display to use template variable.

Commit: `feat: accessibility, mobile responsiveness, version display fix`

---

### Task 28: Final integration test and release

**Files:**
- All version files

Full local test: login, run all tests, dark mode, mobile view. Bump version to 2.0.0. Commit, tag, push.

Commit: `release: v2.0.0 - production-ready test pod with 16 test cards`

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1 | 1-7 | Security & correctness |
| Phase 2 | 8-16 | New AI providers, DNS, Helm |
| Phase 3 | 17-22 | Production hardening |
| Phase 4 | 23-28 | UI redesign & simplification |

**28 tasks, 4 phases.** Each phase is a separate PR. Phase 1 deploys first (security).
