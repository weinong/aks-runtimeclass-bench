#!/usr/bin/env python3
import argparse
import csv
import json
import math
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
KUBELET_STARTUP_METRICS = [
    {
        "metricName": "kubeletRunPodSandboxDurationSeconds",
        "metricFamily": "kubelet_run_podsandbox_duration_seconds",
        "unit": "seconds",
    },
    {
        "metricName": "kubeletPodStartSliDurationSeconds",
        "metricFamily": "kubelet_pod_start_sli_duration_seconds",
        "unit": "seconds",
    },
    {
        "metricName": "kubeletPodStartTotalDurationSeconds",
        "metricFamily": "kubelet_pod_start_total_duration_seconds",
        "unit": "seconds",
    },
]
KUBELET_METRIC_FAMILIES = {metric["metricFamily"] for metric in KUBELET_STARTUP_METRICS}
KUBELET_METRIC_NAME_TO_FAMILY = {metric["metricName"]: metric["metricFamily"] for metric in KUBELET_STARTUP_METRICS}
ENVIRONMENT_CSV_FIELDS = ["node_pool", "vm_sku", "kernel_version", "containerd_version", "kubelet_version", "kata_version"]
KUBELET_DIRECT_QUANTILE_METRICS = {
    f"{metric['metricName']}{quantile}": (metric["metricFamily"], quantile)
    for metric in KUBELET_STARTUP_METRICS
    for quantile in REQUIRED_QUANTILES
}


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
    pod_records = []
    kubelet_records = []
    for path in sorted(input_dir.rglob("*.json")):
        for value in iter_json_values(path):
            if isinstance(value, dict) and value.get("metricName") == "podLatencyQuantilesMeasurement":
                pod_records.append(value)
            elif isinstance(value, dict) and is_kubelet_metric_record(value):
                kubelet_records.append(value)
    return pod_records, kubelet_records


def record_runtime_key(record, expected_keys=None, record_type="pod latency"):
    expected_keys = set(expected_keys or [])
    candidates = set()
    for name in ["jobName", "job", "job_name", "kubeBurnerJob"]:
        value = record.get(name)
        if isinstance(value, str) and value:
            if value.startswith("runtimeclass-pod-latency-"):
                key = value.removeprefix("runtimeclass-pod-latency-")
                if expected_keys and key not in expected_keys:
                    raise SystemExit(f"{record_type} record references unknown runtime job: {value}")
                candidates.add(key)
            elif value in expected_keys:
                candidates.add(value)
    labels = record.get("labels")
    if isinstance(labels, dict):
        value = labels.get("runtimeclass-bench-key")
        if isinstance(value, str) and value:
            if expected_keys and value not in expected_keys:
                raise SystemExit(f"{record_type} record references unknown runtime label: {value}")
            candidates.add(value)
    if len(candidates) > 1:
        raise SystemExit(f"{record_type} record contains conflicting runtime identifiers: {sorted(candidates)}")
    return next(iter(candidates), None)


def kubelet_metric_labels(record):
    labels = {}
    for name in ["labels", "metric"]:
        value = record.get(name)
        if isinstance(value, dict):
            labels.update(value)
    for name in ["__name__", "le"]:
        value = record.get(name)
        if isinstance(value, str):
            labels[name] = value
    return labels


def is_kubelet_metric_record(record):
    if record.get("metricName") in KUBELET_DIRECT_QUANTILE_METRICS:
        return True
    return kubelet_metric_family(record) in KUBELET_METRIC_FAMILIES


def kubelet_metric_family(record):
    name = kubelet_metric_labels(record).get("__name__")
    if isinstance(name, str):
        for suffix in ["_bucket", "_sum", "_count"]:
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name
    return KUBELET_METRIC_NAME_TO_FAMILY.get(record.get("metricName"))


def kubelet_metric_is_bucket(record, family):
    name = kubelet_metric_labels(record).get("__name__")
    if isinstance(name, str):
        return name == f"{family}_bucket"
    return kubelet_metric_labels(record).get("le") is not None


