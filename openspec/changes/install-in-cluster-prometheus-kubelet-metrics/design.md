## Context

The repository provisions and bootstraps an AKS runtime class benchmark cluster, then runs kube-burner from the operator environment with a checked-in static suite config. Today the kube-burner config only writes local kube-burner measurement output. The requested metrics are kubelet metrics, so kube-burner needs a Prometheus endpoint that has already scraped kubelet targets during the benchmark window.

Prometheus supports Kubernetes node service discovery from inside the cluster. For the node role, Prometheus discovers one target per node and can scrape kubelet over HTTPS using the pod service account token and Kubernetes CA material mounted into the Prometheus pod. This matches an in-cluster deployment and avoids requiring users to configure an external monitoring stack.

## Goals / Non-Goals

**Goals:**

- Install Prometheus in the benchmark cluster using `mcr.microsoft.com/oss/v2/prometheus/prometheus:v3.11.3`.
- Schedule Prometheus only on the configured system node pool.
- Configure Prometheus to scrape kubelet metrics for all cluster nodes.
- Make the `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds` metric families available for kube-burner collection.
- Integrate Prometheus installation into `make bootstrap-cluster` and the fresh-cluster workflow.
- Keep the deployment lightweight and repository-managed so benchmark setup remains reproducible.

**Non-Goals:**

- Deploy a full production monitoring stack, Prometheus Operator, Grafana, Alertmanager, or long-term storage.
- Replace existing kube-burner local pod latency output or summary extraction.
- Add custom Prometheus recording rules or dashboards.
- Expose Prometheus publicly outside the cluster.

## Decisions

### Decision: Use Plain Kubernetes Manifests

Add repository-managed manifests for namespace, service account, RBAC, config, deployment, and service rather than adding Helm or Prometheus Operator.

Rationale: The benchmark needs a single-purpose Prometheus instance. Plain manifests keep the install path inspectable, dry-run friendly, and consistent with the current bootstrap style.

Alternatives considered:

- Prometheus Operator or kube-prometheus-stack. Rejected because it adds CRDs and a large operational surface that is unnecessary for three kubelet metrics.
- Helm chart install. Rejected because it adds another tool dependency for a small fixed deployment.

### Decision: Scrape Kubelet With Kubernetes Node Discovery

Configure Prometheus with `kubernetes_sd_configs` using `role: node`, `scheme: https`, `metrics_path: /metrics`, and the mounted service account token. Keep or add metric relabeling so only the requested kubelet metric families are retained, including their `_bucket`, `_sum`, and `_count` series where present.

Rationale: Node discovery automatically tracks the benchmark cluster's system and runtime node pools. Retaining only the required metric families reduces local Prometheus storage and query noise without dropping histogram series needed for duration queries.

Alternatives considered:

- Static node target list. Rejected because cluster node names and IPs are dynamic.
- Scraping via Kubernetes API server proxy paths. Possible, but direct node discovery is simpler for an in-cluster Prometheus pod and matches common Prometheus Kubernetes configuration patterns.

### Decision: Run Prometheus Only On The System Node Pool

Constrain the Prometheus deployment to the configured system node pool, while still allowing Prometheus to discover and scrape kubelet targets from all benchmark cluster nodes.

Rationale: Prometheus is benchmark infrastructure, not part of the runtime workload under test. Keeping it on system nodes avoids consuming capacity on the runtime-specific node pools and prevents the monitoring component from interfering with runtime placement or latency measurements.

Alternatives considered:

- Allow Prometheus to schedule anywhere. Rejected because it could land on a runtime-specific node pool and affect the workloads being benchmarked.
- Run one Prometheus instance per runtime node pool. Rejected because the benchmark only needs a single scrape source and multiple instances would add unnecessary overhead and query complexity.

### Decision: Keep Prometheus Cluster-Internal By Default

Expose Prometheus as a ClusterIP service named predictably, and document an access path for kube-burner when it runs outside the cluster, such as `kubectl port-forward` to localhost before running the benchmark.

Rationale: The current workflow runs kube-burner from the operator environment, not as a pod. A ClusterIP service is the safest default for the benchmark cluster, while port-forwarding avoids public exposure and keeps access explicit.

Alternatives considered:

- LoadBalancer service. Rejected because it exposes benchmark metrics externally and can add cloud resource cost and provisioning delay.
- Run kube-burner in-cluster. Rejected as out of scope for this change because the existing workflow invokes kube-burner locally.

### Decision: Preserve Local Metrics Output

Keep the existing local kube-burner metrics endpoint and add Prometheus scraping for the kubelet metrics instead of replacing the local endpoint.

Rationale: Existing pod latency extraction and validation depend on local output files. Adding Prometheus collection should extend the benchmark metrics without breaking existing summaries.

Alternatives considered:

- Switch kube-burner entirely to Prometheus output. Rejected because it would create unrelated changes to result extraction and validation.

## Risks / Trade-offs

- AKS kubelet TLS or authorization behavior may differ by cluster version -> use service account auth and Kubernetes CA material, document expected RBAC, and keep manual verification queries in README.
- kube-burner runs outside the cluster while Prometheus is ClusterIP -> document or script a port-forward flow and make the Prometheus endpoint configurable.
- Prometheus system-node scheduling depends on node pool labels -> use the configured system node pool identity in manifests or rendering and document the expected AKS node pool label.
- Prometheus may not scrape the metric series before the benchmark starts -> bootstrap should wait for the Prometheus deployment rollout, and documentation should advise confirming targets are up before running long benchmarks.
- Metric families may not exist on every Kubernetes version or runtime path -> kube-burner collection should tolerate missing series the same way exploratory Prometheus metrics commonly do, while documentation lists the expected metric families.
- Retaining only three metrics reduces storage but hides other kubelet diagnostics -> keep the filter scoped to the benchmark request; operators can edit the config if they need broader scraping.

## Migration Plan

1. Add Prometheus Kubernetes manifests with the requested image, system-node scheduling constraint, kubelet scrape config, RBAC, deployment, and ClusterIP service.
2. Extend bootstrap to apply the manifests and wait for the Prometheus deployment to become available.
3. Add kube-burner config entries that query the Prometheus endpoint for the three kubelet metrics while preserving the local metrics endpoint.
4. Add Make/config defaults for the Prometheus endpoint or port-forward address used by kube-burner.
5. Update validation so static config checks cover the Prometheus manifest path and required metric families.
6. Update README with install, endpoint access, and manual target/query verification steps.

Rollback is to remove the Prometheus manifests from the cluster and use the existing kube-burner local-only workflow. No persisted data migration is required.

## Open Questions

- Should implementation add a dedicated `make prometheus-port-forward` helper, or only document the `kubectl port-forward` command?
- Should kube-burner fail when any of the three Prometheus metrics are absent, or should absence be accepted because metric availability can depend on kubelet version and runtime activity?
