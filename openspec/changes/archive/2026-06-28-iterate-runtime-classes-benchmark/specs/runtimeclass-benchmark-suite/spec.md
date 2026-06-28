## MODIFIED Requirements

### Requirement: Configurable runtime class workload
The kube-burner workload SHALL create pods from a pod spec whose runtime class and placement settings are selected from the configured benchmark runtime inventory at benchmark execution time.

#### Scenario: Run benchmark for configured runtime classes
- **WHEN** an operator runs the benchmark target with the default runtime inventory
- **THEN** kube-burner creates benchmark pods for each configured runtime class with `runtimeClassName`, node selector, and tolerations rendered from that runtime entry

#### Scenario: Run benchmark for standard runtime
- **WHEN** an operator runs the benchmark target with the default runtime inventory
- **THEN** kube-burner creates a standard runtime benchmark entry without a `runtimeClassName` field and with the standard runtime placement settings

### Requirement: Benchmark execution target
The benchmark suite SHALL provide a Make target that runs kube-burner against the AKS cluster under test for every enabled runtime entry in one benchmark invocation.

#### Scenario: Run kube-burner benchmark suite
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite generates a kube-burner config with one job per enabled runtime entry and invokes kube-burner once with that config

### Requirement: Default runtime baseline benchmark execution
The benchmark suite SHALL include the default Kubernetes runtime as the automatic first benchmark entry and SHALL run all configured runtime class entries in the same benchmark invocation.

#### Scenario: Run all configured runtimes by default
- **WHEN** an operator runs the benchmark target without specifying `RUNTIME_CLASS`, `NODE_SELECTOR`, or `TOLERATIONS_JSON`
- **THEN** the suite runs the default-runtime baseline and each configured runtime class benchmark exactly once

#### Scenario: Keep benchmark invocation output together
- **WHEN** the benchmark target runs the default baseline and configured runtime class benchmarks
- **THEN** the suite writes the generated kube-burner config, runtime manifest, raw metrics, and combined summaries under one result root for the invocation

#### Scenario: Label baseline summaries
- **WHEN** the default-runtime baseline summary is extracted
- **THEN** the suite labels the runtime class value as `standard`

#### Scenario: Support future runtime entries
- **WHEN** a new runtime entry is added to the benchmark runtime inventory with runtime class and placement settings
- **THEN** the benchmark target includes that runtime entry without requiring new benchmark control-flow branches

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
