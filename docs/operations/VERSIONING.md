# Version Management Guide

This guide explains how version synchronization works across the entire Airia Infrastructure Test Pod application and what to do to maintain it.

## Automatic Version Management

The application uses **fully automated version management** with the following workflow:

### 1. Automatic Release Creation
- **Manual releases**: Use GitHub UI or `gh release create v1.x.x` 
- **Automatic releases**: Push to `main` branch auto-increments patch version
- **Manual workflow**: Use GitHub Actions "Release" workflow with custom version

### 2. Automatic Version Updates
When a release is created, the GitHub Actions workflow automatically updates:

#### Application Code
- `app/config.py` → `version: str = "1.x.x"`
- `app/main.py` → `FastAPI(..., version="1.x.x")`

#### Helm Charts  
- `helm/airia-test-pod/Chart.yaml` → `version: 1.x.x` and `appVersion: "1.x.x"`

#### Template Fallbacks
- `templates/dashboard.html` → JavaScript fallback version
- `templates/index.html` → JavaScript fallback version

#### Version Persistence
- Changes are automatically committed back to the repository with `[skip ci]` flag
- This ensures all files stay synchronized without triggering infinite workflows

### 3. Dynamic Version Display
The UI dynamically loads versions from the `/version` API endpoint:

```javascript
// Both templates include this logic
async function loadVersion() {
    try {
        const response = await fetch('/version');
        const data = await response.json();
        document.getElementById('version-display').textContent = 'v' + data.version;
    } catch (error) {
        // Fallback to hardcoded version if API fails
        document.getElementById('version-display').textContent = 'v1.x.x';
    }
}
```

## Manual Version Updates (If Needed)

If you ever need to manually update versions, update these files:

1. **Core Application**
   ```python
   # app/config.py
   version: str = "1.x.x"
   
   # app/main.py  
   app = FastAPI(title="Airia Infrastructure Test Pod", version="1.x.x")
   ```

2. **Helm Chart**
   ```yaml
   # helm/airia-test-pod/Chart.yaml
   version: 1.x.x
   appVersion: "1.x.x"
   ```

3. **Template Fallbacks** (optional - only if JavaScript fails)
   ```javascript
   // templates/dashboard.html & templates/index.html
   document.getElementById('version-display').textContent = 'v1.x.x';
   ```

## Deployment Process

### For Version Updates
1. **Create Release**: GitHub UI, CLI, or push to main
2. **Wait for Build**: GitHub Actions builds new Docker image  
3. **Deploy**: `helm upgrade` with latest values
4. **Force Update**: `kubectl rollout restart` if using `:latest` tag

### For Immediate Deployment
```bash
# Check latest release
gh release list --limit 1

# Upgrade deployment (using local chart)
helm upgrade airia-test-pod ./helm/airia-test-pod -n airia-preprod -f values.yaml

# Force pod restart to pull latest image
kubectl rollout restart deployment/airia-test-pod -n airia-preprod
kubectl rollout status deployment/airia-test-pod -n airia-preprod
```

## Verification Steps

After deployment, verify version synchronization:

```bash
# Check API version
curl http://localhost:8080/version

# Check GitHub releases  
gh release list --limit 3

# Check Helm chart version
helm list -n airia-preprod

# Check running pod image
kubectl get pods -n airia-preprod -o jsonpath='{.items[0].spec.containers[0].image}'
```

## Troubleshooting

### Version Mismatch Issues

**Problem**: UI shows wrong version
- **Cause**: Pod not restarted after new image build
- **Solution**: `kubectl rollout restart deployment/airia-test-pod -n airia-preprod`

**Problem**: API returns old version  
- **Cause**: Application code not updated in source
- **Solution**: Check if GitHub Actions workflow completed successfully

**Problem**: Helm chart version mismatch
- **Cause**: Using cached local chart instead of updated version
- **Solution**: Use chart from repository or update local files

### Docker Image Caching

**Problem**: `:latest` tag not updating
- **Cause**: Kubernetes ImagePullPolicy not forcing updates
- **Solution**: Use `imagePullPolicy: Always` in values.yaml or specific version tags

## Best Practices

1. **Use Semantic Versioning**: Major.Minor.Patch (e.g., 1.2.3)
2. **Test Before Release**: Verify functionality before creating releases
3. **Monitor Workflows**: Check GitHub Actions completed successfully  
4. **Verify Deployment**: Always check version endpoints after deployment
5. **Use Specific Tags**: For production, consider specific version tags instead of `:latest`

## API Endpoints

- `GET /version` → `{"version": "1.x.x"}` (public endpoint)
- `GET /api/version` → `{"version": "1.x.x"}` (same as above)
- `GET /health` → Health check with version info

## Files That Control Versioning

### Critical Files (Auto-updated by workflow)
- `app/config.py` - Core application version
- `app/main.py` - FastAPI application version  
- `helm/airia-test-pod/Chart.yaml` - Helm chart versions

### Template Files (Auto-updated fallbacks)
- `templates/dashboard.html` - Dynamic loading + fallback
- `templates/index.html` - Dynamic loading + fallback

### Workflow Files
- `.github/workflows/release.yml` - Handles version updates and releases
- `.github/workflows/build-and-publish.yml` - Builds Docker images

This system ensures that all version references stay synchronized automatically without manual intervention.