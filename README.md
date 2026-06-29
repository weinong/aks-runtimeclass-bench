# AKS Runtime Class Benchmark

This repository provisions an AKS cluster shape for runtime class benchmarking, installs a small in-cluster Prometheus instance for kubelet startup metrics, runs a static kube-burner suite config, and extracts pod latency quantiles into JSON and CSV summaries.

## Prerequisites

- `make`, `bash`, `python3`, `curl`, `tar`, and either `sha256sum` or `shasum` for local validation and tool installation.
- Azure CLI logged in with access to the target subscription.
- `kubectl` for credential validation, runtime and Prometheus bootstrap, optional port-forwarding, and benchmark execution.
- `helm` for installing the Kata Deploy chart used by the Firecracker-backed Kata runtime bootstrap.
- Azure permissions to create resource groups, AKS clusters, node pools, and to fetch AKS credentials. Contributor on the benchmark resource group or equivalent scoped permissions is sufficient for the default workflow.
- AKS pod sandboxing support for Kata runtime benchmarks. Public AKS pod sandboxing requires Kubernetes 1.27 or newer, Azure Linux node pools, and a Generation 2 VM size that supports nested virtualization. The default `VM_SIZE=Standard_D8s_v5` satisfies the suite's 8 vCPU minimum, but operators must confirm regional quota and feature availability.
- Runtime support for gVisor and Firecracker in the target environment. Their AKS CLI flags are intentionally configurable through `GVISOR_NODEPOOL_EXTRA_ARGS` and `FIRECRACKER_NODEPOOL_EXTRA_ARGS` because support can be private, preview, or environment-specific.

## Basic Workflow

```bash
make validate
make cluster-create RESOURCE_GROUP=rg-aks-rc-bench CLUSTER_NAME=aks-rc-bench LOCATION=eastus
make bootstrap-cluster
make kube-burner-install
make benchmark-with-port-forward
make cluster-delete RESOURCE_GROUP=rg-aks-rc-bench CLUSTER_NAME=aks-rc-bench
```

Use `make benchmark-dry-run` to prepare the result-local kube-burner suite config and print the kube-burner command without contacting a cluster. By default, `make benchmark` runs the checked-in static suite from `configs/kube-burner-runtimeclass-suite.yml`, which includes the standard runtime baseline plus the Kata, optimized Kata, gVisor, and Firecracker-backed Kata runtime entries in one kube-burner invocation.

`make bootstrap-cluster` installs the repository-managed Prometheus manifests after applying the optimized Kata RuntimeClass and waits for the Prometheus deployment rollout. Prometheus is exposed as an in-cluster ClusterIP service, so the default local kube-burner workflow expects `make prometheus-port-forward` to be running in another terminal before `make benchmark`. For a one-command local run, use `make benchmark-with-port-forward`; it starts the Prometheus port-forward, waits for the endpoint to answer, runs the benchmark, and stops the port-forward when the benchmark exits.

## Important Make Variables

Azure lifecycle variables:

- `AZURE_SUBSCRIPTION`: Optional subscription ID or name passed to `az account set`.
- `RESOURCE_GROUP`: Benchmark resource group. Default: `rg-aks-runtimeclass-bench`.
- `CLUSTER_NAME`: Benchmark AKS cluster name. Default: `aks-runtimeclass-bench`.
- `LOCATION`: Azure region. Default: `eastus`.
- `VM_SIZE`: VM size for all node pools. Must validate to at least 8 vCPUs before provisioning. Default: `Standard_D8s_v5`.
- `KUBERNETES_VERSION`: Optional AKS Kubernetes version.
- `CLUSTER_EXTRA_ARGS`: Optional extra words appended to `az aks create` or `az aks update`.
- `TEARDOWN_SCOPE`: `cluster` deletes only the AKS cluster; `resource-group` deletes the whole resource group. Default: `cluster`.

Node pool variables:

- `SYSTEM_NODEPOOL_NAME`: System node pool name. Default: `sys`; node count is fixed at 2.
- `KATA_NODEPOOL_NAME`, `GVISOR_NODEPOOL_NAME`, `FIRECRACKER_NODEPOOL_NAME`: Runtime node pool names; node count is fixed at 1 each.
- `KATA_NODE_LABELS`, `GVISOR_NODE_LABELS`, `FIRECRACKER_NODE_LABELS`: Space-separated labels applied to runtime pools.
- `KATA_NODE_TAINTS`, `GVISOR_NODE_TAINTS`, `FIRECRACKER_NODE_TAINTS`: Space-separated taints applied to runtime pools. Set to empty to disable taints.
- `KATA_NODEPOOL_EXTRA_ARGS`, `GVISOR_NODEPOOL_EXTRA_ARGS`, `FIRECRACKER_NODEPOOL_EXTRA_ARGS`: Extra words appended to each runtime `az aks nodepool add` command. Kata defaults to `--workload-runtime KataVmIsolation`.
- `KATA_OPTIMIZED_RUNTIME_CLASS`: Custom RuntimeClass applied by `make bootstrap-cluster`. Default: `kata-optimized`. If you override this, update `configs/kube-burner-runtimeclass-suite.yml` and `configs/runtime-manifest.json` to use the same runtime class name before benchmarking.
- `KATA_OPTIMIZED_RUNTIME_OVERHEAD_MEMORY`: Fixed pod memory overhead for the optimized Kata RuntimeClass. Default: `32Mi`.
- `GVISOR_RUNTIME_CLASS`: Repository-managed gVisor RuntimeClass applied by `make bootstrap-cluster`. Default: `gvisor`.
- `FIRECRACKER_RUNTIME_CLASS`: Repository-managed Firecracker-backed Kata RuntimeClass applied by `make bootstrap-cluster`. Default: `kata-fc`; benchmark summaries use the runtime key `firecracker`.
- `KATA_DEPLOY_CHART`: Helm chart reference used for Firecracker-backed Kata installation. Default: `oci://quay.io/kata-containers/kata-deploy-charts/kata-deploy`.
- `PROMETHEUS_MANIFEST`: Repo-relative Prometheus manifest applied by `make bootstrap-cluster`. Default: `manifests/prometheus/prometheus.yml`.
- `PROMETHEUS_NAMESPACE`: Namespace for the in-cluster Prometheus instance. Default: `runtimeclass-bench-prometheus`.
- `PROMETHEUS_SERVICE_NAME`: ClusterIP service name for Prometheus. Default: `prometheus`.
- `PROMETHEUS_SYSTEM_NODE_SELECTOR_KEY`: Node selector key used to pin Prometheus to the system node pool. Default: `kubernetes.azure.com/agentpool`.
- `PROMETHEUS_SYSTEM_NODE_SELECTOR_VALUE`: Node selector value used to pin Prometheus to the system node pool. Default: `$(SYSTEM_NODEPOOL_NAME)`.
- `PROMETHEUS_ROLLOUT_TIMEOUT`: Timeout for `kubectl rollout status` during bootstrap. Default: `5m`.
- `PROMETHEUS_LOCAL_PORT`: Local port used by `make prometheus-port-forward` and `make benchmark-with-port-forward`. Default: `9090`.
- `PROMETHEUS_REMOTE_PORT`: Prometheus service port targeted by port-forward helpers. Default: `9090`.
- `PROMETHEUS_PORT_FORWARD_ADDRESS`: Local bind address for port-forward helpers. Default: `127.0.0.1`.
- `PROMETHEUS_PORT_FORWARD_TIMEOUT`: Time `make benchmark-with-port-forward` waits for the local Prometheus endpoint before failing. Default: `30s`.

kube-burner and workload variables:

