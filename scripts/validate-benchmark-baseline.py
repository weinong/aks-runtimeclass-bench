#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path


def runtime_slug(value):
    return re.sub(r"[^A-Za-z0-9_.-]", "-", value or "standard")


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


def assert_runtime_summary(run_dir, expected_runtime):
    summary = read_json(run_dir / "summary.json")
    require(
        summary.get("runtimeClass") == expected_runtime,
        f"{run_dir}/summary.json runtimeClass is {summary.get('runtimeClass')!r}, expected {expected_runtime!r}",
    )

    rows = read_csv(run_dir / "summary.csv")
    require(rows, f"{run_dir}/summary.csv has no data rows")
    mismatched = [row.get("runtime_class") for row in rows if row.get("runtime_class") != expected_runtime]
    require(not mismatched, f"{run_dir}/summary.csv contains runtime_class values other than {expected_runtime!r}")


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark baseline dry-run and summary outputs")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runtime-class", required=True)
    parser.add_argument("--pod-template", type=Path, default=Path("templates/runtimeclass-pod.yml"))
    parser.add_argument("--baseline-only-run-id")
    args = parser.parse_args()

    standard_dir = args.output_dir / f"{args.run_id}-standard"
    explicit_dir = args.output_dir / f"{args.run_id}-{runtime_slug(args.runtime_class)}"

    standard_user_data = standard_dir / "user-data.yml"
    explicit_user_data = explicit_dir / "user-data.yml"
    require(standard_user_data.is_file(), f"missing file: {standard_user_data}")
    require(explicit_user_data.is_file(), f"missing file: {explicit_user_data}")

    standard_text = standard_user_data.read_text(encoding="utf-8")
    explicit_text = explicit_user_data.read_text(encoding="utf-8")
    require('runtimeClass: ""' in standard_text, "standard baseline user data must leave runtimeClass empty")
    require("nodeSelector:\n  {}" in standard_text, "standard baseline user data must leave nodeSelector empty")
    require("tolerations:\n  []" in standard_text, "standard baseline user data must leave tolerations empty")
    require("runtimeClassName" not in standard_text, "standard baseline user data must not include runtimeClassName")
    require(
        f'runtimeClass: "{args.runtime_class}"' in explicit_text,
        f"explicit runtime user data must include runtimeClass {args.runtime_class!r}",
    )
    require('runtimeclass: "kata"' in explicit_text, "explicit runtime user data must include the requested node selector")
    require('key: "runtimeclass"' in explicit_text, "explicit runtime user data must include the requested toleration")

    template_text = args.pod_template.read_text(encoding="utf-8")
    require(
        "{{- if .runtimeClass }}\n  runtimeClassName:" in template_text,
        "pod template must guard runtimeClassName behind .runtimeClass",
    )

    assert_runtime_summary(standard_dir, "standard")
    assert_runtime_summary(explicit_dir, args.runtime_class)

    if args.baseline_only_run_id:
        baseline_only_dir = args.output_dir / args.baseline_only_run_id
        duplicate_dir = args.output_dir / f"{args.baseline_only_run_id}-standard"
        baseline_only_user_data = baseline_only_dir / "user-data.yml"
        require(baseline_only_user_data.is_file(), f"missing file: {baseline_only_user_data}")
        require(not duplicate_dir.exists(), f"baseline-only benchmark must not create duplicate directory: {duplicate_dir}")
        baseline_only_text = baseline_only_user_data.read_text(encoding="utf-8")
        require('runtimeClass: ""' in baseline_only_text, "baseline-only user data must leave runtimeClass empty")
        require("nodeSelector:\n  {}" in baseline_only_text, "baseline-only user data must leave nodeSelector empty")
        require("tolerations:\n  []" in baseline_only_text, "baseline-only user data must leave tolerations empty")


if __name__ == "__main__":
    main()
