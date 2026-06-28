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
suite_config="$REPO_ROOT/${KUBE_BURNER_CONFIG:-configs/kube-burner-runtimeclass-suite.yml}"
suite_manifest="$REPO_ROOT/${RUNTIME_MANIFEST:-configs/runtime-manifest.json}"
metrics_placeholder="__METRICS_DIR__"
prometheus_endpoint_placeholder="__PROMETHEUS_ENDPOINT__"
prometheus_metrics_config_placeholder="__PROMETHEUS_METRICS_CONFIG__"
prometheus_endpoint=${KUBE_BURNER_PROMETHEUS_ENDPOINT:-http://127.0.0.1:9090}
prometheus_metrics_config="$REPO_ROOT/${KUBE_BURNER_PROMETHEUS_METRICS_CONFIG:-configs/kubelet-startup-metrics.yml}"

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

[[ -f "$suite_config" ]] || die "kube-burner suite config not found: $suite_config"
[[ -f "$suite_manifest" ]] || die "runtime manifest not found: $suite_manifest"
[[ -f "$prometheus_metrics_config" ]] || die "Prometheus metrics profile not found: $prometheus_metrics_config"
[[ -n "$prometheus_endpoint" ]] || die "KUBE_BURNER_PROMETHEUS_ENDPOINT must not be empty"

config_text=$(<"$suite_config")
if [[ "$config_text" != *"$metrics_placeholder"* ]]; then
  die "kube-burner suite config must contain metrics directory placeholder: $metrics_placeholder"
fi
if [[ "$config_text" != *"$prometheus_endpoint_placeholder"* ]]; then
  die "kube-burner suite config must contain Prometheus endpoint placeholder: $prometheus_endpoint_placeholder"
fi
if [[ "$config_text" != *"$prometheus_metrics_config_placeholder"* ]]; then
  die "kube-burner suite config must contain Prometheus metrics profile placeholder: $prometheus_metrics_config_placeholder"
fi
config_text=${config_text//$metrics_placeholder/$raw_dir}
config_text=${config_text//$prometheus_endpoint_placeholder/$prometheus_endpoint}
config_text=${config_text//$prometheus_metrics_config_placeholder/$prometheus_metrics_config}
printf '%s' "$config_text" > "$rendered_config"
cp "$suite_manifest" "$runtime_manifest"
log "Prepared kube-burner config from $suite_config at $rendered_config"

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
