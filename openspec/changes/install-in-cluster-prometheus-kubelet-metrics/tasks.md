## 1. Prometheus Manifests

- [ ] 1.1 Add repository-managed Kubernetes manifests for Prometheus namespace, service account, RBAC, ConfigMap, deployment, and ClusterIP service.
- [ ] 1.2 Configure the Prometheus deployment to use `mcr.microsoft.com/oss/v2/prometheus/prometheus:v3.11.3`.
- [ ] 1.3 Constrain the Prometheus deployment so Prometheus pods run only on the configured system node pool.
- [ ] 1.4 Configure Prometheus node discovery and kubelet `/metrics` scraping with in-cluster service account authentication.
- [ ] 1.5 Add metric relabeling or equivalent config so Prometheus retains the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families, including `_bucket`, `_sum`, and `_count` series where present.

## 2. Bootstrap Integration

- [ ] 2.1 Add Make or script defaults for the Prometheus manifest path, namespace, service name, system node pool selector, and kube-burner Prometheus endpoint.
- [ ] 2.2 Extend `scripts/bootstrap-cluster.sh` to apply Prometheus manifests during cluster bootstrap.
- [ ] 2.3 Wait for the Prometheus deployment rollout in non-dry-run bootstrap.
- [ ] 2.4 Preserve dry-run behavior by printing Prometheus apply and rollout commands without mutating the cluster.

## 3. Kube-burner Configuration

- [ ] 3.1 Extend `scripts/run-benchmark.sh` to render the configured Prometheus endpoint into the per-run kube-burner config.
- [ ] 3.2 Update `configs/kube-burner-runtimeclass-suite.yml` so kube-burner queries Prometheus for the three requested kubelet startup metrics.
- [ ] 3.3 Preserve existing local kube-burner metrics output and pod latency summary extraction.
- [ ] 3.4 Add or document a port-forward workflow for local kube-burner access to the ClusterIP Prometheus service.

## 4. Validation and Documentation

- [ ] 4.1 Update local validation checks so required Prometheus manifests and kubelet metric families are present.
- [ ] 4.2 Update README prerequisites, workflow, configuration variables, and manual verification steps for Prometheus and kubelet metric queries.
- [ ] 4.3 Run `make validate` and resolve local validation failures.
- [ ] 4.4 Run `make benchmark-dry-run` and confirm the rendered config preserves local output and includes Prometheus collection for the requested kubelet metrics.
- [ ] 4.5 Document any AKS manual verification that cannot be completed locally, including expected `kubectl rollout status` and Prometheus query checks.
