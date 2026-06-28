## Why

The runtime class benchmark currently relies on kube-burner local pod latency output, but the requested kubelet startup metrics are exposed through kubelet metrics and need a Prometheus endpoint for kube-burner to scrape. Installing a small in-cluster Prometheus instance makes kubelet sandbox and pod start duration metrics available during benchmark runs without depending on an external monitoring stack.

## What Changes

- Add repository-managed Kubernetes manifests for an in-cluster Prometheus deployment using `mcr.microsoft.com/oss/v2/prometheus/prometheus:v3.11.3`.
- Configure Prometheus to scrape kubelet metrics for `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds`.
- Expose Prometheus through an in-cluster service that kube-burner can use as its metrics endpoint.
- Extend cluster bootstrap so Prometheus can be installed with the other repository-managed Kubernetes components.
- Update kube-burner configuration and documentation so benchmark runs can scrape the Prometheus endpoint for the kubelet startup metrics.

## Capabilities

### New Capabilities

- `in-cluster-prometheus-kubelet-metrics`: Installing and using an in-cluster Prometheus instance that scrapes kubelet startup metrics for kube-burner benchmark collection.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: Benchmark execution and bootstrap requirements change to make kubelet startup metrics available through the repository-managed Prometheus endpoint.

## Impact

- Affected files are expected to include Kubernetes manifests under a repository-managed config path, `scripts/bootstrap-cluster.sh`, `configs/kube-burner-runtimeclass-suite.yml`, validation fixtures or config checks, and `README.md`.
- The benchmark cluster will run a Prometheus deployment, service account, RBAC, config, and service in-cluster.
- kube-burner runs will depend on the Prometheus service being reachable from the environment where kube-burner executes, or on a documented access path such as port-forwarding if the service remains cluster-internal.
