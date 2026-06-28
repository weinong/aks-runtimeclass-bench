# AKS Runtime Class Benchmark

This repository provisions an AKS cluster shape for runtime class benchmarking, runs a kube-burner pod startup workload, and extracts pod latency quantiles into JSON and CSV summaries.

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
make benchmark RUNTIME_CLASS=kata-vm-isolation NODE_SELECTOR=runtimeclass=kata TOLERATIONS_JSON='[{"key":"runtimeclass","operator":"Equal","value":"kata","effect":"NoSchedule"}]'
make cluster-delete RESOURCE_GROUP=rg-aks-rc-bench CLUSTER_NAME=aks-rc-bench
```

Use `make benchmark-dry-run` to render benchmark input and print the kube-burner command without contacting a cluster.

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
- `RUNTIME_CLASS`: Runtime class rendered into pod specs. Leave empty for standard runtime pods.
- `NODE_SELECTOR`: Comma-separated `key=value` selector used for pod placement, for example `runtimeclass=kata`.
- `TOLERATIONS_JSON`: JSON array of Kubernetes toleration objects.
- `POD_COUNT`: kube-burner job iterations. Default: `50`.
- `POD_REPLICAS`: Replicas per iteration. Default: `1`.
- `POD_IMAGE`: Container image. Default: `registry.k8s.io/pause:3.10`.
- `POD_COMMAND_JSON`: Optional JSON string array for container command.
- `POD_CPU_REQUEST`, `POD_MEMORY_REQUEST`, `POD_CPU_LIMIT`, `POD_MEMORY_LIMIT`: Pod resource settings.
- `BENCHMARK_NAMESPACE`, `BENCHMARK_QPS`, `BENCHMARK_BURST`, `BENCHMARK_CLEANUP`, `BENCHMARK_WAIT_WHEN_FINISHED`, `BENCHMARK_POD_WAIT`, `BENCHMARK_TIMEOUT`: kube-burner job settings.
- `OUTPUT_DIR`: Result root. Default: `results`.
- `RUN_ID`: Benchmark UUID and per-run directory name. Defaults to a UTC timestamp.
- `CSV_OUTPUT`: Set to `false` to skip CSV summary output.

## Result Files

Each benchmark run writes raw kube-burner metrics under `results/<RUN_ID>/raw` and summary files under `results/<RUN_ID>`.

- `summary.json`: Run metadata and required pod latency quantiles for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`.
- `summary.csv`: Rows for `run_id`, `runtime_class`, `condition`, `p50`, `p95`, and `p99` when `CSV_OUTPUT=true`.
- `user-data.yml`: Rendered kube-burner user data for the run.

The extractor fails if any required condition or P50/P95/P99 value is missing.

## Manual End-to-End Verification

1. Run `make validate` and confirm the extractor creates `results/validation/summary.json` and `results/validation/summary.csv` from fixture metrics.
2. Run `make cluster-create` with the target Azure settings. Confirm the command completes and `az aks nodepool list --resource-group <rg> --cluster-name <cluster> --query '[].{name:name,count:count}'` reports `sys=2`, `kata=1`, `gvisor=1`, and `firecracker=1` unless you overrode node pool names.
3. Run `make kube-burner-install` and confirm `tools/bin/kube-burner version` works.
4. Run at least one runtime benchmark, for example the Kata command in the basic workflow.
5. Confirm `results/<RUN_ID>/summary.json` and `results/<RUN_ID>/summary.csv` contain all five required pod latency conditions and P50/P95/P99 values.
6. Run `make cluster-delete` with the same resource variables. Use `TEARDOWN_SCOPE=resource-group` only when the resource group is dedicated to the benchmark.
