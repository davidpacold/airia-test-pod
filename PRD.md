# Product Requirements Document: Infrastructure Readiness Test Application

## Overview
A Kubernetes-based application that validates customer infrastructure readiness before deploying the main application by testing connectivity and functionality of required Azure services.

## Problem Statement
Customers often begin deployment processes prematurely without proper infrastructure setup, leading to poor deployment experiences. Common issues include incomplete SSL certificate chains, missing database extensions, and inaccessible LLM models.

## Target Users
Application administrators responsible for infrastructure setup and deployment.

## Core Features

### 1. Connectivity Testing Suite
Tests connectivity and basic operations for:
- **Azure Flexible PostgreSQL Server**
  - List all databases
  - List all installed extensions
  - Verify connection and authentication
  
- **Azure Blob Storage**
  - Test upload operation
  - Test download operation
  - Verify authentication and permissions
  
- **Azure Document Intelligence** (Optional)
  - Send test document
  - Retrieve response
  - Verify API connectivity
  
- **Azure OpenAI**
  - Test completion endpoint
  - Test embedding endpoint
  - Verify model accessibility
  
- **Self-hosted OpenAI-compatible model** (Optional)
  - Test completion endpoint
  - Test embedding endpoint
  
- **Self-hosted Llama-compatible model** (Optional)
  - Test completion endpoint
  - Test embedding endpoint
  
- **Kubernetes Persistent Volume Claim (PVC)**
  - Test PVC creation
  - Verify storage class availability
  - Test read/write operations
  - Clean up test PVC

### 2. Web Dashboard
- Display test results with status indicators (Pass/Fail/Running)
- Show detailed logs for each test
- Basic authentication (username/password)
- On-demand test execution
- Real-time status updates

### 3. Error Detection & Remediation
Specific checks for common issues:
- SSL certificate chain validation for public URLs
- PostgreSQL extension verification
- LLM model accessibility checks
- Kubernetes storage class availability
- PVC creation permissions
- Provide remediation suggestions for detected issues

## Technical Requirements

### Application Stack
- Language: Python or Node.js (TBD based on team preference)
- Web Framework: FastAPI/Flask (Python) or Express (Node.js)
- Frontend: Simple HTML/CSS/JavaScript or React
- Container: Docker
- Orchestration: Kubernetes

### Configuration
- All credentials via environment variables
- Test results stored in-memory only
- Configuration for optional services

### Kubernetes Deployment
- Namespace: `airia-preprod`
- Ingress Controller: NGINX
- HTTPS/TLS: Customer-managed (SSL offloading at ingress)
- Service Type: ClusterIP with Ingress
- Multiple hostname support: Up to 5 customer-defined hostnames
- Each hostname can have its own TLS certificate

### Security
- Basic authentication for web interface
- Secure credential handling
- No persistent storage of test results or logs
- Minimal permissions principle for Azure service connections

## Non-Functional Requirements
- Lightweight and fast deployment
- Clear error messages and logs
- Responsive web interface
- Support for concurrent test execution
- Graceful handling of service timeouts

## Success Criteria
1. Accurately identifies infrastructure readiness issues before main app deployment
2. Reduces failed deployments by 80%
3. Provides clear, actionable feedback for remediation
4. Easy to deploy and configure in customer environments

## Out of Scope
- Email/webhook notifications
- Historical test result storage
- Scheduled/automated testing
- Multi-tenancy support
- Advanced authentication methods (OAuth, SAML, etc.)

## Deliverables
1. Containerized application
2. Published container image in registry (Docker Hub, ACR, or customer's choice)
3. Helm chart for easy deployment
4. Kubernetes manifests (Deployment, Service, Ingress, ConfigMap, Secret templates)
5. Documentation (deployment guide, configuration reference)
6. Example environment variable configuration
7. Troubleshooting guide with common issues and solutions

## Distribution Strategy
- Container images published to public or private registry
- Helm chart in a Helm repository or as downloadable package
- Support for multiple registry options (Docker Hub, Azure Container Registry, etc.)
- Versioned releases with semantic versioning
- Multi-architecture support (amd64, arm64)