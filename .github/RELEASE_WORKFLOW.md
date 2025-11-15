# 🚀 Release Workflow Guide

## Overview

This guide explains how to use the improved release workflow that **eliminates git sync issues**.

### What Changed?

**Before (Problematic):**
```
PR merge → Auto-release → Version commit → Local main out of sync ❌
```

**After (Clean):**
```
PR merge → Done ✅
When ready: Manual release → Version commit on release branch ✅
```

---

## 📋 New Workflow Process

### 1. Normal Development (No Changes!)

Work on features as usual:

```bash
# Start from clean main
git checkout main
git pull

# Create feature branch
git checkout -b fix/my-feature

# Make changes and commit
git add .
git commit -m "Fix: description"

# Push and create PR
git push -u origin fix/my-feature
gh pr create --title "Fix: My Feature" --base main

# Merge PR (via GitHub UI or CLI)
gh pr merge --squash --delete-branch
```

✅ **Your local main stays in sync!**

---

### 2. Creating a Release (Two Options)

#### Option A: Manual Trigger (Recommended)

Use GitHub Actions UI or CLI:

```bash
# Via GitHub CLI
gh workflow run "🚀 Release & Version Management" \
  --field version="1.0.188"

# Or use GitHub UI:
# Actions → 🚀 Release & Version Management → Run workflow
```

#### Option B: Git Tags (Cleanest)

Create and push a version tag:

```bash
# Make sure you're on latest main
git checkout main
git pull

# Create version tag
git tag v1.0.188 -m "Release v1.0.188"

# Push tag (triggers release)
git push origin v1.0.188
```

---

### 3. What Happens During Release

The workflow automatically:

1. ✅ Updates version references in all files
2. ✅ Commits changes with `[skip ci]` tag
3. ✅ Creates GitHub Release
4. ✅ Publishes Helm chart to OCI registry
5. ✅ Builds and pushes Docker images
6. ✅ Runs health validation
7. ✅ Auto-rollback if issues detected

---

## 🎯 Best Practices

### When to Release?

- ✅ After merging one or more feature PRs
- ✅ Before deploying to production
- ✅ When you want a snapshot of current main
- ❌ Not after every single PR (use batching)

### Version Numbering

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features (backwards compatible)
- **PATCH** (x.x.1): Bug fixes

### Batch Multiple PRs

Instead of:
```
PR #1 → Release 1.0.188
PR #2 → Release 1.0.189
PR #3 → Release 1.0.190
```

Do this:
```
PR #1 → Merge
PR #2 → Merge
PR #3 → Merge
→ Release 1.0.188 (includes all 3)
```

---

## 🔧 Troubleshooting

### Release Failed?

Check the workflow run:
```bash
gh run list --workflow="🚀 Release & Version Management"
gh run view <run-id> --log-failed
```

### Version Already Exists?

The workflow prevents duplicate versions:
```bash
# Check existing releases
gh release list

# Use next version number
gh workflow run "🚀 Release & Version Management" \
  --field version="1.0.189"
```

### Need to Rollback?

Use the rollback workflow:
```bash
gh workflow run "rollback.yml" \
  --field namespace="default" \
  --field release_name="airia-test-pod"
```

---

## 📊 Comparison: Before vs After

| Aspect | Before (Auto) | After (Manual) |
|--------|--------------|----------------|
| **Sync Issues** | ❌ Yes, frequent | ✅ None |
| **Git History** | ❌ Cluttered | ✅ Clean |
| **Control** | ❌ No control | ✅ Full control |
| **Version Spam** | ❌ Yes (188+ versions) | ✅ No, intentional only |
| **Convenience** | ✅ Automatic | ⚠️ Manual step |
| **Production Ready** | ❌ Risky | ✅ Safe |

---

## 🚦 Quick Reference

```bash
# Normal PR workflow (unchanged)
git checkout -b fix/feature
git commit -m "Fix: ..."
gh pr create
gh pr merge --squash

# Create release (when ready)
gh workflow run "🚀 Release & Version Management" \
  --field version="1.0.X"

# OR use tags
git tag v1.0.X && git push origin v1.0.X

# Check release status
gh run list --limit 5

# View latest release
gh release view --web
```

---

## 💡 Pro Tips

1. **Use GitHub CLI**: Much faster than UI
2. **Batch releases**: Combine multiple PRs into one release
3. **Semantic versioning**: Makes version numbers meaningful
4. **Test before release**: Merge to main, test, then release
5. **Monitor workflows**: `gh run watch` to see progress

---

🤖 **Questions?** Check workflow logs with `gh run view <run-id> --log`
