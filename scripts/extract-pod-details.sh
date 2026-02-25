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
#
# Progress lines are emitted as: PROGRESS:<step>:<detail>
# These are parsed by the backend for real-time UI feedback.
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

echo "PROGRESS:init:Collecting diagnostics for namespace ${NAMESPACE}"

# Track counts
POD_COUNT=0
TOTAL_PODS=0
ERROR_COUNT=0

# ── Namespace-level info ─────────────────────────────────────────────────────

echo "PROGRESS:events:Collecting namespace events"
kubectl get events -n "${NAMESPACE}" --sort-by='.lastTimestamp' \
  > "${OUTPUT_DIR}/namespace-events.txt" 2>&1 || true

echo "PROGRESS:services:Collecting services"
kubectl get services -n "${NAMESPACE}" -o wide \
  > "${OUTPUT_DIR}/services.txt" 2>&1 || true

echo "PROGRESS:configmaps:Collecting configmaps list"
kubectl get configmaps -n "${NAMESPACE}" \
  > "${OUTPUT_DIR}/configmaps-list.txt" 2>&1 || true

echo "PROGRESS:secrets:Collecting secrets list"
kubectl get secrets -n "${NAMESPACE}" \
  > "${OUTPUT_DIR}/secrets-list.txt" 2>&1 || true

# ── Pod-level diagnostics ────────────────────────────────────────────────────

echo "PROGRESS:discover:Discovering pods"
PODS=$(kubectl get pods -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -z "${PODS}" ]; then
  echo "PROGRESS:discover:No pods found in namespace ${NAMESPACE}"
  echo "No pods found in namespace ${NAMESPACE}" > "${OUTPUT_DIR}/no-pods.txt"
else
  # Count total pods for progress reporting
  for POD in ${PODS}; do
    TOTAL_PODS=$((TOTAL_PODS + 1))
  done
  echo "PROGRESS:discover:Found ${TOTAL_PODS} pods"

  for POD in ${PODS}; do
    POD_COUNT=$((POD_COUNT + 1))
    POD_DIR="${OUTPUT_DIR}/pods/${POD}"
    mkdir -p "${POD_DIR}"
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - status"

    # Pod status (JSON)
    kubectl get pod "${POD}" -n "${NAMESPACE}" -o json \
      > "${POD_DIR}/status.json" 2>&1 || { ERROR_COUNT=$((ERROR_COUNT + 1)); true; }

    # Pod describe
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - describe"
    kubectl describe pod "${POD}" -n "${NAMESPACE}" \
      > "${POD_DIR}/describe.txt" 2>&1 || { ERROR_COUNT=$((ERROR_COUNT + 1)); true; }

    # Pod YAML
    kubectl get pod "${POD}" -n "${NAMESPACE}" -o yaml \
      > "${POD_DIR}/spec.yaml" 2>&1 || { ERROR_COUNT=$((ERROR_COUNT + 1)); true; }

    # Environment variables (via exec into first container)
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - env vars"
    FIRST_CONTAINER=$(kubectl get pod "${POD}" -n "${NAMESPACE}" \
      -o jsonpath='{.spec.containers[0].name}' 2>/dev/null || echo "")
    if [ -n "${FIRST_CONTAINER}" ]; then
      kubectl exec "${POD}" -n "${NAMESPACE}" -c "${FIRST_CONTAINER}" \
        -- env 2>/dev/null | sort > "${POD_DIR}/env-vars.txt" 2>&1 || true
    fi

    # Container logs (all containers in the pod)
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - logs"
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

    echo "PROGRESS:pod-done:${POD_COUNT}/${TOTAL_PODS} ${POD}"
  done
fi

# ── Archive ──────────────────────────────────────────────────────────────────

echo "PROGRESS:archive:Creating archive"

cat > "${OUTPUT_DIR}/summary.txt" <<EOF
Diagnostics Collection Summary
===============================
Namespace:  ${NAMESPACE}
Timestamp:  ${TIMESTAMP}
Pods Found: ${POD_COUNT}
Errors:     ${ERROR_COUNT}
Since:      ${SINCE:-all available}
EOF

echo "PROGRESS:complete:${POD_COUNT} pods processed, ${ERROR_COUNT} errors"
