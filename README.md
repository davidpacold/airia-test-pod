# Airia Infrastructure Test Pod

A comprehensive Kubernetes application that validates infrastructure readiness before deploying production applications. This tool tests connectivity to essential Azure services and provides actionable feedback for resolving common configuration issues.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidpacold/airia-test-pod)](https://github.com/davidpacold/airia-test-pod/releases)
[![Container Image](https://img.shields.io/badge/container-ghcr.io%2Fdavidpacold%2Fairia--test--pod-blue)](https://github.com/davidpacold/airia-test-pod/pkgs/container/airia-test-pod)
[![Build Status](https://github.com/davidpacold/airia-test-pod/actions/workflows/build-and-publish.yml/badge.svg)](https://github.com/davidpacold/airia-test-pod/actions)

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster
- Ingress Controller (if using ingress):
  
  **NGINX Ingress Controller:**
  ```bash
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
  helm install ingress-nginx ingress-nginx/ingress-nginx --create-namespace --namespace ingress-nginx
  ```
  
  **Azure Application Gateway Ingress Controller (AGIC):**
  ```bash
  # Follow Azure documentation to set up AGIC
  # Then use: --set ingress.className="azure-application-gateway"
  ```

### Using Helm Repository (Recommended)

```bash
# 1. Add the Helm repository
helm repo add airia-test-pod https://davidpacold.github.io/airia-test-pod/
helm repo update

# 2. Create your configuration
cat > my-test-values.yaml << EOF
config:
  auth:
    username: "admin"
    password: "YourSecurePassword123!"
    secretKey: "your-random-jwt-secret-key"
  # Add your service configurations here...
EOF

# 3. Install (always gets the latest version)
helm install airia-test-pod airia-test-pod/airia-test-pod -f my-test-values.yaml

# 4. Access the dashboard
kubectl port-forward -n airia-preprod svc/airia-test-pod 8080:80
# Open http://localhost:8080
```

### Alternative: Direct GitHub Release

```bash
# Install specific version from GitHub release
helm install airia-test-pod https://github.com/davidpacold/airia-test-pod/releases/download/v1.0.1/airia-test-pod-1.0.1.tgz -f my-test-values.yaml
```

### Using Local Source

```bash
# 1. Clone the repository
git clone https://github.com/davidpacold/airia-test-pod.git
cd airia-test-pod

# 2. Create configuration and deploy
helm install airia-test-pod ./helm/airia-test-pod -f my-test-values.yaml
```

**⏱️ Complete deployment takes 5-10 minutes**

## 📋 What Does It Test?

### Core Services ✅
- **Azure PostgreSQL** - Connection validation, database listing, extension verification  
- **Azure Blob Storage** - Authentication, upload/download operations, container access
- **Azure OpenAI** - API connectivity, completion endpoints, embedding endpoints
- **Kubernetes Storage** - Storage class availability, PVC creation permissions

### Optional Services ⚙️
- **Azure Document Intelligence** - Document processing API
- **Self-hosted OpenAI-compatible models** - Local LLM deployments  
- **Self-hosted Llama models** - Ollama or similar
- **Enhanced SSL Certificate Validation** - Full certificate chain analysis (like `openssl s_client -showcerts`)
  - Detects missing intermediate certificates
  - Validates certificate chain completeness  
  - Checks certificate expiration and hostname matching
  - Identifies SSL misconfigurations that cause client failures

## 📖 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment and configuration guide
- **[Helm Chart README](helm/airia-test-pod/README.md)** - Helm-specific configuration options

## 🔧 Configuration Example

Create `my-test-values.yaml`:

```yaml
config:
  auth:
    username: "admin"
    password: "ChangeThisPassword123!"
    
  postgresql:
    enabled: true
    host: "your-server.postgres.database.azure.com"
    username: "your-username"
    password: "your-password"
    
  blobStorage:
    enabled: true
    accountName: "yourstorageaccount"
    accountKey: "your-storage-key"
    
  openai:
    enabled: true
    endpoint: "https://your-openai.openai.azure.com/"
    apiKey: "your-openai-key"

ingress:
  enabled: true
  className: "nginx"  # Use "azure-application-gateway" for Azure App Gateway
  hosts:
    - host: airia-test.yourdomain.com
      paths:
        - path: /
          pathType: Prefix

# For Azure Application Gateway users, also add:
# ingress:
#   className: "azure-application-gateway"
#   annotations:
#     kubernetes.io/ingress.class: azure/application-gateway
#     appgw.ingress.kubernetes.io/ssl-redirect: "false"
```

## 🔍 Understanding Results

| Status | Icon | Meaning |
|--------|------|---------|
| **Passed** | ✅ | Service is correctly configured |
| **Failed** | ❌ | Service has critical issues that need fixing |
| **Skipped** | ⏭️ | Optional service not configured (normal) |

## 🛠️ Alternative Deployments

### Docker (Development/Testing)
```bash
docker run -d -p 8080:8080 \
  -e AUTH_USERNAME=admin -e AUTH_PASSWORD=changeme \
  -e POSTGRES_HOST=your-server.postgres.database.azure.com \
  -e POSTGRES_USER=your-username -e POSTGRES_PASSWORD=your-password \
  ghcr.io/davidpacold/airia-test-pod:latest
```

### Raw Kubernetes Manifests
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret-example.yaml  # Edit first!
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

## 📊 Features

- **Real-time Dashboard** - Interactive web interface with live updates
- **WebSocket Integration** - Real-time test progress and status updates  
- **JWT Authentication** - Secure login system
- **Multiple Deployment Options** - Helm, Kubernetes, Docker
- **Comprehensive Testing** - 6 different infrastructure tests
- **Production Ready** - RBAC, security contexts, resource limits

## 🏗️ Architecture

```mermaid
graph TB
    Browser["🖥️ Web Browser<br/>• Dashboard UI<br/>• WebSocket<br/>• Real-time Updates"]
    
    FastAPI["⚡ FastAPI App<br/>• Authentication<br/>• Test Engine<br/>• WebSocket<br/>• API Endpoints"]
    
    Azure["☁️ Azure Services<br/>• PostgreSQL<br/>• Blob Storage<br/>• OpenAI<br/>• Doc Intel"]
    
    K8s["☸️ Kubernetes<br/>• Storage (PVC)<br/>• RBAC<br/>• Secrets<br/>• ConfigMaps"]
    
    Browser <--> FastAPI
    FastAPI <--> Azure
    FastAPI --> K8s
```

## 🔒 Security

- JWT authentication with configurable credentials
- Kubernetes RBAC with minimal required permissions
- Secure secret management via Kubernetes secrets
- Multi-stage Docker builds with security best practices
- TLS/HTTPS termination at ingress/load balancer level (pod accepts HTTP)
- Enhanced SSL certificate chain validation for external services

## 🆘 Troubleshooting

### Common Issues

**Connection Failed:**
- Check firewall rules and network connectivity
- Verify service endpoints and credentials
- Review Azure service configurations

**Permission Denied (PVC tests):**
- RBAC is configured automatically with Helm
- Manual deployments need proper service account permissions

**View Logs:**
```bash
kubectl logs -f -n airia-preprod -l app.kubernetes.io/name=airia-test-pod
```

## 📦 Project Structure

```
airia_test_pod/
├── app/                    # Application source code
│   ├── auth.py            # JWT authentication
│   ├── main.py            # FastAPI application
│   ├── models.py          # Data models
│   └── tests/             # Test implementations
├── templates/             # HTML templates
├── static/               # CSS and static assets
├── k8s/                  # Kubernetes manifests
├── helm/airia-test-pod/  # Helm chart
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies
└── DEPLOYMENT_GUIDE.md   # Complete deployment guide
```

## 🤝 Support

- **Documentation:** See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions
- **Issues:** When contacting support, include test results and pod logs
- **Email:** support@airia.io

## ✅ Project Status: COMPLETE

All requirements successfully implemented:
- ✅ Kubernetes application with infrastructure testing
- ✅ Web interface with real-time updates  
- ✅ Tests for PostgreSQL, Blob Storage, OpenAI, Document Intelligence, SSL, and PVC
- ✅ Multiple deployment options (Helm, K8s manifests, Docker)
- ✅ Production-ready security and best practices
- ✅ Comprehensive documentation

---

Made with ❤️ by the Airia Team