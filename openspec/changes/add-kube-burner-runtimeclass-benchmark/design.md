## Context

The repository is being prepared as a benchmark suite for measuring AKS pod startup latency across Kubernetes runtime classes. The target benchmark provisions an AKS cluster with a fixed node pool shape, runs a kube-burner workload that creates pods with a configurable `runtimeClassName`, and stores kube-burner `podLatency` quantiles for later comparison.

The suite depends on external command-line tools rather than application runtime code: Azure CLI for AKS lifecycle operations, `kubectl` for cluster access, `make` for operator-facing entry points, and `kube-burner` for workload execution and latency measurement. AKS pod sandboxing for Kata requires Azure Linux node pools, Kubernetes 1.27 or newer, a Generation 2 VM size that supports nested virtualization, and `--workload-runtime KataVmIsolation`. gVisor and Firecracker support is expected to be supplied by AKS runtime-specific node pool configuration available to the target environment; the suite should keep those runtime settings configurable instead of hard-coding unverified preview flags.

## Goals / Non-Goals

**Goals:**

- Provide Make targets to create and tear down the benchmark AKS cluster.
- Provision a cluster with a two-node system node pool and one-node Kata, gVisor, and Firecracker node pools.
- Ensure all benchmark node pools use VM sizes with at least 8 vCPUs by default and validate user overrides before provisioning.
- Provide a Make target to install kube-burner locally into a repository-managed tools directory.
- Provide a Make target to run the kube-burner benchmark against the current AKS kubeconfig.
- Make the pod workload runtime class configurable at run time.
- Store kube-burner output locally as JSON and/or CSV files.
- Capture P50, P95, and P99 `podLatency` quantiles for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`.

**Non-Goals:**

- Provide a hosted dashboard, long-term metrics database, or Prometheus/OpenSearch deployment.
- Automate Azure subscription selection, quota requests, or preview feature registration beyond documenting required variables.
- Implement runtime installation inside AKS nodes if a runtime requires provider-specific preview setup not exposed by stable AKS CLI parameters.
- Compare benchmark results statistically across multiple runs; the suite only produces run artifacts.

## Decisions

- Use a `Makefile` as the public interface for cluster lifecycle, kube-burner installation, and benchmark execution. This keeps the workflow discoverable and matches the request for make targets, while allowing scripts to hold command details.
- Use shell scripts under `scripts/` for non-trivial operations such as AKS provisioning, teardown, kube-burner installation, and result extraction. This avoids an oversized Makefile and keeps each step testable with `bash -n`.
- Default the benchmark VM size to an 8-vCPU Generation 2 nested-virtualization-capable SKU, such as `Standard_D8s_v5`, while allowing overrides through Make variables or environment variables. This satisfies the minimum CPU requirement and gives operators a path to use regionally available SKUs.
- Create the system node pool during `az aks create` with `--node-count 2`, then add one user node pool each for Kata, gVisor, and Firecracker. Kata uses AKS pod sandboxing parameters where available; gVisor and Firecracker node pool creation is parameterized so environments can supply the correct runtime flags, labels, and taints.
- Label and optionally taint runtime-specific node pools, then template benchmark pods with `runtimeClassName`, `nodeSelector`, and tolerations. Runtime class selection alone does not guarantee node placement when multiple runtime pools exist, so node selection should be explicit and configurable.
- Use kube-burner `init` with a repository config file and `podLatency` measurement enabled. Kube-burner documents `podLatencyQuantilesMeasurement` documents with quantile names that include `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`, which matches the requested output.
- Use kube-burner local indexing to write raw metrics to an output directory, then add a small extraction step that filters `podLatencyQuantilesMeasurement` records to JSON and CSV summaries. This avoids a required external metrics service while producing portable artifacts.

## Risks / Trade-offs

- Runtime-specific AKS flags for gVisor and Firecracker may be private, preview, or environment-specific -> Keep node pool creation options configurable and document required variables instead of embedding unstable flags.
- Region quota or SKU availability may prevent the default 8-vCPU VM size from provisioning -> Allow VM size override and fail early if the configured SKU is known to be below 8 vCPUs.
- Kube-burner output formats can vary by version -> Pin or expose the kube-burner version and make the extraction logic tolerant of newline-delimited JSON and JSON arrays.
- Pod scheduling can land on the wrong node pool if only `runtimeClassName` is set -> Include node selectors and tolerations in the pod template and expose them as benchmark parameters.
- Sandbox runtime pods can have different resource requirements than standard pods -> Expose pod CPU and memory requests/limits in the kube-burner user data or Make variables.

## Migration Plan

This is a new benchmark suite, so there is no data migration. Implementation should add files incrementally, validate shell and Make syntax locally, and document required environment variables. Rollback is removal of the added benchmark files and generated output directories.

## Open Questions

- What AKS CLI flags, feature registrations, or internal extensions are required for gVisor and Firecracker node pools in the target environment?
- What runtime class names should be used for gVisor and Firecracker by default?
- Should benchmark runs default to one runtime class at a time or include a convenience target that runs all configured runtime classes sequentially?