def kubelet_metric_value(record):
    for name in ["value", "metricValue", "Value"]:
        value = record.get(name)
        if isinstance(value, list) and len(value) >= 2:
            value = value[1]
        if value is not None:
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                raise SystemExit(f"kubelet metric record has non-numeric value: {value!r}")
            if not math.isfinite(numeric_value):
                raise SystemExit(f"kubelet metric value must be finite: {value!r}")
            return numeric_value
    raise SystemExit("kubelet metric record is missing a numeric value")


def parse_bucket_bound(value):
    if value in ["+Inf", "Inf", "inf"]:
        return float("inf")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise SystemExit(f"kubelet metric record has invalid histogram bucket bound: {value!r}")


def clean_float(value):
    return round(value, 12)


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        return ""
    return value


def latest_record(records):
    return max(enumerate(records), key=lambda item: (parse_timestamp(item[1].get("timestamp")), item[0]))[1]


def kubelet_series_key(record):
    labels = dict(kubelet_metric_labels(record))
    labels.pop("__name__", None)
    labels.pop("le", None)
    return tuple(sorted(labels.items()))


def reduce_histogram_buckets(records):
    series = {}
    aggregate_by_timestamp = {}
    for record in records:
        labels = kubelet_metric_labels(record)
        upper = parse_bucket_bound(labels.get("le"))
        key = (upper, kubelet_series_key(record))
        timestamp = parse_timestamp(record.get("timestamp"))
        value = kubelet_metric_value(record)
        if key[1] == ():
            aggregate_key = (upper, timestamp)
            aggregate_by_timestamp[aggregate_key] = aggregate_by_timestamp.get(aggregate_key, 0.0) + value
            continue
        current = series.setdefault(key, [])
        current.append((timestamp, value))

    for (upper, timestamp), value in aggregate_by_timestamp.items():
        current = series.setdefault((upper, ()), [])
        current.append((timestamp, value))

    buckets = []
    for (upper, _series_key), samples in series.items():
        samples.sort(key=lambda item: item[0])
        if len(samples) < 2:
            if samples[0][0] == "":
                buckets.append((upper, samples[0][1]))
                continue
            raise SystemExit("kubelet metric histogram counters requires at least two Prometheus samples")
        value = samples[-1][1] - samples[0][1]
        if value < 0:
            value = samples[-1][1]
        buckets.append((upper, value))
    return buckets


def histogram_quantile(metric_family, quantile_name, quantile, buckets):
    aggregated = {}
    for upper, count in buckets:
        aggregated[upper] = aggregated.get(upper, 0.0) + count

    finite_buckets = sorted((upper, count) for upper, count in aggregated.items() if upper != float("inf"))
    infinite_buckets = [count for upper, count in aggregated.items() if upper == float("inf")]
    if not finite_buckets or not infinite_buckets:
        raise SystemExit(f"kubelet metric {metric_family} is missing finite or +Inf histogram buckets")

    total = max(infinite_buckets)
    if total <= 0:
        raise SystemExit(f"kubelet metric {metric_family} has no histogram samples")

    rank = total * quantile
    previous_upper = 0.0
    previous_count = 0.0
    for upper, count in finite_buckets:
        if count < previous_count:
            raise SystemExit(f"kubelet metric {metric_family} histogram buckets are not cumulative")
        if count >= rank:
            bucket_count = count - previous_count
            if bucket_count <= 0:
                return clean_float(upper)
            fraction = (rank - previous_count) / bucket_count
            return clean_float(previous_upper + (upper - previous_upper) * fraction)
        previous_upper = upper
        previous_count = count

    return clean_float(finite_buckets[-1][0])


def prometheus_attribution_map(runtime_manifest):
    label_key = None
    by_key = {}
    seen_values = {}
    for runtime in runtime_manifest:
        key = runtime["key"]
        attribution = runtime.get("prometheusAttribution")
        if not isinstance(attribution, dict):
            raise SystemExit(f"runtime {key} must declare prometheusAttribution")
        current_label_key = attribution.get("labelKey")
        label_value = attribution.get("labelValue")
        if not isinstance(current_label_key, str) or not current_label_key:
            raise SystemExit(f"runtime {key} must declare a Prometheus attribution labelKey")
        if not isinstance(label_value, str) or not label_value:
            raise SystemExit(f"runtime {key} must declare a Prometheus attribution labelValue")
        if label_key is None:
            label_key = current_label_key
        elif current_label_key != label_key:
            raise SystemExit("runtime manifest must use one Prometheus attribution label key")
        if label_value in seen_values:
            raise SystemExit(
                f"duplicate Prometheus runtime attribution value {label_value!r} for {seen_values[label_value]} and {key}"
            )
        seen_values[label_value] = key
        by_key[key] = {"labelKey": current_label_key, "labelValue": label_value}
    return label_key, by_key


