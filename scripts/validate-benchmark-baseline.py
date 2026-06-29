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
    required_kubelet_metric_families = {
        "kubelet_run_podsandbox_duration_seconds",
        "kubelet_pod_start_sli_duration_seconds",
        "kubelet_pod_start_total_duration_seconds",
    }
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
        kubelet_quantiles = run.get("kubeletMetricQuantiles")
        require(
            isinstance(kubelet_quantiles, list) and kubelet_quantiles,
            f"aggregate run {run.get('runtimeKey')!r} must include kubelet metric quantiles",
        )
        actual_families = {item.get("metricFamily") for item in kubelet_quantiles}
        require(
            actual_families == required_kubelet_metric_families,
            f"aggregate run {run.get('runtimeKey')!r} kubelet metric families are {actual_families!r}, expected {required_kubelet_metric_families!r}",
        )
        for item in kubelet_quantiles:
            for quantile in ["P50", "P95", "P99"]:
                require(
                    isinstance(item.get(quantile), (int, float)),
                    f"aggregate run {run.get('runtimeKey')!r} kubelet metric {item.get('metricFamily')!r} must include numeric {quantile}",
                )
    require(
        p50_by_runtime.get("standard") != p50_by_runtime.get("kata"),
        "standard and Kata fixture quantiles must stay separated",
    )
    require(
        p50_by_runtime.get("kata") != p50_by_runtime.get("kata-optimized"),
        "Kata and optimized Kata fixture quantiles must stay separated",
    )
    require(
        p50_by_runtime.get("kata-optimized") != p50_by_runtime.get("gvisor"),
        "optimized Kata and gVisor fixture quantiles must stay separated",
    )
    require(
        p50_by_runtime.get("gvisor") != p50_by_runtime.get("firecracker"),
        "gVisor and Firecracker fixture quantiles must stay separated",
    )

    rows = read_csv(run_dir / "summary.csv")
    row_keys = {row.get("runtime_key") for row in rows}
    require(row_keys == set(expected_runtimes), f"aggregate CSV runtime keys are {row_keys!r}, expected {set(expected_runtimes)!r}")
    for key in expected_runtimes:
        runtime_rows = [row for row in rows if row.get("runtime_key") == key]
        pod_rows = [row for row in runtime_rows if row.get("metric_category") == "pod_latency"]
        kubelet_rows = [row for row in runtime_rows if row.get("metric_category") == "kubelet_metric"]
        for field in ["node_pool", "vm_sku", "kernel_version", "containerd_version", "kubelet_version", "kata_version"]:
            require(field in rows[0], f"aggregate CSV must include environment metadata column {field!r}")
        require(len(pod_rows) == 5, f"aggregate CSV runtime {key!r} must include 5 pod latency rows")
        actual_families = {row.get("metric_family") for row in kubelet_rows}
        require(
            actual_families == required_kubelet_metric_families,
            f"aggregate CSV runtime {key!r} kubelet metric families are {actual_families!r}, expected {required_kubelet_metric_families!r}",
        )
        for row in kubelet_rows:
            for quantile in ["p50", "p95", "p99"]:
                require(row.get(quantile), f"aggregate CSV runtime {key!r} kubelet metric row must include {quantile}")


def assert_runtime_manifest(path, expected_runtimes):
    manifest = read_json(path)
    runtimes = manifest.get("runtimes")
    require(isinstance(runtimes, list), f"{path} must contain a runtimes array")
    actual = {runtime.get("key"): runtime.get("runtimeClass") for runtime in runtimes}
    require(actual == expected_runtimes, f"runtime manifest is {actual!r}, expected {expected_runtimes!r}")


