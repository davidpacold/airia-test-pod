#!/bin/bash
# =============================================================================
# Pod Diagnostics Collector
# =============================================================================
# Collects comprehensive pod diagnostics from a Kubernetes namespace.
# Each pod produces a single .txt file with === SECTION === headers,
# matching the standalone extract-pod-details format.
#
# Sections per pod:
#   POD STATUS, POD METADATA, POD DESCRIBE, NODE CONDITIONS,
#   RELATED SERVICES, POD EVENTS, ENVIRONMENT VARIABLES,
#   MOUNTED SECRETS (DECODED), MOUNTED CONFIGMAPS,
#   POD SPECIFICATION, INIT CONTAINER LOGS, POD LOGS
#
# Usage: ./extract-pod-details.sh <namespace> [output_dir] [--since=<duration>]
#
# Progress lines: PROGRESS:<step>:<detail>
# =============================================================================

set -euo pipefail

NAMESPACE="${1:?Usage: $0 <namespace> [output_dir] [--since=<duration>]}"
OUTPUT_BASE="${2:-/tmp/diagnostics}"
SINCE=""
SINCE_FLAG=""

# Parse optional flags
for arg in "$@"; do
  case "$arg" in
    --since=*) SINCE="${arg#--since=}"; SINCE_FLAG="--since=${SINCE}" ;;
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

# ── Helpers ──────────────────────────────────────────────────────────────────

get_containers() {
  kubectl get pod -n "$1" "$2" \
    -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}' 2>/dev/null
}

get_init_containers() {
  kubectl get pod -n "$1" "$2" \
    -o jsonpath='{range .spec.initContainers[*]}{.name}{"\n"}{end}' 2>/dev/null
}

get_secret_mounts() {
  local ns="$1" pod="$2"
  kubectl get pod -n "$ns" "$pod" \
    -o jsonpath='{range .spec.volumes[?(@.secret)]}{.name}={.secret.secretName}{"\n"}{end}' 2>/dev/null | \
  while IFS='=' read -r vol_name secret_name; do
    [ -z "$vol_name" ] && continue
    mount_path=$(kubectl get pod -n "$ns" "$pod" \
      -o jsonpath="{.spec.containers[0].volumeMounts[?(@.name==\"$vol_name\")].mountPath}" 2>/dev/null)
    [ -n "$mount_path" ] && echo "${mount_path}|${secret_name}"
  done
}

get_configmap_mounts() {
  local ns="$1" pod="$2"
  kubectl get pod -n "$ns" "$pod" \
    -o jsonpath='{range .spec.volumes[?(@.configMap)]}{.name}={.configMap.name}{"\n"}{end}' 2>/dev/null | \
  while IFS='=' read -r vol_name cm_name; do
    [ -z "$vol_name" ] && continue
    mount_path=$(kubectl get pod -n "$ns" "$pod" \
      -o jsonpath="{.spec.containers[0].volumeMounts[?(@.name==\"$vol_name\")].mountPath}" 2>/dev/null)
    [ -n "$mount_path" ] && echo "${mount_path}|${cm_name}"
  done
}

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
  # Count total pods
  for POD in ${PODS}; do
    TOTAL_PODS=$((TOTAL_PODS + 1))
  done
  echo "PROGRESS:discover:Found ${TOTAL_PODS} pods"

  for POD in ${PODS}; do
    POD_COUNT=$((POD_COUNT + 1))
    OUT="${OUTPUT_DIR}/${POD}.txt"
    ERRORS=0

    # Start the file
    echo "=== POD: ${POD} ===" > "${OUT}"

    # ── POD STATUS ─────────────────────────────────────────────────────
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - status"
    echo "" >> "${OUT}"
    echo "=== POD STATUS ===" >> "${OUT}"
    echo "" >> "${OUT}"
    if ! kubectl get pod -n "${NAMESPACE}" "${POD}" -o wide --no-headers >> "${OUT}" 2>/dev/null; then
      echo "Could not retrieve pod status" >> "${OUT}"
      ERRORS=$((ERRORS + 1))
    fi
    echo "" >> "${OUT}"
    echo "ContainerStatuses:" >> "${OUT}"
    kubectl get pod -n "${NAMESPACE}" "${POD}" \
      -o jsonpath='{.status.containerStatuses}' >> "${OUT}" 2>/dev/null || true
    echo "" >> "${OUT}"

    # ── POD METADATA ───────────────────────────────────────────────────
    echo "" >> "${OUT}"
    echo "=== POD METADATA ===" >> "${OUT}"
    echo "" >> "${OUT}"
    kubectl get pod -n "${NAMESPACE}" "${POD}" -o jsonpath='Node: {.spec.nodeName}
