## MODIFIED Requirements

### Requirement: Benchmark execution target
The benchmark suite SHALL provide a primary `benchmark` Make target that starts local access to the repository-managed Prometheus endpoint when needed, runs kube-burner against the AKS cluster under test using a repository-managed static suite config for every runtime entry in one benchmark invocation, configures kube-burner to query the repository-managed Prometheus endpoint for Prometheus-calculated kubelet startup quantiles, and stops the local Prometheus access path after the run completes.

#### Scenario: Run kube-burner benchmark suite
- **WHEN** an operator runs the benchmark Make target after cluster credentials are configured
- **THEN** the suite starts the Prometheus port-forward workflow, runs the checked-in kube-burner config through one benchmark invocation, and stops the port-forward workflow when the invocation exits

#### Scenario: Configure kubelet startup metric collection
- **WHEN** the benchmark target prepares the kube-burner config for an invocation
- **THEN** the rendered config includes Prometheus `histogram_quantile()` collection for P50, P95, and P99 values of the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families from the configured Prometheus endpoint

#### Scenario: Preserve direct benchmark invocation for wrapper use
- **WHEN** repository automation needs to run the lower-level benchmark without managing a Prometheus port-forward
- **THEN** the suite provides a Make-accessible direct benchmark target that invokes the underlying benchmark script without starting or stopping the port-forward workflow
