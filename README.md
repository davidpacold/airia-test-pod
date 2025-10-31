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
  --install --create-namespace --namespace default
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
  -f your-config.yaml
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

📚 **For complete version management details:** [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)

---

## 🎯 Production Setup & Advanced Deployment

For ingress, TLS, and production deployments, see:
- **[📄 Complete Deployment Guide](DEPLOYMENT.md)** - OCI registry, version management, troubleshooting
- **[🚀 Production Deployment Guide](DEPLOYMENT_GUIDE.md)** - Ingress, TLS, and production setup
- **[🔄 Version Management Guide](VERSION_MANAGEMENT.md)** - Automated updates and version control

## 🧪 What Does It Test?

### ✅ **Core Infrastructure** (Essential for most deployments)
- **🗄️ PostgreSQL Database** - Connection, extensions, permissions
- **💾 Azure Blob Storage** - Authentication, file operations
- **⚙️ Kubernetes Storage (PVC)** - Storage classes, volume creation
- **🔒 SSL Certificates** - Complete certificate chain validation
- **🎮 GPU Detection** - NVIDIA GPU availability, driver, and CUDA installation

### 🤖 **AI & Machine Learning** (Configure as needed)
- **Azure OpenAI** - API connectivity, model access, embeddings
- **Azure Document Intelligence** - Document processing capabilities
- **Custom AI Testing** - Upload files and test prompts with your AI models
- **Embedding Models** - Text vectorization and similarity analysis

### 🔧 **Additional Services** (Optional)
- **Apache Cassandra** - NoSQL database clusters
- **Amazon S3 / MinIO** - S3-compatible storage
- **Self-hosted LLMs** - Local OpenAI-compatible and Llama models

### 🎯 **Advanced Features**
- **Custom File Upload Testing** - Test AI models with PDFs, images, documents (up to 25MB)
- **Intelligent Error Detection** - Automatic remediation suggestions
- **Real-time Results** - Live dashboard with detailed test outcomes

## 📚 Configuration Guide

### **1. PostgreSQL Database**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.postgresql.enabled=true \
  --set config.postgresql.host="your-server.postgres.database.azure.com" \
  --set config.postgresql.username="your-username" \
  --set config.postgresql.password="your-password"
```

### **2. Azure Blob Storage**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.blobStorage.enabled=true \
  --set config.blobStorage.accountName="yourstorageaccount" \
  --set config.blobStorage.accountKey="your-storage-key" \
  --set config.blobStorage.containerName="test-container"
```

### **3. Azure OpenAI**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.openai.enabled=true \
  --set config.openai.endpoint="https://your-openai.openai.azure.com/" \
  --set config.openai.apiKey="your-openai-key" \
  --set config.openai.deploymentName="gpt-35-turbo"
```

### **4. GPU Detection**
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.gpu.enabled=true \
  --set config.gpu.required=false
```

### **5. Using a Values File (Recommended for Multiple Services)**

Create `my-config.yaml`:
```yaml
config:
  # Enable and configure the services you use
  postgresql:
    enabled: true
    host: "your-server.postgres.database.azure.com"
    username: "your-username"
    password: "your-password"

  openai:
    enabled: true
    endpoint: "https://your-openai.openai.azure.com/"
    apiKey: "your-openai-key"
    deploymentName: "gpt-35-turbo"

  gpu:
    enabled: true
    required: false  # Set to true to require GPU presence

# Optional: Enable version checking strict mode
versionCheck:
  enabled: true
  strict: false  # Set to true to block upgrades if not using latest version
```

Then upgrade:
```bash
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-config.yaml
```

---

## 📖 Complete Documentation

### 🎯 **Deployment & Configuration**
- **[🚀 Deployment Guide](DEPLOYMENT.md)** - OCI registry, traditional Helm repo, automated upgrades
- **[🔄 Version Management](VERSION_MANAGEMENT.md)** - Automatic updates, version checking, upgrade scripts
- **[🏭 Production Setup](DEPLOYMENT_GUIDE.md)** - Ingress, TLS, and production deployment
- **[📄 Complete Configuration Example](Test%20deploy/values-example.yaml)** - All tests with detailed examples
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
kubectl logs -n airia-preprod -l app.kubernetes.io/name=airia-test-pod

# Verify services are accessible from the pod
kubectl exec -n airia-preprod deployment/airia-test-pod -- nslookup your-server.postgres.database.azure.com
```

### **Dashboard Access Problems**
```bash
# Port forward not working? Try:
kubectl get pods -n airia-preprod
kubectl port-forward -n airia-preprod pod/airia-test-pod-xxx 8080:8080

# Check if ingress is configured
kubectl get ingress -n airia-preprod
```

### **Configuration Not Taking Effect**
```bash
# Verify your configuration was applied
helm get values airia-test-pod

# Restart the pod to pick up new config
kubectl rollout restart -n airia-preprod deployment/airia-test-pod
```

---

## 🤝 Support & Feedback

- **📚 Complete Documentation**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **🐛 Found an Issue?** [GitHub Issues](https://github.com/davidpacold/airia-test-pod/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/davidpacold/airia-test-pod/discussions)

---

<div align="center">

**⭐ If this tool helped you validate your infrastructure, please star the repo!**

Made with ❤️ for DevOps teams everywhere

</div>
# Force version sync build Tue Sep  9 15:14:59 EDT 2025
# Final version sync build Tue Sep  9 15:31:16 EDT 2025