def assert_environment_metadata(path, expected_runtimes):
    metadata = read_json(path)
    require(
        metadata.get("schemaVersion") == "runtimeclass-benchmark-environment/v1",
        f"{path} must declare the environment metadata schema version",
    )
    require(isinstance(metadata.get("capturedAt"), str) and metadata.get("capturedAt"), f"{path} must include capturedAt")
    require("cluster" not in metadata, f"{path} must not include cluster metadata")
    require(isinstance(metadata.get("metadataSources"), dict), f"{path} must include metadataSources")
    require(
        metadata["metadataSources"].get("kubeletVersion") == "kubernetes node status nodeInfo.kubeletVersion",
        f"{path} must document kubeletVersion metadata source",
    )
    require(
        metadata.get("runtimeNodePools") == {
            "standard": "sys",
            "kata": "kata",
            "kata-optimized": "kata",
            "gvisor": "gvisor",
            "firecracker": "firecracker",
        },
        f"{path} runtimeNodePools must map default runtimes to node pools",
    )
    require(set(metadata.get("runtimeNodePools", {})) == set(expected_runtimes), f"{path} must map every runtime")
    require(isinstance(metadata.get("nodePools"), list), f"{path} must include nodePools")
    require(isinstance(metadata.get("warnings"), list), f"{path} must include warnings")


