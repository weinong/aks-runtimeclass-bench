#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys


def parse_bool(name, default):
    value = os.environ.get(name, default)
    return str(value).lower() in {"1", "true", "yes", "on"}


def parse_selector(value, name="NODE_SELECTOR"):
    result = {}
    value = value.strip()
    if not value:
        return result
    for item in re.split(r"[\s,]+", value):
        if not item.strip():
            continue
        if "=" not in item:
            raise SystemExit(f"{name} item must be key=value: {item}")
        key, selector_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"{name} contains an empty key")
        result[key] = selector_value.strip()
    return result


def parse_json_array(name, default="[]"):
    raw = os.environ.get(name, default) or "[]"
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


def runtime_slug(value):
    slug = re.sub(r"[^a-z0-9-]", "-", (value or "standard").lower()).strip("-")
    if not slug:
        raise SystemExit(f"runtime key {value!r} does not contain any DNS-safe characters")
    return slug


def env_prefix_for_key(key):
    return re.sub(r"[^A-Za-z0-9]", "_", key).upper()


def default_tolerations(runtime_value):
    return [
        {
            "key": "runtimeclass",
            "operator": "Equal",
            "value": runtime_value,
            "effect": "NoSchedule",
        }
    ]


def runtime_entry(key):
    if key == "standard":
        return {
            "key": key,
            "runtimeClass": "",
            "runtimeLabel": "standard",
            "nodeSelector": parse_selector(os.environ.get("BASELINE_NODE_SELECTOR", ""), "BASELINE_NODE_SELECTOR"),
            "tolerations": parse_json_array("BASELINE_TOLERATIONS_JSON"),
        }
    if key == "kata":
        return {
            "key": key,
            "runtimeClass": os.environ.get("KATA_RUNTIME_CLASS", "kata-vm-isolation"),
            "runtimeLabel": os.environ.get("KATA_RUNTIME_CLASS", "kata-vm-isolation"),
            "nodeSelector": parse_selector(os.environ.get("KATA_NODE_LABELS", "runtimeclass=kata"), "KATA_NODE_LABELS"),
            "tolerations": parse_json_array("KATA_TOLERATIONS_JSON", json.dumps(default_tolerations("kata"))),
        }
    if key == "gvisor":
        return {
            "key": key,
            "runtimeClass": os.environ.get("GVISOR_RUNTIME_CLASS", "gvisor"),
            "runtimeLabel": os.environ.get("GVISOR_RUNTIME_CLASS", "gvisor"),
            "nodeSelector": parse_selector(os.environ.get("GVISOR_NODE_LABELS", "runtimeclass=gvisor"), "GVISOR_NODE_LABELS"),
            "tolerations": parse_json_array("GVISOR_TOLERATIONS_JSON", json.dumps(default_tolerations("gvisor"))),
        }
    if key == "firecracker":
        return {
            "key": key,
            "runtimeClass": os.environ.get("FIRECRACKER_RUNTIME_CLASS", "firecracker"),
            "runtimeLabel": os.environ.get("FIRECRACKER_RUNTIME_CLASS", "firecracker"),
            "nodeSelector": parse_selector(os.environ.get("FIRECRACKER_NODE_LABELS", "runtimeclass=firecracker"), "FIRECRACKER_NODE_LABELS"),
            "tolerations": parse_json_array("FIRECRACKER_TOLERATIONS_JSON", json.dumps(default_tolerations("firecracker"))),
        }
    if key == "custom":
        runtime_class = os.environ.get("RUNTIME_CLASS", "")
        return {
            "key": key,
            "runtimeClass": runtime_class,
            "runtimeLabel": runtime_class or "standard",
            "nodeSelector": parse_selector(os.environ.get("NODE_SELECTOR", ""), "NODE_SELECTOR"),
            "tolerations": parse_json_array("TOLERATIONS_JSON"),
        }

    prefix = env_prefix_for_key(key)
    runtime_class = os.environ.get(f"{prefix}_RUNTIME_CLASS", key)
    selector = os.environ.get(f"{prefix}_NODE_SELECTOR")
    if selector is None:
        selector = os.environ.get(f"{prefix}_NODE_LABELS", f"runtimeclass={key}")
    return {
        "key": key,
        "runtimeClass": runtime_class,
        "runtimeLabel": runtime_class or "standard",
        "nodeSelector": parse_selector(selector, f"{prefix}_NODE_SELECTOR"),
        "tolerations": parse_json_array(f"{prefix}_TOLERATIONS_JSON", json.dumps(default_tolerations(key))),
    }


