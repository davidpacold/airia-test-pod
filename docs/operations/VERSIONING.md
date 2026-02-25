# Version Management

## OCI Registry

Helm charts are published to GitHub Container Registry as OCI artifacts. No `helm repo add` or `helm repo update` needed — OCI always pulls the latest version.

```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-values.yaml \
  --namespace airia --create-namespace
```

Every release automatically pushes the chart to `ghcr.io/davidpacold/airia-test-pod/charts`. No local cache to become stale.

## Pre-Upgrade Version Check

The Helm chart includes a pre-upgrade job that checks for newer versions during `helm upgrade`.

**Configuration:**
```yaml
versionCheck:
  enabled: true     # Enable automatic version checking
  strict: false     # Set true to block upgrades if not using latest
```

In strict mode, upgrades will fail if you're not deploying the latest version:
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-values.yaml \
  --set versionCheck.strict=true \
  --namespace airia
```

## CI/CD Validation

After each release, the CI pipeline validates:
- OCI chart is pullable
- Chart version matches expected version
- Docker image is available

## Pin a Specific Version

```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version 1.0.200 \
  -f my-values.yaml \
  --namespace airia
```

## Troubleshooting

**"Error: failed to download chart"** — Authentication required:
```bash
echo $GITHUB_TOKEN | helm registry login ghcr.io -u USERNAME --password-stdin
```

**Version check job is slow** — Disable if not needed:
```yaml
versionCheck:
  enabled: false
```
