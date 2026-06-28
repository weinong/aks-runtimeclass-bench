#!/usr/bin/env python3
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_CONDITIONS = [
    "PodScheduled",
    "PodReadyToStartContainers",
    "ContainersStarted",
    "ContainersReady",
    "Ready",
]
REQUIRED_QUANTILES = ["P50", "P95", "P99"]


def iter_json_values(path):
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        for line_number, line in enumerate(text.splitlines(), start=1):
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"failed to parse JSON in {path}:{line_number}: {exc}") from exc
        return

    if isinstance(parsed, list):
        for item in parsed:
            yield item
    else:
        yield parsed


def collect_records(input_dir):
    records = []
    for path in sorted(input_dir.rglob("*.json")):
        for value in iter_json_values(path):
            if isinstance(value, dict) and value.get("metricName") == "podLatencyQuantilesMeasurement":
                records.append(value)
    return records


def record_runtime_key(record, expected_keys=None):
    expected_keys = set(expected_keys or [])
    candidates = set()
    for name in ["jobName", "job", "job_name", "kubeBurnerJob"]:
        value = record.get(name)
        if isinstance(value, str) and value:
            if value.startswith("runtimeclass-pod-latency-"):
                key = value.removeprefix("runtimeclass-pod-latency-")
                if expected_keys and key not in expected_keys:
                    raise SystemExit(f"pod latency record references unknown runtime job: {value}")
                candidates.add(key)
            elif value in expected_keys:
                candidates.add(value)
    labels = record.get("labels")
    if isinstance(labels, dict):
        value = labels.get("runtimeclass-bench-key")
        if isinstance(value, str) and value:
            if expected_keys and value not in expected_keys:
                raise SystemExit(f"pod latency record references unknown runtime label: {value}")
            candidates.add(value)
    if len(candidates) > 1:
        raise SystemExit(f"pod latency record contains conflicting runtime identifiers: {sorted(candidates)}")
    return next(iter(candidates), None)


def build_runtime_quantiles(records, runtime_key, expected_keys=None):
    by_condition = {}
    for record in records:
        if runtime_key is not None and record_runtime_key(record, expected_keys) != runtime_key:
            continue
        condition = record.get("quantileName")
        if condition in REQUIRED_CONDITIONS and condition not in by_condition:
            by_condition[condition] = record

    missing = []
    quantiles = []
    for condition in REQUIRED_CONDITIONS:
        record = by_condition.get(condition)
        if record is None:
            missing.append(condition)
            continue
        missing_quantiles = [name for name in REQUIRED_QUANTILES if name not in record]
        if missing_quantiles:
            missing.append(f"{condition}: {', '.join(missing_quantiles)}")
            continue
        quantiles.append(
            {
                "condition": condition,
                "P50": record["P50"],
                "P95": record["P95"],
                "P99": record["P99"],
            }
        )

    if missing:
        raise SystemExit("missing required pod latency quantiles: " + "; ".join(missing))

    return quantiles


def build_single_summary(records, input_dir, run_id, runtime_class):
    quantiles = build_runtime_quantiles(records, None)

    return {
        "runId": run_id,
        "runtimeClass": runtime_class or "standard",
        "sourceDirectory": str(input_dir),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "quantiles": quantiles,
    }


def load_runtime_manifest(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"failed to parse runtime manifest {path}: {exc}") from exc
    runtimes = data.get("runtimes")
    if not isinstance(runtimes, list) or not runtimes:
        raise SystemExit(f"runtime manifest {path} must contain a non-empty runtimes array")
    for runtime in runtimes:
        if not isinstance(runtime, dict) or not runtime.get("key") or not runtime.get("runtimeClass"):
            raise SystemExit(f"runtime manifest {path} contains an invalid runtime entry")
    return runtimes


def build_suite_summary(records, input_dir, run_id, runtime_manifest):
    expected_keys = {runtime["key"] for runtime in runtime_manifest}
    keyed_records = [record for record in records if record_runtime_key(record, expected_keys) is not None]
    use_keyed_records = bool(keyed_records)
    if use_keyed_records and len(keyed_records) != len(records):
        raise SystemExit("mixed keyed and unkeyed pod latency records found; cannot safely separate runtime results")
    if not use_keyed_records and len(runtime_manifest) > 1:
        raise SystemExit("pod latency records do not include runtime job metadata; cannot safely separate runtime results")
    runs = []
    for runtime in runtime_manifest:
        key = runtime["key"]
        runtime_records = records if not use_keyed_records else keyed_records
        quantiles = build_runtime_quantiles(runtime_records, key if use_keyed_records else None, expected_keys)
        runs.append(
            {
                "runtimeKey": key,
                "runtimeClass": runtime["runtimeClass"],
                "runId": f"{run_id}-{key}",
                "sourceDirectory": str(input_dir),
                "quantiles": quantiles,
            }
        )

    return {
        "runId": run_id,
        "sourceDirectory": str(input_dir),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
    }


def write_csv(summary, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "runtime_class", "condition", "p50", "p95", "p99"])
        writer.writeheader()
        for item in summary["quantiles"]:
            writer.writerow(
                {
                    "run_id": summary["runId"],
                    "runtime_class": summary["runtimeClass"],
                    "condition": item["condition"],
                    "p50": item["P50"],
                    "p95": item["P95"],
                    "p99": item["P99"],
                }
            )


def write_suite_csv(summary, path):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "runtime_key", "runtime_class", "condition", "p50", "p95", "p99"],
        )
        writer.writeheader()
        for run in summary["runs"]:
            for item in run["quantiles"]:
                writer.writerow(
                    {
                        "run_id": run["runId"],
                        "runtime_key": run["runtimeKey"],
                        "runtime_class": run["runtimeClass"],
                        "condition": item["condition"],
                        "p50": item["P50"],
                        "p95": item["P95"],
                        "p99": item["P99"],
                    }
                )


def main():
    parser = argparse.ArgumentParser(description="Extract kube-burner pod latency quantiles")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runtime-class", default="")
    parser.add_argument("--runtime-manifest", type=Path)
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"input directory does not exist: {args.input_dir}")

    records = collect_records(args.input_dir)
    if not records:
        raise SystemExit(f"no podLatencyQuantilesMeasurement records found under {args.input_dir}")

    if args.runtime_manifest:
        summary = build_suite_summary(records, args.input_dir, args.run_id, load_runtime_manifest(args.runtime_manifest))
    else:
        summary = build_single_summary(records, args.input_dir, args.run_id, args.runtime_class)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {json_path}")

    if not args.no_csv:
        csv_path = args.output_dir / "summary.csv"
        if args.runtime_manifest:
            write_suite_csv(summary, csv_path)
        else:
            write_csv(summary, csv_path)
        print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