def direct_kubelet_quantile(record):
    metric_name = record.get("metricName")
    if metric_name in KUBELET_DIRECT_QUANTILE_METRICS:
        return KUBELET_DIRECT_QUANTILE_METRICS[metric_name]
    return None


def record_prometheus_attribution_value(record, label_key, metric_family):
    labels = kubelet_metric_labels(record)
    value = labels.get(label_key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"kubelet metric record is missing Prometheus runtime attribution {label_key!r} for {metric_family}")
    return value


def build_kubelet_metric_quantiles(records, runtime_key=None, expected_keys=None, required=False, attribution=None):
    attribution = attribution or {}
    records_by_quantile = {
        metric["metricFamily"]: {quantile: [] for quantile in REQUIRED_QUANTILES} for metric in KUBELET_STARTUP_METRICS
    }
    for record in records:
        direct_quantile = direct_kubelet_quantile(record)
        if direct_quantile is None:
            continue
        family, quantile_name = direct_quantile
        if runtime_key is not None:
            attribution_value = record_prometheus_attribution_value(record, attribution["labelKey"], family)
            if attribution_value != attribution["labelValue"]:
                continue
        elif attribution:
            record_prometheus_attribution_value(record, attribution["labelKey"], family)
        if family not in records_by_quantile:
            continue
        records_by_quantile[family][quantile_name].append(record)

    missing = []
    quantiles = []
    for metric in KUBELET_STARTUP_METRICS:
        family = metric["metricFamily"]
        values = {}
        for quantile_name in REQUIRED_QUANTILES:
            quantile_records = records_by_quantile[family][quantile_name]
            if not quantile_records:
                missing.append(f"{runtime_key}: {family} {quantile_name}" if runtime_key else f"{family} {quantile_name}")
                continue
            values[quantile_name] = clean_float(kubelet_metric_value(latest_record(quantile_records)))
        if any(quantile_name not in values for quantile_name in REQUIRED_QUANTILES):
            continue
        quantiles.append(
            {
                "metricName": metric["metricName"],
                "metricFamily": family,
                "unit": metric["unit"],
                "P50": values["P50"],
                "P95": values["P95"],
                "P99": values["P99"],
            }
        )

    if missing and required:
        raise SystemExit("missing required kubelet metric quantiles: " + "; ".join(missing))

    return quantiles


def validate_kubelet_metric_runtime_attribution(records, expected_keys, label_key, expected_values):
    for record in records:
        direct_quantile = direct_kubelet_quantile(record)
        if direct_quantile is None:
            continue
        family, _quantile_name = direct_quantile
        attribution_value = record_prometheus_attribution_value(record, label_key, family)
        if attribution_value not in expected_values:
            raise SystemExit(f"kubelet metric record references unknown Prometheus runtime attribution: {attribution_value}")


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
    prometheus_attribution_map(runtimes)
    return runtimes


