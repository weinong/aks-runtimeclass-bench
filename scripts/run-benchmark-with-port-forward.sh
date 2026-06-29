#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

prometheus_namespace=${PROMETHEUS_NAMESPACE:-runtimeclass-bench-prometheus}
prometheus_service_name=${PROMETHEUS_SERVICE_NAME:-prometheus}
prometheus_local_port=${PROMETHEUS_LOCAL_PORT:-9090}
prometheus_remote_port=${PROMETHEUS_REMOTE_PORT:-9090}
prometheus_port_forward_address=${PROMETHEUS_PORT_FORWARD_ADDRESS:-127.0.0.1}
prometheus_port_forward_timeout=${PROMETHEUS_PORT_FORWARD_TIMEOUT:-30s}
prometheus_endpoint=${KUBE_BURNER_PROMETHEUS_ENDPOINT:-http://${prometheus_port_forward_address}:${prometheus_local_port}}
kubectl_args=()
benchmark_pid=

if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  kubectl_args+=(--context "$KUBE_CONTEXT")
fi

[[ -n "$prometheus_namespace" ]] || die "PROMETHEUS_NAMESPACE must not be empty"
[[ -n "$prometheus_service_name" ]] || die "PROMETHEUS_SERVICE_NAME must not be empty"
[[ -n "$prometheus_local_port" ]] || die "PROMETHEUS_LOCAL_PORT must not be empty"
[[ -n "$prometheus_remote_port" ]] || die "PROMETHEUS_REMOTE_PORT must not be empty"
[[ -n "$prometheus_port_forward_address" ]] || die "PROMETHEUS_PORT_FORWARD_ADDRESS must not be empty"
[[ -n "$prometheus_port_forward_timeout" ]] || die "PROMETHEUS_PORT_FORWARD_TIMEOUT must not be empty"
[[ -n "$prometheus_endpoint" ]] || die "KUBE_BURNER_PROMETHEUS_ENDPOINT must not be empty"
export KUBE_BURNER_PROMETHEUS_ENDPOINT="$prometheus_endpoint"

port_forward_cmd=(kubectl "${kubectl_args[@]}" -n "$prometheus_namespace" port-forward --address "$prometheus_port_forward_address" "svc/$prometheus_service_name" "$prometheus_local_port:$prometheus_remote_port")

if is_true "${DRY_RUN:-0}"; then
  log "DRY_RUN=1: not starting Prometheus port-forward"
  print_cmd "${port_forward_cmd[@]}"
  log "DRY_RUN=1: not waiting for Prometheus endpoint $prometheus_endpoint"
  print_cmd curl -fsS -X POST "$prometheus_endpoint/api/v1/query" --data-urlencode query=up
  log "DRY_RUN=1: preparing benchmark dry-run after port-forward dry-run"
  "$SCRIPT_DIR/run-benchmark.sh"
  exit 0
fi

require_command kubectl
require_command curl
require_command setsid

port_forward_log=$(mktemp)
port_forward_pid=

terminate_benchmark() {
  if [[ -n "$benchmark_pid" ]] && kill -0 "$benchmark_pid" >/dev/null 2>&1; then
    kill -TERM -- "-$benchmark_pid" >/dev/null 2>&1 || true
    for _ in 1 2 3 4 5; do
      if ! kill -0 -- "-$benchmark_pid" >/dev/null 2>&1; then
        break
      fi
      sleep 1
    done
    if kill -0 -- "-$benchmark_pid" >/dev/null 2>&1; then
      kill -KILL -- "-$benchmark_pid" >/dev/null 2>&1 || true
    fi
    wait "$benchmark_pid" >/dev/null 2>&1 || true
  fi
}

cleanup() {
  terminate_benchmark
  if [[ -n "$port_forward_pid" ]] && kill -0 "$port_forward_pid" >/dev/null 2>&1; then
    kill "$port_forward_pid" >/dev/null 2>&1 || true
    wait "$port_forward_pid" >/dev/null 2>&1 || true
  fi
  rm -f "$port_forward_log"
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

log "Starting Prometheus port-forward for benchmark: http://$prometheus_port_forward_address:$prometheus_local_port -> svc/$prometheus_service_name:$prometheus_remote_port"
print_cmd "${port_forward_cmd[@]}"
"${port_forward_cmd[@]}" >"$port_forward_log" 2>&1 &
port_forward_pid=$!

sleep 1
if ! kill -0 "$port_forward_pid" >/dev/null 2>&1; then
  printf 'error: Prometheus port-forward exited before becoming ready\n' >&2
  printf '%s\n' '--- port-forward log ---' >&2
  sed 's/^/  /' "$port_forward_log" >&2 || true
  exit 1
fi

deadline=$((SECONDS + 30))
if [[ "$prometheus_port_forward_timeout" =~ ^([0-9]+)s$ ]]; then
  deadline=$((SECONDS + BASH_REMATCH[1]))
elif [[ "$prometheus_port_forward_timeout" =~ ^[0-9]+$ ]]; then
  deadline=$((SECONDS + prometheus_port_forward_timeout))
else
  die "PROMETHEUS_PORT_FORWARD_TIMEOUT must be seconds, for example 30s"
fi

until curl -fsS -X POST "$prometheus_endpoint/api/v1/query" --data-urlencode query=up >/dev/null; do
  if ! kill -0 "$port_forward_pid" >/dev/null 2>&1; then
    printf 'error: Prometheus port-forward exited before becoming ready\n' >&2
    printf '%s\n' '--- port-forward log ---' >&2
    sed 's/^/  /' "$port_forward_log" >&2 || true
    exit 1
  fi
  if (( SECONDS >= deadline )); then
    printf 'error: timed out waiting for Prometheus endpoint: %s\n' "$prometheus_endpoint" >&2
    printf '%s\n' '--- port-forward log ---' >&2
    sed 's/^/  /' "$port_forward_log" >&2 || true
    exit 1
  fi
  sleep 1
done

log "Prometheus endpoint is ready: $prometheus_endpoint"
print_cmd "$SCRIPT_DIR/run-benchmark.sh"
setsid "$SCRIPT_DIR/run-benchmark.sh" &
benchmark_pid=$!

while kill -0 "$benchmark_pid" >/dev/null 2>&1; do
  if ! kill -0 "$port_forward_pid" >/dev/null 2>&1; then
    printf 'error: Prometheus port-forward exited while benchmark was running\n' >&2
    printf '%s\n' '--- port-forward log ---' >&2
    sed 's/^/  /' "$port_forward_log" >&2 || true
    terminate_benchmark
    exit 1
  fi
  sleep 1
done

if wait "$benchmark_pid"; then
  exit 0
fi
benchmark_status=$?
if ! kill -0 "$port_forward_pid" >/dev/null 2>&1; then
  printf 'error: benchmark failed after Prometheus port-forward exited\n' >&2
  printf '%s\n' '--- port-forward log ---' >&2
  sed 's/^/  /' "$port_forward_log" >&2 || true
fi
exit "$benchmark_status"
