# Airia Infrastructure Test Pod v2: Production Readiness Design

**Date:** 2026-02-24
**Status:** Approved
**Audience:** Customer-facing + SE-facing tool

## Overview

Complete overhaul of the Airia Infrastructure Test Pod to make it a production-grade, standardized infrastructure validation tool. Customers and SEs deploy it via Helm before installing the Airia platform. It tests connectivity to databases, storage, AI services, DNS, SSL, and Kubernetes resources with fully deterministic, standardized test inputs — no user-provided content.

## Design Principles

1. **Zero user input beyond configuration** — All tests use standardized prompts, images, and queries. No custom prompt fields, no file uploads. Configure via Helm values, press Run.
2. **Per-provider AI cards** — Each AI provider gets its own dashboard card with sub-tests for the capabilities it supports.
3. **Secure by default** — CSP headers, no CDN dependencies, escaped output, rate limiting, proper secret management.
4. **Production Kubernetes patterns** — Proper health probes, graceful shutdown, structured logging, thread safety.

---

## Test Inventory (16 cards)

### Storage Tests (3 cards)

| Card | Config | Sub-tests |
|------|--------|-----------|
| Azure Blob Storage | accountName, accountKey, containerName | Connect, container access, upload 67-byte test file, download + verify, list, cleanup |
| Amazon S3 | region, accessKeyId, secretAccessKey, bucketName | Connect, bucket access, upload, download + verify, list, cleanup |
| MinIO Storage | endpointUrl, accessKey, secretKey, bucketName | Connect, bucket access, upload, download + verify, list, cleanup |

**Status:** Exist today, working. Fix `is_configured()` to respect `enabled` flag.

### AI Provider Tests (6 cards)

Each provider tests the capabilities it supports using standardized inputs:

- **Chat prompt:** `"What is 2+2? Reply with just the number."`
- **Embedding input:** `"The quick brown fox jumps over the lazy dog."`
- **Vision input:** Bundled ~50KB test image at `static/test-assets/test-image.png` (a simple diagram with shapes and text labels). Prompt: `"Describe what you see in this image in one sentence."`

| Card | Provider | Sub-tests | Config |
|------|----------|-----------|--------|
| Azure OpenAI | Azure OpenAI Service | Chat, Embedding, Vision | endpoint, apiKey, chatDeployment, embeddingDeployment, visionDeployment |
| AWS Bedrock | Amazon Bedrock | Chat, Embedding, Vision | region, accessKeyId, secretAccessKey, chatModelId, embeddingModelId, visionModelId |
| OpenAI | OpenAI API | API key validation, Chat | apiKey, model (default: gpt-4o-mini) |
| Anthropic | Anthropic API | API key validation, Chat | apiKey, model (default: claude-sonnet-4-20250514) |
| Google Gemini | Google AI | API key validation, Chat | apiKey, model (default: gemini-2.0-flash) |
| Mistral | Mistral AI | API key validation, Chat | apiKey, model (default: mistral-small-latest) |

**Azure OpenAI** and **AWS Bedrock** get full capability testing (chat + embedding + vision) because these are the platforms where customers deploy their own models. Vision sub-test is optional — only runs if visionDeployment/visionModelId is configured.

**OpenAI, Anthropic, Gemini, Mistral** are connectivity + API key validation with a simple chat completion. These confirm the customer has a valid key and network access.

**Architecture:**
```
BaseTest (ABC)
  └── BaseAIProviderTest
        ├── AzureOpenAITest      (chat + embedding + vision)
        ├── BedrockTest          (chat + embedding + vision)
        ├── OpenAIDirectTest     (key + chat)
        ├── AnthropicTest        (key + chat)
        ├── GeminiTest           (key + chat)
        └── MistralTest          (key + chat)
```

`BaseAIProviderTest` provides shared logic for:
- Standardized chat sub-test (send fixed prompt, validate non-empty response, measure latency)
- Standardized embedding sub-test (send fixed text, validate dimensions returned)
- Standardized vision sub-test (send bundled image, validate non-empty description)

Each provider subclass implements `_create_chat_client()`, `_create_embedding_client()`, `_create_vision_client()` with provider-specific SDK/auth setup.

