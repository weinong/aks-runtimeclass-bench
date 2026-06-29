## MODIFIED Requirements

### Requirement: Make targets for cluster lifecycle
The benchmark suite SHALL provide Make targets to create and tear down an AKS cluster for runtime class benchmarking, and SHALL provide a reusable bootstrap target for applying repository-managed Kubernetes components to that cluster, including the in-cluster Prometheus instance used for kubelet startup metric collection.

#### Scenario: Create benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite creates or updates the benchmark resource group and AKS cluster using the configured cluster name, location, and VM size

#### Scenario: Bootstrap cluster components
- **WHEN** an operator runs the cluster bootstrap Make target after cluster credentials are configured
- **THEN** the suite applies repository-managed Kubernetes components to the benchmark cluster

#### Scenario: Create optimized Kata runtime class during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite creates or updates a `kata-optimized` RuntimeClass with handler `kata` and `overhead.podFixed.memory` set to `32Mi`

#### Scenario: Install Prometheus during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite installs or updates the repository-managed in-cluster Prometheus instance used for kubelet startup metric collection and constrains it to the configured system node pool

#### Scenario: Bootstrap fresh benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite makes the same repository-managed Kubernetes components available on the created benchmark cluster

#### Scenario: Verify optimized Kata runtime class
- **WHEN** cluster bootstrap validates runtime classes
- **THEN** the suite verifies the `kata-optimized` RuntimeClass exists with handler `kata` and memory overhead `32Mi`

#### Scenario: Tear down benchmark cluster
- **WHEN** an operator runs the cluster teardown Make target
- **THEN** the suite deletes the benchmark AKS cluster and associated benchmark resource group resources according to the configured teardown behavior

### Requirement: Benchmark execution target
The benchmark suite SHALL provide a Make target that runs kube-burner against the AKS cluster under test using a repository-managed static suite config for every runtime entry in one benchmark invocation, and SHALL configure kube-burner to query the repository-managed Prometheus endpoint for kubelet startup metrics.

#### Scenario: Run kube-burner benchmark suite
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite copies or prepares the checked-in kube-burner config for the invocation and invokes kube-burner once with that config

#### Scenario: Configure kubelet startup metric collection
- **WHEN** the benchmark target prepares the kube-burner config for an invocation
- **THEN** the rendered config includes collection for the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families from the configured Prometheus endpoint

### Requirement: Pod latency metrics
The benchmark suite SHALL record kube-burner `podLatency` P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`, and SHALL make kubelet startup duration metrics available through Prometheus-backed kube-burner collection.

#### Scenario: Extract requested pod latency quantiles
- **WHEN** kube-burner completes a benchmark run and writes local metrics
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each requested pod latency condition

#### Scenario: Missing requested quantile
- **WHEN** kube-burner output does not contain one of the requested pod latency condition quantiles
- **THEN** the suite fails the benchmark summary step and reports which quantile is missing

#### Scenario: Collect kubelet startup metrics
- **WHEN** kube-burner runs with the repository-managed Prometheus endpoint configured
- **THEN** kube-burner collects the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families from Prometheus
