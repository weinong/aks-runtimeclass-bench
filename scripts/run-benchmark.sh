#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
source "$SCRIPT_DIR/common.sh"

run_id=${RUN_ID:-runtimeclass-$(date -u +%Y%m%dT%H%M%SZ)}
run_dir="$REPO_ROOT/${OUTPUT_DIR:-results}/$run_id"
raw_dir="$run_dir/raw"
user_data="$run_dir/user-data.yml"
config_file=${CONFIG_FILE:-config/runtimeclass-pod-latency.yml}
runtime_class=${RUNTIME_CLASS:-}

mkdir -p "$raw_dir"
if ! is_true "${DRY_RUN:-0}"; then
  shopt -s nullglob dotglob
  raw_entries=("$raw_dir"/*)
  shopt -u nullglob dotglob
  if (( ${#raw_entries[@]} > 0 )); then
    die "raw metrics directory is not empty: $raw_dir; choose a new RUN_ID or clean the directory first"
  fi
fi
RUN_OUTPUT_DIR="$run_dir" METRICS_DIR="$raw_dir" "$SCRIPT_DIR/render-user-data.py" > "$user_data"
log "Rendered kube-burner user data to $user_data"

repo_kube_burner="$REPO_ROOT/${TOOLS_DIR:-tools}/bin/kube-burner"
if [[ -x "$repo_kube_burner" ]]; then
  kube_burner="$repo_kube_burner"
elif command -v kube-burner >/dev/null 2>&1; then
  kube_burner=$(command -v kube-burner)
else
  kube_burner="$repo_kube_burner"
  if ! is_true "${DRY_RUN:-0}"; then
    die "kube-burner not found; run 'make kube-burner-install' or add kube-burner to PATH"
  fi
fi

cmd=("$kube_burner" init
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
  log "DRY_RUN=1: not invoking kube-burner"
  print_cmd "${cmd[@]}"
  exit 0
fi

run_cmd "${cmd[@]}"

extract_cmd=("$SCRIPT_DIR/extract-results.py" "$raw_dir" --output-dir "$run_dir" --run-id "$run_id" --runtime-class "$runtime_class")
if ! is_true "${CSV_OUTPUT:-true}"; then
  extract_cmd+=(--no-csv)
fi
run_cmd "${extract_cmd[@]}"
log "Benchmark summaries written to $run_dir"
