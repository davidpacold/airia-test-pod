# Airia Test Pod - Deployment Guide

## 🚀 OCI Registry Deployment

The Airia Test Pod uses **OCI registry** for Helm chart distribution. No `helm repo add` or `helm repo update` needed!

### Quick Start

```bash
# Deploy with OCI registry - always gets latest version!
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f your-config.yaml \
  --namespace default \
  --install
```

### Install Specific Version

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version 1.0.159 \
  -f your-config.yaml \
  --namespace default \
  --install
```

### Automated Upgrade Script

Use our automated upgrade script for the easiest experience:

```bash
# From the airia-test-pod repository
./scripts/upgrade.sh --oci -f /path/to/your-config.yaml

# Or remotely
curl -sSL https://raw.githubusercontent.com/davidpacold/airia-test-pod/main/scripts/upgrade.sh | \
  bash -s -- --oci -f your-config.yaml
```

---

## Version Management

### Check Current Installed Version

```bash
helm list -n default
```

### Check Available Versions

```bash
helm show chart oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod
```

### Install Specific Version

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version 1.0.159 \
  --namespace default
```

## Automatic Version Checking

The Helm chart includes **automatic version checking** to help ensure you're always using the latest version!

### How It Works

During `helm upgrade`, a pre-upgrade hook automatically:
1. ✅ Checks if you're installing the latest version
2. ⚠️ Warns you if a newer version is available
3. 🚫 Optionally blocks upgrades if not using the latest (strict mode)

### Configuration

In your `values.yaml` or config file:

```yaml
versionCheck:
  enabled: true          # Enable/disable version checking
  useOCI: true          # Use OCI registry for checks
  strict: false         # Set to true to block upgrades of older versions
```

### Strict Mode

To **enforce** always using the latest version:

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f your-config.yaml \
  --set versionCheck.strict=true
```

With strict mode enabled, Helm will **fail the upgrade** if you're not using the latest version!

---

## Automated Release Process

When code is pushed to `main`, the following happens automatically:

1. ✅ **Version Calculation** - Next version is calculated from GitHub releases
2. ✅ **Version Updates** - All files updated atomically with new version
3. ✅ **Helm Chart Packaging** - Chart packaged
4. ✅ **OCI Registry Publish** - Chart published to GitHub Container Registry
5. ✅ **Docker Image Build** - Image built and tagged as `latest` + version
6. ✅ **Health Validation** - Verifies:
   - OCI chart is pullable
   - Chart version matches expected version
   - Docker image is available
7. ✅ **GitHub Release** - Release created with chart and release notes

---

## Troubleshooting

### Problem: "Error: failed to download chart"

**Cause:** Authentication or network issue with OCI registry.

**Solution:**
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | helm registry login ghcr.io -u USERNAME --password-stdin

# Or use Docker credentials
docker login ghcr.io
```

### Problem: Want to verify chart before installing

**Solution:**
```bash
# Show chart metadata
helm show chart oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod

# Show all chart details
helm show all oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod

# Dry-run to see what will change
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f your-config.yaml \
  --dry-run --debug
```

### Problem: Need to rollback to previous version

**Solution:**
```bash
# View revision history
helm history airia-test-pod -n default

# Rollback to previous revision
helm rollback airia-test-pod -n default

# Or rollback to specific revision
helm rollback airia-test-pod 11 -n default
```

---

## Recommended Workflow

```bash
# 1. Navigate to your configs directory
cd /Users/your-username/configs

# 2. Check current version
helm list -n default | grep airia-test-pod

# 3. Check for new versions (optional)
helm show chart oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod

# 4. Review what will change (optional but recommended)
helm diff upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f your-config.yaml

# 5. Perform the upgrade
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f your-config.yaml \
  --namespace default

# 6. Verify the upgrade
kubectl get pods -n default | grep airia-test-pod
kubectl rollout status deployment/airia-test-pod -n default
```

## Checking Pod Health After Deployment

```bash
# Check pod status
kubectl get pods -n default -l app.kubernetes.io/name=airia-test-pod

# Check pod logs
kubectl logs -n default -l app.kubernetes.io/name=airia-test-pod --tail=100

# Port forward to access locally
kubectl port-forward -n default svc/airia-test-pod 8080:8080

# Test health endpoints
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
curl http://localhost:8080/version
```

---

## Why OCI Registry?

**Benefits:**
- ✅ No `helm repo add` or `helm repo update` needed
- ✅ Always pulls latest version by default
- ✅ Better authentication and security
- ✅ Same infrastructure as Docker images
- ✅ Faster and more reliable than traditional Helm repos
- ✅ No caching issues

**GitHub Repository:** https://github.com/davidpacold/airia-test-pod
**OCI Registry:** oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod
**Docker Registry:** ghcr.io/davidpacold/airia-test-pod
