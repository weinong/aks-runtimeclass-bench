#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/common.sh"

validate_vm_size() {
  local cores
  cores=$(az vm list-sizes --location "$LOCATION" --query "[?name=='$VM_SIZE'].numberOfCores | [0]" -o tsv)
  if [[ ! "$cores" =~ ^[0-9]+$ ]]; then
    die "VM_SIZE=$VM_SIZE could not be validated in LOCATION=$LOCATION; node VM sizes must provide at least 8 vCPUs"
  fi
  if (( cores < 8 )); then
    die "VM_SIZE=$VM_SIZE has $cores vCPUs; node VM sizes must provide at least 8 vCPUs"
  fi
  log "Validated VM_SIZE=$VM_SIZE has $cores vCPUs"
}

cluster_exists() {
  az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" >/dev/null 2>&1
}

nodepool_exists() {
  az aks nodepool show --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" --name "$1" >/dev/null 2>&1
}

ensure_nodepool_count() {
  local name=$1
  local expected=$2
  local actual

  if ! is_true "${DRY_RUN:-0}"; then
    actual=$(az aks nodepool show --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" --name "$name" --query count -o tsv)
    if [[ "$actual" == "$expected" ]]; then
      log "Node pool $name already has count $expected; skipping scale"
      return
    fi
  fi

  run_cmd az aks nodepool scale --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" --name "$name" --node-count "$expected"
}

ensure_cluster() {
  local cmd
  run_cmd az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

  if ! is_true "${DRY_RUN:-0}" && cluster_exists; then
    log "Cluster $CLUSTER_NAME already exists; updating mutable cluster settings"
    if [[ -n "${CLUSTER_EXTRA_ARGS:-}" ]]; then
      cmd=(az aks update --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME")
      append_words cmd "${CLUSTER_EXTRA_ARGS:-}"
      run_cmd "${cmd[@]}"
    else
      log "No CLUSTER_EXTRA_ARGS specified; skipping cluster update"
    fi
    ensure_nodepool_count "$SYSTEM_NODEPOOL_NAME" 2
    return
  fi

  cmd=(az aks create
    --resource-group "$RESOURCE_GROUP"
    --name "$CLUSTER_NAME"
    --location "$LOCATION"
    --nodepool-name "$SYSTEM_NODEPOOL_NAME"
    --node-count 2
    --node-vm-size "$VM_SIZE"
    --os-sku "$SYSTEM_OS_SKU"
    --enable-managed-identity
    --generate-ssh-keys)
  if [[ -n "${KUBERNETES_VERSION:-}" ]]; then
    cmd+=(--kubernetes-version "$KUBERNETES_VERSION")
  fi
  append_words cmd "${CLUSTER_EXTRA_ARGS:-}"
  run_cmd "${cmd[@]}"
}

ensure_nodepool() {
  local name=$1
  local labels=$2
  local taints=$3
  local extra_args=$4
  local cmd update_cmd

  if ! is_true "${DRY_RUN:-0}" && nodepool_exists "$name"; then
    log "Node pool $name already exists; enforcing count and placement metadata"
    ensure_nodepool_count "$name" 1
    update_cmd=(az aks nodepool update --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" --name "$name")
    if [[ -n "$labels" ]]; then
      update_cmd+=(--labels)
      append_words update_cmd "$labels"
    fi
    if [[ -n "$taints" ]]; then
      update_cmd+=(--node-taints)
      append_words update_cmd "$taints"
    fi
    run_cmd "${update_cmd[@]}"
    return
  fi

  cmd=(az aks nodepool add
    --resource-group "$RESOURCE_GROUP"
    --cluster-name "$CLUSTER_NAME"
    --name "$name"
    --mode User
    --node-count 1
    --node-vm-size "$VM_SIZE"
    --os-sku "$RUNTIME_OS_SKU")
  if [[ -n "$labels" ]]; then
    cmd+=(--labels)
    append_words cmd "$labels"
  fi
  if [[ -n "$taints" ]]; then
    cmd+=(--node-taints)
    append_words cmd "$taints"
  fi
  append_words cmd "$extra_args"
  run_cmd "${cmd[@]}"
}

verify_nodepool_count() {
  local name=$1
  local expected=$2
  local actual
  actual=$(az aks nodepool show --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" --name "$name" --query count -o tsv)
  [[ "$actual" == "$expected" ]] || die "node pool $name expected count $expected, got $actual"
  log "Verified node pool $name has count $expected"
}

verify_runtime_class() {
  local name=$1
  [[ -n "$name" ]] || return 0
  kubectl get runtimeclass "$name" >/dev/null 2>&1 || die "runtime class $name was not found after AKS pod sandboxing update"
  log "Verified runtime class $name exists"
}

if is_true "${DRY_RUN:-0}"; then
  log "DRY_RUN=1: printing Azure commands without validating live VM size or provisioning"
else
  require_command az
  require_command kubectl
  set_azure_subscription
  validate_vm_size
fi

ensure_cluster
ensure_nodepool "$KATA_NODEPOOL_NAME" "$KATA_NODE_LABELS" "$KATA_NODE_TAINTS" "$KATA_NODEPOOL_EXTRA_ARGS"
ensure_nodepool "$GVISOR_NODEPOOL_NAME" "$GVISOR_NODE_LABELS" "$GVISOR_NODE_TAINTS" "$GVISOR_NODEPOOL_EXTRA_ARGS"
ensure_nodepool "$FIRECRACKER_NODEPOOL_NAME" "$FIRECRACKER_NODE_LABELS" "$FIRECRACKER_NODE_TAINTS" "$FIRECRACKER_NODEPOOL_EXTRA_ARGS"

if ! is_true "${DRY_RUN:-0}"; then
  run_cmd az aks update --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --yes
  run_cmd az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --overwrite-existing
  verify_nodepool_count "$SYSTEM_NODEPOOL_NAME" 2
  verify_nodepool_count "$KATA_NODEPOOL_NAME" 1
  verify_nodepool_count "$GVISOR_NODEPOOL_NAME" 1
  verify_nodepool_count "$FIRECRACKER_NODEPOOL_NAME" 1
  verify_runtime_class "$KATA_RUNTIME_CLASS"
fi
