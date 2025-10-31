# Version Management & Automatic Updates

This document explains the comprehensive version management system for the Airia Test Pod.

## 🎯 Problem Solved

Users no longer need to remember to run `helm repo update` before upgrading! We've implemented multiple layers of version management to ensure you always get the latest version.

## 🚀 Solutions Implemented

### 1. OCI Registry (Recommended) ⭐

**What it does:** Helm charts are published to GitHub Container Registry as OCI artifacts.

**Benefits:**
- ✅ No need for `helm repo update`
- ✅ Always pulls latest version by default
- ✅ Better authentication and security
- ✅ Same infrastructure as Docker images
- ✅ Faster than traditional Helm repos

**Usage:**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml \
  --install
```

**How it works:**
- Every release automatically pushes the chart to `ghcr.io/davidpacold/airia-test-pod/charts`
- Helm pulls directly from the OCI registry
- No local cache to become stale

---

### 2. Automated Upgrade Script

**What it does:** A shell script that handles the entire upgrade process automatically.

**Location:** `scripts/upgrade.sh`

**Features:**
- ✅ Automatically updates repository (traditional method) or uses OCI
- ✅ Checks current vs. latest version
- ✅ Shows what will be upgraded
- ✅ Asks for confirmation
- ✅ Monitors rollout status
- ✅ Displays pod health

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

### 3. Helm Pre-Upgrade Version Check

**What it does:** Automatically checks for newer versions during `helm upgrade`.

**Location:** `helm/airia-test-pod/templates/pre-upgrade-job.yaml`

**How it works:**
1. Runs as a Kubernetes Job before each upgrade
2. Fetches the latest version from OCI registry or Helm repo
3. Compares with the version being installed
4. Shows warnings if not using the latest version
5. Optionally blocks upgrades in strict mode

**Configuration:**
```yaml
versionCheck:
  enabled: true          # Enable automatic version checking
  useOCI: true          # Check OCI registry (faster)
  strict: false         # Block upgrades if not latest (set to true to enforce)
```

**Strict Mode Example:**
```bash
# This will FAIL if not installing the latest version
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml \
  --set versionCheck.strict=true
```

---

### 4. CI/CD Health Validation

**What it does:** After each release, validates that the Helm repository is properly updated.

**Location:** `.github/workflows/release.yml` (post-deployment-validation job)

**Checks performed:**
1. ✅ GitHub Pages is accessible
2. ✅ `index.yaml` exists and is valid
3. ✅ New version is listed in `index.yaml`
4. ✅ Chart package (`.tgz`) is downloadable
5. ✅ Docker image is available

**If checks fail:** Automatic rollback is triggered!

---

## 📊 Comparison Matrix

| Method | Manual Update Required | Auto-Detects Latest | Strict Enforcement | Speed |
|--------|----------------------|--------------------|--------------------|-------|
| **OCI Registry** | ❌ No | ✅ Yes | ⚠️ Optional | ⚡ Fast |
| **Upgrade Script** | ❌ No | ✅ Yes | ⚠️ Optional | ⚡ Fast |
| **Pre-Upgrade Hook** | ⚠️ Sometimes | ✅ Yes | ✅ Yes (strict mode) | 🐢 Slower |
| **Traditional Repo** | ✅ Yes (`helm repo update`) | ❌ No | ❌ No | 🐢 Slower |

---

## 🎯 Recommended Workflow

### For End Users (Easiest)

**Option 1: Use the upgrade script (zero configuration)**
```bash
cd /path/to/Airia-Configs/AWS
curl -sSL https://raw.githubusercontent.com/davidpacold/airia-test-pod/main/scripts/upgrade.sh | \
  bash -s -- --oci -f aws-pre-install-config.yaml
```

**Option 2: Use OCI directly**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f aws-pre-install-config.yaml \
  --install
```

### For CI/CD Pipelines

**With strict version enforcement:**
```bash
# This will FAIL if not deploying the latest version
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml \
  --set versionCheck.strict=true \
  --install
```

**Or fetch latest version explicitly:**
```bash
LATEST_VERSION=$(helm show chart oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod | \
  grep '^version:' | awk '{print $2}')

helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version "$LATEST_VERSION" \
  -f config.yaml \
  --install
```

### For Development/Testing

**With warnings but allow older versions:**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version 1.0.150 \
  -f config.yaml \
  --set versionCheck.strict=false
```

---

## 🔄 Migration Guide

### From Traditional Helm Repo to OCI

**Old way:**
```bash
helm repo add airia-test-pod https://davidpacold.github.io/airia-test-pod/
helm repo update airia-test-pod
helm upgrade airia-test-pod airia-test-pod/airia-test-pod -f config.yaml
```

**New way:**
```bash
# No repo add needed!
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f config.yaml \
  --install
```

**To remove old repo (optional):**
```bash
helm repo remove airia-test-pod
```

---

## 🛠️ Troubleshooting

### "Error: failed to download chart" with OCI

**Cause:** Authentication required for private registry.

**Solution:**
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | helm registry login ghcr.io -u USERNAME --password-stdin

# Or use Docker credentials
docker login ghcr.io
```

### Version check job is slow

**Cause:** Pre-upgrade job needs to fetch version information.

**Solutions:**
1. Use OCI mode (faster): `versionCheck.useOCI: true`
2. Disable if not needed: `versionCheck.enabled: false`
3. Keep using OCI registry which doesn't need the check

### Want to force a specific version

**Disable version checking:**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --version 1.0.150 \
  -f config.yaml \
  --set versionCheck.enabled=false
```

---

## 📚 Additional Resources

- **Deployment Guide:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **GitHub Repository:** https://github.com/davidpacold/airia-test-pod
- **OCI Registry:** https://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod
- **Helm Repository:** https://davidpacold.github.io/airia-test-pod/
- **Docker Registry:** https://ghcr.io/davidpacold/airia-test-pod

---

## 🎉 Summary

You now have **4 layers of protection** against deploying outdated versions:

1. ⭐ **OCI Registry** - Always fresh, no cache
2. 🤖 **Automated Script** - Handles updates automatically
3. 🛡️ **Pre-Upgrade Hook** - Warns or blocks old versions
4. ✅ **CI/CD Validation** - Ensures releases are properly deployed

**Recommended:** Use OCI registry with the upgrade script for the best experience!