- `KUBE_BURNER_VERSION`: Release tag installed under `tools/`. Default: `v2.7.3`.
- `KUBE_BURNER_CONFIG`: Repo-relative static kube-burner suite config copied into each result root before execution. Default: `configs/kube-burner-runtimeclass-suite.yml`.
- `KUBE_BURNER_PROMETHEUS_ENDPOINT`: Prometheus endpoint rendered into the per-run kube-burner config. Default: `http://$(PROMETHEUS_PORT_FORWARD_ADDRESS):$(PROMETHEUS_LOCAL_PORT)`.
- `KUBE_BURNER_PROMETHEUS_METRICS_CONFIG`: Repo-relative kube-burner metrics profile for kubelet startup metrics. Default: `configs/kubelet-startup-metrics.yml`.
- `RUNTIME_MANIFEST`: Repo-relative static runtime key and label manifest copied into each result root for extraction. Default: `configs/runtime-manifest.json`.
- `KATA_VERSION`: Optional Kata runtime version value recorded for the configured Kata node pool in `environment-metadata.json`.
- `FIRECRACKER_KATA_VERSION`: Optional Kata runtime version value recorded for the configured Firecracker node pool in `environment-metadata.json`.
- `BENCHMARK_TIMEOUT`: Timeout passed to `kube-burner init`. Default: `4h`.
- `OUTPUT_DIR`: Result root. Default: `results`.
- `RUN_ID`: Benchmark UUID and per-run directory name. Defaults to a UTC timestamp.
- `CSV_OUTPUT`: Set to `false` to skip CSV summary output.

## Result Files

Each benchmark invocation writes one result root under `results/<RUN_ID>`. The static kube-burner config is copied to `results/<RUN_ID>/kube-burner.yml`, with the local metrics directory and Prometheus endpoint placeholders replaced for that invocation. The config contains one job per runtime key and writes raw metrics under `results/<RUN_ID>/raw`.

The default runtime keys are:

- `standard`: Standard-runtime baseline with no `runtimeClassName`.
- `kata`: Kata runtime benchmark with runtime class, selector, and toleration defined in `configs/kube-burner-runtimeclass-suite.yml`.
- `kata-optimized`: Custom Kata runtime benchmark using `runtimeClassName: kata-optimized`, handler `kata`, and `overhead.podFixed.memory: 32Mi`; it reuses the Kata node selector and toleration.
- `gvisor`: gVisor benchmark using `runtimeClassName: gvisor`, handler `runsc`, and the gVisor node selector and toleration.
- `firecracker`: Firecracker-backed Kata benchmark using `runtimeClassName: kata-fc`, handler `kata-fc`, and the Firecracker node selector and toleration.

To change runtime topology, edit both checked-in benchmark inputs together:

- Add or remove kube-burner jobs in `configs/kube-burner-runtimeclass-suite.yml`.
- Add or remove matching runtime entries in `configs/runtime-manifest.json` so the extractor expects the same runtime keys.
- Keep the `__METRICS_DIR__`, `__PROMETHEUS_ENDPOINT__`, and `__PROMETHEUS_METRICS_CONFIG__` placeholders in the static suite config; `make benchmark` replaces them with the run's raw metrics directory, configured Prometheus endpoint, and metrics profile path.

- `environment-metadata.json`: Result-local environment metadata captured before kube-burner runs. It records the schema version, capture timestamp, metadata source descriptions, runtime-to-node-pool attribution, node pool metadata, and warnings for unavailable optional fields. Node pool and VM SKU come from Kubernetes node labels such as `kubernetes.azure.com/agentpool` and `node.kubernetes.io/instance-type`; kernel version comes from retained Prometheus `machine_info` labels when available; containerd version comes from Kubernetes node status `nodeInfo.containerRuntimeVersion`; kubelet version comes from Kubernetes node status `nodeInfo.kubeletVersion`; Kata version comes from runtime-specific inspection input when available and is otherwise `null` with a warning.
- `summary.json`: Aggregate run metadata for every runtime entry. Each run includes `quantiles` for required pod latency conditions, `kubeletMetricQuantiles` for configured kubelet startup metric families, and runtime node-pool environment metadata when `environment-metadata.json` is passed to the extractor. The top-level `environment` object preserves the full captured metadata and warnings.
- `summary.csv`: Aggregate rows for `run_id`, `runtime_key`, `runtime_class`, `metric_category`, `condition`, `metric_name`, `metric_family`, `unit`, `node_pool`, `vm_sku`, `kernel_version`, `containerd_version`, `kubelet_version`, `kata_version`, `p50`, `p95`, and `p99` when `CSV_OUTPUT=true`. Pod latency rows use `metric_category=pod_latency` and set `condition`; kubelet startup metric rows use `metric_category=kubelet_metric` and set `metric_name`, `metric_family`, and `unit`. Unavailable metadata is `null` in JSON and an empty cell in CSV.
- `kube-burner.yml`: Static kube-burner suite config prepared for the invocation.
- `runtime-manifest.json`: Copied runtime keys and summary labels used by the extractor.
- `raw/`: kube-burner local metrics output.