def load_environment_metadata(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"failed to parse environment metadata {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"environment metadata {path} must contain a JSON object")
    return data


def runtime_environment(environment_metadata, runtime_key):
    if not environment_metadata:
        return None
    runtime_node_pools = environment_metadata.get("runtimeNodePools")
    node_pools = environment_metadata.get("nodePools")
    if not isinstance(runtime_node_pools, dict) or not isinstance(node_pools, list):
        return None
    node_pool_name = runtime_node_pools.get(runtime_key)
    if not isinstance(node_pool_name, str) or not node_pool_name:
        return None
    node_pool = next((item for item in node_pools if isinstance(item, dict) and item.get("name") == node_pool_name), None)
    if node_pool is None:
        return {"nodePool": node_pool_name, "vmSku": None, "kernelVersion": None, "containerdVersion": None, "kubeletVersion": None, "kataVersion": None}
    return {
        "nodePool": node_pool_name,
        "vmSku": node_pool.get("vmSku"),
        "kernelVersion": node_pool.get("kernelVersion"),
        "containerdVersion": node_pool.get("containerdVersion"),
        "kubeletVersion": node_pool.get("kubeletVersion"),
        "kataVersion": node_pool.get("kataVersion"),
        "nodes": node_pool.get("nodes", []),
    }


def environment_csv_values(run):
    environment = run.get("environment") or {}
    return {
        "node_pool": environment.get("nodePool") or "",
        "vm_sku": environment.get("vmSku") or "",
        "kernel_version": environment.get("kernelVersion") or "",
        "containerd_version": environment.get("containerdVersion") or "",
        "kubelet_version": environment.get("kubeletVersion") or "",
        "kata_version": environment.get("kataVersion") or "",
    }


def build_suite_summary(records, kubelet_records, input_dir, run_id, runtime_manifest, environment_metadata=None):
    expected_keys = {runtime["key"] for runtime in runtime_manifest}
    attribution_label_key, attribution_by_key = prometheus_attribution_map(runtime_manifest)
    expected_attribution_values = {value["labelValue"] for value in attribution_by_key.values()}
    keyed_records = [record for record in records if record_runtime_key(record, expected_keys) is not None]
    validate_kubelet_metric_runtime_attribution(
        kubelet_records, expected_keys, attribution_label_key, expected_attribution_values
    )
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
        kubelet_metric_quantiles = build_kubelet_metric_quantiles(
            kubelet_records, key, expected_keys, required=True, attribution=attribution_by_key[key]
        )
        run = {
            "runtimeKey": key,
            "runtimeClass": runtime["runtimeClass"],
            "runId": f"{run_id}-{key}",
            "sourceDirectory": str(input_dir),
            "quantiles": quantiles,
            "kubeletMetricQuantiles": kubelet_metric_quantiles,
        }
        environment = runtime_environment(environment_metadata, key)
        if environment is not None:
            run["environment"] = environment
        runs.append(run)

    summary = {
        "runId": run_id,
        "sourceDirectory": str(input_dir),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
    }
    if environment_metadata is not None:
        summary["environment"] = environment_metadata
    return summary


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
            fieldnames=[
                "run_id",
                "runtime_key",
                "runtime_class",
                "metric_category",
                "condition",
                "metric_name",
                "metric_family",
                "unit",
                *ENVIRONMENT_CSV_FIELDS,
                "p50",
                "p95",
                "p99",
            ],
        )
        writer.writeheader()
        for run in summary["runs"]:
            environment = environment_csv_values(run)
            for item in run["quantiles"]:
                writer.writerow(
                    {
                        "run_id": run["runId"],
                        "runtime_key": run["runtimeKey"],
                        "runtime_class": run["runtimeClass"],
                        "metric_category": "pod_latency",
                        "condition": item["condition"],
                        "metric_name": "",
                        "metric_family": "",
                        "unit": "",
                        **environment,
                        "p50": item["P50"],
                        "p95": item["P95"],
                        "p99": item["P99"],
                    }
                )
            for item in run["kubeletMetricQuantiles"]:
                writer.writerow(
                    {
                        "run_id": run["runId"],
                        "runtime_key": run["runtimeKey"],
                        "runtime_class": run["runtimeClass"],
                        "metric_category": "kubelet_metric",
                        "condition": "",
                        "metric_name": item["metricName"],
                        "metric_family": item["metricFamily"],
                        "unit": item["unit"],
                        **environment,
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
    parser.add_argument("--environment-metadata", type=Path)
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        raise SystemExit(f"input directory does not exist: {args.input_dir}")

    records, kubelet_records = collect_records(args.input_dir)
    if not records:
        raise SystemExit(f"no podLatencyQuantilesMeasurement records found under {args.input_dir}")

    environment_metadata = load_environment_metadata(args.environment_metadata) if args.environment_metadata else None
    if args.runtime_manifest:
        summary = build_suite_summary(
            records,
            kubelet_records,
            args.input_dir,
            args.run_id,
            load_runtime_manifest(args.runtime_manifest),
            environment_metadata,
        )
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
