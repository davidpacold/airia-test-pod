# V2 Bugfix, Hardening & Documentation Design

**Goal:** Fix all critical and important bugs, security issues, CI/CD problems, and documentation gaps discovered in the post-v2 audit.

**Audit scope:** 60 issues across Python app, frontend JS/CSS, Helm chart, GitHub Actions workflows, and customer-facing documentation.

---

## Phase 1: Security & Correctness Fixes

Fixes that prevent auth bypass, crashes, or security vulnerabilities.

1. **JWT unsanitized username** — `main.py:221,286` uses raw `username` instead of `sanitized_username` in `create_access_token`
2. **`request.client` None crash** — `main.py:188,257` dereferences `request.client.host` without null check; crashes behind proxies
3. **`require_auth` returns RedirectResponse** — `auth.py:96-109` should raise HTTPException instead of returning a response object
4. **Rate limiter memory leak** — `main.py:29-46` never prunes stale IP keys from `_rate_limit_attempts`
5. **Sanitization order bug** — `sanitization.py:46-50` runs `html.escape` before pattern removal, making regexes dead code
6. **Bare `except:` in S3/MinIO** — `s3_test.py:265,424,439` and `minio_test.py:340,354` swallow KeyboardInterrupt
7. **MinIO `verify=self.secure` misuse** — `minio_test.py:149-156` conflates SSL toggle with cert verification
8. **SSL timezone-naive expiry** — `ssl_test.py:298-301` uses `datetime.now()` instead of `datetime.now(timezone.utc)`
9. **Cassandra CERT_NONE** — `cassandra_test.py:86-89` silently disables cert verification with no opt-in
10. **Default secret key warning** — No startup warning when JWT secretKey is the default publicly-known value
11. **CSP blocks inline scripts** — `main.py:93-99` CSP blocks the two inline `<script>` tags in dashboard.html; move to data attributes

## Phase 2: Bug Fixes & Code Quality

Logic bugs, dead code, inconsistencies, and inefficiencies.

12. **Critical extensions object/string mismatch** — `dashboard.js:165-174` treats extension objects as strings; always shows missing
13. **`runAllTests` missing finally** — `dashboard.js:287-321` button stays disabled on error
14. **`handleApiError` unused det** — `dashboard.js:54-71` context param is silently dropped
15. **TestService invalid ErrorCodes** — `test_service.py:192,203,258` references non-existent enum values
16. **BaseTest.execute() missing log** — `base_test.py:194-195` early return bypasses completion logging
17. **AI provider TestResult timing** — `ai_provider_base.py:61-62` creates own TestResult; timeout returns RUNNING status
18. **Test image error message** — `ai_provider_base.py:25-34` no error handling on missing file
19. **get_test_summary pending/running** — `test_runner.py:221-225` conflates running with failed
20. **SSL signature check no-op** — `ssl_test.py:696-713` always returns success
21. **SSL dead code duplication** — `ssl_test.py:74-78` duplicate `add_sub_test` in both branches
22. **DocIntel duplicate methods** — `document_intelligence_test.py:213-310` near-identical URL/content methods
23. **DocIntel wasteful connectivity test** — `document_intelligence_test.py:164-193` submits full document then cancels
24. **GPU redundant nvidia-smi** — `gpu_test.py:303-317` runs 4-7 subprocess calls; consolidate to 1
25. **PVC double k8s config load** — `pvc_test.py:40-71` loads config in `is_configured()` and `run_test()`
26. **Unused TestStatus imports** — 5 test files import but never use TestStatus
27. **Blob storage triple client** — `blob_storage_test.py:63,77` creates 2 extra BlobServiceClient instances
28. **DNS hostname regex** — `dns_test.py:118` rejects single-char valid hostnames
29. **AI sub-test schema inconsistency** — `ai_provider_base.py:75-85` uses `status` string vs `success` bool
30. **Bedrock Titan-only response key** — `bedrock_test.py:93-95` hardcodes `embedding` key
31. **S3/MinIO os.getenv** — Use Pydantic Settings instead of manual os.getenv
32. **S3/MinIO naive datetime** — Use `datetime.now(timezone.utc)` consistently
33. **Optional test skip not recorded** — `base_test.py:321-366` silently drops optional tests from results
34. **Duplicate import os** — `main.py:156` redundant import inside function

