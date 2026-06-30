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
The benchmark cluster SHALL contain a system node pool with two nodes and one dedicated schedulable node pool with one node for each benchmark runtime entry: `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker`.

#### Scenario: Provision required node pools
- **WHEN** cluster creation completes successfully
- **THEN** the AKS cluster contains node pools for system, standard, Kata, optimized Kata, gVisor, and Firecracker workloads with node counts of 2, 1, 1, 1, 1, and 1 respectively

#### Scenario: Runtime pools are schedulable targets
- **WHEN** the runtime-specific node pools are created
- **THEN** each runtime-specific node pool has labels and optional taints that the benchmark workload can use for explicit pod placement and Prometheus attribution

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
The kube-burner workload SHALL create pods from a checked-in static suite config whose runtime class, node placement, and Prometheus attribution settings are visible in repository-managed configuration before benchmark execution.

#### Scenario: Run benchmark for configured runtime classes
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates benchmark pods for each configured runtime entry with `runtimeClassName` where applicable, node selector, tolerations, and Prometheus attribution labels aligned with the runtime manifest

#### Scenario: Run benchmark for optimized Kata runtime class
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates a benchmark entry for `kata-optimized` with `runtimeClassName: kata-optimized` and dedicated optimized-Kata node pool placement settings aligned with its runtime manifest Prometheus attribution label

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
The benchmark suite SHALL provide a Make target that runs kube-burner against the AKS cluster under test using a repository-managed static suite config for every runtime entry in one benchmark invocation, and SHALL configure kube-burner to query the repository-managed Prometheus endpoint for Prometheus-calculated kubelet startup quantiles.

#### Scenario: Run kube-burner benchmark suite
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite copies or prepares the checked-in kube-burner config for the invocation and invokes kube-burner once with that config

#### Scenario: Configure kubelet startup metric collection
- **WHEN** the benchmark target prepares the kube-burner config for an invocation
- **THEN** the rendered config includes Prometheus `histogram_quantile()` collection for P50, P95, and P99 values of the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families from the configured Prometheus endpoint

### Requirement: Default runtime baseline benchmark execution
The benchmark suite SHALL include the default Kubernetes runtime as a static benchmark entry and SHALL run the checked-in runtime class entries in the same benchmark invocation, with each runtime entry scheduled onto node-pool placement that preserves an unambiguous Prometheus label for that runtime entry.

#### Scenario: Run all configured runtimes by default
- **WHEN** an operator runs the benchmark target without modifying the repository-managed static suite config
- **THEN** the suite runs the default-runtime baseline, the existing Kata runtime class benchmark, the `kata-optimized` runtime class benchmark, the gVisor runtime class benchmark, and the Firecracker-backed Kata runtime class benchmark exactly once

#### Scenario: Keep benchmark invocation output together
- **WHEN** the benchmark target runs the default baseline and checked-in runtime class benchmarks
- **THEN** the suite writes the kube-burner config used for the invocation, runtime manifest, raw metrics, and combined summaries under one result root for the invocation

#### Scenario: Label baseline summaries
- **WHEN** the default-runtime baseline summary is extracted
- **THEN** the suite labels the runtime class value as `standard`

#### Scenario: Preserve baseline attribution
- **WHEN** the checked-in suite config includes the default-runtime baseline benchmark entry
- **THEN** the baseline entry uses a dedicated node-pool selector so Prometheus kubelet metrics can be grouped separately from system-node workload activity

#### Scenario: Label optimized Kata summaries
- **WHEN** the optimized Kata runtime class summary is extracted
- **THEN** the suite labels the runtime key and runtime class value as `kata-optimized`

#### Scenario: Label gVisor summaries
- **WHEN** the gVisor runtime class summary is extracted
- **THEN** the suite labels the runtime key and runtime class value as `gvisor`

#### Scenario: Label Firecracker summaries
- **WHEN** the Firecracker-backed Kata runtime class summary is extracted
- **THEN** the suite labels the runtime key as `firecracker` and the runtime class value as `kata-fc`

#### Scenario: Preserve optimized Kata attribution
- **WHEN** the checked-in suite config includes both `kata` and `kata-optimized` benchmark entries
- **THEN** those entries use distinct node-pool selectors so Prometheus kubelet metrics can be grouped separately for each entry without relying on `runtime_handler`

#### Scenario: Declare Prometheus attribution labels
- **WHEN** the runtime manifest lists benchmark runtime entries
- **THEN** each runtime entry declares exactly one Prometheus attribution label key and value matching its suite node selector, with one shared label key across all runtime entries and a distinct label value per runtime entry

