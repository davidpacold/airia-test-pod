# Airia Test Pod Deployment Guide

## Quick Start

1. Copy the example values file:
```bash
cp values-example.yaml values.yaml
```

2. Edit `values.yaml` with your configuration (see Required Configuration below)

3. Deploy with Helm:
```bash
helm install airia-test-pod ./helm/airia-test-pod -f values.yaml
```

## Required Configuration

Before deployment, you **must** update these sections in `values.yaml`:

### 1. Domain Configuration
```yaml
ingress:
  className: "nginx"  # or "azure-application-gateway" for Azure App Gateway
  hosts:
    - host: your-domain.com  # Replace with your domain
  tls:
    - secretName: your-tls-secret
      hosts:
        - your-domain.com
```

**For Azure Application Gateway users:**
```yaml
ingress:
  className: "azure-application-gateway"
  annotations:
    kubernetes.io/ingress.class: azure/application-gateway
    appgw.ingress.kubernetes.io/ssl-redirect: "false"
```

### 2. Authentication (Security Critical)
```yaml
config:
  auth:
    password: "your-secure-password"     # Change default password
    secretKey: "your-super-secret-key"   # Generate a secure secret key
```

### 3. Namespace
```yaml
namespace:
  name: "your-namespace"  # Choose your namespace name
```

## Optional Configuration

Enable and configure services as needed:

- **PostgreSQL**: Set `config.postgresql.enabled: true` and provide connection details
- **Azure Blob Storage**: Set `config.blobStorage.enabled: true` and provide credentials
- **Azure OpenAI**: Set `config.openai.enabled: true` and provide API details
- **Document Intelligence**: Set `config.documentIntelligence.enabled: true`
- **SSL Testing**: Set `config.ssl.enabled: true` and specify URLs to test

## Security Notes

⚠️ **Important**: Never commit real credentials to version control
- Use Kubernetes secrets for production credentials
- Generate strong passwords and secret keys
- Rotate credentials regularly
- Consider using external secret management (Azure Key Vault, etc.)

## Troubleshooting

- Ensure your TLS certificate matches your domain
- Verify all required credentials are correct
- Check namespace permissions
- Review pod logs: `kubectl logs -n airia deployment/airia-test-pod`