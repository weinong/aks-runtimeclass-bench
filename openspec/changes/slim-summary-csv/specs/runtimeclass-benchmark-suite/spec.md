## MODIFIED Requirements

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

### Requirement: Benchmark summaries include environment metadata
The benchmark suite SHALL include captured environment metadata in aggregate JSON benchmark summaries so benchmark results can be compared with their cluster and runtime context while keeping aggregate CSV summaries focused on metric rows.

#### Scenario: Include environment metadata in JSON summary
- **WHEN** aggregate JSON summary extraction runs with an environment metadata file
- **THEN** the top-level JSON summary contains an `environment` object with capture details, metadata sources, runtime-to-node-pool attribution, node pool metadata, and any metadata capture warnings

#### Scenario: Include runtime environment metadata in JSON run entries
- **WHEN** aggregate JSON summary extraction writes a runtime entry
- **THEN** the runtime entry includes the node pool metadata associated with that runtime entry, including VM SKU, kernel version, containerd version, kubelet version, and Kata runtime version when available

#### Scenario: Omit environment metadata from CSV rows
- **WHEN** aggregate CSV summary extraction runs with an environment metadata file
- **THEN** CSV metric rows omit repeated environment metadata columns including node pool, VM SKU, kernel version, containerd version, kubelet version, and Kata runtime version

#### Scenario: Extract summaries from fixture metadata
- **WHEN** summary extraction is run for local tests with a fixture environment metadata file
- **THEN** the extractor uses the fixture metadata without requiring live cluster, Azure, or Prometheus access
