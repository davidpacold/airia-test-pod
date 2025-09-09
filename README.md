# Airia Infrastructure Test Pod

**Validate your infrastructure before deployment** - A comprehensive Kubernetes tool that tests connectivity to essential cloud services and provides intelligent remediation guidance.

Perfect for DevOps teams who need to verify that Azure services, databases, storage, and AI/ML endpoints are correctly configured before deploying production applications.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidpacold/airia-test-pod)](https://github.com/davidpacold/airia-test-pod/releases)
[![Container Image](https://img.shields.io/badge/container-ghcr.io%2Fdavidpacold%2Fairia--test--pod-blue)](https://github.com/davidpacold/airia-test-pod/pkgs/container/airia-test-pod)
[![Docker Hub](https://img.shields.io/docker/v/davidpacold/airia-test-pod?label=Docker%20Hub)](https://hub.docker.com/r/davidpacold/airia-test-pod)
[![Build Status](https://github.com/davidpacold/airia-test-pod/actions/workflows/build-and-publish.yml/badge.svg)](https://github.com/davidpacold/airia-test-pod/actions)

## ⚡ Get Started in 3 Steps

### Step 1: Install with Helm (Recommended)

```bash
# Add the Helm repository
helm repo add airia-test-pod https://davidpacold.github.io/airia-test-pod/
helm repo update

# Install with basic authentication (customize as needed)
helm install airia-test-pod airia-test-pod/airia-test-pod \
  --set config.auth.username="admin" \
  --set config.auth.password="YourSecurePassword123!" \
  --set config.auth.secretKey="$(openssl rand -hex 32)"
```

### Step 2: Access the Dashboard

```bash
# Port forward to access the web interface
kubectl port-forward -n airia-preprod svc/airia-test-pod 8080:80

# Open your browser
open http://localhost:8080
# Login: admin / YourSecurePassword123!
```

### Step 3: Configure Your Services

Click "Run All Tests" to see which services need configuration, then add your service details using the [Configuration Guide](#-configuration-guide).

**⏱️ Total setup time: 5-10 minutes**

---

## 🎯 Need Production Setup?

For ingress, TLS, and production deployments, see our **[Complete Deployment Guide](DEPLOYMENT_GUIDE.md)** with step-by-step instructions.

## 🧪 What Does It Test?

### ✅ **Core Infrastructure** (Essential for most deployments)
- **🗄️ PostgreSQL Database** - Connection, extensions, permissions
- **💾 Azure Blob Storage** - Authentication, file operations
- **⚙️ Kubernetes Storage (PVC)** - Storage classes, volume creation
- **🔒 SSL Certificates** - Complete certificate chain validation

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
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  --set config.postgresql.enabled=true \
  --set config.postgresql.host="your-server.postgres.database.azure.com" \
  --set config.postgresql.username="your-username" \
  --set config.postgresql.password="your-password"
```

### **2. Azure Blob Storage**
```bash
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  --set config.blobStorage.enabled=true \
  --set config.blobStorage.accountName="yourstorageaccount" \
  --set config.blobStorage.accountKey="your-storage-key" \
  --set config.blobStorage.containerName="test-container"
```

### **3. Azure OpenAI**
```bash
helm upgrade airia-test-pod airia-test-pod/airia-test-pod \
  --set config.openai.enabled=true \
  --set config.openai.endpoint="https://your-openai.openai.azure.com/" \
  --set config.openai.apiKey="your-openai-key" \
  --set config.openai.deploymentName="gpt-35-turbo"
```

### **4. Using a Values File (Recommended for Multiple Services)**

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
```

Then upgrade:
```bash
helm upgrade airia-test-pod airia-test-pod/airia-test-pod -f my-config.yaml
```

---

## 📖 Complete Documentation

### 🎯 **Need More Configuration Options?**
- **[📄 Complete Configuration Example](Test%20deploy/values-example.yaml)** - All 7 tests with detailed examples
- **[🚀 Production Deployment Guide](DEPLOYMENT_GUIDE.md)** - Ingress, TLS, and production setup
- **[⚙️ Helm Configuration Reference](helm/airia-test-pod/values.yaml)** - Every available setting

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
