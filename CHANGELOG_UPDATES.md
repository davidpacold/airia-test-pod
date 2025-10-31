# Recent Updates Summary

This document summarizes all the major improvements made to the Airia Test Pod project.

## 🎯 Major Features Added

### 1. GPU Detection Test ✨
- **Location:** [app/tests/gpu_test.py](app/tests/gpu_test.py)
- **Web UI:** Added GPU test card to Infrastructure Tests section in [templates/dashboard.html](templates/dashboard.html)
- **Features:**
  - Detects NVIDIA GPU availability
  - Validates GPU drivers and CUDA installation
  - Checks GPU memory, temperature, and utilization
  - Configurable requirements via environment variables

**Configuration:**
```yaml
# Environment variables for GPU testing
GPU_REQUIRED: "false"           # Set to true to require GPU
GPU_MIN_MEMORY_GB: "0"          # Minimum GPU memory required
GPU_MAX_TEMP_CELSIUS: "85"      # Maximum temperature threshold
```

---

### 2. OCI Registry Support 🚀
- **Location:** [.github/workflows/release.yml](/.github/workflows/release.yml#L279-L294)
- **Helm charts now published to GitHub Container Registry as OCI artifacts**
- **Benefits:**
  - ✅ No need for `helm repo update`
  - ✅ Always pulls latest version automatically
  - ✅ Better authentication and security
  - ✅ Same infrastructure as Docker images

**Usage:**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml --install
```

---

### 3. Automated Version Checking 🔍
- **Location:** [helm/airia-test-pod/templates/pre-upgrade-job.yaml](helm/airia-test-pod/templates/pre-upgrade-job.yaml)
- **Kubernetes pre-upgrade hook that validates version before deployment**
- **Features:**
  - Checks if you're installing the latest version
  - Warns if a newer version is available
  - Optionally blocks upgrades in strict mode
  - Works with both OCI registry and traditional Helm repo

**Configuration:**
```yaml
versionCheck:
  enabled: true          # Enable version checking
  useOCI: true          # Use OCI registry for checks
  strict: false         # Set to true to block old versions
```

---

### 4. Automated Upgrade Script 🤖
- **Location:** [scripts/upgrade.sh](scripts/upgrade.sh)
- **One-command upgrade with automatic version checking**
- **Features:**
  - Automatically updates Helm repository (traditional method)
  - Supports OCI registry (recommended)
  - Shows current vs. latest version
  - Asks for confirmation before upgrading
  - Monitors rollout status
  - Displays pod health after upgrade

**Usage:**
```bash
# OCI method (recommended)
./scripts/upgrade.sh --oci -f config.yaml

# Traditional method
./scripts/upgrade.sh -f config.yaml

# Remote execution
curl -sSL https://raw.githubusercontent.com/davidpacold/airia-test-pod/main/scripts/upgrade.sh | \
  bash -s -- --oci -f config.yaml
```

---

### 5. Improved CI/CD Pipeline 🔄

#### OCI-Only Simplification
- **Removed traditional Helm repository** (GitHub Pages)
- **Removed static.yml workflow** - No longer needed
- **Simplified to OCI registry only** - Faster and more reliable
- **Location:** [.github/workflows/release.yml](/.github/workflows/release.yml)

**Changes:**
1. ✅ Single atomic commit for all version updates
2. ✅ OCI registry publishing only
3. ✅ No GitHub Pages deployment
4. ✅ Cleaner git history
5. ✅ Faster releases

#### Real OCI Registry Health Validation
- **Location:** [.github/workflows/release.yml](/.github/workflows/release.yml#L460-L535)
- **Validates actual OCI registry deployment**

**Validates:**
1. ✅ OCI chart is pullable
2. ✅ Chart version matches expected version
3. ✅ Docker image is available

**If checks fail:** Automatic rollback is triggered!

---

## 📚 Documentation Updates

### New Documents
1. **[DEPLOYMENT.md](DEPLOYMENT.md)** - OCI-only deployment guide
   - OCI registry usage
   - Automated upgrade script
   - Version management
   - Troubleshooting guide

2. **[VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)** - Version management guide
   - OCI registry version management
   - Automated upgrade script
   - CI/CD integration examples
   - Troubleshooting version issues

3. **[CHANGELOG_UPDATES.md](CHANGELOG_UPDATES.md)** - This document!

### Updated Documents
1. **[README.md](README.md)**
   - Simplified to OCI registry only
   - Removed traditional Helm repository references
   - Added version management section
   - Added GPU test to infrastructure tests list
   - Updated all Helm commands to use OCI method
   - Added badges for Helm chart

---

## 🔧 Configuration Changes

### New Helm Values
```yaml
# Version checking configuration
versionCheck:
  enabled: true
  useOCI: true
  ociRepo: "oci://ghcr.io/davidpacold/airia-test-pod/charts"
  strict: false
```

### GPU Configuration
```yaml
# GPU detection settings (via environment variables)
GPU_REQUIRED: "false"
GPU_MIN_MEMORY_GB: "0"
GPU_MAX_TEMP_CELSIUS: "85"
```

---

## 📊 Release Workflow Changes

### Before vs After

**Before:**
```
1. Calculate version
2. Update version files → Commit #1
3. Package Helm chart
4. Create docs → Commit #2
5. Manually trigger Pages deployment (race condition!)
6. Build Docker image
7. Simulate health check (not real)
```

**After (OCI-Only):**
```
1. Calculate version
2. Update version files
3. Package Helm chart
4. Commit everything atomically → Single commit
5. Push to OCI registry
6. Build Docker image
7. Real health validation (checks OCI registry)
8. Auto-rollback if validation fails
```

---

## 🚀 Deployment Guide

### Quick Start

**OCI Registry (Only Method):**
```bash
# No repo add needed! Always latest version!
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml --install
```

**Or use the automated script:**
```bash
./scripts/upgrade.sh --oci -f config.yaml
```

### For CI/CD Pipelines

**Enforce latest version:**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml \
  --set versionCheck.strict=true
```

---

## 🎉 Summary

### What's New
- ✅ GPU detection test added
- ✅ OCI registry as the only deployment method
- ✅ Automatic version checking
- ✅ Automated upgrade script
- ✅ Simplified CI/CD pipeline with real validation
- ✅ Comprehensive documentation

### Benefits
- 🚀 Faster deployments (OCI registry only)
- 🔒 Always use latest version (version checking)
- 🤖 Automated upgrades (upgrade script)
- ✅ Validated releases (OCI health checks)
- 📚 Better documentation (3 new guides)
- 🧹 Cleaner codebase (removed traditional Helm repo)

### Breaking Changes
- ⚠️ Traditional Helm repository removed
- 📦 OCI registry is now the only deployment method
- 🔄 Users must switch to OCI registry URLs

---

## 📝 Next Steps

1. **Use the OCI registry (only method):**
   ```bash
   helm upgrade airia-test-pod \
     oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
     -f your-config.yaml
   ```

2. **Enable version checking:**
   ```yaml
   versionCheck:
     enabled: true
     strict: false  # Set to true for enforcement
   ```

3. **Use the automated upgrade script:**
   ```bash
   ./scripts/upgrade.sh --oci -f your-config.yaml
   ```

4. **Test GPU detection** (if you have GPUs):
   - Check the Infrastructure Tests section in the web UI
   - Look for "GPU Detection" test card

5. **Remove old Helm repository (if previously added):**
   ```bash
   helm repo remove airia-test-pod
   ```

---

## 🤝 Feedback

Have questions or feedback about these changes?
- 🐛 [Report Issues](https://github.com/davidpacold/airia-test-pod/issues)
- 💡 [Request Features](https://github.com/davidpacold/airia-test-pod/discussions)
- 📚 [Read Docs](README.md)

---

**Last Updated:** October 31, 2025
**Version:** 1.0.159
