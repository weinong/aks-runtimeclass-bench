#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
source "$SCRIPT_DIR/common.sh"

optimized_runtime_class=${KATA_OPTIMIZED_RUNTIME_CLASS:-kata-optimized}
optimized_overhead_memory=${KATA_OPTIMIZED_RUNTIME_OVERHEAD_MEMORY:-32Mi}
optimized_handler=kata
gvisor_runtime_class=${GVISOR_RUNTIME_CLASS:-gvisor}
gvisor_nodepool_name=${GVISOR_NODEPOOL_NAME:-gvisor}
gvisor_handler=runsc
firecracker_runtime_class=${FIRECRACKER_RUNTIME_CLASS:-kata-fc}
firecracker_nodepool_name=${FIRECRACKER_NODEPOOL_NAME:-firecracker}
firecracker_handler=kata-fc
kata_deploy_chart=${KATA_DEPLOY_CHART:-oci://quay.io/kata-containers/kata-deploy-charts/kata-deploy}
kubectl_args=()
helm_args=()
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  kubectl_args+=(--context "$KUBE_CONTEXT")
  helm_args+=(--kube-context "$KUBE_CONTEXT")
fi

render_manifest() {
  local path=$1
  [[ -f "$path" ]] || die "manifest not found: $path"
  local content
  content=$(<"$path")
  content=${content//__GVISOR_NODEPOOL_NAME__/$gvisor_nodepool_name}
  content=${content//__FIRECRACKER_NODEPOOL_NAME__/$firecracker_nodepool_name}
  content=${content//__FIRECRACKER_RUNTIME_CLASS__/$firecracker_runtime_class}
  printf '%s' "$content"
}

apply_rendered_manifest() {
  local path=$1
  print_cmd kubectl "${kubectl_args[@]}" apply -f -
  if is_true "${DRY_RUN:-0}"; then
    render_manifest "$path"
    printf '\n'
  else
    render_manifest "$path" | kubectl "${kubectl_args[@]}" apply -f -
  fi
}

wait_for_pod_succeeded() {
  local namespace=$1 pod=$2 timeout=$3
  run_cmd kubectl "${kubectl_args[@]}" -n "$namespace" wait --for=jsonpath='{.status.phase}'=Succeeded "pod/$pod" --timeout "$timeout"
}

ensure_containerd_conf_import() {
  local nodepool_name=$1
  local namespace=$2
  local selector=$3
  local pod
  local pods

  log "Ensuring containerd imports /etc/containerd/conf.d on node pool $nodepool_name"
  print_cmd kubectl "${kubectl_args[@]}" -n "$namespace" get pods -l "$selector" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
  if ! is_true "${DRY_RUN:-0}"; then
    pods=$(kubectl "${kubectl_args[@]}" -n "$namespace" get pods -l "$selector" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
    [[ -n "$pods" ]] || die "no pods found for selector $selector in namespace $namespace"
  else
    pods='<runtime-installer-pod>'
  fi

  while IFS= read -r pod; do
    [[ -n "$pod" ]] || continue
    print_cmd kubectl "${kubectl_args[@]}" -n "$namespace" exec -i "pod/$pod" -- chroot /host sh -seu '...'
    if is_true "${DRY_RUN:-0}"; then
      continue
    fi
    kubectl "${kubectl_args[@]}" -n "$namespace" exec -i "pod/$pod" -- chroot /host sh -seu <<'EOF'
import_path='"/etc/containerd/conf.d/*.toml"'
if ! grep -Fq "$import_path" /etc/containerd/config.toml; then
  tmp="/etc/containerd/config.toml.tmp"
  awk -v import_path="$import_path" '
    /^imports[[:space:]]*=/ {
      sub(/\[/, "[" import_path ", ");
      inserted=1;
    }
    /^version[[:space:]]*=/ { version_line=NR }
    /^\[/ && !first_table { first_table=NR }
    { line=$0; lines[NR]=line }
    END {
      insert_after = version_line ? version_line : first_table - 1;
      for (i = 1; i <= NR; i++) {
        print lines[i];
        if (!inserted && i == insert_after) {
          print "imports = [" import_path "]";
        }
      }
      if (!inserted && !insert_after) {
        print "imports = [" import_path "]";
      }
    }
  ' /etc/containerd/config.toml > "$tmp"
  mv "$tmp" /etc/containerd/config.toml
  systemctl restart containerd
fi
EOF
  done <<< "$pods"
}

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

verify_runtime_class_handler() {
  local name=$1
  local expected_handler=$2
  local handler
  handler=$(kubectl "${kubectl_args[@]}" get runtimeclass "$name" -o jsonpath='{.handler}')
  [[ "$handler" == "$expected_handler" ]] || die "runtime class $name handler is $handler, expected $expected_handler"
  log "Verified runtime class $name uses handler $expected_handler"
}

install_gvisor() {
  [[ -n "$gvisor_runtime_class" ]] || die "GVISOR_RUNTIME_CLASS must not be empty"
  [[ "$gvisor_runtime_class" == "gvisor" ]] || die "GVISOR_RUNTIME_CLASS must remain gvisor for the repository-managed installer"
  [[ -n "$gvisor_nodepool_name" ]] || die "GVISOR_NODEPOOL_NAME must not be empty"

  log "Installing gVisor runtime on node pool $gvisor_nodepool_name"
  apply_rendered_manifest "$REPO_ROOT/configs/runtime-install/gvisor/install.yaml"
  if ! is_true "${DRY_RUN:-0}"; then
    run_cmd kubectl "${kubectl_args[@]}" -n runtimeclass-gvisor rollout status daemonset/gvisor-installer --timeout=10m
    wait_for_pod_succeeded runtimeclass-gvisor gvisor-smoke 10m
  fi
}

install_firecracker() {
  [[ -n "$firecracker_runtime_class" ]] || die "FIRECRACKER_RUNTIME_CLASS must not be empty"
  [[ "$firecracker_runtime_class" == "kata-fc" ]] || die "FIRECRACKER_RUNTIME_CLASS must remain kata-fc for the Kata fc shim"
  [[ -n "$firecracker_nodepool_name" ]] || die "FIRECRACKER_NODEPOOL_NAME must not be empty"
  [[ -n "$kata_deploy_chart" ]] || die "KATA_DEPLOY_CHART must not be empty"

  log "Installing Firecracker-backed Kata runtime on node pool $firecracker_nodepool_name"
  apply_rendered_manifest "$REPO_ROOT/configs/runtime-install/firecracker/devmapper.yaml"
  if ! is_true "${DRY_RUN:-0}"; then
    run_cmd kubectl "${kubectl_args[@]}" -n runtimeclass-firecracker rollout status daemonset/firecracker-devmapper-installer --timeout=10m
  fi

  local values_file
  values_file=$(mktemp)
  render_manifest "$REPO_ROOT/configs/runtime-install/firecracker/kata-deploy-values-fc.yaml" > "$values_file"
  print_cmd helm "${helm_args[@]}" upgrade --install kata-deploy-fc "$kata_deploy_chart" --namespace kata-system --create-namespace --values "$values_file"
  if is_true "${DRY_RUN:-0}"; then
    printf '# Rendered Firecracker Kata Deploy values from configs/runtime-install/firecracker/kata-deploy-values-fc.yaml\n'
    render_manifest "$REPO_ROOT/configs/runtime-install/firecracker/kata-deploy-values-fc.yaml"
    printf '\n'
    rm -f "$values_file"
  else
    helm "${helm_args[@]}" upgrade --install kata-deploy-fc "$kata_deploy_chart" --namespace kata-system --create-namespace --values "$values_file"
    rm -f "$values_file"
    run_cmd kubectl "${kubectl_args[@]}" -n kata-system rollout status daemonset/kata-deploy --timeout=20m
    ensure_containerd_conf_import "${firecracker_nodepool_name}" runtimeclass-firecracker app.kubernetes.io/name=firecracker-devmapper-installer
  fi

  apply_rendered_manifest "$REPO_ROOT/configs/runtime-install/firecracker/pre-pull.yaml"
  if ! is_true "${DRY_RUN:-0}"; then
    run_cmd kubectl "${kubectl_args[@]}" -n runtimeclass-firecracker rollout status daemonset/firecracker-pre-pull --timeout=10m
    apply_rendered_manifest "$REPO_ROOT/configs/runtime-install/firecracker/smoke-pod.yaml"
    wait_for_pod_succeeded runtimeclass-firecracker firecracker-smoke 10m
  fi
}

if is_true "${DRY_RUN:-0}"; then
  log "DRY_RUN=1: printing Kubernetes bootstrap commands without applying components"
else
  require_command kubectl
  require_command helm
fi

verify_runtime_class_exists "${KATA_RUNTIME_CLASS:-kata-vm-isolation}"
apply_optimized_runtime_class
install_gvisor
install_firecracker

if ! is_true "${DRY_RUN:-0}"; then
  verify_optimized_runtime_class
  verify_runtime_class_handler "$gvisor_runtime_class" "$gvisor_handler"
  verify_runtime_class_handler "$firecracker_runtime_class" "$firecracker_handler"
fi