### Document Processing (1 card)

| Card | Sub-tests | Config |
|------|-----------|--------|
| Document Intelligence | API connectivity, analyze sample document, model info | endpoint, apiKey, model |

**Status:** Exists, working. No changes needed beyond code quality fixes.

### Database Tests (2 cards)

| Card | Sub-tests | Config |
|------|-----------|--------|
| PostgreSQL | Connect, list databases, list extensions, SSL mode check | host, port, database, username, password, sslmode |
| Cassandra | Connect, keyspace access, read/write test, cluster health | hosts, port, username, password, keyspace, datacenter, useSsl |

**Status:** Exist, working. Fixes needed:
- PostgreSQL: Reuse single connection across sub-tests instead of 3 separate connections
- Cassandra: Replace bare `except:` with `except Exception:`
- Cassandra: Fix SSL cert verification (currently `CERT_NONE`)

### Infrastructure Tests (4 cards)

| Card | Sub-tests | Config |
|------|-----------|--------|
| Kubernetes PVC | Create test PVC, check status, cleanup | storageClass, testPvcSize |
| GPU Detection | nvidia-smi availability, driver version, GPU count, memory | gpu.enabled, gpu.required |
| DNS Resolution | Resolve each hostname, report IP addresses, TTL, response time | dns.hostnames (comma-separated), dns.timeout |
| SSL Certificates | Cert validity, expiration warning, chain validation, TLS version | ssl.testUrls (comma-separated) + ad-hoc UI entry, ssl.warningDays |

**DNS Resolution is new.** Implementation:
- Uses `socket.getaddrinfo()` for basic resolution and `dnspython` library for detailed queries
- Config: `DNS_TEST_HOSTNAMES` env var, comma-separated for pre-configured hosts (e.g., `"api.example.com,db.internal.svc"`)
- UI: Also allows user to enter arbitrary hostnames in the dashboard (e.g., `box.com`, `yahoo.com`) to test ad-hoc DNS resolution
- Reports: resolved IPs, response time in ms, any resolution failures
- `is_configured()` always returns `True` (DNS is always available; pre-configured hostnames are optional)
- **Exception to the no-user-input rule:** DNS and SSL tests accept user-entered hostnames since the purpose is testing arbitrary network connectivity. Hostnames are validated (alphanumeric + dots + hyphens only) before use.

**SSL exists** but has dead code methods that always return success. Clean up and fix.

---

## Code Removals

The following features are removed to align with the standardized-test-only design:

1. **File upload system** — Remove `app/utils/file_handler.py` (`FileUploadHandler`, `ProcessedFile`)
2. **Custom prompt endpoints** — Remove `POST /api/tests/openai/custom`, `POST /api/tests/llama/custom`, `POST /api/tests/docintel/custom`, `POST /api/tests/embeddings/custom`
3. **Input sanitization for AI prompts** — Remove `sanitize_ai_prompt()` from `app/utils/sanitization.py`
4. **Custom prompt env vars** — Remove `OPENAI_CUSTOM_PROMPT`, `OPENAI_CUSTOM_SYSTEM_MESSAGE`
5. **Upload form UI** — Remove all `<form>` elements and file upload JavaScript from dashboard.html
6. **Ollama native test** — Remove `app/tests/llama_test.py`. Ollama endpoints are OpenAI-compatible and can be tested via the OpenAI Direct card with `baseUrl` override.
7. **Dead code** — Remove `models.py` unused `TestResult`/`TestSuiteResult`, `index.html`, `showLoadingState`/`hideLoadingState`, duplicate `toggleDocumentContent`, dead SSL methods

---

## Security Fixes

### Critical
1. **XSS prevention** — Add `esc()` helper function to escape all `innerHTML` interpolations in all formatter functions. Every server response field must be escaped before DOM insertion.
2. **Content-Security-Policy header** — Add CSP that blocks inline scripts (move all JS to external files first), restricts `connect-src` to `'self'`, blocks `eval`.
3. **Self-host axios** — Download axios.min.js into `static/`, remove CDN `<script>` tag. Eliminates supply chain risk.
4. **Rate limiting** — Add middleware to limit `/login` and `/token` to 5 attempts per minute per IP. Use in-memory counter (no Redis needed for single-replica).

