## Why

AKS runtime class options need a repeatable benchmark that compares pod startup latency across standard and sandboxed runtimes. A kube-burner based suite will let contributors provision a consistent AKS cluster shape, run a configurable runtime class pod workload, and collect the latency percentiles needed for runtime class evaluation.

## What Changes

- Add a kube-burner benchmark suite for AKS runtime class pod startup latency.
- Add Make targets to create and tear down the AKS cluster under test.
- Add Make targets to install kube-burner and run the benchmark.
- Define the AKS cluster topology as one system node pool with two nodes and one-node node pools for Kata, gVisor, and Firecracker.
- Require benchmark VM sizes with at least 8 vCPUs.
- Support a customizable Kubernetes `runtimeClassName` in the pod workload.
- Emit benchmark output in JSON and/or CSV format.
- Record kube-burner pod latency P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`.

## Capabilities

### New Capabilities
- `runtimeclass-benchmark-suite`: Defines cluster provisioning, kube-burner installation, benchmark execution, runtime class customization, and required pod latency outputs.

### Modified Capabilities

None.

## Impact

- Adds benchmark configuration files and workload manifests for kube-burner.
- Adds Make targets for cluster lifecycle, kube-burner installation, and benchmark execution.
- Adds scripts or supporting configuration for AKS node pool creation and runtime-specific benchmark runs.
- Introduces kube-burner as a benchmark tool dependency and Azure CLI/Kubernetes CLI usage for AKS lifecycle operations.
