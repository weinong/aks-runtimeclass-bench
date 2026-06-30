#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "runtimeclass-benchmark-environment/v1"
NODE_POOL_LABELS = ["kubernetes.azure.com/agentpool", "agentpool", "Agentpool"]
VM_SKU_LABELS = ["node.kubernetes.io/instance-type", "beta.kubernetes.io/instance-type", "kubernetes.azure.com/instance-sku"]
KATA_RUNTIME_KEYS = {"kata", "kata-optimized", "firecracker"}


def run_json(command, default=None, required=False, description="command"):
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except (FileNotFoundError, PermissionError) as exc:
        if required:
            raise SystemExit(f"failed to collect {description}: command not found: {command[0]}") from exc
        return default if default is not None else {}
    except subprocess.CalledProcessError as exc:
        if required:
            detail = exc.stderr.strip() or f"exit code {exc.returncode}"
            raise SystemExit(f"failed to collect {description}: {detail}") from exc
        return default if default is not None else {}
    if not result.stdout.strip():
        return default if default is not None else {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return default if default is not None else {}


def first_label(labels, names):
    for name in names:
        value = labels.get(name)
        if isinstance(value, str) and value:
            return value
    return None


def runtime_entries(runtime_manifest):
    entries = runtime_manifest.get("runtimes") if isinstance(runtime_manifest, dict) else None
    return entries if isinstance(entries, list) else []


def kernel_versions_by_node(machine_info):
    versions = {}
    result = ((machine_info or {}).get("data") or {}).get("result")
    if not isinstance(result, list):
        return versions
    for item in result:
        if not isinstance(item, dict):
            continue
        metric = item.get("metric")
        if not isinstance(metric, dict):
            continue
        node = first_label(metric, ["node", "nodename", "instance"])
        kernel = first_label(metric, ["kernel_version", "kernelVersion"])
        if node and kernel:
            versions[node] = kernel
    return versions


def append_unique(values, value):
    if value is not None and value not in values:
        values.append(value)


def first_observed(values):
    return values[0] if values else None


def collect_node_pools(nodes, machine_info, kata_versions):
    kernel_by_node = kernel_versions_by_node(machine_info)
    pools = {}
    warnings = []
    for node in nodes.get("items", []) if isinstance(nodes, dict) else []:
        if not isinstance(node, dict):
            continue
        metadata = node.get("metadata") or {}
        labels = metadata.get("labels") or {}
        node_name = metadata.get("name")
        pool_name = first_label(labels, NODE_POOL_LABELS) or "unknown"
        pool = pools.setdefault(
            pool_name,
            {
                "name": pool_name,
                "vmSku": None,
                "kernelVersion": None,
                "containerdVersion": None,
                "kubeletVersion": None,
                "kataVersion": kata_versions.get(pool_name),
                "nodes": [],
                "_vmSkuValues": [],
                "_kernelVersionValues": [],
                "_containerdVersionValues": [],
                "_kubeletVersionValues": [],
                "_kubeletVersionMissing": 0,
            },
        )
        if isinstance(node_name, str) and node_name:
            pool["nodes"].append(node_name)
        append_unique(pool["_vmSkuValues"], first_label(labels, VM_SKU_LABELS))
        if node_name:
            append_unique(pool["_kernelVersionValues"], kernel_by_node.get(node_name))
        node_info = (node.get("status") or {}).get("nodeInfo") or {}
        runtime_version = node_info.get("containerRuntimeVersion")
        append_unique(pool["_containerdVersionValues"], runtime_version if isinstance(runtime_version, str) and runtime_version else None)
        kubelet_version = node_info.get("kubeletVersion")
        if isinstance(kubelet_version, str) and kubelet_version:
            append_unique(pool["_kubeletVersionValues"], kubelet_version)
        else:
            pool["_kubeletVersionMissing"] += 1

    for pool in pools.values():
        pool["nodes"].sort()
        for output_name, scratch_name, label in [
            ("vmSku", "_vmSkuValues", "VM SKU"),
            ("kernelVersion", "_kernelVersionValues", "kernel version"),
            ("containerdVersion", "_containerdVersionValues", "containerd version"),
            ("kubeletVersion", "_kubeletVersionValues", "kubelet version"),
        ]:
            values = pool.pop(scratch_name)
            pool[output_name] = first_observed(values)
            if len(values) > 1:
                warnings.append(f"node pool {pool['name']}: multiple {label} values observed: {', '.join(values)}")
        if pool["vmSku"] is None:
            warnings.append(f"node pool {pool['name']}: VM SKU unavailable from node labels")
        if pool["kernelVersion"] is None:
            warnings.append(f"node pool {pool['name']}: kernel version unavailable from Prometheus machine_info")
        if pool["containerdVersion"] is None:
            warnings.append(f"node pool {pool['name']}: containerd version unavailable from Kubernetes node status")
        missing_kubelet_versions = pool.pop("_kubeletVersionMissing")
        if pool["kubeletVersion"] is None:
            warnings.append(f"node pool {pool['name']}: kubelet version unavailable from Kubernetes node status")
        elif missing_kubelet_versions:
            warnings.append(f"node pool {pool['name']}: kubelet version unavailable for {missing_kubelet_versions} node(s)")
    return sorted(pools.values(), key=lambda item: item["name"]), warnings


def default_runtime_node_pool_names(runtime_manifest):
    names = {}
    for runtime in runtime_entries(runtime_manifest):
        key = runtime.get("key") if isinstance(runtime, dict) else None
        if isinstance(key, str) and key:
            names[key] = "kataopt" if key == "kata-optimized" else key
    return names


def build_environment_metadata(nodes, machine_info, runtime_manifest, captured_at, runtime_node_pool_names, kata_versions):
    node_pools, warnings = collect_node_pools(nodes, machine_info, kata_versions)
    pool_by_name = {pool["name"]: pool for pool in node_pools}
    for runtime in runtime_entries(runtime_manifest):
        key = runtime.get("key") if isinstance(runtime, dict) else None
        if not isinstance(key, str):
            continue
        pool_name = runtime_node_pool_names.get(key)
        if pool_name and pool_name not in pool_by_name:
            warnings.append(f"runtime {key}: mapped node pool {pool_name} was not observed")
        if key not in KATA_RUNTIME_KEYS:
            continue
        pool = pool_by_name.get(pool_name)
        if pool is not None and pool.get("kataVersion") is None:
            warnings.append(f"runtime {key}: Kata runtime version unavailable")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "capturedAt": captured_at,
        "metadataSources": {
            "nodePool": "Kubernetes node labels: " + ", ".join(NODE_POOL_LABELS),
            "vmSku": "Kubernetes node labels: " + ", ".join(VM_SKU_LABELS),
            "kernelVersion": "Prometheus machine_info kernel_version label",
            "containerdVersion": "Kubernetes node status nodeInfo.containerRuntimeVersion",
            "kubeletVersion": "kubernetes node status nodeInfo.kubeletVersion",
            "kataVersion": "runtime-specific inspection when available",
        },
        "runtimeNodePools": runtime_node_pool_names,
        "nodePools": node_pools,
        "warnings": sorted(set(warnings)),
    }