#### Scenario: Support future runtime entries
- **WHEN** a new runtime entry is added to the benchmark suite
- **THEN** the runtime entry is added by changing the repository-managed static suite config and aligned runtime manifest rather than by adding benchmark control-flow branches or runtime generation logic

### Requirement: Pod latency metrics
The benchmark suite SHALL record kube-burner `podLatency` P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`, and SHALL collect P50, P95, and P99 values for configured kubelet startup duration metrics from Prometheus `histogram_quantile()` query output.

#### Scenario: Extract requested pod latency quantiles
- **WHEN** kube-burner completes a benchmark run and writes local metrics
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each requested pod latency condition

#### Scenario: Missing requested quantile
- **WHEN** kube-burner output does not contain one of the requested pod latency condition quantiles
- **THEN** the suite fails the benchmark summary step and reports which quantile is missing

#### Scenario: Collect kubelet startup metrics
- **WHEN** kube-burner runs with the repository-managed Prometheus endpoint configured
- **THEN** kube-burner collects Prometheus-calculated P50, P95, and P99 values for the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families

#### Scenario: Extract kubelet startup metric quantiles
- **WHEN** kube-burner completes a benchmark run and writes Prometheus-backed kubelet startup quantile output for the configured metric families
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each configured kubelet startup metric family for each runtime entry

#### Scenario: Missing kubelet startup metric input
- **WHEN** kube-burner output does not contain enough Prometheus-backed kubelet startup quantile data for one of the requested metric families and runtime entries
- **THEN** the suite fails the benchmark summary step and reports which kubelet metric family or runtime entry is missing, incomplete, or `NaN`

#### Scenario: Ambiguous kubelet startup metric attribution
- **WHEN** runtime manifest attribution labels are missing, duplicated across runtime entries, or do not match the suite node selectors
- **THEN** the suite fails validation or summary extraction before producing aggregate kubelet startup quantiles

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

### Requirement: Benchmark environment metadata capture
The benchmark suite SHALL capture environment metadata for each benchmark invocation before summary extraction completes, including capture timestamp, node pool identity, VM SKU when discoverable, kernel version when discoverable, containerd version when discoverable, kubelet version when discoverable, and Kata runtime version when discoverable for Kata-based runtime entries.

#### Scenario: Capture metadata during benchmark invocation
- **WHEN** an operator runs the benchmark target against a live cluster
- **THEN** the suite writes an environment metadata file under the benchmark result root before writing aggregate summaries

#### Scenario: Prefer metrics-backed node metadata where reliable
- **WHEN** the repository-managed Prometheus endpoint exposes node metadata from kubelet or cAdvisor metrics
- **THEN** the suite uses that metrics-backed metadata for supported node labels and kernel information where available

#### Scenario: Use node status for runtime metadata not reliably exposed by metrics
- **WHEN** container runtime version is required for the benchmark environment summary
- **THEN** the suite reads the Kubernetes node status container runtime version rather than requiring it to be present as a Prometheus metric

#### Scenario: Handle unavailable optional metadata
- **WHEN** a supported metadata field cannot be discovered for a runtime node pool
- **THEN** the suite records the field as unavailable without discarding successfully extracted benchmark latency results

### Requirement: Benchmark summaries include environment metadata
The benchmark suite SHALL include captured environment metadata in aggregate JSON and CSV benchmark summaries so benchmark results can be compared with their cluster and runtime context.

#### Scenario: Include environment metadata in JSON summary
- **WHEN** aggregate JSON summary extraction runs with an environment metadata file
- **THEN** the top-level JSON summary contains an `environment` object with capture details, metadata sources, runtime-to-node-pool attribution, node pool metadata, and any metadata capture warnings

#### Scenario: Include runtime environment metadata in JSON run entries
- **WHEN** aggregate JSON summary extraction writes a runtime entry
- **THEN** the runtime entry includes the node pool metadata associated with that runtime entry, including VM SKU, kernel version, containerd version, kubelet version, and Kata runtime version when available

#### Scenario: Include environment metadata in CSV rows
- **WHEN** aggregate CSV summary extraction runs with an environment metadata file
- **THEN** every CSV metric row includes stable environment metadata columns for the runtime entry, including node pool, VM SKU, kernel version, containerd version, kubelet version, and Kata runtime version

#### Scenario: Extract summaries from fixture metadata
- **WHEN** summary extraction is run for local tests with a fixture environment metadata file
- **THEN** the extractor uses the fixture metadata without requiring live cluster, Azure, or Prometheus access
