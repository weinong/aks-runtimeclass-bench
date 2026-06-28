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
The kube-burner workload SHALL create pods from a pod spec whose runtime class is configurable at benchmark execution time.

#### Scenario: Run benchmark for Kata runtime class
- **WHEN** an operator runs the benchmark with `RUNTIME_CLASS` set to the Kata runtime class and matching node selector settings
- **THEN** kube-burner creates benchmark pods with `runtimeClassName` set to that value and schedules them onto the configured Kata node pool selector

#### Scenario: Run benchmark for standard runtime
- **WHEN** an operator runs the benchmark with no runtime class configured
- **THEN** kube-burner creates benchmark pods without a `runtimeClassName` field and schedules them according to the configured default node selector

### Requirement: Benchmark execution target
The benchmark suite SHALL provide a Make target that runs kube-burner against the AKS cluster under test.

#### Scenario: Run kube-burner benchmark
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite invokes kube-burner with the repository benchmark configuration, runtime class parameters, and output directory settings

### Requirement: Pod latency metrics
The benchmark suite SHALL record kube-burner `podLatency` P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`.

#### Scenario: Extract requested pod latency quantiles
- **WHEN** kube-burner completes a benchmark run and writes local metrics
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each requested pod latency condition

#### Scenario: Missing requested quantile
- **WHEN** kube-burner output does not contain one of the requested pod latency condition quantiles
- **THEN** the suite fails the benchmark summary step and reports which quantile is missing

### Requirement: JSON and CSV benchmark output
The benchmark suite SHALL produce benchmark result files in JSON and/or CSV format.

#### Scenario: Write JSON summary
- **WHEN** a benchmark run finishes successfully
- **THEN** the suite writes a JSON summary file containing the requested pod latency quantiles and run metadata

#### Scenario: Write CSV summary
- **WHEN** a benchmark run finishes successfully and CSV output is enabled
- **THEN** the suite writes a CSV summary file with rows for runtime class, condition, P50, P95, and P99 values