def load_json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def kubectl_base_args(kubeconfig, context):
    args = ["kubectl"]
    if kubeconfig:
        args.extend(["--kubeconfig", kubeconfig])
    if context:
        args.extend(["--context", context])
    return args


def capture_machine_info(prometheus_endpoint):
    if not prometheus_endpoint:
        return {}
    import urllib.parse
    import urllib.request

    query = urllib.parse.urlencode({"query": "machine_info"})
    try:
        with urllib.request.urlopen(f"{prometheus_endpoint.rstrip('/')}/api/v1/query?{query}", timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return {}


def parse_key_value_map(values):
    result = {}
    for item in values or []:
        if "=" not in item:
            raise SystemExit(f"expected KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description="Capture benchmark environment metadata")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--prometheus-endpoint", default="")
    parser.add_argument("--runtime-node-pool", action="append", default=[], help="Runtime to node pool mapping as runtimeKey=nodePool")
    parser.add_argument("--kata-version", action="append", default=[], help="Kata runtime version as nodePool=version")
    parser.add_argument("--kubeconfig", default="")
    parser.add_argument("--kube-context", default="")
    args = parser.parse_args()

    runtime_manifest = load_json_file(args.runtime_manifest)
    runtime_node_pool_names = default_runtime_node_pool_names(runtime_manifest)
    runtime_node_pool_names.update(parse_key_value_map(args.runtime_node_pool))
    kata_versions = parse_key_value_map(args.kata_version)
    base = kubectl_base_args(args.kubeconfig, args.kube_context)
    nodes = run_json(base + ["get", "nodes", "-o", "json"], default={"items": []}, required=True, description="Kubernetes nodes")
    metadata = build_environment_metadata(
        nodes,
        capture_machine_info(args.prometheus_endpoint),
        runtime_manifest,
        datetime.now(timezone.utc).isoformat(),
        runtime_node_pool_names,
        kata_versions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
