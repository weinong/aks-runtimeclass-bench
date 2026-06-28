#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
source "$SCRIPT_DIR/common.sh"

requested_run_id=${RUN_ID:-runtimeclass-$(date -u +%Y%m%dT%H%M%SZ)}
run_dir="$REPO_ROOT/${OUTPUT_DIR:-results}/$requested_run_id"
raw_dir="$run_dir/raw"
rendered_config="$run_dir/kube-burner.yml"
runtime_manifest="$run_dir/runtime-manifest.json"

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

mkdir -p "$raw_dir"
if ! is_true "${DRY_RUN:-0}"; then
  shopt -s nullglob dotglob
  raw_entries=("$raw_dir"/*)
  shopt -u nullglob dotglob
  if (( ${#raw_entries[@]} > 0 )); then
    die "raw metrics directory is not empty: $raw_dir; choose a new RUN_ID or clean the directory first"
  fi
fi

METRICS_DIR="$raw_dir" "$SCRIPT_DIR/render-kube-burner-config.py" --runtime-manifest "$runtime_manifest" > "$rendered_config"
log "Rendered kube-burner config to $rendered_config"

kube_burner=$(resolve_kube_burner)
cmd=("$kube_burner" init
  --config "$rendered_config"
  --uuid "$requested_run_id"
  --allow-missing
  --timeout "${BENCHMARK_TIMEOUT:-4h}")

if [[ -n "${KUBECONFIG:-}" ]]; then
  cmd+=(--kubeconfig "$KUBECONFIG")
fi
if [[ -n "${KUBE_CONTEXT:-}" ]]; then
  cmd+=(--kube-context "$KUBE_CONTEXT")
fi

if is_true "${DRY_RUN:-0}"; then
  log "DRY_RUN=1: not invoking kube-burner for $requested_run_id"
  print_cmd "${cmd[@]}"
  log "DRY_RUN=1: not extracting benchmark summaries for $requested_run_id"
  print_cmd "$SCRIPT_DIR/extract-results.py" "$raw_dir" --output-dir "$run_dir" --run-id "$requested_run_id" --runtime-manifest "$runtime_manifest"
  exit 0
fi

run_cmd "${cmd[@]}"

extract_cmd=("$SCRIPT_DIR/extract-results.py" "$raw_dir" --output-dir "$run_dir" --run-id "$requested_run_id" --runtime-manifest "$runtime_manifest")
if ! is_true "${CSV_OUTPUT:-true}"; then
  extract_cmd+=(--no-csv)
fi
run_cmd "${extract_cmd[@]}"
log "Benchmark summaries written to $run_dir"
