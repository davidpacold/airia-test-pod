#!/bin/bash
# =============================================================================
# Pod Diagnostics Collector
# =============================================================================
# Collects comprehensive pod diagnostics from a Kubernetes namespace:
# - Pod status, metadata, describe output
# - Events
# - Environment variables (via exec)
# - Mounted secrets and configmaps
# - Container logs
#
# Usage: ./extract-pod-details.sh <namespace> [output_dir] [--since=<duration>]
# =============================================================================

set -euo pipefail

NAMESPACE="${1:?Usage: $0 <namespace> [output_dir] [--since=<duration>]}"
OUTPUT_BASE="${2:-/tmp/diagnostics}"
SINCE=""

# Parse optional flags
for arg in "$@"; do
  case "$arg" in
    --since=*) SINCE="${arg#--since=}" ;;
  esac
done

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="${OUTPUT_BASE}/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

echo "Collecting diagnostics for namespace: ${NAMESPACE}"
echo "Output directory: ${OUTPUT_DIR}"

# Track counts
POD_COUNT=0
ERROR_COUNT=0

# ── Namespace-level info ─────────────────────────────────────────────────────

echo "Collecting namespace events..."
kubectl get events -n "${NAMESPACE}" --sort-by='.lastTimestamp' \
  > "${OUTPUT_DIR}/namespace-events.txt" 2>&1 || true

echo "Collecting services..."
kubectl get services -n "${NAMESPACE}" -o wide \
  > "${OUTPUT_DIR}/services.txt" 2>&1 || true

echo "Collecting configmaps list..."
kubectl get configmaps -n "${NAMESPACE}" \
  > "${OUTPUT_DIR}/configmaps-list.txt" 2>&1 || true

echo "Collecting secrets list..."
kubectl get secrets -n "${NAMESPACE}" \
  > "${OUTPUT_DIR}/secrets-list.txt" 2>&1 || true

# ── Pod-level diagnostics ────────────────────────────────────────────────────

PODS=$(kubectl get pods -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -z "${PODS}" ]; then
  echo "No pods found in namespace ${NAMESPACE}"
  echo "No pods found in namespace ${NAMESPACE}" > "${OUTPUT_DIR}/no-pods.txt"
else
  for POD in ${PODS}; do
    POD_COUNT=$((POD_COUNT + 1))
    POD_DIR="${OUTPUT_DIR}/pods/${POD}"
    mkdir -p "${POD_DIR}"
    echo "Processing pod: ${POD} (${POD_COUNT})"

    # Pod status (JSON)
    kubectl get pod "${POD}" -n "${NAMESPACE}" -o json \
      > "${POD_DIR}/status.json" 2>&1 || { ERROR_COUNT=$((ERROR_COUNT + 1)); true; }

    # Pod describe
    kubectl describe pod "${POD}" -n "${NAMESPACE}" \
      > "${POD_DIR}/describe.txt" 2>&1 || { ERROR_COUNT=$((ERROR_COUNT + 1)); true; }

    # Pod YAML
    kubectl get pod "${POD}" -n "${NAMESPACE}" -o yaml \
      > "${POD_DIR}/spec.yaml" 2>&1 || { ERROR_COUNT=$((ERROR_COUNT + 1)); true; }

    # Environment variables (via exec into first container)
    FIRST_CONTAINER=$(kubectl get pod "${POD}" -n "${NAMESPACE}" \
      -o jsonpath='{.spec.containers[0].name}' 2>/dev/null || echo "")
    if [ -n "${FIRST_CONTAINER}" ]; then
      kubectl exec "${POD}" -n "${NAMESPACE}" -c "${FIRST_CONTAINER}" \
        -- env 2>/dev/null | sort > "${POD_DIR}/env-vars.txt" 2>&1 || true
    fi

    # Container logs (all containers in the pod)
    CONTAINERS=$(kubectl get pod "${POD}" -n "${NAMESPACE}" \
      -o jsonpath='{.spec.containers[*].name}' 2>/dev/null || echo "")
    for CONTAINER in ${CONTAINERS}; do
      LOG_FILE="${POD_DIR}/logs-${CONTAINER}.txt"
      if [ -n "${SINCE}" ]; then
        kubectl logs "${POD}" -n "${NAMESPACE}" -c "${CONTAINER}" \
          --since="${SINCE}" > "${LOG_FILE}" 2>&1 || true
      else
        kubectl logs "${POD}" -n "${NAMESPACE}" -c "${CONTAINER}" \
          --tail=1000 > "${LOG_FILE}" 2>&1 || true
      fi
    done

    # Previous container logs (if restarted)
    for CONTAINER in ${CONTAINERS}; do
      kubectl logs "${POD}" -n "${NAMESPACE}" -c "${CONTAINER}" \
        --previous --tail=200 > "${POD_DIR}/logs-${CONTAINER}-previous.txt" 2>&1 || true
      # Remove empty previous log files
      [ ! -s "${POD_DIR}/logs-${CONTAINER}-previous.txt" ] && \
        rm -f "${POD_DIR}/logs-${CONTAINER}-previous.txt"
    done

    # Init container logs
    INIT_CONTAINERS=$(kubectl get pod "${POD}" -n "${NAMESPACE}" \
      -o jsonpath='{.spec.initContainers[*].name}' 2>/dev/null || echo "")
    for CONTAINER in ${INIT_CONTAINERS}; do
      kubectl logs "${POD}" -n "${NAMESPACE}" -c "${CONTAINER}" \
        > "${POD_DIR}/logs-init-${CONTAINER}.txt" 2>&1 || true
    done

    # Mounted volumes info
    kubectl get pod "${POD}" -n "${NAMESPACE}" \
      -o jsonpath='{range .spec.volumes[*]}{.name}{"\t"}{.configMap.name}{"\t"}{.secret.secretName}{"\n"}{end}' \
      > "${POD_DIR}/mounted-volumes.txt" 2>&1 || true

  done
fi

# ── Summary ──────────────────────────────────────────────────────────────────

cat > "${OUTPUT_DIR}/summary.txt" <<EOF
Diagnostics Collection Summary
===============================
Namespace:  ${NAMESPACE}
Timestamp:  ${TIMESTAMP}
Pods Found: ${POD_COUNT}
Errors:     ${ERROR_COUNT}
Since:      ${SINCE:-all available}
EOF

echo ""
echo "Collection complete: ${POD_COUNT} pods processed, ${ERROR_COUNT} errors"
echo "Output: ${OUTPUT_DIR}"
