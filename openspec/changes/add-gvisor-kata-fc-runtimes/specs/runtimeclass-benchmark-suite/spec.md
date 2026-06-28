## MODIFIED Requirements

### Requirement: Make targets for cluster lifecycle
The benchmark suite SHALL provide Make targets to create and tear down an AKS cluster for runtime class benchmarking, and SHALL provide a reusable bootstrap target for applying repository-managed Kubernetes runtime components to that cluster.

#### Scenario: Create benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite creates or updates the benchmark resource group and AKS cluster using the configured cluster name, location, and VM size

#### Scenario: Bootstrap cluster components
- **WHEN** an operator runs the cluster bootstrap Make target after cluster credentials are configured
- **THEN** the suite applies repository-managed Kubernetes runtime components to the benchmark cluster

#### Scenario: Create optimized Kata runtime class during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite creates or updates a `kata-optimized` RuntimeClass with handler `kata` and `overhead.podFixed.memory` set to `32Mi`

#### Scenario: Install gVisor runtime during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite installs gVisor runtime support on the configured gVisor node pool and creates or updates a `gvisor` RuntimeClass with handler `runsc`

#### Scenario: Install Kata Firecracker runtime during bootstrap
- **WHEN** cluster bootstrap runs
- **THEN** the suite installs Firecracker-backed Kata runtime support on the configured Firecracker node pool and creates or updates a `kata-fc` RuntimeClass with handler `kata-fc`

#### Scenario: Bootstrap fresh benchmark cluster
- **WHEN** an operator runs the cluster creation Make target with required Azure configuration
- **THEN** the suite makes the same repository-managed Kubernetes runtime components available on the created benchmark cluster

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

#### Scenario: Include all default runtimes in aggregate summaries
- **WHEN** a benchmark invocation includes the checked-in runtime manifest
- **THEN** the aggregate JSON and CSV summaries include rows for `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker`
