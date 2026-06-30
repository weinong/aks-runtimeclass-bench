#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


METRICS_DIR_PLACEHOLDER = "__METRICS_DIR__"
PROMETHEUS_ENDPOINT_PLACEHOLDER = "__PROMETHEUS_ENDPOINT__"
PROMETHEUS_METRICS_CONFIG_PLACEHOLDER = "__PROMETHEUS_METRICS_CONFIG__"
PROMETHEUS_RUNTIMECLASS_PLACEHOLDER = "__PROMETHEUS_RUNTIMECLASS__"
JOB_NAME_PREFIX = "runtimeclass-pod-latency-"


def die(message):
    raise SystemExit(message)


def load_runtime_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    runtimes = data.get("runtimes")
    if not isinstance(runtimes, list) or not runtimes:
        die(f"runtime manifest {path} must contain a non-empty runtimes array")
    return runtimes


def require_placeholders(config_text, metrics_text):
    for placeholder in [METRICS_DIR_PLACEHOLDER, PROMETHEUS_ENDPOINT_PLACEHOLDER, PROMETHEUS_METRICS_CONFIG_PLACEHOLDER]:
        if placeholder not in config_text:
            die(f"kube-burner suite config must contain placeholder: {placeholder}")
    if PROMETHEUS_RUNTIMECLASS_PLACEHOLDER not in metrics_text:
        die(f"Prometheus metrics profile must contain placeholder: {PROMETHEUS_RUNTIMECLASS_PLACEHOLDER}")


def job_block_bounds(config_text, job_name):
    marker = f"\n  - name: {job_name}\n"
    start = config_text.find(marker)
    if start == -1:
        die(f"kube-burner suite config is missing job: {job_name}")
    next_start = config_text.find("\n  - name: ", start + len(marker))
    if next_start == -1:
        next_start = len(config_text)
    return start, next_start


def render_config_for_runtime(config_text, key, raw_dir, prometheus_endpoint, metrics_profile):
    job_name = f"{JOB_NAME_PREFIX}{key}"
    start, end = job_block_bounds(config_text, job_name)
    header = config_text[: config_text.find("jobs:") + len("jobs:\n")]
    job_block = config_text[start + 1 : end].rstrip() + "\n"
    rendered = header + job_block
    rendered = rendered.replace(METRICS_DIR_PLACEHOLDER, str(raw_dir))
    rendered = rendered.replace(PROMETHEUS_ENDPOINT_PLACEHOLDER, prometheus_endpoint)
    rendered = rendered.replace(PROMETHEUS_METRICS_CONFIG_PLACEHOLDER, str(metrics_profile))
    return rendered


def runtime_attribution_value(runtime):
    key = runtime.get("key")
    attribution = runtime.get("prometheusAttribution")
    if not isinstance(attribution, dict):
        die(f"runtime {key} must declare prometheusAttribution")
    label_value = attribution.get("labelValue")
    if not isinstance(label_value, str) or not label_value:
        die(f"runtime {key} must declare a Prometheus attribution labelValue")
    return label_value


def main():
    parser = argparse.ArgumentParser(description="Render per-runtime kube-burner configs and Prometheus metrics profiles")
    parser.add_argument("--suite-config", type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--metrics-template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--prometheus-endpoint", required=True)
    args = parser.parse_args()

    config_text = args.suite_config.read_text(encoding="utf-8")
    metrics_text = args.metrics_template.read_text(encoding="utf-8")
    require_placeholders(config_text, metrics_text)
    runtimes = load_runtime_manifest(args.runtime_manifest)

    config_dir = args.output_dir / "kube-burner"
    metrics_dir = args.output_dir / "prometheus-metrics"
    config_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    runtime_keys = []

    for runtime in runtimes:
        key = runtime.get("key")
        if not isinstance(key, str) or not key:
            die(f"runtime manifest {args.runtime_manifest} contains an invalid runtime entry")
        runtime_keys.append(key)
        label_value = runtime_attribution_value(runtime)
        metrics_profile = metrics_dir / f"{key}.yml"
        metrics_profile.write_text(
            metrics_text.replace(PROMETHEUS_RUNTIMECLASS_PLACEHOLDER, label_value),
            encoding="utf-8",
        )
        rendered_config = render_config_for_runtime(
            config_text,
            key,
            args.raw_dir,
            args.prometheus_endpoint,
            metrics_profile,
        )
        (config_dir / f"{key}.yml").write_text(rendered_config, encoding="utf-8")
    (args.output_dir / "runtime-keys.txt").write_text("\n".join(runtime_keys) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
