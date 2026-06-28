## Purpose

TBD - Runtime class benchmark suite requirements.

## Requirements

### Requirement: Make targets for cluster lifecycle
The benchmark suite SHALL provide Make targets to create and tear down an AKS cluster for runtime class benchmarking.

#### Scenario: Create benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite creates or updates the benchmark resource group and AKS cluster using the configured cluster name, location, and VM size

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

#### Scenario: Run benchmark for standard runtime
- **WHEN** an operator runs the benchmark target with the repository-managed static suite config
- **THEN** kube-burner creates a standard runtime benchmark entry without a `runtimeClassName` field and with the standard runtime placement settings defined by that checked-in suite config

### Requirement: Benchmark execution target
The benchmark suite SHALL provide a Make target that runs kube-burner against the AKS cluster under test using a repository-managed static suite config for every runtime entry in one benchmark invocation.

#### Scenario: Run kube-burner benchmark suite
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite copies or prepares the checked-in kube-burner config for the invocation and invokes kube-burner once with that config

### Requirement: Default runtime baseline benchmark execution
The benchmark suite SHALL include the default Kubernetes runtime as a static benchmark entry and SHALL run the checked-in runtime class entries in the same benchmark invocation.

#### Scenario: Run all configured runtimes by default
- **WHEN** an operator runs the benchmark target without modifying the repository-managed static suite config
- **THEN** the suite runs the default-runtime baseline and each checked-in runtime class benchmark exactly once

#### Scenario: Keep benchmark invocation output together
- **WHEN** the benchmark target runs the default baseline and checked-in runtime class benchmarks
- **THEN** the suite writes the kube-burner config used for the invocation, runtime manifest, raw metrics, and combined summaries under one result root for the invocation

#### Scenario: Label baseline summaries
- **WHEN** the default-runtime baseline summary is extracted
- **THEN** the suite labels the runtime class value as `standard`

#### Scenario: Support future runtime entries
- **WHEN** a new runtime entry is added to the benchmark suite
- **THEN** the runtime entry is added by changing the repository-managed static suite config and aligned runtime manifest rather than by adding benchmark control-flow branches or runtime generation logic

### Requirement: Pod latency metrics
The benchmark suite SHALL record kube-burner `podLatency` P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`.

#### Scenario: Extract requested pod latency quantiles
- **WHEN** kube-burner completes a benchmark run and writes local metrics
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each requested pod latency condition

#### Scenario: Missing requested quantile
- **WHEN** kube-burner output does not contain one of the requested pod latency condition quantiles
- **THEN** the suite fails the benchmark summary step and reports which quantile is missing

### Requirement: JSON and CSV benchmark output
The benchmark suite SHALL produce benchmark result files in JSON and/or CSV format, including aggregate result files for each full benchmark invocation.

#### Scenario: Write aggregate JSON summary
- **WHEN** all runtime entries in a benchmark invocation finish successfully
- **THEN** the suite writes a top-level JSON summary containing run metadata and pod latency quantiles for every runtime entry

#### Scenario: Write aggregate CSV summary
- **WHEN** all runtime entries in a benchmark invocation finish successfully and CSV output is enabled
- **THEN** the suite writes a top-level CSV summary with rows for every runtime class, condition, P50, P95, and P99 value

#### Scenario: Preserve runtime identity in summaries
- **WHEN** a runtime entry finishes successfully
- **THEN** the suite includes that runtime entry's key, runtime class label, and pod latency quantiles in the combined JSON and CSV summaries
