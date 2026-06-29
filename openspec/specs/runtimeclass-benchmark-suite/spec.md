## Purpose

TBD - Runtime class benchmark suite requirements.

## Requirements

### Requirement: Make targets for cluster lifecycle
The benchmark suite SHALL provide Make targets to create and tear down an AKS cluster for runtime class benchmarking, and SHALL provide a reusable bootstrap target for applying repository-managed Kubernetes runtime components and the in-cluster Prometheus instance used for kubelet startup metric collection to that cluster.

#### Scenario: Create benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite creates or updates the benchmark resource group and AKS cluster using the configured cluster name, location, and VM size

#### Scenario: Bootstrap cluster components
- **WHEN** an operator runs the cluster bootstrap Make target after cluster credentials are configured
- **THEN** the suite applies repository-managed Kubernetes runtime components and Prometheus manifests to the benchmark cluster

#### Scenario: Create optimized Kata runtime class during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite creates or updates a `kata-optimized` RuntimeClass with handler `kata` and `overhead.podFixed.memory` set to `32Mi`

#### Scenario: Install gVisor runtime during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite installs gVisor runtime support on the configured gVisor node pool and creates or updates a `gvisor` RuntimeClass with handler `runsc`

#### Scenario: Install Kata Firecracker runtime during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite installs Firecracker-backed Kata runtime support on the configured Firecracker node pool and creates or updates a `kata-fc` RuntimeClass with handler `kata-fc`
- **AND** the repository-managed Firecracker Kata Deploy values expose the `fc` RuntimeClass CPU overhead knob and set it to `0` for the current benchmark experiment

#### Scenario: Install Prometheus during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite installs or updates the repository-managed in-cluster Prometheus instance used for kubelet startup metric collection and constrains it to the configured system node pool

#### Scenario: Bootstrap fresh benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite makes the same repository-managed Kubernetes runtime components and in-cluster Prometheus instance available on the created benchmark cluster

#### Scenario: Verify optimized Kata runtime class
- **WHEN** cluster bootstrap validates runtime classes
- **THEN** the suite verifies the `kata-optimized` RuntimeClass exists with handler `kata` and memory overhead `32Mi`

#### Scenario: Verify gVisor runtime class
- **WHEN** cluster bootstrap validates runtime classes
- **THEN** the suite verifies the `gvisor` RuntimeClass exists with handler `runsc`

#### Scenario: Verify Kata Firecracker runtime class
- **WHEN** cluster bootstrap validates runtime classes
- **THEN** the suite verifies the `kata-fc` RuntimeClass exists with handler `kata-fc`

#### Scenario: Tear down benchmark cluster
- **WHEN** an operator runs the cluster teardown Make target
- **THEN** the suite deletes the benchmark AKS cluster and associated benchmark resource group resources according to the configured teardown behavior

### Requirement: AKS node pool topology
The benchmark cluster SHALL contain a system node pool with two nodes, a Kata node pool with one node, a gVisor node pool with one node, and a Firecracker node pool with one node.

#### Scenario: Provision required node pools
- **WHEN** cluster creation completes successfully
- **THEN** the AKS cluster contains node pools for system, Kata, gVisor, and Firecracker workloads with node counts of 2, 1, 1, and 1 respectively

#### Scenario: Runtime pools are schedulable targets
- **WHEN** the runtime-specific node pools are created
- **THEN** each runtime-specific node pool has labels and optional taints that the benchmark workload can use for explicit pod placement

### Requirement: Minimum VM CPU size
The benchmark suite SHALL require configured AKS node VM sizes to have at least 8 vCPUs.

#### Scenario: VM size meets minimum
- **WHEN** the configured VM size has 8 or more vCPUs
- **THEN** the suite allows cluster creation to proceed

#### Scenario: VM size below minimum
- **WHEN** the configured VM size has fewer than 8 vCPUs or cannot be validated
- **THEN** the suite stops before cluster creation and reports that the VM size must provide at least 8 vCPUs

### Requirement: kube-burner installation target
The benchmark suite SHALL provide a Make target that installs kube-burner into a repository-managed tools directory.

#### Scenario: Install kube-burner
- **WHEN** an operator runs the kube-burner installation Make target
- **THEN** the requested kube-burner version is downloaded or installed locally and the benchmark run target can invoke it without requiring a global installation

### Requirement: Configurable runtime class workload
The kube-burner workload SHALL create pods from a checked-in static suite config whose runtime class and placement settings are visible in repository-managed configuration before benchmark execution.

#### Scenario: Run benchmark for configured runtime classes
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates benchmark pods for each configured runtime class with `runtimeClassName`, node selector, and tolerations defined by that checked-in suite config

#### Scenario: Run benchmark for optimized Kata runtime class
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates a benchmark entry for `kata-optimized` with `runtimeClassName: kata-optimized` and Kata node pool placement settings defined by that checked-in suite config

#### Scenario: Run benchmark for gVisor runtime class
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates a benchmark entry for `gvisor` with `runtimeClassName: gvisor` and gVisor node pool placement settings defined by that checked-in suite config

#### Scenario: Run benchmark for Firecracker-backed Kata runtime class
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates a benchmark entry for `firecracker` with `runtimeClassName: kata-fc` and Firecracker node pool placement settings defined by that checked-in suite config

