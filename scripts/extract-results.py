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


def build_summary(records, input_dir, run_id, runtime_class):
    by_condition = {}
    for record in records:
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

    return {
        "runId": run_id,
        "runtimeClass": runtime_class or "standard",
        "sourceDirectory": str(input_dir),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "quantiles": quantiles,
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


def main():
    parser = argparse.ArgumentParser(description="Extract kube-burner pod latency quantiles")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runtime-class", default="")
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"input directory does not exist: {args.input_dir}")

    records = collect_records(args.input_dir)
    if not records:
        raise SystemExit(f"no podLatencyQuantilesMeasurement records found under {args.input_dir}")

    summary = build_summary(records, args.input_dir, args.run_id, args.runtime_class)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {json_path}")

    if not args.no_csv:
        csv_path = args.output_dir / "summary.csv"
        write_csv(summary, csv_path)
        print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
