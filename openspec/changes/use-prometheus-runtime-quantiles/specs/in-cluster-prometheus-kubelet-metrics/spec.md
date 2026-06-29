## MODIFIED Requirements

### Requirement: Kubelet startup metrics scraping
The in-cluster Prometheus instance SHALL run on the configured system node pool, scrape kubelet metrics from all benchmark cluster nodes including system and runtime-specific node pools, retain the metric families `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds`, and preserve node-pool labels needed to attribute kubelet startup quantile queries to benchmark runtime entries.

#### Scenario: Discover kubelet targets
- **WHEN** Prometheus runs in the benchmark cluster
- **THEN** Prometheus discovers kubelet scrape targets for system and runtime-specific nodes from Kubernetes node discovery rather than from a static node list

#### Scenario: Scrape kubelet metrics endpoint
- **WHEN** Prometheus scrapes a discovered node target
- **THEN** Prometheus scrapes the kubelet metrics endpoint over HTTPS using in-cluster service account authentication

#### Scenario: Retain requested kubelet metric families
- **WHEN** Prometheus stores scraped kubelet samples
- **THEN** Prometheus retains the full `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families, including `_bucket`, `_sum`, and `_count` series where present

#### Scenario: Preserve runtime attribution labels
- **WHEN** Prometheus stores scraped kubelet bucket samples from a benchmark runtime node pool
- **THEN** the stored samples include the stable node-pool label key and value declared by the matching runtime manifest entry, with one shared key across runtime entries and distinct values for `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker`

### Requirement: Prometheus verification guidance
The benchmark suite SHALL document how operators verify that Prometheus is running, that requested kubelet metrics are queryable, and that runtime attribution labels are present before running the benchmark.

#### Scenario: Verify Prometheus deployment
- **WHEN** an operator follows the manual verification workflow
- **THEN** the workflow includes checking that the Prometheus deployment is available

#### Scenario: Verify kubelet metric queries
- **WHEN** an operator follows the manual verification workflow
- **THEN** the workflow includes querying Prometheus for the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families

#### Scenario: Verify runtime attribution labels
- **WHEN** an operator follows the manual verification workflow
- **THEN** the workflow includes querying Prometheus to confirm that each configured runtime entry has an unambiguous node-pool label available on the retained kubelet histogram bucket series