def runtime_entries():
    keys = [runtime_slug(item) for item in os.environ.get("BENCHMARK_RUNTIMES", "standard kata").split()]
    if not keys:
        raise SystemExit("BENCHMARK_RUNTIMES must include at least one runtime key")

    seen = set()
    entries = []
    for key in keys:
        if key in seen:
            raise SystemExit(f"duplicate benchmark runtime key: {key}")
        seen.add(key)
        entries.append(runtime_entry(key))
    return entries


def validate_tolerations(entries):
    for entry in entries:
        for toleration in entry["tolerations"]:
            if not isinstance(toleration, dict):
                raise SystemExit(f"toleration entries for runtime {entry['key']} must be objects")
            toleration.setdefault("operator", "Equal")
            toleration.setdefault("effect", "NoSchedule")


def write_job(out, entry, data):
    key = entry["key"]
    out.append(f"  - name: runtimeclass-pod-latency-{key}")
    out.append(f"    jobIterations: {data['podCount']}")
    out.append(f"    qps: {data['qps']}")
    out.append(f"    burst: {data['burst']}")
    out.append(f"    namespace: {scalar(data['namespace'] + '-' + key)}")
    out.append("    namespacedIterations: false")
    out.append(f"    cleanup: {scalar(data['cleanup'])}")
    out.append(f"    waitWhenFinished: {scalar(data['waitWhenFinished'])}")
    out.append(f"    podWait: {scalar(data['podWait'])}")
    out.append("    objects:")
    out.append(f"      - objectTemplate: {scalar(data['podTemplatePath'])}")
    out.append(f"        replicas: {data['podReplicas']}")
    out.append("        inputVars:")
    out.append(f"          runtimeKey: {scalar(key)}")
    out.append(f"          runtimeClass: {scalar(entry['runtimeClass'])}")
    out.append(f"          containerImage: {scalar(data['podImage'])}")
    out.append("          command:")
    write_list(out, data["podCommand"], 12)
    out.append(f"          cpuRequest: {scalar(data['podCpuRequest'])}")
    out.append(f"          memoryRequest: {scalar(data['podMemoryRequest'])}")
    out.append(f"          cpuLimit: {scalar(data['podCpuLimit'])}")
    out.append(f"          memoryLimit: {scalar(data['podMemoryLimit'])}")
    out.append("          nodeSelector:")
    write_mapping(out, entry["nodeSelector"], 12)
    out.append("          tolerations:")
    write_list(out, entry["tolerations"], 12)


def render_config(entries):
    pod_command = parse_json_array("POD_COMMAND_JSON")
    if any(not isinstance(item, str) for item in pod_command):
        raise SystemExit("POD_COMMAND_JSON must be a JSON array of strings")

    data = {
        "metricsDirectory": os.environ.get("METRICS_DIR", "results/validation/raw"),
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
        "podImage": os.environ.get("POD_IMAGE", "mcr.microsoft.com/oss/v2/kubernetes/pause:3.10.2"),
        "podCommand": pod_command,
        "podCpuRequest": os.environ.get("POD_CPU_REQUEST", "10m"),
        "podMemoryRequest": os.environ.get("POD_MEMORY_REQUEST", "32Mi"),
        "podCpuLimit": os.environ.get("POD_CPU_LIMIT", "100m"),
        "podMemoryLimit": os.environ.get("POD_MEMORY_LIMIT", "128Mi"),
    }

    out = [
        "metricsEndpoints:",
        "  - indexer:",
        "      type: local",
        f"      metricsDirectory: {scalar(data['metricsDirectory'])}",
        "      createTarball: false",
        "global:",
        f"  gc: {scalar(data['gc'])}",
        "  measurements:",
        "    - name: podLatency",
        "jobs:",
    ]
    for entry in entries:
        write_job(out, entry, data)
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Render a kube-burner config for the runtime class suite")
    parser.add_argument("--runtime-manifest", help="Optional path to write runtime extraction metadata as JSON")
    args = parser.parse_args()

    entries = runtime_entries()
    validate_tolerations(entries)

    if args.runtime_manifest:
        manifest = [{"key": entry["key"], "runtimeClass": entry["runtimeLabel"]} for entry in entries]
        with open(args.runtime_manifest, "w", encoding="utf-8") as handle:
            json.dump({"runtimes": manifest}, handle, indent=2, sort_keys=True)
            handle.write("\n")

    sys.stdout.write(render_config(entries))


if __name__ == "__main__":
    main()
