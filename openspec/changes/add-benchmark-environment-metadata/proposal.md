## Why

Benchmark summaries currently include runtime identity and latency quantiles, but they do not record enough environment context to compare runs safely across cluster shapes or runtime versions. Operators need the summary to carry node pool, VM SKU, kernel, containerd, and Kata runtime context so performance differences can be interpreted without manually reconstructing the cluster state after the run.

## What Changes

- Capture benchmark environment metadata during each benchmark invocation and store it under the result root.
- Extend aggregate JSON summaries with environment metadata for runtime node pools.
- Extend aggregate CSV summaries with stable environment metadata columns repeated on each metric row so CSV-only comparisons retain the same context.
- Prefer metadata available from the existing Prometheus kubelet scrape path where practical, while allowing direct Kubernetes node API or host/runtime inspection for fields that are not reliably exposed as kubelet metrics.
- Keep summary extraction deterministic for tests by accepting fixture metadata input instead of requiring a live cluster.

## Capabilities

### New Capabilities

### Modified Capabilities

- `runtimeclass-benchmark-suite`: Add benchmark environment metadata capture and summary output requirements.

## Impact

- `scripts/run-benchmark.sh` will prepare and pass a per-run environment metadata file to summary extraction.
- A metadata capture helper may query Prometheus, Kubernetes node objects, and runtime installation details.
- `scripts/extract-results.py` will load environment metadata and include it in `summary.json` and `summary.csv`.
- `manifests/prometheus/prometheus.yml` and kube-burner metric profiles may retain/query node information metrics in addition to existing kubelet startup metrics.
- Summary fixtures, extractor tests, README result-file documentation, and baseline validation will need updates.