The Prometheus metrics profile queries these kubelet metric families from the configured Prometheus endpoint: `kubelet_run_podsandbox_duration_seconds`, `kubelet_pod_start_sli_duration_seconds`, and `kubelet_pod_start_total_duration_seconds`, including `_bucket`, `_sum`, and `_count` series where present. It also retains `machine_info` so environment metadata capture can use Prometheus-backed kernel labels when available. The extractor derives P50, P95, and P99 duration values from the collected histogram buckets for each runtime entry and writes them under `kubeletMetricQuantiles` in JSON and as `kubelet_metric` rows in CSV.

Each runtime job uses `metricsClosing: afterJobPause` and `jobPause: 20s` so Prometheus has time to scrape at least once after fast jobs complete. Keep this pause longer than the Prometheus scrape interval; otherwise fast runtime jobs can produce zero bucket deltas and the extractor will fail rather than report misleading kubelet metric quantiles.

The extractor fails if any required pod latency condition, kubelet startup metric family, or P50/P95/P99 value is missing or cannot be attributed to exactly one runtime.

## Manual End-to-End Verification

1. Run `make validate` and confirm the extractor creates `results/validation/summary.json` and `results/validation/summary.csv` from fixture metrics.
2. Run `make cluster-create` with the target Azure settings. Confirm the command completes and `az aks nodepool list --resource-group <rg> --cluster-name <cluster> --query '[].{name:name,count:count}'` reports `sys=2`, `kata=1`, `gvisor=1`, and `firecracker=1` unless you overrode node pool names.
3. Run `make bootstrap-cluster` if you need to reapply repository-managed Kubernetes components after cluster credentials are configured. Set `KUBE_CONTEXT=<context>` to target a specific kube context. Confirm `kubectl get runtimeclass kata-optimized -o jsonpath='{.handler}{" "}{.overhead.podFixed.memory}'` prints `kata 32Mi`, and confirm `kubectl get runtimeclass gvisor kata-fc` shows both repository-managed runtime classes. For exact handlers, `kubectl get runtimeclass gvisor -o jsonpath='{.handler}'` should print `runsc` and `kubectl get runtimeclass kata-fc -o jsonpath='{.handler}'` should print `kata-fc`.
4. Run `make kube-burner-install` and confirm `tools/bin/kube-burner version` works.
5. Confirm Prometheus is available with `kubectl -n runtimeclass-bench-prometheus rollout status deployment/prometheus --timeout 5m`.
6. If kube-burner runs from your local shell, start `make prometheus-port-forward` and leave it running. If you use a different local port, set `PROMETHEUS_LOCAL_PORT=<port>`; the default kube-burner Prometheus endpoint follows that port. Alternatively, run `make benchmark-with-port-forward` to start and stop the local Prometheus port-forward around the benchmark automatically.
7. Before a long benchmark, verify Prometheus can query the kubelet metrics:

```bash
curl -G 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=kubelet_run_podsandbox_duration_seconds_count'
curl -G 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=kubelet_pod_start_sli_duration_seconds_count'
curl -G 'http://127.0.0.1:9090/api/v1/query' --data-urlencode 'query=kubelet_pod_start_total_duration_seconds_count'
```

8. Run `make benchmark`.
9. Confirm `results/<RUN_ID>/environment-metadata.json`, `results/<RUN_ID>/summary.json`, `results/<RUN_ID>/summary.csv`, and `results/<RUN_ID>/kube-burner.yml` exist, and that the summaries contain all five required pod latency conditions plus P50/P95/P99 kubelet startup metric values for `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker`.
10. Confirm the rendered `results/<RUN_ID>/kube-burner.yml` contains the configured Prometheus endpoint and references `configs/kubelet-startup-metrics.yml`; confirm that metrics profile contains the three kubelet startup metric queries.
11. Run `make cluster-delete` with the same resource variables. Use `TEARDOWN_SCOPE=resource-group` only when the resource group is dedicated to the benchmark.
