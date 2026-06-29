## Context

The benchmark suite already writes aggregate `summary.json` and `summary.csv` files from kube-burner pod latency quantile records. The Prometheus integration adds kubelet startup metric collection through kube-burner and writes the raw query output under the same run root, but `scripts/extract-results.py` ignores those records because it only selects `podLatencyQuantilesMeasurement` entries.

The kubelet startup metrics are histogram-based duration families configured in `configs/kubelet-startup-metrics.yml`:

- `kubelet_run_podsandbox_duration_seconds`
- `kubelet_pod_start_sli_duration_seconds`
- `kubelet_pod_start_total_duration_seconds`

The summary should make these metrics comparable across runtime entries without requiring operators to inspect raw Prometheus output manually.

## Goals / Non-Goals

**Goals:**

- Add P50, P95, and P99 kubelet startup duration values to aggregate benchmark summaries per runtime entry.
- Preserve existing pod latency summary values and runtime identity fields.
- Keep raw kube-burner metric output unchanged for deeper analysis.
- Fail fast with actionable errors when required kubelet metric inputs are missing or cannot be quantiled.

**Non-Goals:**

- Changing the in-cluster Prometheus deployment, scrape target discovery, or retained metric families.
- Adding a new long-term metrics backend or dashboard.
- Replacing kube-burner pod latency measurements with Prometheus-derived values.

## Decisions

### Add a dedicated kubelet metric quantile section per runtime in JSON

Each run object in `summary.json` should keep `quantiles` for pod latency and add a separate `kubeletMetricQuantiles` array for Prometheus-backed kubelet startup metrics. Each entry should include the configured kube-burner metric name, the Prometheus metric family, unit, and P50/P95/P99 values.

This avoids overloading pod lifecycle `condition` values with kubelet metric names and keeps the JSON contract explicit.

Alternative considered: merge kubelet metrics into the existing `quantiles` array. That would be smaller, but it would mix two different dimensions and make downstream parsing ambiguous.

### Represent kubelet metric rows explicitly in CSV

The CSV summary should include kubelet startup quantile rows with enough columns to distinguish metric category, metric name, and pod latency condition. Existing pod latency rows should remain present. The implementation can either extend `summary.csv` with category/name columns or write an additional summary CSV only if preserving the existing header is required during implementation.

The preferred implementation is to extend `summary.csv` because operators asked for the quantiled kubelet metrics in the summary artifact, and a single aggregate CSV is easiest to compare across runtimes.

Alternative considered: write only `summary-kubelet.csv`. That minimizes header churn but makes the summary split across files and does not fully satisfy the request.

### Derive quantiles from collected Prometheus histogram data

Summary extraction should derive P50/P95/P99 from kube-burner's Prometheus-backed histogram output for the configured kubelet metric families. The parser should group records by runtime job metadata, metric family, and histogram bucket, then compute quantiles for each runtime entry.

If kube-burner output already contains directly quantiled records for these metrics after implementation changes, the extractor may consume those records instead, but the summary contract should stay the same.

Alternative considered: change the metrics profile to query Prometheus `histogram_quantile()` expressions directly. That may be simpler if kube-burner records those values cleanly, but it pushes summary semantics into the Prometheus query file and can make validation harder. Implementation should choose this only if raw bucket reconstruction is unreliable for kube-burner's stored format.

## Risks / Trade-offs

- CSV schema change could affect consumers that assume the old header -> update fixtures and validation, and document the new columns in the implementation.
- Histogram quantile calculation depends on kube-burner's raw Prometheus output shape -> add fixture-based tests using representative kube-burner output before changing extraction logic.
- Runtime attribution depends on kube-burner job metadata in Prometheus metric records -> validate that every kubelet metric record can be associated with exactly one configured runtime job and fail clearly on mixed or missing metadata.
- Some kubelet histogram families may be absent on a cluster or kubelet version -> treat configured metric families as required for this benchmark change so incomplete data does not produce misleading summaries.

## Migration Plan

No deployment migration is required. After implementation, new benchmark runs will produce expanded summaries. Existing result directories remain readable as historical outputs, but regenerating summaries from old raw data may fail if the required kubelet Prometheus records are not present.

Rollback is to revert the extractor, validation, and fixture changes; raw Prometheus metric collection remains independently useful.

## Open Questions

- Whether implementation should compute quantiles from histogram buckets in `extract-results.py` or add direct `histogram_quantile()` queries to the kube-burner metrics profile depends on the most stable shape of kube-burner's saved Prometheus records. Resolve this with fixture tests during implementation.
