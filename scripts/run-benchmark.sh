#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
source "$SCRIPT_DIR/common.sh"

config_file=${CONFIG_FILE:-config/runtimeclass-pod-latency.yml}
requested_run_id=${RUN_ID:-runtimeclass-$(date -u +%Y%m%dT%H%M%SZ)}
requested_runtime_class=${RUNTIME_CLASS:-}
requested_node_selector=${NODE_SELECTOR:-}
requested_tolerations_json=${TOLERATIONS_JSON:-[]}
baseline_node_selector=${BASELINE_NODE_SELECTOR:-}
baseline_tolerations_json=${BASELINE_TOLERATIONS_JSON:-[]}

runtime_slug() {
  local value=${1:-standard}
  value=${value//[^A-Za-z0-9_.-]/-}
  printf '%s' "$value"
}

resolve_kube_burner() {
  local repo_kube_burner="$REPO_ROOT/${TOOLS_DIR:-tools}/bin/kube-burner"
  if [[ -x "$repo_kube_burner" ]]; then
    printf '%s' "$repo_kube_burner"
  elif command -v kube-burner >/dev/null 2>&1; then
    command -v kube-burner
  else
    if ! is_true "${DRY_RUN:-0}"; then
      die "kube-burner not found; run 'make kube-burner-install' or add kube-burner to PATH"
    fi
    printf '%s' "$repo_kube_burner"
  fi
}

run_single_benchmark() {
  local runtime_class=$1
  local run_id=$2
  local node_selector=$3
  local tolerations_json=$4
  local run_dir="$REPO_ROOT/${OUTPUT_DIR:-results}/$run_id"
  local raw_dir="$run_dir/raw"
  local user_data="$run_dir/user-data.yml"
  local runtime_label=${runtime_class:-standard}

  log "Starting benchmark run '$run_id' for runtime class '$runtime_label'"

  mkdir -p "$raw_dir"
  if ! is_true "${DRY_RUN:-0}"; then
    shopt -s nullglob dotglob
    raw_entries=("$raw_dir"/*)
    shopt -u nullglob dotglob
    if (( ${#raw_entries[@]} > 0 )); then
      die "raw metrics directory is not empty: $raw_dir; choose a new RUN_ID or clean the directory first"
    fi
  fi

  RUNTIME_CLASS="$runtime_class" \
    NODE_SELECTOR="$node_selector" \
    TOLERATIONS_JSON="$tolerations_json" \
    RUN_OUTPUT_DIR="$run_dir" \
    METRICS_DIR="$raw_dir" \
    "$SCRIPT_DIR/render-user-data.py" > "$user_data"
  log "Rendered kube-burner user data to $user_data"

  local kube_burner
  kube_burner=$(resolve_kube_burner)

  local cmd=("$kube_burner" init
    --config "$config_file"
    --uuid "$run_id"
    --user-data "$user_data"
    --allow-missing
    --timeout "${BENCHMARK_TIMEOUT:-4h}")

  if [[ -n "${KUBECONFIG:-}" ]]; then
    cmd+=(--kubeconfig "$KUBECONFIG")
  fi
  if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    cmd+=(--kube-context "$KUBE_CONTEXT")
  fi

  if is_true "${DRY_RUN:-0}"; then
    log "DRY_RUN=1: not invoking kube-burner for $run_id"
    print_cmd "${cmd[@]}"
    return 0
  fi

  run_cmd "${cmd[@]}"

  local extract_cmd=("$SCRIPT_DIR/extract-results.py" "$raw_dir" --output-dir "$run_dir" --run-id "$run_id" --runtime-class "$runtime_class")
  if ! is_true "${CSV_OUTPUT:-true}"; then
    extract_cmd+=(--no-csv)
  fi
  run_cmd "${extract_cmd[@]}"
  log "Benchmark summaries written to $run_dir"
}

if [[ -n "$requested_runtime_class" ]]; then
  baseline_run_id="${requested_run_id}-standard"
  requested_runtime_run_id="${requested_run_id}-$(runtime_slug "$requested_runtime_class")"
  if [[ "$requested_runtime_run_id" == "$baseline_run_id" ]]; then
    requested_runtime_run_id="${requested_runtime_run_id}-runtime"
  fi
  run_single_benchmark "" "$baseline_run_id" "$baseline_node_selector" "$baseline_tolerations_json"
  run_single_benchmark "$requested_runtime_class" "$requested_runtime_run_id" "$requested_node_selector" "$requested_tolerations_json"
else
  run_single_benchmark "" "$requested_run_id" "$baseline_node_selector" "$baseline_tolerations_json"
fi
