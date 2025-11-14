# Deployment Documentation

This directory contains deployment guides and examples for the Airia Test Pod.

## Available Guides

### [Deployment Guide](deployment-guide.md)
Comprehensive guide for deploying the application using:
- Docker
- Kubernetes
- Helm
- Includes configuration examples, troubleshooting, and best practices

### [Example Deployment](example-deployment.md)
Step-by-step walkthrough of a sample deployment with:
- Configuration examples
- Testing procedures
- Common scenarios

### [Rollback Procedures](../operations/ROLLBACK.md)
How to rollback deployments when issues occur

## Quick Start

### Using Docker
```bash
docker run -p 8080:8080 airia-test-pod:latest
```

### Using Helm
```bash
helm install my-release helm/airia-test-pod
```

### Using Kubernetes
```bash
kubectl apply -f k8s/
```

## Related Resources

- [Helm Examples](../../examples/helm/) - Example Helm values files
- [Kubernetes Examples](../../examples/kubernetes/) - Example K8s manifests
- [Operations Guide](../operations/) - Operational procedures
