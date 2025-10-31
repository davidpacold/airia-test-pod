# Airia Infrastructure Test Pod Helm Chart

This Helm chart deploys the Airia Infrastructure Test Pod, a comprehensive solution for validating customer infrastructure readiness before deploying the main Airia application.

## Features

**🎯 7 Comprehensive Infrastructure Tests:**

- **PostgreSQL Database Testing**: Validates connection, databases, and extensions
- **Apache Cassandra Testing**: Cluster health, keyspace enumeration, query execution
- **Azure Blob Storage Testing**: Tests authentication and file operations  
- **Azure OpenAI Testing**: Validates API connectivity and model access
- **Azure Document Intelligence Testing**: Tests document processing capabilities
- **SSL Certificate Validation**: Checks certificate chains and expiration
- **Kubernetes PVC Testing**: Validates storage class and permissions

**Plus Additional Features:**
- **Real-time Dashboard**: WebSocket-powered live updates
- **Multi-hostname Ingress**: Support for 5 configurable hostnames
- **Intelligent Error Detection**: Specific remediation suggestions
- **Secure Secrets Management**: Kubernetes-native credential handling

## Prerequisites

- Kubernetes 1.18+
- Helm 3.0+
- NGINX Ingress Controller
- Appropriate RBAC permissions

## Installation

### 1. Create a Custom Values File

Create a `my-values.yaml` file with your configuration:

```yaml
# Authentication (required)
config:
  auth:
    username: "admin"
    password: "your-secure-password"
    secretKey: "your-super-secret-key-change-this"

  # Enable and configure PostgreSQL testing
  postgresql:
    enabled: true
    host: "your-postgres-server.postgres.database.azure.com"
    database: "postgres"
    username: "your-username"
    password: "your-password"

  # Enable and configure Azure Blob Storage testing
  blobStorage:
    enabled: true
    accountName: "yourstorageaccount"
    accountKey: "your-account-key"
    containerName: "test-container"

  # Enable and configure Azure OpenAI testing
  openai:
    enabled: true
    endpoint: "https://your-openai.openai.azure.com/"
    apiKey: "your-api-key"
    deploymentName: "gpt-35-turbo"

  # Enable and configure Document Intelligence testing
  documentIntelligence:
    enabled: true
    endpoint: "https://your-doc-intel.cognitiveservices.azure.com/"
    apiKey: "your-api-key"

  # Enable and configure SSL certificate testing
  ssl:
    enabled: true
    testUrls: "https://api.example.com,https://app.example.com"

# Configure ingress hostnames
ingress:
  className: "nginx"
  annotations:
    # NGINX Ingress Controller annotations
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
  hosts:
    - host: test-pod.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
    - host: infra-test.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
    - host: readiness.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
    - host: validation.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
    - host: precheck.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: airia-test-pod-tls
      hosts:
        - test-pod.yourdomain.com
        - infra-test.yourdomain.com
        - readiness.yourdomain.com
        - validation.yourdomain.com
        - precheck.yourdomain.com
```

### 2. Install the Chart from OCI Registry

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-values.yaml \
  --install --create-namespace --namespace default
```

Or for local development:
```bash
helm install airia-test-pod ./helm/airia-test-pod -f my-values.yaml
```

### 3. Verify Installation

```bash
kubectl get pods -n airia-preprod
kubectl get svc -n airia-preprod
kubectl get ingress -n airia-preprod
```

## Configuration

### Required Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.auth.username` | Admin username | `admin` |
| `config.auth.password` | Admin password | `changeme` |
| `config.auth.secretKey` | JWT secret key | `your-super-secret-key-change-this` |

### Optional Test Configuration

#### PostgreSQL Testing
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.postgresql.enabled` | Enable PostgreSQL testing | `false` |
| `config.postgresql.host` | PostgreSQL server hostname | `""` |
| `config.postgresql.database` | Database name | `postgres` |
| `config.postgresql.username` | Database username | `""` |
| `config.postgresql.password` | Database password | `""` |

#### Azure Blob Storage Testing
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.blobStorage.enabled` | Enable Blob Storage testing | `false` |
| `config.blobStorage.accountName` | Storage account name | `""` |
| `config.blobStorage.accountKey` | Storage account key | `""` |
| `config.blobStorage.containerName` | Container name | `test-container` |

#### Azure OpenAI Testing
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.openai.enabled` | Enable OpenAI testing | `false` |
| `config.openai.endpoint` | Azure OpenAI endpoint | `""` |
| `config.openai.apiKey` | Azure OpenAI API key | `""` |
| `config.openai.deploymentName` | Model deployment name | `gpt-35-turbo` |

#### Document Intelligence Testing
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.documentIntelligence.enabled` | Enable Document Intelligence testing | `false` |
| `config.documentIntelligence.endpoint` | Document Intelligence endpoint | `""` |
| `config.documentIntelligence.apiKey` | Document Intelligence API key | `""` |

#### SSL Certificate Testing
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.ssl.enabled` | Enable SSL testing | `false` |
| `config.ssl.testUrls` | Comma-separated URLs to test | `""` |

#### GPU Detection Testing
| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.gpu.enabled` | Enable GPU detection testing | `false` |
| `config.gpu.required` | Require GPU presence (fail test if not found) | `false` |

### Infrastructure Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts` | List of hostnames | See values.yaml |
| `service.type` | Service type (`ClusterIP`, `NodePort`, `LoadBalancer`) | `ClusterIP` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `256Mi` |
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `512Mi` |

## Usage

1. **Access the Dashboard**: Navigate to one of your configured hostnames
2. **Login**: Use the credentials specified in your values file
3. **Run Tests**: Click "Run All Tests" or run individual tests
4. **View Results**: Real-time updates will show test progress and results
5. **Review Logs**: Expand test cards to see detailed logs and remediation suggestions

## Upgrading

To upgrade the chart with new values:

```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-values.yaml
```

Or use the automated upgrade script:

```bash
./scripts/upgrade.sh --oci -f my-values.yaml
```

## Uninstalling

To remove the chart:

```bash
helm uninstall airia-test-pod
```

To also remove the namespace:

```bash
kubectl delete namespace airia-preprod
```

## Troubleshooting

### Common Issues

1. **Tests show as "Skipped"**: This means the test configuration is not enabled or incomplete
2. **Pod fails to start**: Check resource limits and node capacity
3. **Ingress not working**: Verify ingress controller is installed (NGINX or Azure App Gateway)
4. **Permission errors**: Ensure RBAC is properly configured

### Debug Commands

```bash
# Check pod logs
kubectl logs -n airia-preprod -l app.kubernetes.io/name=airia-test-pod

# Check pod describe
kubectl describe pod -n airia-preprod -l app.kubernetes.io/name=airia-test-pod

# Check configuration
kubectl get configmap -n airia-preprod airia-test-pod-config -o yaml
kubectl get secret -n airia-preprod airia-test-pod-auth -o yaml
```

## Security Considerations

- Change default authentication credentials
- Use strong, unique secret keys
- Store sensitive information in Kubernetes secrets
- Enable TLS/SSL for ingress
- Review RBAC permissions for your security requirements

## Support

For support and documentation, visit: https://github.com/airia/test-pod