#### Scenario: Run benchmark for standard runtime
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates a standard runtime benchmark entry without a `runtimeClassName` field and with the standard runtime placement settings defined by that checked-in suite config

### Requirement: Benchmark execution target
The benchmark suite SHALL provide a Make target that runs kube-burner against the AKS cluster under test using a repository-managed static suite config for every runtime entry in one benchmark invocation, and SHALL configure kube-burner to query the repository-managed Prometheus endpoint for kubelet startup metrics.

#### Scenario: Run kube-burner benchmark suite
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite copies or prepares the checked-in kube-burner config for the invocation and invokes kube-burner once with that config

#### Scenario: Configure kubelet startup metric collection
- **WHEN** the benchmark target prepares the kube-burner config for an invocation
- **THEN** the rendered config includes collection for the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families from the configured Prometheus endpoint

### Requirement: Default runtime baseline benchmark execution
The benchmark suite SHALL include the default Kubernetes runtime as a static benchmark entry and SHALL run the checked-in runtime class entries in the same benchmark invocation.

#### Scenario: Run all configured runtimes by default
- **WHEN** an operator runs the benchmark target without modifying the repository-managed static suite config
- **THEN** the suite runs the default-runtime baseline, the existing Kata runtime class benchmark, the `kata-optimized` runtime class benchmark, the gVisor runtime class benchmark, and the Firecracker-backed Kata runtime class benchmark exactly once

#### Scenario: Keep benchmark invocation output together
- **WHEN** the benchmark target runs the default baseline and checked-in runtime class benchmarks
- **THEN** the suite writes the kube-burner config used for the invocation, runtime manifest, raw metrics, and combined summaries under one result root for the invocation

#### Scenario: Label baseline summaries
- **WHEN** the default-runtime baseline summary is extracted
- **THEN** the suite labels the runtime class value as `standard`

#### Scenario: Label optimized Kata summaries
- **WHEN** the optimized Kata runtime class summary is extracted
- **THEN** the suite labels the runtime key and runtime class value as `kata-optimized`

#### Scenario: Label gVisor summaries
- **WHEN** the gVisor runtime class summary is extracted
- **THEN** the suite labels the runtime key and runtime class value as `gvisor`

#### Scenario: Label Firecracker summaries
- **WHEN** the Firecracker-backed Kata runtime class summary is extracted
- **THEN** the suite labels the runtime key as `firecracker` and the runtime class value as `kata-fc`

#### Scenario: Support future runtime entries
- **WHEN** a new runtime entry is added to the benchmark suite
- **THEN** the runtime entry is added by changing the repository-managed static suite config and aligned runtime manifest rather than by adding benchmark control-flow branches or runtime generation logic

### Requirement: Pod latency metrics
The benchmark suite SHALL record kube-burner `podLatency` P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`, and SHALL derive P50, P95, and P99 values for configured kubelet startup duration metrics collected from Prometheus-backed kube-burner output.

#### Scenario: Extract requested pod latency quantiles
- **WHEN** kube-burner completes a benchmark run and writes local metrics
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each requested pod latency condition

#### Scenario: Missing requested quantile
- **WHEN** kube-burner output does not contain one of the requested pod latency condition quantiles
- **THEN** the suite fails the benchmark summary step and reports which quantile is missing

#### Scenario: Collect kubelet startup metrics
- **WHEN** kube-burner runs with the repository-managed Prometheus endpoint configured
- **THEN** kube-burner collects the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families from Prometheus

#### Scenario: Extract kubelet startup metric quantiles
- **WHEN** kube-burner completes a benchmark run and writes Prometheus-backed kubelet startup metric output for the configured metric families
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each configured kubelet startup metric family for each runtime entry

#### Scenario: Missing kubelet startup metric input
- **WHEN** kube-burner output does not contain enough Prometheus-backed kubelet startup metric data to derive one of the requested metric family quantiles
- **THEN** the suite fails the benchmark summary step and reports which kubelet metric family is missing or incomplete

### Requirement: JSON and CSV benchmark output
The benchmark suite SHALL produce benchmark result files in JSON and/or CSV format, including aggregate result files for each full benchmark invocation with pod latency quantiles and quantiled kubelet startup metrics for every runtime entry.

#### Scenario: Write aggregate JSON summary
- **WHEN** all runtime entries in a benchmark invocation finish successfully
- **THEN** the suite writes a top-level JSON summary containing run metadata, pod latency quantiles, and kubelet startup metric quantiles for every runtime entry

#### Scenario: Write aggregate CSV summary
- **WHEN** all runtime entries in a benchmark invocation finish successfully and CSV output is enabled
- **THEN** the suite writes a top-level CSV summary with rows for every runtime class, pod latency condition, kubelet startup metric family, and P50, P95, and P99 value

#### Scenario: Preserve runtime identity in summaries
- **WHEN** a runtime entry finishes successfully
- **THEN** the suite includes that runtime entry's key, runtime class label, pod latency quantiles, and kubelet startup metric quantiles in the combined JSON and CSV summaries

#### Scenario: Include all default runtimes in aggregate summaries
- **WHEN** a benchmark invocation includes the checked-in runtime manifest
- **THEN** the aggregate JSON and CSV summaries include pod latency and kubelet startup metric quantiles for `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker`
