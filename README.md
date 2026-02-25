# Airia Infrastructure Test Pod

**Validate your infrastructure before deployment** - A comprehensive Kubernetes tool that tests connectivity to essential cloud services and provides intelligent remediation guidance.

Perfect for DevOps teams who need to verify that Azure services, databases, storage, and AI/ML endpoints are correctly configured before deploying production applications.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/davidpacold/airia-test-pod)](https://github.com/davidpacold/airia-test-pod/releases)
[![Helm Chart](https://img.shields.io/badge/helm-oci%3A%2F%2Fghcr.io-blue)](https://github.com/davidpacold/airia-test-pod/pkgs/container/airia-test-pod%2Fcharts%2Fairia-test-pod)
[![Container Image](https://img.shields.io/badge/container-ghcr.io-blue)](https://github.com/davidpacold/airia-test-pod/pkgs/container/airia-test-pod)
[![Build Status](https://github.com/davidpacold/airia-test-pod/actions/workflows/release.yml/badge.svg)](https://github.com/davidpacold/airia-test-pod/actions)

## ⚡ Quick Start

### 1. Install with Helm

```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.auth.password="YourSecurePassword123!" \
  --set config.auth.secretKey="$(openssl rand -hex 32)" \
  --namespace airia --create-namespace
```

> **Tip:** No `helm repo add` needed! OCI registry always pulls the latest version. Username defaults to `admin`.

### 2. Access the Dashboard

```bash
kubectl port-forward -n airia svc/airia-test-pod 8080:80
open http://localhost:8080
# Login: admin / YourSecurePassword123!
```

### 3. Configure Your Services

Click "Run All Tests" to see which services need configuration, then add your service details using the [example values file](helm/airia-test-pod/examples/basic-values.yaml).

**Total setup time: 5-10 minutes**

---

## 📚 Configuration

### Using a Values File (Recommended)

Download the [example values file](helm/airia-test-pod/examples/basic-values.yaml), fill in your service details, and deploy:

```bash
helm upgrade --install airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  -f my-config.yaml \
  --namespace airia
```

The example file includes every available test with clear comments — just set `enabled: true` and fill in your credentials for the services you need.

### Using --set Flags (Quick Single-Service Setup)

For enabling individual services without a values file:

```bash
# Example: Enable PostgreSQL
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set config.postgresql.enabled=true \
  --set config.postgresql.host="your-server.postgres.database.azure.com" \
  --set config.postgresql.username="your-username" \
  --set config.postgresql.password="your-password" \
  --install --namespace airia
```

---

## 🧪 What Does It Test?

### Required for Successful Airia Deployment
These tests **must pass** for a successful Airia deployment:
- **PostgreSQL Database** - Connection, extensions, permissions
- **Apache Cassandra** - NoSQL database clusters, keyspace access
- **Blob Storage** - Must have ONE of: Azure Blob Storage, Amazon S3, or S3 Compatible (MinIO, etc.)
- **Kubernetes Storage (PVC)** - Storage classes, volume creation (always enabled)
- **SSL Certificates** - Complete certificate chain validation

### AI & Machine Learning (Configure as needed)
- **Azure OpenAI** - Chat completions, embeddings, and vision
- **AWS Bedrock** - Chat, embedding, and vision via Bedrock API
- **OpenAI Direct** - Chat completions with your OpenAI API key
- **Anthropic** - Chat completions with Claude models
- **Google Gemini** - Chat completions with Gemini models
- **Mistral AI** - Chat completions with Mistral models
- **Vision Model** - Self-hosted OpenAI-compatible vision endpoints
- **Dedicated Embedding** - Standalone embedding endpoints (LM Studio, vLLM, Ollama, etc.)
- **Azure Document Intelligence** - OCR and document processing

### Infrastructure (Configure as needed)
- **DNS Resolution** - Hostname resolution testing
- **GPU Detection** - NVIDIA GPU availability, driver, and CUDA installation

### Custom AI Testing (Interactive)
After automated tests pass, use the dashboard to test with your own data:
- Custom prompts, file uploads (up to 25MB), and custom text embeddings

---

## 🤔 AI/ML Testing Decision Guide

| Your Situation | Test to Configure | Why |
|---------------|-------------------|-----|
| Using Azure OpenAI for chat completions | **Azure OpenAI** | Tests chat APIs and optionally embeddings in one test |
| Using Azure OpenAI embeddings | **Azure OpenAI** (set `embeddingDeployment`) | Azure OpenAI embeddings are tested within the OpenAI test |
| Using AWS Bedrock models | **AWS Bedrock** | Tests chat, embedding, and vision via Bedrock API |
| Using OpenAI API directly | **OpenAI Direct** | Tests chat completions with your OpenAI API key |
| Using Anthropic Claude | **Anthropic** | Tests chat completions with Claude models |
| Using Google Gemini | **Google Gemini** | Tests chat completions with Gemini models |
| Using Mistral AI | **Mistral AI** | Tests chat completions with Mistral models |
| Using self-hosted LLM (vLLM, Ollama, etc.) | **Vision Model** or **OpenAI Direct** | Most local LLMs provide OpenAI-compatible endpoints at `/v1/*` |
| Using separate embedding service | **Dedicated Embedding** | For standalone embedding endpoints (LM Studio, vLLM, Ollama, etc.) |
| Processing PDFs/images for OCR | **Azure Document Intelligence** | Tests document analysis and table extraction |

**Q: Do I need the Embedding test if I have Azure OpenAI?**
No. Azure OpenAI includes embedding testing. Only use Dedicated Embedding for non-Azure endpoints.

**Q: Can I test a self-hosted model?**
Yes. Use **Vision Model** for `/v1/chat/completions` endpoints. Use **Dedicated Embedding** for `/v1/embeddings` endpoints.

---

## 🔍 Understanding Test Results

| Status | Meaning |
|--------|---------|
| ✅ **Passed** | Service is correctly configured and working |
| ❌ **Failed** | Service has issues — see remediation guidance |
| ⏭️ **Skipped** | Service not configured (normal for optional services) |

When tests fail, the dashboard provides detailed error descriptions, root cause analysis, step-by-step remediation, and documentation links.

---

## 🔄 Version Management

The Helm chart includes **automatic version checking**:
- Checks if you're installing the latest version during upgrades
- Warns you if a newer version is available
- Optionally blocks upgrades if not using the latest (strict mode)

```bash
# Enable strict mode to enforce latest version
helm upgrade airia-test-pod \
  oci://ghcr.io/davidpacold/airia-test-pod/charts/airia-test-pod \
  --set versionCheck.strict=true \
  -f your-config.yaml
```

For more details: [Version Management Guide](docs/operations/VERSIONING.md)

---

## 🐳 Alternative: Docker for Local Testing

```bash
docker run -d -p 8080:8080 \
  -e AUTH_USERNAME=admin \
  -e AUTH_PASSWORD=changeme \
  ghcr.io/davidpacold/airia-test-pod:latest
# Access at http://localhost:8080
```

---

## 🆘 Troubleshooting

```bash
# Check pod logs
kubectl logs -l app.kubernetes.io/name=airia-test-pod

# Verify services are accessible from the pod
kubectl exec deployment/airia-test-pod -- nslookup your-server.postgres.database.azure.com

# Verify configuration was applied
helm get values airia-test-pod

# Restart pod to pick up new config
kubectl rollout restart deployment/airia-test-pod
```

---

## 📖 Documentation

- **[Deployment Guide](docs/deployment/deployment-guide.md)** - Complete deployment instructions

- **[Example Values File](helm/airia-test-pod/examples/basic-values.yaml)** - Customer-ready config template
- **[Version Management](docs/operations/VERSIONING.md)** - Automatic updates and version control


## 🤝 Support & Feedback

- **Found an Issue?** [GitHub Issues](https://github.com/davidpacold/airia-test-pod/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/davidpacold/airia-test-pod/discussions)

---

## 🧹 Clean Up

```bash
helm uninstall airia-test-pod
```
