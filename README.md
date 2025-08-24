# Airia Infrastructure Test Pod

A comprehensive Kubernetes application that validates infrastructure readiness before deploying production applications. This tool tests connectivity to essential Azure services and provides actionable feedback for resolving common configuration issues.

![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidpacold/airia-test-pod)
![Container Image](https://img.shields.io/badge/container-ghcr.io-blue)
![License](https://img.shields.io/github/license/davidpacold/airia-test-pod)

## 🚀 Quick Start

### Using Published Container Image

```bash
# 1. Create your configuration file (my-test-values.yaml)
cat > my-test-values.yaml << EOF
image:
  repository: ghcr.io/davidpacold/airia-test-pod
  tag: latest

config:
  auth:
    username: "admin"
    password: "YourSecurePassword123!"
    secretKey: "your-random-jwt-secret-key"
  # Add your service configurations here...
EOF

# 2. Deploy with Helm using published image
helm install airia-test-pod oci://ghcr.io/davidpacold/airia-test-pod/helm/airia-test-pod -f my-test-values.yaml

# 3. Access the dashboard
kubectl port-forward -n airia-preprod svc/airia-test-pod 8080:80
# Open http://localhost:8080
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
  hosts:
    - host: airia-test.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
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
  airia/test-pod:latest
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
- TLS/HTTPS support for production deployments

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