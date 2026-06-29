## Why

The benchmark currently reconstructs kubelet startup histogram quantiles in `extract-results.py`, duplicating Prometheus histogram semantics and making counter-reset, scrape-gap, and bucket aggregation behavior harder to trust. Live cluster inspection also shows that `runtime_handler` alone cannot distinguish `kata-vm-isolation` from `kata-optimized`, so runtime-attributed Prometheus quantiles need a dedicated node-pool attribution model.

## What Changes

- Configure the default benchmark topology so every runtime entry, including `kata` and `kata-optimized`, runs on a distinct node pool with distinct Prometheus-preserved node labels.
- Change the kubelet startup metrics profile to request Prometheus `histogram_quantile()` expressions for P50, P95, and P99 instead of collecting raw histogram buckets as the primary summary input.
- Attribute direct Prometheus quantile records to runtime entries using the runtime manifest and per-runtime node-pool selectors rather than relying only on `runtime_handler`.
- Keep enough raw or diagnostic histogram collection guidance to debug missing or `NaN` Prometheus quantiles during benchmark validation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: require distinct node-pool attribution for runtime entries and require summaries to consume Prometheus-calculated kubelet startup quantiles.
- `in-cluster-prometheus-kubelet-metrics`: require Prometheus scraping and labeling to preserve node-pool labels used for runtime attribution and support direct quantile queries.

## Impact

- Affected configs: AKS/node-pool creation inputs, `configs/kube-burner-runtimeclass-suite.yml`, `configs/runtime-manifest.json`, and `configs/kubelet-startup-metrics.yml`.
- Affected scripts: benchmark provisioning/bootstrap scripts, `scripts/extract-results.py`, validation helpers, and tests/fixtures for kube-burner Prometheus output.
- Affected docs: README workflow and manual verification PromQL examples.
- Operational impact: benchmark clusters will need separate node pools for the default baseline and optimized Kata rather than sharing system nodes or the existing Kata pool.
