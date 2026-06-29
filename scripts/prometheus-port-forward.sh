#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

prometheus_namespace=${PROMETHEUS_NAMESPACE:-runtimeclass-bench-prometheus}
prometheus_service_name=${PROMETHEUS_SERVICE_NAME:-prometheus}
prometheus_local_port=${PROMETHEUS_LOCAL_PORT:-9090}
prometheus_remote_port=${PROMETHEUS_REMOTE_PORT:-9090}
prometheus_port_forward_address=${PROMETHEUS_PORT_FORWARD_ADDRESS:-127.0.0.1}
kubectl_args=()

if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  kubectl_args+=(--context "$KUBE_CONTEXT")
fi

[[ -n "$prometheus_namespace" ]] || die "PROMETHEUS_NAMESPACE must not be empty"
[[ -n "$prometheus_service_name" ]] || die "PROMETHEUS_SERVICE_NAME must not be empty"
[[ -n "$prometheus_local_port" ]] || die "PROMETHEUS_LOCAL_PORT must not be empty"
[[ -n "$prometheus_remote_port" ]] || die "PROMETHEUS_REMOTE_PORT must not be empty"
[[ -n "$prometheus_port_forward_address" ]] || die "PROMETHEUS_PORT_FORWARD_ADDRESS must not be empty"

cmd=(kubectl "${kubectl_args[@]}" -n "$prometheus_namespace" port-forward --address "$prometheus_port_forward_address" "svc/$prometheus_service_name" "$prometheus_local_port:$prometheus_remote_port")

if is_true "${DRY_RUN:-0}"; then
  log "DRY_RUN=1: not starting Prometheus port-forward"
  print_cmd "${cmd[@]}"
  exit 0
fi

require_command kubectl
log "Forwarding Prometheus from http://$prometheus_port_forward_address:$prometheus_local_port to svc/$prometheus_service_name:$prometheus_remote_port in namespace $prometheus_namespace"
run_cmd "${cmd[@]}"
