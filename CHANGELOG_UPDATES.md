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

#### Workflow Chaining Improvements
- **Consolidated version commits** into one atomic operation
- **Removed race conditions** between release.yml and static.yml
- **Added explicit workflow_call** pattern for better control
- **Location:** [.github/workflows/release.yml](/.github/workflows/release.yml)

**Changes:**
1. ✅ Single atomic commit for version updates + Helm repository
2. ✅ Explicit dependency chain using `needs:`
3. ✅ No more duplicate workflow runs
4. ✅ Cleaner git history

#### Real Helm Repository Health Validation
- **Location:** [.github/workflows/release.yml](/.github/workflows/release.yml#L467-L534)
- **Replaces simulated health checks with real validation**

**Validates:**
1. ✅ GitHub Pages is accessible
2. ✅ `index.yaml` exists and is downloadable
3. ✅ New version is in `index.yaml`
4. ✅ Chart package (`.tgz`) is downloadable
5. ✅ Docker image is available

**If checks fail:** Automatic rollback is triggered!

---

## 📚 Documentation Updates

### New Documents
1. **[DEPLOYMENT.md](DEPLOYMENT.md)** - Comprehensive deployment guide
   - OCI registry usage
   - Traditional Helm repository
   - Automated upgrade script
   - Troubleshooting guide

2. **[VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)** - Version management guide
   - Comparison of all version management methods
   - Migration guide from traditional to OCI
   - CI/CD integration examples
   - Troubleshooting version issues

3. **[CHANGELOG_UPDATES.md](CHANGELOG_UPDATES.md)** - This document!

### Updated Documents
1. **[README.md](README.md)**
   - Added OCI registry as recommended installation method
   - Added version management section
   - Added GPU test to infrastructure tests list
   - Updated all Helm commands to show OCI method
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
  repoUrl: "https://davidpacold.github.io/airia-test-pod/"
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

**After:**
```
1. Calculate version
2. Update version files
3. Package Helm chart
4. Create docs
5. Commit everything atomically → Single commit
6. Push to OCI registry
7. Explicit Pages deployment via workflow_call
8. Build Docker image
9. Real health validation (checks actual deployment)
10. Auto-rollback if validation fails
```

---

## 🚀 Migration Guide

### For End Users

**Old way (Traditional Helm):**
```bash
helm repo add airia-test-pod https://davidpacold.github.io/airia-test-pod/
helm repo update airia-test-pod  # ⚠️ Easy to forget!
helm upgrade airia-test-pod airia-test-pod/airia-test-pod -f config.yaml
```

**New way (OCI Registry - Recommended):**
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
- ✅ OCI registry support for Helm charts
- ✅ Automatic version checking
- ✅ Automated upgrade script
- ✅ Improved CI/CD pipeline with real validation
- ✅ Comprehensive documentation

### Benefits
- 🚀 Faster deployments (OCI registry)
- 🔒 Always use latest version (version checking)
- 🤖 Automated upgrades (upgrade script)
- ✅ Validated releases (CI/CD health checks)
- 📚 Better documentation (3 new guides)

### Breaking Changes
- ⚠️ None! All changes are backward compatible
- 📦 Traditional Helm repository still works
- 🔄 No migration required (but recommended)

---

## 📝 Next Steps

1. **Try the OCI registry method:**
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

---

## 🤝 Feedback

Have questions or feedback about these changes?
- 🐛 [Report Issues](https://github.com/davidpacold/airia-test-pod/issues)
- 💡 [Request Features](https://github.com/davidpacold/airia-test-pod/discussions)
- 📚 [Read Docs](README.md)

---

**Last Updated:** October 31, 2025
**Version:** 1.0.159
