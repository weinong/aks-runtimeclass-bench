## MODIFIED Requirements

### Requirement: Pod latency metrics
The benchmark suite SHALL record kube-burner `podLatency` P50, P95, and P99 values for `PodScheduled`, `PodReadyToStartContainers`, `ContainersStarted`, `ContainersReady`, and `Ready`, and SHALL derive P50, P95, and P99 values for configured kubelet startup duration metrics collected from Prometheus-backed kube-burner output.

#### Scenario: Extract requested pod latency quantiles
- **WHEN** kube-burner completes a benchmark run and writes local metrics
- **THEN** the suite writes a summary containing P50, P95, and P99 values for each requested pod latency condition

#### Scenario: Missing requested quantile
- **WHEN** kube-burner output does not contain one of the requested pod latency condition quantiles
- **THEN** the suite fails the benchmark summary step and reports which quantile is missing

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

#### Scenario: Include optimized Kata in aggregate summaries
- **WHEN** a benchmark invocation includes the checked-in runtime manifest
- **THEN** the aggregate JSON and CSV summaries include pod latency and kubelet startup metric quantiles for `standard`, `kata`, and `kata-optimized`
