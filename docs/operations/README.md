# Operations Documentation

This directory contains operational procedures, versioning strategy, and maintenance guides.

## Available Guides

### [Versioning](versioning.md)
Version management strategy including:
- Semantic versioning approach
- How versions are updated
- CI/CD integration
- Release process

### [Rollback Procedures](ROLLBACK.md)
How to rollback deployments including:
- Helm rollback commands
- Kubernetes rollback procedures
- Verification steps
- Troubleshooting

## Common Operations

### Check Deployment Status
```bash
# Helm
helm status my-release

# Kubernetes
kubectl get pods
kubectl describe deployment airia-test-pod
```

### View Logs
```bash
# Helm
kubectl logs -l app.kubernetes.io/instance=my-release

# Kubernetes
kubectl logs -l app=airia-test-pod
```

### Update Deployment
```bash
# Helm
helm upgrade my-release helm/airia-test-pod -f values.yaml

# Kubernetes
kubectl apply -f k8s/
```

### Rollback Deployment
```bash
# Helm
helm rollback my-release

# See full guide
See [Rollback Procedures](ROLLBACK.md)
```

## Monitoring

### Health Checks
- Liveness probe: `/health`
- Readiness probe: `/ready`

### Metrics
- Application metrics available at `/metrics` (if enabled)

## Troubleshooting

### Common Issues

1. **Pod not starting**
   - Check logs: `kubectl logs <pod-name>`
   - Check events: `kubectl describe pod <pod-name>`

2. **Service unavailable**
   - Check service: `kubectl get svc`
   - Check endpoints: `kubectl get endpoints`

3. **Configuration issues**
   - Verify ConfigMap: `kubectl get configmap`
   - Verify Secrets: `kubectl get secrets`

## Related Resources

- [Deployment Guide](../deployment/)
- [Development Guide](../development/)
- [Helm Examples](../../examples/helm/)
