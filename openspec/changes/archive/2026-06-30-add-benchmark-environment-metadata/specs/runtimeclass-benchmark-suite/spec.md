## ADDED Requirements

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
