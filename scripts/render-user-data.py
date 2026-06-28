#!/usr/bin/env python3
import json
import os
import sys


def parse_bool(name, default):
    value = os.environ.get(name, default)
    return str(value).lower() in {"1", "true", "yes", "on"}


def parse_selector(value):
    result = {}
    value = value.strip()
    if not value:
        return result
    for item in value.split(","):
        if not item.strip():
            continue
        if "=" not in item:
            raise SystemExit(f"NODE_SELECTOR item must be key=value: {item}")
        key, selector_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit("NODE_SELECTOR contains an empty key")
        result[key] = selector_value.strip()
    return result


def parse_json_array(name):
    raw = os.environ.get(name, "[]") or "[]"
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{name} must be a JSON array: {exc}") from exc
    if not isinstance(value, list):
        raise SystemExit(f"{name} must be a JSON array")
    return value


def scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if value is None:
        return "null"
    return json.dumps(str(value))


def write_mapping(out, mapping, indent):
    prefix = " " * indent
    if not mapping:
        out.append(f"{prefix}{{}}")
        return
    for key in sorted(mapping):
        out.append(f"{prefix}{key}: {scalar(mapping[key])}")


def write_list(out, values, indent):
    prefix = " " * indent
    if not values:
        out.append(f"{prefix}[]")
        return
    for value in values:
        if isinstance(value, dict):
            out.append(f"{prefix}-")
            for key in sorted(value):
                out.append(f"{prefix}  {key}: {scalar(value[key])}")
        else:
            out.append(f"{prefix}- {scalar(value)}")


def main():
    tolerations = parse_json_array("TOLERATIONS_JSON")
    for toleration in tolerations:
        if not isinstance(toleration, dict):
            raise SystemExit("TOLERATIONS_JSON entries must be objects")
        toleration.setdefault("operator", "Equal")
        toleration.setdefault("effect", "NoSchedule")

    pod_command = parse_json_array("POD_COMMAND_JSON")
    if any(not isinstance(item, str) for item in pod_command):
        raise SystemExit("POD_COMMAND_JSON must be a JSON array of strings")

    data = {
        "metricsDirectory": os.environ.get("METRICS_DIR", os.path.join(os.environ.get("RUN_OUTPUT_DIR", "results/validation"), "raw")),
        "gc": parse_bool("BENCHMARK_CLEANUP", "true"),
        "podCount": int(os.environ.get("POD_COUNT", "50")),
        "qps": int(os.environ.get("BENCHMARK_QPS", "20")),
        "burst": int(os.environ.get("BENCHMARK_BURST", "20")),
        "namespace": os.environ.get("BENCHMARK_NAMESPACE", "runtimeclass-bench"),
        "cleanup": parse_bool("BENCHMARK_CLEANUP", "true"),
        "waitWhenFinished": parse_bool("BENCHMARK_WAIT_WHEN_FINISHED", "true"),
        "podWait": parse_bool("BENCHMARK_POD_WAIT", "true"),
        "podTemplatePath": os.environ.get("POD_TEMPLATE", "templates/runtimeclass-pod.yml"),
        "podReplicas": int(os.environ.get("POD_REPLICAS", "1")),
        "runtimeClass": os.environ.get("RUNTIME_CLASS", ""),
        "podImage": os.environ.get("POD_IMAGE", "registry.k8s.io/pause:3.10"),
        "podCommand": pod_command,
        "podCpuRequest": os.environ.get("POD_CPU_REQUEST", "10m"),
        "podMemoryRequest": os.environ.get("POD_MEMORY_REQUEST", "32Mi"),
        "podCpuLimit": os.environ.get("POD_CPU_LIMIT", "100m"),
        "podMemoryLimit": os.environ.get("POD_MEMORY_LIMIT", "128Mi"),
        "nodeSelector": parse_selector(os.environ.get("NODE_SELECTOR", "")),
        "tolerations": tolerations,
    }

    out = []
    for key in [
        "metricsDirectory",
        "gc",
        "podCount",
        "qps",
        "burst",
        "namespace",
        "cleanup",
        "waitWhenFinished",
        "podWait",
        "podTemplatePath",
        "podReplicas",
        "runtimeClass",
        "podImage",
        "podCpuRequest",
        "podMemoryRequest",
        "podCpuLimit",
        "podMemoryLimit",
    ]:
        out.append(f"{key}: {scalar(data[key])}")
    out.append("podCommand:")
    write_list(out, data["podCommand"], 2)
    out.append("nodeSelector:")
    write_mapping(out, data["nodeSelector"], 2)
    out.append("tolerations:")
    write_list(out, data["tolerations"], 2)
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
