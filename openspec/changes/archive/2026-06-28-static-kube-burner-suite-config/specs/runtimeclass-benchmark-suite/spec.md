## MODIFIED Requirements

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