## Phase 3: CI/CD Pipeline Fixes

Fix the release, rollback, and cleanup workflows.

35. **Command injection in release.yml** — User inputs interpolated directly in `run:` blocks; use env vars
36. **Command injection in rollback.yml** — Same pattern with `reason`, `namespace`, `release_name` inputs
37. **Duplicate Release creation** — Two jobs create same GitHub Release; broken heredoc quoting
38. **Tag not created before Docker checkout** — Docker build checks out a tag that doesn't exist yet
39. **Docker built from pre-update code** — Tag points to commit before version strings updated
40. **Dead auto-rollback-check job** — `rollback.yml:367-414` can never execute; inverted loop logic
41. **Cleanup dry-run bypass on schedule** — `registry-cleanup.yml` runs real cleanup on cron triggers
42. **Division by zero in cleanup** — `registry-cleanup.yml:270-271` when total_images is 0
43. **Missing permissions blocks** — registry-cleanup.yml and rollback.yml lack top-level permissions
44. **Artifact retention too short** — 7-day retention insufficient for rollback scenarios
45. **Redundant version indirection step** — `release.yml:313-317` copies output with no transformation
46. **Forced rollouts on every upgrade** — `deployment.yaml` timestamp annotation + BUILD_TIMESTAMP env
47. **Detached HEAD push to main** — `release.yml:200` can fail or overwrite on tag-triggered runs
48. **Missing packages:read permission** — `post-deployment-validation` job can't read OCI registry

## Phase 4: Documentation & Helm Fixes

Fix customer-facing docs, Helm chart issues, and accessibility.

49. **README namespace mismatch** — Install uses `default`, port-forward uses `airia`
50. **README config keys wrong** — Uses `config.openai.*` instead of `config.azureOpenai.*`
51. **Chart.yaml wrong URLs** — `home` and `sources` point to wrong GitHub repo
52. **NOTES.txt wrong support URL** — Links to `github.com/airia/test-pod` instead of correct repo
53. **NOTES.txt stale upgrade command** — Uses traditional repo path instead of OCI
54. **Deployment guide outdated config** — References removed features (llama, embeddings, openaiCompatible)
55. **Add cleanup step to README** — Missing "Step 4: Clean Up" in quick start
56. **Remove trailing build noise** — README has CI artifact comments at bottom
57. **RBAC storageclasses in Role** — Cluster-scoped resource in namespace-scoped Role has no effect
58. **Pre-upgrade-job security context** — Job runs as root with application RBAC service account
59. **image.tag label empty** — `deployment.yaml:30` doesn't apply default like the image ref does
60. **autoscaling maxReplicas: 100** — Unreasonable default for validation tool; change to 3
61. **aria-live on status spans** — Screen readers don't announce test status changes
62. **Dark mode contrast** — Sub-test messages below WCAG AA threshold
63. **Explicit Jinja2 autoescape** — Configure autoescaping explicitly, don't rely on default
64. **Create basic-values.yaml** — Example config file referenced by README but missing
65. **Helm README ingress default wrong** — Says `true`, actually `false`
66. **Version template escaping** — URL-encode version in URL contexts

---

## Architecture Notes

- All fixes are backward-compatible; no API changes
- Phase 1 and 2 are Python/JS changes testable locally
- Phase 3 requires careful workflow testing (can test with `act` or dry-run)
- Phase 4 is documentation/Helm; no runtime risk
- Each phase produces a single commit or small commit group