def assert_prometheus_inputs(manifest_path, metrics_profile_path, source_config_text, rendered_config_text, expected_endpoint):
    required_metric_families = [
        "kubelet_run_podsandbox_duration_seconds",
        "kubelet_pod_start_sli_duration_seconds",
        "kubelet_pod_start_total_duration_seconds",
    ]

    require(manifest_path.is_file(), f"missing file: {manifest_path}")
    manifest_text = manifest_path.read_text(encoding="utf-8")
    for expected in [
        "kind: Namespace",
        "kind: ServiceAccount",
        "kind: ClusterRole",
        "kind: ClusterRoleBinding",
        "kind: ConfigMap",
        "kind: Deployment",
        "kind: Service",
        "mcr.microsoft.com/oss/v2/prometheus/prometheus:v3.11.3",
        "kubernetes_sd_configs:",
        "role: node",
        "metrics_path: /metrics",
        "metrics_path: /metrics/cadvisor",
        "bearer_token_file:",
        "__PROMETHEUS_SYSTEM_NODE_SELECTOR_KEY__",
        "__PROMETHEUS_SYSTEM_NODE_SELECTOR_VALUE__",
    ]:
        require(expected in manifest_text, f"Prometheus manifest must include {expected!r}")
    for forbidden_resource in ["services", "endpoints", "pods"]:
        require(f"- {forbidden_resource}" not in manifest_text, f"Prometheus RBAC must not grant {forbidden_resource}")
    for family in required_metric_families:
        require(family in manifest_text, f"Prometheus manifest must retain {family}")
    require("machine_info" in manifest_text, "Prometheus manifest must retain machine_info for kernel metadata")
    require("_bucket|_sum|_count" in manifest_text, "Prometheus relabeling must retain histogram bucket/sum/count series")

    require(metrics_profile_path.is_file(), f"missing file: {metrics_profile_path}")
    metrics_profile_text = metrics_profile_path.read_text(encoding="utf-8")
    for family in required_metric_families:
        require(family in metrics_profile_text, f"kube-burner metrics profile must query {family}")
    require("machine_info" in metrics_profile_text, "kube-burner metrics profile must query machine_info")

    require("__PROMETHEUS_ENDPOINT__" in source_config_text, "static suite config must include the Prometheus endpoint placeholder")
    require("__PROMETHEUS_METRICS_CONFIG__" in source_config_text, "static suite config must include the Prometheus metrics profile placeholder")
    require("__PROMETHEUS_ENDPOINT__" not in rendered_config_text, "prepared config must replace the Prometheus endpoint placeholder")
    require("__PROMETHEUS_METRICS_CONFIG__" not in rendered_config_text, "prepared config must replace the Prometheus metrics profile placeholder")
    require(expected_endpoint in rendered_config_text, "prepared config must include the configured Prometheus endpoint")
    expected_metrics_paths = {str(metrics_profile_path), str(metrics_profile_path.resolve())}
    require(
        any(path in rendered_config_text for path in expected_metrics_paths),
        "prepared config must include the Prometheus metrics profile path",
    )
    require("type: local" in rendered_config_text, "prepared config must preserve local metrics output")


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark baseline dry-run and summary outputs")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pod-template", type=Path, default=Path("templates/runtimeclass-pod.yml"))
    parser.add_argument("--suite-config", type=Path, default=Path("configs/kube-burner-runtimeclass-suite.yml"))
    parser.add_argument("--source-manifest", type=Path, default=Path("configs/runtime-manifest.json"))
    parser.add_argument("--prometheus-manifest", type=Path, default=Path("manifests/prometheus/prometheus.yml"))
    parser.add_argument("--prometheus-metrics-profile", type=Path, default=Path("configs/kubelet-startup-metrics.yml"))
    parser.add_argument("--prometheus-endpoint", default="http://127.0.0.1:9090")
    args = parser.parse_args()

    run_dir = args.output_dir / args.run_id
    expected_runtimes = {
        "standard": "standard",
        "kata": "kata-vm-isolation",
        "kata-optimized": "kata-optimized",
        "gvisor": "gvisor",
        "firecracker": "kata-fc",
    }
    runtime_dirs = {key: run_dir / "runs" / key for key in expected_runtimes}

    require(not any(path.exists() for path in runtime_dirs.values()), "suite benchmark must not create per-runtime result directories")

    rendered_config = run_dir / "kube-burner.yml"
    runtime_manifest = run_dir / "runtime-manifest.json"
    environment_metadata = run_dir / "environment-metadata.json"
    require(args.suite_config.is_file(), f"missing file: {args.suite_config}")
    require(args.source_manifest.is_file(), f"missing file: {args.source_manifest}")
    require(rendered_config.is_file(), f"missing file: {rendered_config}")
    require(runtime_manifest.is_file(), f"missing file: {runtime_manifest}")
    require(environment_metadata.is_file(), f"missing file: {environment_metadata}")
    source_config_text = args.suite_config.read_text(encoding="utf-8")
    require("__METRICS_DIR__" in source_config_text, "static suite config must include the metrics directory placeholder")
    config_text = rendered_config.read_text(encoding="utf-8")
    require("__METRICS_DIR__" not in config_text, "prepared config must replace the metrics directory placeholder")
    require(str(run_dir / "raw") in config_text, "prepared config must include the run raw metrics directory")
    require("name: runtimeclass-pod-latency-standard" in config_text, "config must include standard job")
    require("name: runtimeclass-pod-latency-kata" in config_text, "config must include Kata job")
    require("name: runtimeclass-pod-latency-kata-optimized" in config_text, "config must include optimized Kata job")
    require("name: runtimeclass-pod-latency-gvisor" in config_text, "config must include gVisor job")
    require("name: runtimeclass-pod-latency-firecracker" in config_text, "config must include Firecracker job")
    require(
        config_text.count("metricsClosing: afterJobPause") >= 5,
        "runtime jobs must close Prometheus metrics after jobPause",
    )
    require(
        config_text.count("jobPause: 20s") >= 5,
        "runtime jobs must pause long enough for at least one Prometheus scrape before closing metrics",
    )
    require('runtimeClass: ""' in config_text, "standard job must leave runtimeClass empty")
    require('runtimeClass: "kata-vm-isolation"' in config_text, "Kata job must include runtimeClass")
    require('runtimeClass: "kata-optimized"' in config_text, "optimized Kata job must include runtimeClass")
    require('runtimeClass: "gvisor"' in config_text, "gVisor job must include runtimeClass")
    require('runtimeClass: "kata-fc"' in config_text, "Firecracker job must include runtimeClass")
    require(config_text.count('runtimeclass: "kata"') >= 2, "Kata jobs must include node selectors")
    require('runtimeclass: "gvisor"' in config_text, "gVisor job must include node selector")
    require('runtimeclass: "firecracker"' in config_text, "Firecracker job must include node selector")
    require(config_text.count('key: "runtimeclass"') >= 4, "runtime jobs must include tolerations")
    require("runtimeClassName" not in config_text, "rendered config should not contain pod runtimeClassName directly")

    assert_prometheus_inputs(
        args.prometheus_manifest,
        args.prometheus_metrics_profile,
        source_config_text,
        config_text,
        args.prometheus_endpoint,
    )

    assert_runtime_manifest(args.source_manifest, expected_runtimes)
    assert_runtime_manifest(runtime_manifest, expected_runtimes)
    assert_environment_metadata(environment_metadata, expected_runtimes)

    template_text = args.pod_template.read_text(encoding="utf-8")
    require(
        "{{- if .runtimeClass }}\n  runtimeClassName:" in template_text,
        "pod template must guard runtimeClassName behind .runtimeClass",
    )

    assert_aggregate_summary(run_dir, expected_runtimes)


if __name__ == "__main__":
    main()
