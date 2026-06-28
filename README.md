# AKS Runtime Class Benchmark

This repository provisions an AKS cluster shape for runtime class benchmarking, generates a kube-burner suite config, runs a pod startup workload, and extracts pod latency quantiles into JSON and CSV summaries.

## Prerequisites

- `make`, `bash`, `python3`, `curl`, `tar`, and either `sha256sum` or `shasum` for local validation and tool installation.
- Azure CLI logged in with access to the target subscription.
- `kubectl` for credential validation and benchmark execution.
- Azure permissions to create resource groups, AKS clusters, node pools, and to fetch AKS credentials. Contributor on the benchmark resource group or equivalent scoped permissions is sufficient for the default workflow.
- AKS pod sandboxing support for Kata runtime benchmarks. Public AKS pod sandboxing requires Kubernetes 1.27 or newer, Azure Linux node pools, and a Generation 2 VM size that supports nested virtualization. The default `VM_SIZE=Standard_D8s_v5` satisfies the suite's 8 vCPU minimum, but operators must confirm regional quota and feature availability.
- Runtime support for gVisor and Firecracker in the target environment. Their AKS CLI flags are intentionally configurable through `GVISOR_NODEPOOL_EXTRA_ARGS` and `FIRECRACKER_NODEPOOL_EXTRA_ARGS` because support can be private, preview, or environment-specific.

## Basic Workflow

```bash
make validate
make cluster-create RESOURCE_GROUP=rg-aks-rc-bench CLUSTER_NAME=aks-rc-bench LOCATION=eastus
make kube-burner-install
make benchmark
make cluster-delete RESOURCE_GROUP=rg-aks-rc-bench CLUSTER_NAME=aks-rc-bench
```

Use `make benchmark-dry-run` to render the kube-burner suite config and print the kube-burner command without contacting a cluster. By default, `make benchmark` runs the standard runtime baseline plus the configured Kata runtime entry in one kube-burner invocation.

## Important Make Variables

Azure lifecycle variables:

- `AZURE_SUBSCRIPTION`: Optional subscription ID or name passed to `az account set`.
- `RESOURCE_GROUP`: Benchmark resource group. Default: `rg-aks-runtimeclass-bench`.
- `CLUSTER_NAME`: Benchmark AKS cluster name. Default: `aks-runtimeclass-bench`.
- `LOCATION`: Azure region. Default: `eastus`.
- `VM_SIZE`: VM size for all node pools. Must validate to at least 8 vCPUs before provisioning. Default: `Standard_D8s_v5`.
- `KUBERNETES_VERSION`: Optional AKS Kubernetes version.
- `CLUSTER_EXTRA_ARGS`: Optional extra words appended to `az aks create` or `az aks update`.
- `TEARDOWN_SCOPE`: `cluster` deletes only the AKS cluster; `resource-group` deletes the whole resource group. Default: `cluster`.

Node pool variables:

- `SYSTEM_NODEPOOL_NAME`: System node pool name. Default: `sys`; node count is fixed at 2.
- `KATA_NODEPOOL_NAME`, `GVISOR_NODEPOOL_NAME`, `FIRECRACKER_NODEPOOL_NAME`: Runtime node pool names; node count is fixed at 1 each.
- `KATA_NODE_LABELS`, `GVISOR_NODE_LABELS`, `FIRECRACKER_NODE_LABELS`: Space-separated labels applied to runtime pools.
- `KATA_NODE_TAINTS`, `GVISOR_NODE_TAINTS`, `FIRECRACKER_NODE_TAINTS`: Space-separated taints applied to runtime pools. Set to empty to disable taints.
- `KATA_NODEPOOL_EXTRA_ARGS`, `GVISOR_NODEPOOL_EXTRA_ARGS`, `FIRECRACKER_NODEPOOL_EXTRA_ARGS`: Extra words appended to each runtime `az aks nodepool add` command. Kata defaults to `--workload-runtime KataVmIsolation`.

kube-burner and workload variables:

- `KUBE_BURNER_VERSION`: Release tag installed under `tools/`. Default: `v2.7.3`.
- `BENCHMARK_RUNTIMES`: Space-separated runtime keys to run. Default: `standard kata`. Built-in keys are `standard`, `kata`, `gvisor`, `firecracker`, and `custom`; additional keys can be configured with `<KEY>_RUNTIME_CLASS`, `<KEY>_NODE_SELECTOR` or `<KEY>_NODE_LABELS`, and `<KEY>_TOLERATIONS_JSON`.
- `BASELINE_NODE_SELECTOR`: Optional comma-separated `key=value` selector for the automatic standard-runtime baseline. Default: empty.
- `BASELINE_TOLERATIONS_JSON`: Optional JSON array of tolerations for the automatic standard-runtime baseline. Default: `[]`.
- `KATA_TOLERATIONS_JSON`, `GVISOR_TOLERATIONS_JSON`, `FIRECRACKER_TOLERATIONS_JSON`: Optional JSON arrays for runtime benchmark tolerations. Defaults match the corresponding `runtimeclass=<runtime>:NoSchedule` taints.
- `RUNTIME_CLASS`, `NODE_SELECTOR`, `TOLERATIONS_JSON`: Runtime class, selector, and tolerations used by the `custom` runtime key when `BENCHMARK_RUNTIMES` includes `custom`.
- `POD_COUNT`: kube-burner job iterations. Default: `50`.
- `POD_REPLICAS`: Replicas per iteration. Default: `1`.
- `POD_IMAGE`: Container image. Default: `mcr.microsoft.com/oss/v2/kubernetes/pause:3.10.2`.
- `POD_COMMAND_JSON`: Optional JSON string array for container command.
- `POD_CPU_REQUEST`, `POD_MEMORY_REQUEST`, `POD_CPU_LIMIT`, `POD_MEMORY_LIMIT`: Pod resource settings.
- `BENCHMARK_NAMESPACE`, `BENCHMARK_QPS`, `BENCHMARK_BURST`, `BENCHMARK_CLEANUP`, `BENCHMARK_WAIT_WHEN_FINISHED`, `BENCHMARK_POD_WAIT`, `BENCHMARK_TIMEOUT`: kube-burner job settings.
- `OUTPUT_DIR`: Result root. Default: `results`.
- `RUN_ID`: Benchmark UUID and per-run directory name. Defaults to a UTC timestamp.
- `CSV_OUTPUT`: Set to `false` to skip CSV summary output.

## Result Files

Each benchmark invocation writes one result root under `results/<RUN_ID>`. The generated kube-burner config contains one job per runtime key and writes raw metrics under `results/<RUN_ID>/raw`.

The default runtime keys are:

- `standard`: Automatic standard-runtime baseline with no `runtimeClassName`.
- `kata`: Kata runtime benchmark using `KATA_RUNTIME_CLASS`, `KATA_NODE_LABELS`, and `KATA_TOLERATIONS_JSON`.

Additional available runtime keys are:

- `gvisor`: gVisor runtime benchmark using `GVISOR_RUNTIME_CLASS`, `GVISOR_NODE_LABELS`, and `GVISOR_TOLERATIONS_JSON`.
- `firecracker`: Firecracker runtime benchmark using `FIRECRACKER_RUNTIME_CLASS`, `FIRECRACKER_NODE_LABELS`, and `FIRECRACKER_TOLERATIONS_JSON`.

- `summary.json`: Aggregate run metadata and required pod latency quantiles for every runtime entry.
- `summary.csv`: Aggregate rows for `run_id`, `runtime_key`, `runtime_class`, `condition`, `p50`, `p95`, and `p99` when `CSV_OUTPUT=true`.
- `kube-burner.yml`: Rendered kube-burner suite config for the invocation.
- `runtime-manifest.json`: Runtime keys and summary labels used by the extractor.
- `raw/`: kube-burner local metrics output.

The extractor fails if any required condition or P50/P95/P99 value is missing.

## Manual End-to-End Verification

1. Run `make validate` and confirm the extractor creates `results/validation/summary.json` and `results/validation/summary.csv` from fixture metrics.
2. Run `make cluster-create` with the target Azure settings. Confirm the command completes and `az aks nodepool list --resource-group <rg> --cluster-name <cluster> --query '[].{name:name,count:count}'` reports `sys=2`, `kata=1`, `gvisor=1`, and `firecracker=1` unless you overrode node pool names.
3. Run `make kube-burner-install` and confirm `tools/bin/kube-burner version` works.
4. Run `make benchmark`.
5. Confirm `results/<RUN_ID>/summary.json`, `results/<RUN_ID>/summary.csv`, and `results/<RUN_ID>/kube-burner.yml` exist, and that the summaries contain all five required pod latency conditions and P50/P95/P99 values for each runtime key.
6. Run `make cluster-delete` with the same resource variables. Use `TEARDOWN_SCOPE=resource-group` only when the resource group is dedicated to the benchmark.