### High
5. **NOTES.txt** — Remove plain-text password. Print username only, instruct user to retrieve password via `kubectl get secret`.
6. **OpenAI API key in deployment.yaml** — Move from literal `value:` to `secretKeyRef`.
7. **Timing side-channel** — Always call `verify_password()` regardless of username match. Use `hmac.compare_digest()` for username comparison.

### Medium
8. **Thread-safe dict access** — All `TestRunner` methods that read `test_results` must acquire `self._lock` and return a copy.
9. **Password hash caching** — Guard `_cached_password_hash` with `threading.Lock`.

---

## Production Hardening

### Health & Lifecycle
1. **Readiness probe** — Change from `/health/live` to `/health/ready` in deployment.yaml
2. **Startup config validation** — Add lifespan handler that validates critical config at boot (e.g., `SECRET_KEY` is not default in production)
3. **Graceful shutdown** — Add shutdown handler that sets a flag to prevent new test runs and waits for in-progress tests to complete (up to 30s)

### Logging & Observability
4. **Structured logging** — Configure logging in app startup (not as module import side-effect). Use JSON formatter for Kubernetes log collectors.
5. **Replace all `print()` calls** — Use `logger.info()` / `logger.error()` throughout
6. **Request ID middleware** — Generate `X-Request-ID` header, thread through log context

### Configuration
7. **Consolidate `os.getenv()` calls** — Move all env var reads into Pydantic Settings. No direct `os.getenv()` anywhere except `config.py`.
8. **Remove `readOnlyRootFilesystem` comment** — Enable it in values.yaml, add `emptyDir` mount for `/tmp`

### Helm
9. **Timestamp annotation** — Replace `now` with chart version for stable annotations
10. **RBAC** — Document that `storageclasses` requires ClusterRole or will be silently ignored
11. **Pre-upgrade job** — Add `namespace:` field, pin `alpine/helm` image version

---

## UI Redesign

### Architecture
1. **Extract JavaScript** — Move all inline JS from `dashboard.html` to `static/dashboard.js` (~2000 lines). Enables browser caching and CSP compliance.
2. **Deduplicate formatters** — Create shared `buildTestHeader(result, label)` and `buildSubTests(subTests)` helpers. Each formatter only provides test-specific details section.
3. **Remove custom test forms** — All form elements, file upload UI, and custom prompt inputs removed. Dashboard is pure run-and-view.

### Visual
4. **Dark mode** — Add `@media (prefers-color-scheme: dark)` with inverted color tokens
5. **Icon system** — Replace emoji with inline SVG icons for cross-platform consistency
6. **Brand identity** — Add Airia logo/wordmark to header
7. **Clean up CSS** — Deduplicate `result-header`/`stat-label` definitions, consolidate ~90 color tokens to ~20, remove stale comments
8. **Fix version display** — Use template variable `{{ version }}` for fallback instead of hardcoded string

### Accessibility
9. **Focus rings** — Restore visible focus indicators (remove `outline: none` without replacement)
10. **ARIA labels** — Add `aria-label` to all "Run Test" buttons identifying which test they control
11. **Status announcements** — Add `aria-live="polite"` to status badge elements

### Responsiveness
12. **Mobile breakpoints** — Add breakpoints for header, notification container, test grid at <600px
13. **Fix status badge** — Wire up "READY" badge to actual connectivity state or remove it

---

## New Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `dnspython` | DNS resolution test | ~2.6 |
| `anthropic` | Anthropic API test | ~0.40 |
| `google-generativeai` | Google Gemini API test | ~0.8 |
| `mistralai` | Mistral API test | ~1.0 |

**Note:** `boto3` is already a dependency (used for S3 test). Bedrock uses the same SDK via `boto3.client('bedrock-runtime')`.
**Note:** `openai` is already a dependency. OpenAI Direct test uses it directly.

---

## Helm Values Structure

