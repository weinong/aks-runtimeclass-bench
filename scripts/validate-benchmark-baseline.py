#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def read_json(path):
    require(path.is_file(), f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    require(path.is_file(), f"missing file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def assert_aggregate_summary(run_dir, expected_runtimes):
    summary = read_json(run_dir / "summary.json")
    runs = summary.get("runs")
    require(isinstance(runs, list), f"{run_dir}/summary.json must contain a runs array")

    actual = {run.get("runtimeKey"): run.get("runtimeClass") for run in runs}
    require(actual == expected_runtimes, f"aggregate runtimes are {actual!r}, expected {expected_runtimes!r}")
    p50_by_runtime = {}
    for run in runs:
        quantiles = run.get("quantiles")
        require(isinstance(quantiles, list) and quantiles, f"aggregate run {run.get('runtimeKey')!r} must include quantiles")
        ready = next((item for item in quantiles if item.get("condition") == "Ready"), None)
        require(ready is not None, f"aggregate run {run.get('runtimeKey')!r} must include Ready quantiles")
        p50_by_runtime[run.get("runtimeKey")] = ready.get("P50")
    require(
        p50_by_runtime.get("standard") != p50_by_runtime.get("kata"),
        "standard and Kata fixture quantiles must stay separated",
    )

    rows = read_csv(run_dir / "summary.csv")
    row_keys = {row.get("runtime_key") for row in rows}
    require(row_keys == set(expected_runtimes), f"aggregate CSV runtime keys are {row_keys!r}, expected {set(expected_runtimes)!r}")


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark baseline dry-run and summary outputs")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pod-template", type=Path, default=Path("templates/runtimeclass-pod.yml"))
    args = parser.parse_args()

    run_dir = args.output_dir / args.run_id
    expected_runtimes = {
        "standard": "standard",
        "kata": "kata-vm-isolation",
    }
    runtime_dirs = {key: run_dir / "runs" / key for key in expected_runtimes}

    require(not any(path.exists() for path in runtime_dirs.values()), "suite benchmark must not create per-runtime result directories")

    rendered_config = run_dir / "kube-burner.yml"
    runtime_manifest = run_dir / "runtime-manifest.json"
    require(rendered_config.is_file(), f"missing file: {rendered_config}")
    require(runtime_manifest.is_file(), f"missing file: {runtime_manifest}")
    config_text = rendered_config.read_text(encoding="utf-8")
    require("name: runtimeclass-pod-latency-standard" in config_text, "config must include standard job")
    require("name: runtimeclass-pod-latency-kata" in config_text, "config must include Kata job")
    require('runtimeClass: ""' in config_text, "standard job must leave runtimeClass empty")
    require('runtimeClass: "kata-vm-isolation"' in config_text, "Kata job must include runtimeClass")
    require('runtimeclass: "kata"' in config_text, "Kata job must include node selector")
    require('key: "runtimeclass"' in config_text, "Kata job must include toleration")
    require("runtimeClassName" not in config_text, "rendered config should not contain pod runtimeClassName directly")

    template_text = args.pod_template.read_text(encoding="utf-8")
    require(
        "{{- if .runtimeClass }}\n  runtimeClassName:" in template_text,
        "pod template must guard runtimeClassName behind .runtimeClass",
    )

    assert_aggregate_summary(run_dir, expected_runtimes)


if __name__ == "__main__":
    main()
