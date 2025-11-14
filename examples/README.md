# Examples

This directory contains example configurations for deploying and testing the Airia Test Pod.

## Available Examples

### [Helm Examples](helm/)
Example Helm values files for different deployment scenarios:
- **basic-values.yaml** - Basic deployment configuration

### Kubernetes Examples
Kubernetes manifest examples are located in the [k8s/](../k8s/) directory:
- Basic deployments
- Deployments with secrets
- Deployments with health checks
- Production configurations

## Using Examples

### Helm Deployment with Examples

```bash
# Basic deployment
helm install my-release helm/airia-test-pod -f examples/helm/basic-values.yaml

# Upgrade with custom values
helm upgrade my-release helm/airia-test-pod -f examples/helm/basic-values.yaml
```

### Kubernetes Deployment with Examples

```bash
# Apply manifests
kubectl apply -f k8s/

# Apply specific example
kubectl apply -f k8s/deployment-example.yaml
```

## Creating Custom Configurations

### Helm Custom Values

Create your own values file based on the examples:

```bash
# Copy example
cp examples/helm/basic-values.yaml my-custom-values.yaml

# Edit as needed
vim my-custom-values.yaml

# Deploy with custom values
helm install my-release helm/airia-test-pod -f my-custom-values.yaml
```

### Kubernetes Custom Manifests

Create custom manifests based on examples:

```bash
# Copy example
cp k8s/deployment-example.yaml my-deployment.yaml

# Edit as needed
vim my-deployment.yaml

# Apply
kubectl apply -f my-deployment.yaml
```

## Testing Examples

See [Manual Tests](../tests/manual_tests/) for test scripts and configurations.

## Related Resources

- [Deployment Guide](../docs/deployment/deployment-guide.md)
- [Operations Guide](../docs/operations/)
- [Manual Tests](../tests/manual_tests/)
