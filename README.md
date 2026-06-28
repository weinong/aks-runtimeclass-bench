# AKS Runtime Class Benchmark

This repository provisions an AKS cluster shape for runtime class benchmarking, runs a static kube-burner suite config, and extracts pod latency quantiles into JSON and CSV summaries.

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

Use `make benchmark-dry-run` to prepare the result-local kube-burner suite config and print the kube-burner command without contacting a cluster. By default, `make benchmark` runs the checked-in static suite from `configs/kube-burner-runtimeclass-suite.yml`, which includes the standard runtime baseline plus the Kata runtime entry in one kube-burner invocation.

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
- `KUBE_BURNER_CONFIG`: Repo-relative static kube-burner suite config copied into each result root before execution. Default: `configs/kube-burner-runtimeclass-suite.yml`.
- `RUNTIME_MANIFEST`: Repo-relative static runtime key and label manifest copied into each result root for extraction. Default: `configs/runtime-manifest.json`.
- `BENCHMARK_TIMEOUT`: Timeout passed to `kube-burner init`. Default: `4h`.
- `OUTPUT_DIR`: Result root. Default: `results`.
- `RUN_ID`: Benchmark UUID and per-run directory name. Defaults to a UTC timestamp.
- `CSV_OUTPUT`: Set to `false` to skip CSV summary output.

## Result Files

Each benchmark invocation writes one result root under `results/<RUN_ID>`. The static kube-burner config is copied to `results/<RUN_ID>/kube-burner.yml`, with only the metrics directory placeholder replaced for that invocation. The config contains one job per runtime key and writes raw metrics under `results/<RUN_ID>/raw`.

The default runtime keys are:

- `standard`: Standard-runtime baseline with no `runtimeClassName`.
- `kata`: Kata runtime benchmark with runtime class, selector, and toleration defined in `configs/kube-burner-runtimeclass-suite.yml`.

To change runtime topology, edit both checked-in benchmark inputs together:

- Add or remove kube-burner jobs in `configs/kube-burner-runtimeclass-suite.yml`.
- Add or remove matching runtime entries in `configs/runtime-manifest.json` so the extractor expects the same runtime keys.
- Keep the `__METRICS_DIR__` placeholder in the static suite config; `make benchmark` replaces it with the run's raw metrics directory.

- `summary.json`: Aggregate run metadata and required pod latency quantiles for every runtime entry.
- `summary.csv`: Aggregate rows for `run_id`, `runtime_key`, `runtime_class`, `condition`, `p50`, `p95`, and `p99` when `CSV_OUTPUT=true`.
- `kube-burner.yml`: Static kube-burner suite config prepared for the invocation.
- `runtime-manifest.json`: Copied runtime keys and summary labels used by the extractor.
- `raw/`: kube-burner local metrics output.

The extractor fails if any required condition or P50/P95/P99 value is missing.

## Manual End-to-End Verification

1. Run `make validate` and confirm the extractor creates `results/validation/summary.json` and `results/validation/summary.csv` from fixture metrics.
2. Run `make cluster-create` with the target Azure settings. Confirm the command completes and `az aks nodepool list --resource-group <rg> --cluster-name <cluster> --query '[].{name:name,count:count}'` reports `sys=2`, `kata=1`, `gvisor=1`, and `firecracker=1` unless you overrode node pool names.
3. Run `make kube-burner-install` and confirm `tools/bin/kube-burner version` works.
4. Run `make benchmark`.
5. Confirm `results/<RUN_ID>/summary.json`, `results/<RUN_ID>/summary.csv`, and `results/<RUN_ID>/kube-burner.yml` exist, and that the summaries contain all five required pod latency conditions and P50/P95/P99 values for each runtime key.
6. Run `make cluster-delete` with the same resource variables. Use `TEARDOWN_SCOPE=resource-group` only when the resource group is dedicated to the benchmark.
