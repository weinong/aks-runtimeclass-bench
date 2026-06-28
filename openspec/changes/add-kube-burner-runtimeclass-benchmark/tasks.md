## 1. Project Structure

- [x] 1.1 Add a `Makefile` with documented variables for Azure resource names, location, VM size, kube-burner version, runtime class, node selector, tolerations, pod count, and output directory.
- [x] 1.2 Create `scripts/` for lifecycle and benchmark helper scripts, `config/` for kube-burner configuration, `templates/` for Kubernetes object templates, and `results/` as a gitignored output location.
- [x] 1.3 Add repository documentation that explains prerequisites, required Azure permissions, expected AKS runtime support, and the basic create/install/run/teardown workflow.

## 2. AKS Cluster Lifecycle

- [x] 2.1 Implement a cluster creation script invoked by `make cluster-create` that creates the resource group and AKS cluster with a two-node system node pool.
- [x] 2.2 Add VM size validation that permits only configured node VM sizes with at least 8 vCPUs and fails before provisioning when validation cannot prove the minimum.
- [x] 2.3 Add creation of one-node Kata, gVisor, and Firecracker node pools with configurable runtime-specific AKS flags, labels, and taints.
- [x] 2.4 Fetch AKS credentials after cluster creation and verify that the four required node pools exist with counts of 2, 1, 1, and 1.
- [x] 2.5 Implement `make cluster-delete` to tear down the benchmark cluster or resource group according to documented variables.

## 3. kube-burner Installation

- [x] 3.1 Implement `make kube-burner-install` to install the configured kube-burner version into a repository-local tools directory.
- [x] 3.2 Add checksum or release asset validation where practical, and make the install script idempotent when the requested version is already installed.
- [x] 3.3 Ensure `make benchmark` uses the repository-local kube-burner binary before falling back to `PATH`.

## 4. Benchmark Configuration

- [x] 4.1 Add a kube-burner configuration that enables local indexing and the `podLatency` measurement.
- [x] 4.2 Add a pod object template that renders an optional `runtimeClassName`, configurable image, command, resource requests/limits, node selector, and tolerations.
- [x] 4.3 Configure kube-burner job parameters for namespace naming, pod iterations, replicas, QPS, burst, cleanup, and wait behavior through Make variables or user data.
- [x] 4.4 Implement `make benchmark` to render or pass user data, invoke `kube-burner init`, and write raw metrics under a per-run output directory.

## 5. Result Extraction

- [x] 5.1 Implement a result extraction script that reads kube-burner local metrics and filters `podLatencyQuantilesMeasurement` records.
- [x] 5.2 Validate that `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready` quantiles are present.
- [x] 5.3 Write a JSON summary with run metadata, runtime class, each required condition, and P50/P95/P99 values.
- [x] 5.4 Write a CSV summary with columns for run ID, runtime class, condition, P50, P95, and P99.

## 6. Verification

- [x] 6.1 Add lightweight validation targets or scripts for Makefile syntax, shell syntax, kube-burner config rendering, and result extraction against fixture metrics.
- [x] 6.2 Add fixture kube-burner metric data that includes all required pod latency quantiles for extractor tests.
- [x] 6.3 Document manual end-to-end verification steps for provisioning the AKS cluster, running at least one runtime class benchmark, and confirming JSON/CSV outputs.
