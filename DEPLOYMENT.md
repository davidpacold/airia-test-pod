# Airia Test Pod - Deployment Guide

## 🚀 Recommended: OCI Registry (No Repo Updates Needed!)

The **easiest and most reliable** method is using OCI registry. This eliminates the need for `helm repo update`!

### Deploy with OCI Registry

```bash
# Always pulls the latest version automatically!
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f aws-pre-install-config.yaml \
  --namespace default \
  --install
```

### Install Specific Version with OCI

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version 1.0.159 \
  -f aws-pre-install-config.yaml \
  --namespace default \
  --install
```

### Automated Upgrade Script

Use the provided script for an even easier experience:

```bash
# From the airia-test-pod repository
./scripts/upgrade.sh --oci -f /path/to/aws-pre-install-config.yaml

# Or from your configs directory
curl -sSL https://raw.githubusercontent.com/davidpacold/airia-test-pod/main/scripts/upgrade.sh | \
  bash -s -- --oci -f aws-pre-install-config.yaml
```

---

## 📦 Alternative: Traditional Helm Repository

If you prefer the traditional Helm repository method:

### First Time Setup

1. **Add the Helm repository:**
   ```bash
   helm repo add airia-test-pod https://davidpacold.github.io/airia-test-pod/
   ```

2. **Verify the repository was added:**
   ```bash
   helm repo list
   ```

### Deploying the Latest Version

**IMPORTANT:** Always update your local Helm repository before upgrading!

```bash
# Step 1: Update your local Helm repository cache
helm repo update airia-test-pod

# Step 2: Check available versions
helm search repo airia-test-pod/airia-test-pod --versions

# Step 3: Upgrade to the latest version
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  -f aws-pre-install-config.yaml \
  --namespace default \
  --install
```

### Complete Deployment Command (One-liner)

From your `Airia-Configs/AWS` directory:

```bash
helm repo update airia-test-pod && \
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  -f aws-pre-install-config.yaml \
  --namespace default \
  --install
```

## Version Management

### Check Current Installed Version

```bash
helm list -n default
```

### Check What Version Will Be Installed

```bash
helm search repo airia-test-pod/airia-test-pod
```

### Install a Specific Version

```bash
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  -f aws-pre-install-config.yaml \
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
  useOCI: true          # Use OCI registry for checks (recommended)
  strict: false         # Set to true to block upgrades of older versions
```

### Strict Mode

To **enforce** always using the latest version:

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f aws-pre-install-config.yaml \
  --set versionCheck.strict=true
```

With strict mode enabled, Helm will **fail the upgrade** if you're not using the latest version!

---

## Automated Release Process

When code is pushed to `main`, the following happens automatically:

1. ✅ **Version Calculation** - Next version is calculated from GitHub releases
2. ✅ **Version Updates** - All files updated atomically with new version
3. ✅ **Helm Chart Packaging** - Chart packaged and added to repository
4. ✅ **OCI Registry Publish** - Chart published to GitHub Container Registry (OCI)
5. ✅ **Docker Image Build** - Image built and tagged as `latest` + version
6. ✅ **GitHub Pages Deploy** - Helm repository updated at https://davidpacold.github.io/airia-test-pod/
7. ✅ **Health Validation** - Verifies:
   - GitHub Pages is accessible
   - `index.yaml` contains the new version
   - Chart package (`.tgz`) is downloadable
   - Docker image is available
8. ✅ **GitHub Release** - Release created with chart and release notes

## Troubleshooting

### Problem: "Error: failed to download" when upgrading

**Cause:** Your local Helm repository cache is outdated.

**Solution:**
```bash
helm repo update airia-test-pod
helm search repo airia-test-pod/airia-test-pod --versions
```

### Problem: Upgrade shows old version

**Cause:** Repository cache not updated before upgrade.

**Solution:**
```bash
# Remove the cached repository
helm repo remove airia-test-pod

# Re-add it fresh
helm repo add airia-test-pod https://davidpacold.github.io/airia-test-pod/

# Update
helm repo update

# Now upgrade
helm upgrade airia-test-pod airia-test-pod/airia-test-pod -f aws-pre-install-config.yaml
```

### Problem: Want to verify what will change before upgrading

**Solution:**
```bash
# Dry-run to see what will change
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  -f aws-pre-install-config.yaml \
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

## Recommended Workflow

```bash
# 1. Navigate to your configs directory
cd /Users/davidpacold/Documents/Github/Airia-Configs/AWS

# 2. Check current version
helm list -n default | grep airia-test-pod

# 3. Update repository and check for new versions
helm repo update airia-test-pod
helm search repo airia-test-pod/airia-test-pod --versions | head -5

# 4. Review what will change (optional but recommended)
helm diff upgrade airia-test-pod airia-test-pod/airia-test-pod \
  -f aws-pre-install-config.yaml

# 5. Perform the upgrade
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  -f aws-pre-install-config.yaml \
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

## CI/CD Integration

The release workflow automatically:
- Increments patch version (1.0.158 → 1.0.159)
- Updates all version references in code
- Builds and publishes Docker image
- Packages and publishes Helm chart
- Validates deployment availability
- Creates GitHub release with notes

**GitHub Repository:** https://github.com/davidpacold/airia-test-pod
**Helm Repository:** https://davidpacold.github.io/airia-test-pod/
**Docker Registry:** ghcr.io/davidpacold/airia-test-pod
