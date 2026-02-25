# Airia Test Pod - Example Deployment

## Quick Start

1. Copy the example values file and fill in your details:
```bash
curl -sSL https://raw.githubusercontent.com/davidpacold/airia-test-pod/main/helm/airia-test-pod/examples/basic-values.yaml \
  -o my-values.yaml
```

2. Edit `my-values.yaml` with your configuration (see Required Configuration below)

3. Deploy with Helm (OCI registry — always pulls latest):
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-values.yaml \
  --namespace airia --create-namespace
```

## Required Configuration

Before deployment, you **must** update these sections in your values file:

### 1. Authentication (Security Critical)
```yaml
config:
  auth:
    username: "admin"
    password: "your-secure-password"       # CHANGE THIS
    secretKey: "your-super-secret-key"     # Generate with: openssl rand -hex 32
```

### 2. Domain Configuration (Optional — for external access)
```yaml
ingress:
  enabled: true
  className: "nginx"  # or "azure-application-gateway" for Azure App Gateway
  hosts:
    - host: your-domain.com
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

## Optional Configuration

Enable and configure services as needed:

- **PostgreSQL**: Set `config.postgresql.enabled: true` and provide connection details
- **Cassandra**: Set `config.cassandra.enabled: true` and provide connection details
- **Azure Blob Storage**: Set `config.blobStorage.enabled: true` and provide credentials
- **Amazon S3**: Set `config.s3.enabled: true` and provide credentials
- **S3 Compatible**: Set `config.s3Compatible.enabled: true` for MinIO, Ceph, etc.
- **Azure OpenAI**: Set `config.azureOpenai.enabled: true` and provide API details
- **OpenAI Direct**: Set `config.openaiDirect.enabled: true` and provide API key
- **Dedicated Embedding**: Set `config.dedicatedEmbedding.enabled: true` for standalone embedding endpoints
- **Document Intelligence**: Set `config.documentIntelligence.enabled: true`
- **SSL Testing**: Set `config.ssl.enabled: true` and specify URLs to test
- **GPU Detection**: Set `config.gpu.enabled: true`

For the full list of options, see the [example values file](../../helm/airia-test-pod/examples/basic-values.yaml).

## Security Notes

**Important**: Never commit real credentials to version control.
- Use Kubernetes secrets for production credentials
- Generate strong passwords and secret keys
- Rotate credentials regularly
- Consider using external secret management (Azure Key Vault, etc.)

## Troubleshooting

- Ensure your TLS certificate matches your domain
- Verify all required credentials are correct
- Check namespace permissions
- Review pod logs: `kubectl logs deployment/airia-test-pod`
