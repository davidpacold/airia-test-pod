#!/bin/bash

# Cassandra connection test script for Kubernetes environment
# This script helps test Cassandra connectivity from the deployed pod

set -e

# Configuration from aws.yaml
CASSANDRA_HOST="${CASSANDRA_HOST:-172.20.102.244}"  # Default to k8s service IP
CASSANDRA_PORT="9042"
CASSANDRA_USERNAME="cassandra"
CASSANDRA_PASSWORD="u1AncgPT2n"
CASSANDRA_KEYSPACE="airia"
CASSANDRA_DATACENTER="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Cassandra Connection Test for Kubernetes${NC}"
echo "=================================================="

# Function to get pod name
get_pod_name() {
    # Try multiple namespaces and label selectors
    POD_NAME=""
    for ns in airia default; do
        # Try different label selectors
        for selector in "app.kubernetes.io/name=airia-test-pod" "app=airia-test-pod" ""; do
            if [[ -n "$selector" ]]; then
                POD_NAME=$(kubectl get pods -n "$ns" -l "$selector" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            else
                POD_NAME=$(kubectl get pods -n "$ns" --no-headers | grep airia-test-pod | head -n1 | awk '{print $1}' 2>/dev/null)
            fi
            if [[ -n "$POD_NAME" ]]; then
                echo "$ns:$POD_NAME"
                return 0
            fi
        done
    done
    echo ""
}

# Function to test network connectivity
test_network() {
    echo -e "${YELLOW}🔍 Testing network connectivity...${NC}"
    
    POD_INFO=$(get_pod_name)
    if [[ -z "$POD_INFO" ]]; then
        echo -e "${RED}❌ No airia-test-pod found in current context${NC}"
        return 1
    fi
    
    NAMESPACE=$(echo "$POD_INFO" | cut -d: -f1)
    POD_NAME=$(echo "$POD_INFO" | cut -d: -f2)
    echo "Using pod: $POD_NAME in namespace: $NAMESPACE"
    
    # Test if host is reachable using Python socket
    echo "Testing connectivity to $CASSANDRA_HOST:$CASSANDRA_PORT"
    
    if kubectl exec -n "$NAMESPACE" "$POD_NAME" -- python3 -c "
import socket
import sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex(('$CASSANDRA_HOST', $CASSANDRA_PORT))
    sock.close()
    if result == 0:
        print('Connection successful')
        sys.exit(0)
    else:
        print('Connection failed')
        sys.exit(1)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo -e "${GREEN}✅ Host $CASSANDRA_HOST:$CASSANDRA_PORT is reachable${NC}"
        return 0
    else
        echo -e "${RED}❌ Cannot reach $CASSANDRA_HOST:$CASSANDRA_PORT${NC}"
        return 1
    fi
}

# Function to run Cassandra test from within pod
test_from_pod() {
    echo -e "${YELLOW}🔄 Running Cassandra test from within the pod...${NC}"
    
    POD_INFO=$(get_pod_name)
    if [[ -z "$POD_INFO" ]]; then
        echo -e "${RED}❌ No airia-test-pod found in current context${NC}"
        return 1
    fi
    
    NAMESPACE=$(echo "$POD_INFO" | cut -d: -f1)
    POD_NAME=$(echo "$POD_INFO" | cut -d: -f2)
    echo "Using pod: $POD_NAME in namespace: $NAMESPACE"
    
    # Set environment variables and run the test
    kubectl exec -n "$NAMESPACE" "$POD_NAME" -- env \
        CASSANDRA_HOSTS="cassandra" \
        CASSANDRA_PORT="$CASSANDRA_PORT" \
        CASSANDRA_USERNAME="$CASSANDRA_USERNAME" \
        CASSANDRA_PASSWORD="$CASSANDRA_PASSWORD" \
        CASSANDRA_KEYSPACE="$CASSANDRA_KEYSPACE" \
        CASSANDRA_DATACENTER="$CASSANDRA_DATACENTER" \
        CASSANDRA_USE_SSL="false" \
        python3 -c "
import os
import sys
sys.path.append('/app')
try:
    from app.tests.cassandra_test import CassandraTest
    test = CassandraTest()
    print('🔧 Test configured:', test.is_configured())
    if test.is_configured():
        print('🚀 Running Cassandra connectivity test...')
        result = test.run_test()
        print('📊 Result:', 'SUCCESS' if result.status.value == 'passed' else 'FAILED')
        if result.message:
            print('📝 Message:', result.message)
        if hasattr(result, 'sub_test_results'):
            for test_name, test_result in result.sub_test_results.items():
                status = '✅' if test_result.get('success', False) else '❌'
                print(f'  {status} {test_name}: {test_result.get(\"message\", \"\")}')
    else:
        print('❌ Cassandra test not properly configured')
        print('💡 Configuration help:', test.get_configuration_help())
except ImportError as e:
    print('❌ Import error:', str(e))
    print('💡 Make sure cassandra-driver is installed in the pod')
except Exception as e:
    print('❌ Test error:', str(e))
    import traceback
    traceback.print_exc()
"
}

# Function to setup port forwarding for local testing
setup_port_forward() {
    echo -e "${YELLOW}🔗 Setting up port forwarding for local testing...${NC}"
    
    POD_INFO=$(get_pod_name)
    if [[ -z "$POD_INFO" ]]; then
        echo -e "${RED}❌ No airia-test-pod found in current context${NC}"
        return 1
    fi
    
    NAMESPACE=$(echo "$POD_INFO" | cut -d: -f1)
    POD_NAME=$(echo "$POD_INFO" | cut -d: -f2)
    echo "Using pod: $POD_NAME in namespace: $NAMESPACE"
    
    echo "Starting port forward from local:8080 to pod:8080"
    echo "You can then access the dashboard at: http://localhost:8080"
    echo "Press Ctrl+C to stop port forwarding"
    
    kubectl port-forward -n "$NAMESPACE" "$POD_NAME" 8080:8080
}

# Function to check pod logs
check_logs() {
    echo -e "${YELLOW}📋 Checking pod logs...${NC}"
    
    POD_INFO=$(get_pod_name)
    if [[ -z "$POD_INFO" ]]; then
        echo -e "${RED}❌ No airia-test-pod found in current context${NC}"
        return 1
    fi
    
    NAMESPACE=$(echo "$POD_INFO" | cut -d: -f1)
    POD_NAME=$(echo "$POD_INFO" | cut -d: -f2)
    echo "Using pod: $POD_NAME in namespace: $NAMESPACE"
    
    echo "Recent logs from $POD_NAME:"
    kubectl logs -n "$NAMESPACE" "$POD_NAME" --tail=50
}

# Function to show pod status
show_status() {
    echo -e "${YELLOW}📊 Pod Status${NC}"
    echo "=============="
    
    # Show pods in airia namespace
    echo "Pods in airia namespace:"
    kubectl get pods -n airia | grep airia-test-pod || echo "No airia-test-pod found in airia namespace"
    
    echo ""
    echo "Services in airia namespace:"
    kubectl get services -n airia | grep airia-test-pod || echo "No airia-test-pod services found"
    
    POD_INFO=$(get_pod_name)
    if [[ -n "$POD_INFO" ]]; then
        NAMESPACE=$(echo "$POD_INFO" | cut -d: -f1)
        POD_NAME=$(echo "$POD_INFO" | cut -d: -f2)
        echo ""
        echo "Pod Environment (Cassandra-related):"
        kubectl exec -n "$NAMESPACE" "$POD_NAME" -- env | grep -i cassandra || echo "No Cassandra environment variables set"
    fi
}

# Main menu
case "${1:-}" in
    "network")
        test_network
        ;;
    "test")
        test_from_pod
        ;;
    "port-forward")
        setup_port_forward
        ;;
    "logs")
        check_logs
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {network|test|port-forward|logs|status}"
        echo ""
        echo "Commands:"
        echo "  network       - Test network connectivity to Cassandra"
        echo "  test          - Run Cassandra test from within the pod"
        echo "  port-forward  - Setup port forwarding for dashboard access"
        echo "  logs          - Show recent pod logs"
        echo "  status        - Show pod and service status"
        echo ""
        echo "Examples:"
        echo "  $0 network     # Test if Cassandra host is reachable"
        echo "  $0 test        # Run the full Cassandra connectivity test"
        echo "  $0 status      # Check pod deployment status"
        exit 1
        ;;
esac