#!/bin/bash
set -e

# Airia Test Pod - Automated Upgrade Script
# This script ensures you always deploy the latest version

REPO_NAME="airia-test-pod"
CHART_NAME="airia-test-pod"
RELEASE_NAME="airia-test-pod"
NAMESPACE="default"
CONFIG_FILE=""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --oci)
            USE_OCI=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --config FILE    Config file (e.g., aws-pre-install-config.yaml)"
            echo "  -n, --namespace NS   Kubernetes namespace (default: default)"
            echo "  --oci                Use OCI registry instead of traditional Helm repo"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Airia Test Pod - Automated Upgrade${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check if config file is provided and exists
if [ -n "$CONFIG_FILE" ] && [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Check current installed version
echo -e "${YELLOW}📊 Checking current installation...${NC}"
CURRENT_VERSION=$(helm list -n "$NAMESPACE" -o json | jq -r ".[] | select(.name==\"$RELEASE_NAME\") | .chart" 2>/dev/null || echo "Not installed")
echo "Current: $CURRENT_VERSION"
echo ""

# Use OCI registry or traditional Helm repo
if [ "$USE_OCI" = true ]; then
    echo -e "${YELLOW}🔄 Using OCI registry (no repo update needed)${NC}"
    OCI_REPO="oci://ghcr.io/davidpacold/airia-test-pod/charts"

    # Get latest version from OCI registry
    echo "Fetching latest version from OCI registry..."
    LATEST_VERSION=$(helm show chart "$OCI_REPO/$CHART_NAME" 2>/dev/null | grep '^version:' | awk '{print $2}')

    if [ -z "$LATEST_VERSION" ]; then
        echo -e "${RED}Failed to fetch version from OCI registry${NC}"
        exit 1
    fi

    echo "Latest: $CHART_NAME-$LATEST_VERSION"
    echo ""

    # Build upgrade command
    UPGRADE_CMD="helm upgrade $RELEASE_NAME $OCI_REPO/$CHART_NAME --version $LATEST_VERSION --namespace $NAMESPACE --install"

else
    echo -e "${YELLOW}🔄 Updating Helm repository...${NC}"
    helm repo add "$REPO_NAME" https://davidpacold.github.io/airia-test-pod/ 2>/dev/null || true
    helm repo update "$REPO_NAME"
    echo ""

    # Check latest available version
    echo -e "${YELLOW}📦 Checking latest available version...${NC}"
    LATEST_VERSION=$(helm search repo "$REPO_NAME/$CHART_NAME" -o json | jq -r '.[0].version' 2>/dev/null || echo "Unknown")
    echo "Latest: $CHART_NAME-$LATEST_VERSION"
    echo ""

    # Build upgrade command
    UPGRADE_CMD="helm upgrade $RELEASE_NAME $REPO_NAME/$CHART_NAME --namespace $NAMESPACE --install"
fi

# Add config file if provided
if [ -n "$CONFIG_FILE" ]; then
    UPGRADE_CMD="$UPGRADE_CMD -f $CONFIG_FILE"
fi

# Show what will be upgraded
echo -e "${YELLOW}🚀 Upgrade Plan:${NC}"
echo "  Release: $RELEASE_NAME"
echo "  Namespace: $NAMESPACE"
echo "  Target Version: $LATEST_VERSION"
[ -n "$CONFIG_FILE" ] && echo "  Config: $CONFIG_FILE"
echo ""

# Ask for confirmation
read -p "Proceed with upgrade? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Upgrade cancelled."
    exit 0
fi

# Perform the upgrade
echo ""
echo -e "${GREEN}⚙️  Performing upgrade...${NC}"
echo "Command: $UPGRADE_CMD"
echo ""

if eval "$UPGRADE_CMD"; then
    echo ""
    echo -e "${GREEN}✅ Upgrade completed successfully!${NC}"
    echo ""

    # Show new status
    echo -e "${YELLOW}📊 New deployment status:${NC}"
    helm list -n "$NAMESPACE" | grep "$RELEASE_NAME" || true
    echo ""

    # Wait for rollout
    echo -e "${YELLOW}⏳ Waiting for rollout to complete...${NC}"
    kubectl rollout status deployment/"$RELEASE_NAME" -n "$NAMESPACE" --timeout=300s || true
    echo ""

    # Show pod status
    echo -e "${YELLOW}📦 Pod status:${NC}"
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name="$CHART_NAME" || true
    echo ""

    echo -e "${GREEN}🎉 Deployment complete!${NC}"
    echo ""
    echo "To check application health:"
    echo "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=$CHART_NAME --tail=50"
    echo "  kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME 8080:8080"

else
    echo ""
    echo -e "${RED}❌ Upgrade failed!${NC}"
    echo ""
    echo "To check what went wrong:"
    echo "  helm status $RELEASE_NAME -n $NAMESPACE"
    echo "  kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=$CHART_NAME"
    echo "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=$CHART_NAME --tail=100"
    exit 1
fi
