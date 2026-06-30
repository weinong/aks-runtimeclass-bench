## Purpose

TBD - In-cluster Prometheus kubelet startup metrics requirements.

## Requirements

### Requirement: In-cluster Prometheus installation
The benchmark suite SHALL provide repository-managed Kubernetes manifests that install a Prometheus instance in the benchmark cluster using image `mcr.microsoft.com/oss/v2/prometheus/prometheus:v3.11.3`, and SHALL schedule Prometheus only on the configured system node pool.

#### Scenario: Bootstrap installs Prometheus
- **WHEN** an operator runs the cluster bootstrap Make target after cluster credentials are configured
- **THEN** the suite applies the repository-managed Prometheus Kubernetes manifests to the benchmark cluster

#### Scenario: Prometheus deployment becomes available
- **WHEN** bootstrap applies the Prometheus Kubernetes manifests in non-dry-run mode
- **THEN** the suite waits for the Prometheus deployment to become available before bootstrap completes successfully

#### Scenario: Prometheus runs on system nodes
- **WHEN** Prometheus pods are scheduled by the benchmark cluster
- **THEN** the pods run only on nodes from the configured system node pool

#### Scenario: Dry-run prints Prometheus install commands
- **WHEN** an operator runs cluster bootstrap in dry-run mode
- **THEN** the suite prints the Prometheus apply and rollout commands without mutating the cluster

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

### Requirement: Kube-burner Prometheus access
The benchmark suite SHALL provide a configurable Prometheus endpoint that kube-burner can use to query the in-cluster Prometheus instance for kubelet startup metrics.

#### Scenario: Configure kube-burner Prometheus endpoint
- **WHEN** an operator runs the benchmark target
- **THEN** the rendered kube-burner config includes the configured Prometheus endpoint for kubelet startup metric queries

#### Scenario: Preserve local kube-burner output
- **WHEN** kube-burner runs with Prometheus metric collection configured
- **THEN** the suite still writes the existing local kube-burner metrics output under the benchmark result root

#### Scenario: Access ClusterIP Prometheus from local kube-burner
- **WHEN** kube-burner runs from outside the cluster and Prometheus is exposed only as a ClusterIP service
- **THEN** the suite documents the required local access path for the configured Prometheus endpoint, such as a `kubectl port-forward`

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