Containers: {range .spec.containers[*]}{.name} {end}
Phase: {.status.phase}
Start: {.status.startTime}' >> "${OUT}" 2>/dev/null || true
    echo "" >> "${OUT}"
    echo "" >> "${OUT}"
    echo "Labels:" >> "${OUT}"
    kubectl get pod -n "${NAMESPACE}" "${POD}" \
      -o custom-columns="LABELS:.metadata.labels" --no-headers >> "${OUT}" 2>/dev/null || true
    echo "" >> "${OUT}"

    # ── POD DESCRIBE ───────────────────────────────────────────────────
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - describe"
    echo "" >> "${OUT}"
    echo "=== POD DESCRIBE ===" >> "${OUT}"
    echo "" >> "${OUT}"
    if ! kubectl describe pod -n "${NAMESPACE}" "${POD}" >> "${OUT}" 2>/dev/null; then
      echo "Could not retrieve pod describe" >> "${OUT}"
      ERRORS=$((ERRORS + 1))
    fi

    # ── NODE CONDITIONS ────────────────────────────────────────────────
    echo "" >> "${OUT}"
    echo "=== NODE CONDITIONS ===" >> "${OUT}"
    echo "" >> "${OUT}"
    NODE=$(kubectl get pod -n "${NAMESPACE}" "${POD}" \
      -o jsonpath='{.spec.nodeName}' 2>/dev/null || echo "")
    if [ -n "${NODE}" ]; then
      kubectl describe node "${NODE}" 2>/dev/null | sed -n '/^Conditions:/,/^[A-Z]/p' | head -20 >> "${OUT}"
    else
      echo "Node not assigned" >> "${OUT}"
    fi

    # ── RELATED SERVICES ──────────────────────────────────────────────
    echo "" >> "${OUT}"
    echo "=== RELATED SERVICES ===" >> "${OUT}"
    echo "" >> "${OUT}"
    kubectl get svc -n "${NAMESPACE}" -o wide --no-headers >> "${OUT}" 2>/dev/null \
      || echo "Could not retrieve services" >> "${OUT}"

    # ── POD EVENTS ─────────────────────────────────────────────────────
    echo "" >> "${OUT}"
    echo "=== POD EVENTS ===" >> "${OUT}"
    echo "" >> "${OUT}"
    if ! kubectl get events -n "${NAMESPACE}" \
      --field-selector "involvedObject.name=${POD}" --sort-by=.lastTimestamp >> "${OUT}" 2>/dev/null; then
      echo "No events found" >> "${OUT}"
    fi

    # ── ENVIRONMENT VARIABLES ──────────────────────────────────────────
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - env vars"
    echo "" >> "${OUT}"
    echo "=== ENVIRONMENT VARIABLES ===" >> "${OUT}"
    echo "" >> "${OUT}"

    CONTAINERS=$(get_containers "${NAMESPACE}" "${POD}")
    CONTAINER_COUNT=$(echo "${CONTAINERS}" | grep -c . 2>/dev/null || echo 0)
    FIRST_CONTAINER=$(echo "${CONTAINERS}" | head -1)

    if [ -n "${CONTAINERS}" ]; then
      while IFS= read -r C; do
        [ -z "${C}" ] && continue
        if [ "${CONTAINER_COUNT}" -gt 1 ]; then
          echo "--- Container: ${C} ---" >> "${OUT}"
        fi
        if ! kubectl exec -n "${NAMESPACE}" "${POD}" -c "${C}" -- env 2>/dev/null | sort >> "${OUT}"; then
          echo "Could not retrieve env vars for ${C}" >> "${OUT}"
        fi
        echo "" >> "${OUT}"
      done <<< "${CONTAINERS}"
    else
      echo "Could not determine containers" >> "${OUT}"
    fi

    # ── MOUNTED SECRETS (DECODED) ──────────────────────────────────────
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - secrets"
    echo "" >> "${OUT}"
    echo "=== MOUNTED SECRETS (DECODED) ===" >> "${OUT}"
    echo "" >> "${OUT}"

    SECRET_MOUNTS=$(get_secret_mounts "${NAMESPACE}" "${POD}")
    if [ -z "${SECRET_MOUNTS}" ]; then
      echo "No secret mounts found" >> "${OUT}"
    else
      while IFS= read -r ENTRY; do
        [ -z "${ENTRY}" ] && continue
        MPATH="${ENTRY%%|*}"
        SNAME="${ENTRY##*|}"
        echo "--- Secret mount: ${SNAME} (${MPATH}) ---" >> "${OUT}"
        if FILES=$(kubectl exec -n "${NAMESPACE}" "${POD}" -c "${FIRST_CONTAINER}" \
          -- find "${MPATH}" -type f 2>/dev/null); then
          while IFS= read -r F; do
            [ -z "${F}" ] && continue
            echo "File: ${F}" >> "${OUT}"
            if CONTENT=$(kubectl exec -n "${NAMESPACE}" "${POD}" -c "${FIRST_CONTAINER}" \
              -- cat "${F}" 2>/dev/null); then
              echo "${CONTENT}" | sed 's/^/  /' >> "${OUT}"
            else
              echo "  Could not read file" >> "${OUT}"
            fi
            echo "" >> "${OUT}"
          done <<< "${FILES}"
        else
          echo "Could not access ${MPATH}" >> "${OUT}"
          ERRORS=$((ERRORS + 1))
        fi
      done <<< "${SECRET_MOUNTS}"
    fi

    # ── MOUNTED CONFIGMAPS ─────────────────────────────────────────────
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - configmaps"
    echo "" >> "${OUT}"
    echo "=== MOUNTED CONFIGMAPS ===" >> "${OUT}"
    echo "" >> "${OUT}"

    CM_MOUNTS=$(get_configmap_mounts "${NAMESPACE}" "${POD}")
    if [ -z "${CM_MOUNTS}" ]; then
      echo "No configmap mounts found" >> "${OUT}"
    else
      while IFS= read -r ENTRY; do
        [ -z "${ENTRY}" ] && continue
        MPATH="${ENTRY%%|*}"
        CMNAME="${ENTRY##*|}"
        echo "--- ConfigMap: ${CMNAME} (mount: ${MPATH}) ---" >> "${OUT}"
        if FILES=$(kubectl exec -n "${NAMESPACE}" "${POD}" -c "${FIRST_CONTAINER}" \
          -- find "${MPATH}" -type f 2>/dev/null); then
          while IFS= read -r F; do
            [ -z "${F}" ] && continue
            echo "File: ${F}" >> "${OUT}"
            if CONTENT=$(kubectl exec -n "${NAMESPACE}" "${POD}" -c "${FIRST_CONTAINER}" \
              -- cat "${F}" 2>/dev/null); then
              echo "${CONTENT}" | sed 's/^/  /' >> "${OUT}"
            else
              echo "  Could not read file" >> "${OUT}"
            fi
            echo "" >> "${OUT}"
          done <<< "${FILES}"
        else
          echo "Could not access ${MPATH}" >> "${OUT}"
          ERRORS=$((ERRORS + 1))
        fi
      done <<< "${CM_MOUNTS}"
    fi

    # ── POD SPECIFICATION ──────────────────────────────────────────────
    echo "" >> "${OUT}"
    echo "=== POD SPECIFICATION ===" >> "${OUT}"
    echo "" >> "${OUT}"
    if ! kubectl get pod -n "${NAMESPACE}" "${POD}" -o jsonpath='{.spec}' >> "${OUT}" 2>/dev/null; then
      echo "Could not retrieve pod spec" >> "${OUT}"
      ERRORS=$((ERRORS + 1))
    fi
    echo "" >> "${OUT}"

    # ── INIT CONTAINER LOGS ────────────────────────────────────────────
    echo "" >> "${OUT}"
    echo "=== INIT CONTAINER LOGS ===" >> "${OUT}"
    echo "" >> "${OUT}"

    INIT_CONTAINERS=$(get_init_containers "${NAMESPACE}" "${POD}")
    if [ -z "${INIT_CONTAINERS}" ]; then
      echo "No init containers" >> "${OUT}"
    else
      while IFS= read -r IC; do
        [ -z "${IC}" ] && continue
        echo "--- Init Container: ${IC} ---" >> "${OUT}"
        if ! kubectl logs -n "${NAMESPACE}" "${POD}" -c "${IC}" --timestamps ${SINCE_FLAG} >> "${OUT}" 2>/dev/null; then
          echo "Could not retrieve init container logs" >> "${OUT}"
        fi
        # Previous init logs
        PREV=$(kubectl logs -n "${NAMESPACE}" "${POD}" -c "${IC}" --previous --timestamps ${SINCE_FLAG} 2>/dev/null || true)
        if [ -n "${PREV}" ] && ! echo "${PREV}" | grep -q "^Error from server"; then
          echo "" >> "${OUT}"
          echo "[Previous container logs]" >> "${OUT}"
          echo "${PREV}" >> "${OUT}"
        fi
        echo "" >> "${OUT}"
      done <<< "${INIT_CONTAINERS}"
    fi

    # ── POD LOGS ───────────────────────────────────────────────────────
    echo "PROGRESS:pod:${POD_COUNT}/${TOTAL_PODS} ${POD} - logs"
    echo "" >> "${OUT}"
    echo "=== POD LOGS ===" >> "${OUT}"
    echo "" >> "${OUT}"

    if [ -n "${CONTAINERS}" ]; then
      while IFS= read -r C; do
        [ -z "${C}" ] && continue
        if [ "${CONTAINER_COUNT}" -gt 1 ]; then
          echo "--- Container: ${C} ---" >> "${OUT}"
        fi

        if [ -n "${SINCE}" ]; then
          LOGS=$(kubectl logs -n "${NAMESPACE}" "${POD}" -c "${C}" --timestamps ${SINCE_FLAG} 2>/dev/null || true)
          if [ -z "${LOGS}" ]; then
            # --since returned nothing, fall back to --tail for startup logs
            echo "[No logs in last ${SINCE}; showing most recent]" >> "${OUT}"
            kubectl logs -n "${NAMESPACE}" "${POD}" -c "${C}" --timestamps --tail=500 >> "${OUT}" 2>/dev/null || true
          else
            echo "${LOGS}" >> "${OUT}"
          fi
        else
          if ! kubectl logs -n "${NAMESPACE}" "${POD}" -c "${C}" --timestamps --tail=1000 >> "${OUT}" 2>/dev/null; then
            echo "Could not retrieve logs for ${C}" >> "${OUT}"
            ERRORS=$((ERRORS + 1))
          fi
        fi

        # Previous logs
        PREV=$(kubectl logs -n "${NAMESPACE}" "${POD}" -c "${C}" --previous --timestamps ${SINCE_FLAG} 2>/dev/null || true)
        if [ -n "${PREV}" ] && ! echo "${PREV}" | grep -q "^Error from server"; then
          echo "" >> "${OUT}"
          echo "[Previous container logs]" >> "${OUT}"
          echo "${PREV}" >> "${OUT}"
        fi
        echo "" >> "${OUT}"
      done <<< "${CONTAINERS}"
    else
      echo "Could not retrieve logs" >> "${OUT}"
      ERRORS=$((ERRORS + 1))
    fi

    # ── Track results ──────────────────────────────────────────────────
    if [ "${ERRORS}" -gt 0 ]; then
      ERROR_COUNT=$((ERROR_COUNT + ERRORS))
    fi

    echo "PROGRESS:pod-done:${POD_COUNT}/${TOTAL_PODS} ${POD}"
  done
fi

# ── Extraction metadata ─────────────────────────────────────────────────────

echo "PROGRESS:archive:Creating archive"

CLUSTER=$(kubectl config current-context 2>/dev/null || echo "unknown")

cat > "${OUTPUT_DIR}/_extraction-info.txt" <<EOF
=== EXTRACTION METADATA ===
Namespace:  ${NAMESPACE}
Cluster:    ${CLUSTER}
Timestamp:  ${TIMESTAMP}
Extracted:  $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Pods Found: ${POD_COUNT}
Errors:     ${ERROR_COUNT}
Since:      ${SINCE:-all available}
EOF

echo "PROGRESS:complete:${POD_COUNT} pods processed, ${ERROR_COUNT} errors"