```yaml
config:
  auth:
    username: "admin"
    password: "changeme"
    secretKey: "change-this"

  # Storage
  blobStorage:
    enabled: false
    accountName: ""
    accountKey: ""
    containerName: "test-container"

  s3:
    enabled: false
    region: "us-east-1"
    accessKeyId: ""
    secretAccessKey: ""
    bucketName: "test-bucket"

  minio:
    enabled: false
    endpointUrl: ""
    accessKey: ""
    secretKey: ""
    bucketName: "test-bucket"

  # AI Providers (full capability)
  azureOpenai:
    enabled: false
    endpoint: ""
    apiKey: ""
    chatDeployment: ""        # e.g., "gpt-4.1"
    embeddingDeployment: ""   # e.g., "text-embedding-3-large"
    visionDeployment: ""      # e.g., "gpt-4o" (optional)

  bedrock:
    enabled: false
    region: "us-east-1"
    accessKeyId: ""
    secretAccessKey: ""
    chatModelId: ""           # e.g., "anthropic.claude-3-sonnet"
    embeddingModelId: ""      # e.g., "amazon.titan-embed-text-v2"
    visionModelId: ""         # optional

  # AI Providers (connectivity + chat only)
  openai:
    enabled: false
    apiKey: ""
    model: "gpt-4o-mini"

  anthropic:
    enabled: false
    apiKey: ""
    model: "claude-sonnet-4-20250514"

  gemini:
    enabled: false
    apiKey: ""
    model: "gemini-2.0-flash"

  mistral:
    enabled: false
    apiKey: ""
    model: "mistral-small-latest"

  # Document Processing
  documentIntelligence:
    enabled: false
    endpoint: ""
    apiKey: ""
    model: "prebuilt-document"

  # Databases
  postgresql:
    enabled: false
    host: ""
    port: "5432"
    database: "postgres"
    username: ""
    password: ""
    sslmode: "require"

  cassandra:
    enabled: false
    hosts: ""
    port: "9042"
    username: ""
    password: ""
    keyspace: ""
    datacenter: "datacenter1"
    useSsl: false

  # Infrastructure
  dns:
    enabled: false
    hostnames: ""             # Comma-separated: "api.example.com,db.internal"
    timeout: 10

  ssl:
    enabled: false
    testUrls: ""              # Comma-separated: "https://api.example.com"
    warningDays: 30

  kubernetes:
    storageClass: "default"
    testPvcSize: "1Gi"

  gpu:
    enabled: true
    required: false
```

---

## Implementation Phases

### Phase 1: Security & Correctness
- XSS fixes (escape all innerHTML)
- Self-host axios, add CSP header
- Rate limiting on auth
- Fix timing side-channel in auth
- Thread safety fixes in TestRunner
- Fix is_configured() for all tests
- Fix Helm secrets (NOTES.txt, secretKeyRef)
- Remove custom prompt/upload endpoints and UI
- Remove dead code

### Phase 2: New AI Provider Tests + DNS
- Create BaseAIProviderTest base class
- Implement AzureOpenAITest (replaces current openai test)
- Implement BedrockTest
- Implement OpenAIDirectTest, AnthropicTest, GeminiTest, MistralTest
- Bundle test image for vision tests
- Implement DNSTest
- Add new dependencies to requirements.txt
- Update Helm chart (configmap, secrets, deployment env vars, values.yaml)

### Phase 3: Production Hardening
- Fix readiness probe
- Add startup config validation
- Add graceful shutdown handler
- Structured logging (replace print, configure at startup)
- Request ID middleware
- Consolidate os.getenv into Pydantic Settings
- Fix PostgreSQL connection reuse
- Fix Cassandra bare except and SSL
- Clean up SSL test dead code
- Helm fixes (timestamp, RBAC docs, pre-upgrade job)

### Phase 4: UI Redesign
- Extract inline JS to static/dashboard.js
- Deduplicate formatter functions
- Dark mode CSS
- Replace emoji with SVG icons
- Accessibility fixes (focus rings, aria-labels, aria-live)
- Mobile responsiveness
- Clean up CSS (dedup selectors, consolidate tokens)
- Fix version display
- Remove index.html
