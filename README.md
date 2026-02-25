# Airia Infrastructure Test Pod

**Validate your infrastructure before deployment** - A comprehensive Kubernetes tool that tests connectivity to essential cloud services and provides intelligent remediation guidance.

Perfect for DevOps teams who need to verify that Azure services, databases, storage, and AI/ML endpoints are correctly configured before deploying production applications.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidpacold/airia-test-pod)](https://github.com/davidpacold/airia-test-pod/releases)
[![Helm Chart](https://img.shields.io/badge/helm-oci%3A%2F%2Fghcr.io-blue)](https://github.com/davidpacold/airia-test-pod/pkgs/container/airia-test-pod%2Fcharts%2Fairia-test-pod)
[![Container Image](https://img.shields.io/badge/container-ghcr.io-blue)](https://github.com/davidpacold/airia-test-pod/pkgs/container/airia-test-pod)
[![Build Status](https://github.com/davidpacold/airia-test-pod/actions/workflows/release.yml/badge.svg)](https://github.com/davidpacold/airia-test-pod/actions)

## ⚡ Get Started in 3 Steps

### Step 1: Install with Helm

```bash
# Install with OCI registry - automatically pulls latest version!
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.auth.username="admin" \
  --set config.auth.password="YourSecurePassword123!" \
  --set config.auth.secretKey="$(openssl rand -hex 32)" \
  --install --create-namespace \
  --namespace default
```

> **💡 Tip:** No `helm repo add` needed! OCI registry always pulls the latest version.

### Step 2: Access the Dashboard

```bash
# Port forward to access the web interface
kubectl port-forward -n default svc/airia-test-pod 8080:80

# Open your browser
open http://localhost:8080
# Login: admin / YourSecurePassword123!
```

### Step 3: Configure Your Services

Click "Run All Tests" to see which services need configuration, then add your service details using the [Configuration Guide](#-configuration-guide).

**⏱️ Total setup time: 5-10 minutes**

---

## 🔄 Version Management & Updates

### Automatic Version Checking ✨

The Helm chart includes **automatic version checking** to ensure you're always deploying the latest version:

- ✅ Checks if you're installing the latest version during upgrades
- ⚠️ Warns you if a newer version is available
- 🚫 Optionally blocks upgrades if not using the latest (strict mode)

**Enable strict mode to enforce always using the latest version:**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set versionCheck.strict=true \
  -f your-config.yaml \
  --namespace airia
```

### Automated Upgrade Script

Use our automated upgrade script for the easiest experience:

```bash
# From the repository
./scripts/upgrade.sh --oci -f your-config.yaml

# Or remotely
curl -sSL https://raw.githubusercontent.com/davidpacold/airia-test-pod/main/scripts/upgrade.sh | \
  bash -s -- --oci -f your-config.yaml
```

📚 **For complete version management details:** [Version Management Guide](docs/operations/versioning.md)

---

## 🎯 Production Setup & Advanced Deployment

For ingress, TLS, and production deployments, see:
- **[📄 Deployment Guide](docs/deployment/deployment-guide.md)** - Complete deployment instructions
- **[🚀 Example Deployment](docs/deployment/example-deployment.md)** - Step-by-step walkthrough
- **[🔄 Version Management Guide](docs/operations/versioning.md)** - Automated updates and version control

## 🧪 What Does It Test?

### ✅ **Required for Successful Airia Deployment**
These tests **must pass** for a successful Airia deployment:
- **🗄️ PostgreSQL Database** - Connection, extensions, permissions
- **🗄️ Apache Cassandra** - NoSQL database clusters, keyspace access
- **💾 Blob Storage** - Must have ONE of:
  - **Azure Blob Storage** - Authentication, file operations
  - **Amazon S3** - S3-compatible storage
  - **S3 Compatible** - S3-compatible storage (MinIO, etc.)
- **⚙️ Kubernetes Storage (PVC)** - Storage classes, volume creation (always enabled)
- **🔒 SSL Certificates** - Complete certificate chain validation

### 🎯 **Optional Tests** (Configure as needed)
- **🎮 GPU Detection** - NVIDIA GPU availability, driver, and CUDA installation

### 🤖 **AI & Machine Learning** (Configure as needed)

#### **Automated Standard Tests**
These tests verify that your AI services are configured correctly with automated checks:

- **Azure OpenAI & OpenAI-Compatible APIs** - Chat completions, model access, and embeddings
  - Tests both Azure-hosted and self-hosted OpenAI-compatible endpoints
  - Automatically validates API keys, endpoints, and model deployments

- **Ollama Native API** - Local Ollama server with native API endpoints
  - Tests Ollama's native REST API (`/api/generate`, `/api/chat`, `/api/tags`)
  - For local LLM testing with Ollama (llama3, codellama, mistral, phi3, etc.)
  - Note: For OpenAI-compatible Ollama endpoints (`/v1/*`), use the OpenAI test above

- **Azure Document Intelligence** - OCR and document processing capabilities
  - Tests document analysis, table extraction, and content recognition
  - Validates Azure Document Intelligence API configuration

- **Embedding Models** - Dedicated text vectorization testing
  - Tests OpenAI-compatible embedding endpoints (separate from Azure OpenAI embeddings)
  - Validates embedding generation, batch processing, and similarity calculations

#### **Custom AI Testing** (Interactive Testing)
After your services pass automated tests, use custom testing to validate with your own data:

- **Custom Prompts** - Test OpenAI-compatible and Ollama models with your own prompts
- **File Upload Testing** - Upload PDFs, images, or documents (up to 25MB) to test:
  - OpenAI vision/multimodal capabilities
  - Ollama model file processing
  - Azure Document Intelligence with your own documents
- **Custom Text Embeddings** - Generate embeddings for your specific text data

> **💡 When to use which:** Standard tests verify connectivity and basic functionality. Custom tests let you validate your specific use cases with real data.

### 🎯 **Advanced Features**
- **Intelligent Error Detection** - Automatic remediation suggestions
- **Real-time Results** - Live dashboard with detailed test outcomes
- **Batch Testing** - Run all tests simultaneously or individually

## 📚 Configuration Guide

### **1. PostgreSQL Database**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.postgresql.enabled=true \
  --set config.postgresql.host="your-server.postgres.database.azure.com" \
  --set config.postgresql.username="your-username" \
  --set config.postgresql.password="your-password" \
  --install --namespace default
```

### **2. Azure Blob Storage**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.blobStorage.enabled=true \
  --set config.blobStorage.accountName="yourstorageaccount" \
  --set config.blobStorage.accountKey="your-storage-key" \
  --set config.blobStorage.containerName="test-container" \
  --install --namespace default
```

### **3. AI & Machine Learning Services**

#### **Azure OpenAI (Chat + Embeddings)**
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.azureOpenai.enabled=true \
  --set config.azureOpenai.endpoint="https://your-openai.openai.azure.com/" \
  --set config.azureOpenai.apiKey="your-openai-key" \
  --set config.azureOpenai.chatDeployment="gpt-35-turbo" \
  --set config.azureOpenai.embeddingDeployment="text-embedding-ada-002" \
  --namespace default
```

#### **Ollama Native API**
For local Ollama server (native API):
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.ollama.enabled=true \
  --set config.ollama.baseUrl="http://ollama-server:11434" \
  --set config.ollama.modelName="llama3.1:8b" \
  --namespace default
```

> **Note:** This tests Ollama's native `/api/*` endpoints. For OpenAI-compatible Ollama endpoints (`/v1/*`), use the OpenAI configuration with `baseUrl="http://ollama-server:11434/v1"`.

#### **Azure Document Intelligence**
For OCR and document processing:
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.documentIntelligence.enabled=true \
  --set config.documentIntelligence.endpoint="https://your-docintel.cognitiveservices.azure.com/" \
  --set config.documentIntelligence.apiKey="your-doc-intel-key" \
  --namespace default
```

#### **OpenAI Direct API**
For direct OpenAI API access:
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.openaiDirect.enabled=true \
  --set config.openaiDirect.apiKey="your-openai-api-key" \
  --set config.openaiDirect.model="gpt-4o-mini" \
  --namespace default
```

### **4. GPU Detection**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.gpu.enabled=true \
  --set config.gpu.required=false \
  --install --namespace default
```

### **5. Using a Values File (Recommended for Multiple Services)**

For a comprehensive configuration file with all available options, see the [Helm Configuration Reference](helm/airia-test-pod/values.yaml). This file includes:
- Detailed comments for every configuration option
- Examples for all supported services
- Cloud provider annotations for AWS, Azure, and GCP
- Advanced Kubernetes settings

**Quick Start Example** - Create `my-config.yaml`:
```yaml
config:
  # Core Infrastructure
  postgresql:
    enabled: true
    host: "your-server.postgres.database.azure.com"
    username: "your-username"
    password: "your-password"

  blobStorage:
    enabled: true
    accountName: "yourstorageaccount"
    accountKey: "your-storage-key"
    containerName: "test-container"

  # AI & Machine Learning

  # Azure OpenAI (includes chat + embeddings)
  azureOpenai:
    enabled: true
    endpoint: "https://your-openai.openai.azure.com/"
    apiKey: "your-openai-key"
    chatDeployment: "gpt-35-turbo"
    embeddingDeployment: "text-embedding-ada-002"  # Optional

  # Ollama native API (separate from OpenAI)
  ollama:
    enabled: true
    baseUrl: "http://ollama-server:11434"
    modelName: "llama3.1:8b"
    maxTokens: 100
    temperature: 0.7
    timeout: 60

  # Azure Document Intelligence
  documentIntelligence:
    enabled: true
    endpoint: "https://your-docintel.cognitiveservices.azure.com/"
    apiKey: "your-doc-intel-key"

  # GPU Detection
  gpu:
    enabled: true
    required: false  # Set to true to require GPU presence

# Optional: Enable version checking strict mode
versionCheck:
  enabled: true
  strict: false  # Set to true to block upgrades if not using latest version
```

Then install or upgrade:
```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-config.yaml \
  --namespace default
```

> **💡 For all configuration options:** See the comprehensive [Helm values.yaml](helm/airia-test-pod/values.yaml) with detailed documentation for every setting.

---

## 🤔 AI/ML Testing Decision Guide

**Not sure which AI test to configure?** Use this decision tree:

| Your Situation | Test to Configure | Why |
|---------------|-------------------|-----|
| Using Azure OpenAI for chat completions | **Azure OpenAI** | Tests chat APIs and optionally embeddings in one test |
| Using Azure OpenAI embeddings | **Azure OpenAI** (set `embeddingDeploymentName`) | Azure OpenAI embeddings are tested within the OpenAI test |
| Using self-hosted LLM (vLLM, LocalAI, etc.) | **OpenAI-Compatible APIs** | Most local LLMs provide OpenAI-compatible endpoints at `/v1/*` |
| Using Ollama's OpenAI-compatible endpoint | **OpenAI-Compatible APIs** | Set `baseUrl` to `http://ollama:11434/v1` |
| Using Ollama's native API | **Ollama Native API** | Tests Ollama's native `/api/*` endpoints for maximum compatibility |
| Processing PDFs/images for OCR | **Azure Document Intelligence** | Tests document analysis and table extraction |
| Using separate embedding service (not Azure) | **Dedicated Embedding Models** | For standalone embedding endpoints like OpenAI's API |
| Want to test custom prompts | Use **Custom AI Testing** in the UI | Available after standard tests pass |
| Want to upload files for testing | Use **Custom AI Testing** in the UI | Supports PDFs, images up to 25MB |

**Common Questions:**

- **Q: Can I configure both Azure OpenAI and Ollama?**
  A: Yes! They're separate tests. Configure both if you use both services.

- **Q: What's the difference between OpenAI-Compatible and Ollama Native tests?**
  A: OpenAI-Compatible tests the `/v1/*` endpoints (works with Ollama, vLLM, etc.). Ollama Native tests Ollama's `/api/*` endpoints for Ollama-specific features.

- **Q: Do I need the Embedding test if I have Azure OpenAI?**
  A: No. Azure OpenAI includes embedding testing. Only use the dedicated Embedding test for non-Azure endpoints.

- **Q: What's the difference between standard tests and custom testing?**
  A: Standard tests run automated checks to verify configuration. Custom testing lets you upload your own files and prompts.

- **Q: Which test should I use for Ollama?**
  A: For Ollama's OpenAI-compatible endpoints (`/v1/*`), use the OpenAI test. For native Ollama API (`/api/*`), use the Ollama test.

---

## 📖 Complete Documentation

### 🎯 **Deployment & Configuration**
- **[🚀 Deployment Guide](docs/deployment/deployment-guide.md)** - Complete deployment instructions
- **[🔄 Version Management](docs/operations/versioning.md)** - Automatic updates, version checking, upgrade scripts
- **[🏭 Example Deployment](docs/deployment/example-deployment.md)** - Step-by-step walkthrough
- **[📄 Complete Configuration Example](examples/helm/basic-values.yaml)** - All tests with detailed examples
- **[⚙️ Helm Configuration Reference](helm/airia-test-pod/values.yaml)** - Every available setting

### 🛠️ **Advanced Features**
- **Automatic Version Checking** - Ensures you're always using the latest version
- **OCI Registry Support** - No need for `helm repo update`, always fresh
- **Pre-Upgrade Hooks** - Validates versions before deployment
- **Automated Upgrade Script** - One-command upgrades with health checks

## 🔍 Understanding Test Results

### **Test Status Indicators**
- ✅ **Passed** - Service is correctly configured and working
- ❌ **Failed** - Service has issues that need attention
- ⏭️ **Skipped** - Service not configured (this is normal for optional services)

### **What Happens When Tests Fail?**
Don't worry! The test pod provides intelligent guidance:

- **Detailed error descriptions** - Clear explanation of what's wrong
- **Root cause analysis** - Why the issue occurred
- **Step-by-step remediation** - Exact commands or configuration changes needed
- **Documentation links** - Additional resources for complex issues

**Common Issues Automatically Detected:**
- SSL certificate problems (missing intermediate certificates, expiration)
- Database connection issues (credentials, network access, missing extensions)
- Storage configuration problems (missing storage classes, permissions)
- AI/ML service access (incorrect endpoints, API keys, model availability)

## 🐳 Alternative: Docker for Local Testing

```bash
# Quick test with Docker (no Kubernetes required)
docker run -d -p 8080:8080 \
  -e AUTH_USERNAME=admin \
  -e AUTH_PASSWORD=changeme \
  ghcr.io/davidpacold/airia-test-pod:latest

# Access at http://localhost:8080
```

**Available Registries:** GitHub Container Registry (recommended), Docker Hub

---

## 🆘 Troubleshooting

### **Connection Issues**
```bash
# Check pod logs for detailed error messages
kubectl logs -n airia -l app.kubernetes.io/name=airia-test-pod

# Verify services are accessible from the pod
kubectl exec -n airia deployment/airia-test-pod -- nslookup your-server.postgres.database.azure.com
```

### **Dashboard Access Problems**
```bash
# Port forward not working? Try:
kubectl get pods -n airia
kubectl port-forward -n airia pod/airia-test-pod-xxx 8080:8080

# Check if ingress is configured
kubectl get ingress -n airia
```

### **Configuration Not Taking Effect**
```bash
# Verify your configuration was applied
helm get values airia-test-pod

# Restart the pod to pick up new config
kubectl rollout restart -n airia deployment/airia-test-pod
```

---

## 📚 Documentation & Resources

### Documentation
- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Deployment](docs/deployment/)** - Deployment guides and examples
- **[Operations](docs/operations/)** - Version management and rollback procedures
- **[Development](docs/development/)** - Development setup and contributing

### Examples
- **[Examples Index](examples/README.md)** - Configuration examples overview
- **[Helm Examples](examples/helm/)** - Helm values files
- **[Kubernetes Examples](k8s/)** - Kubernetes manifests

### Testing
- **[Manual Tests](tests/manual_tests/)** - Manual test scripts and configurations

## 🤝 Support & Feedback

- **🐛 Found an Issue?** [GitHub Issues](https://github.com/davidpacold/airia-test-pod/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/davidpacold/airia-test-pod/discussions)

---

<div align="center">

**⭐ If this tool helped you validate your infrastructure, please star the repo!**

Made with ❤️ for DevOps teams everywhere

</div>

## 🧹 Clean Up

When you're done testing, remove the test pod:

```bash
helm uninstall airia-test-pod
```
