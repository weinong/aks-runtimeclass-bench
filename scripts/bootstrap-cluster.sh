#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

optimized_runtime_class=${KATA_OPTIMIZED_RUNTIME_CLASS:-kata-optimized}
optimized_overhead_memory=${KATA_OPTIMIZED_RUNTIME_OVERHEAD_MEMORY:-32Mi}
optimized_handler=kata
kubectl_args=()
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  kubectl_args+=(--context "$KUBE_CONTEXT")
fi

verify_runtime_class_exists() {
  local name=$1
  [[ -n "$name" ]] || return 0
  if is_true "${DRY_RUN:-0}"; then
    run_cmd kubectl "${kubectl_args[@]}" get runtimeclass "$name"
  else
    kubectl "${kubectl_args[@]}" get runtimeclass "$name" >/dev/null 2>&1 || die "runtime class $name was not found"
  fi
  log "Verified runtime class $name exists"
}

apply_optimized_runtime_class() {
  [[ -n "$optimized_runtime_class" ]] || die "KATA_OPTIMIZED_RUNTIME_CLASS must not be empty"
  [[ -n "$optimized_overhead_memory" ]] || die "KATA_OPTIMIZED_RUNTIME_OVERHEAD_MEMORY must not be empty"

  print_cmd kubectl "${kubectl_args[@]}" apply -f -
  if ! is_true "${DRY_RUN:-0}"; then
    kubectl "${kubectl_args[@]}" apply -f - <<EOF
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: ${optimized_runtime_class}
handler: ${optimized_handler}
overhead:
  podFixed:
    memory: ${optimized_overhead_memory}
EOF
  fi
}

verify_optimized_runtime_class() {
  local handler memory
  handler=$(kubectl "${kubectl_args[@]}" get runtimeclass "$optimized_runtime_class" -o jsonpath='{.handler}')
  memory=$(kubectl "${kubectl_args[@]}" get runtimeclass "$optimized_runtime_class" -o jsonpath='{.overhead.podFixed.memory}')
  [[ "$handler" == "$optimized_handler" ]] || die "runtime class $optimized_runtime_class handler is $handler, expected $optimized_handler"
  [[ "$memory" == "$optimized_overhead_memory" ]] || die "runtime class $optimized_runtime_class memory overhead is $memory, expected $optimized_overhead_memory"
  log "Verified runtime class $optimized_runtime_class uses handler $optimized_handler and memory overhead $optimized_overhead_memory"
}

if is_true "${DRY_RUN:-0}"; then
  log "DRY_RUN=1: printing Kubernetes bootstrap commands without applying components"
else
  require_command kubectl
fi

verify_runtime_class_exists "${KATA_RUNTIME_CLASS:-kata-vm-isolation}"
apply_optimized_runtime_class

if ! is_true "${DRY_RUN:-0}"; then
  verify_optimized_runtime_class
fi
