## Why

Kube-burner now captures kubelet startup metrics from Prometheus, but the benchmark summary only reports pod latency quantiles. Operators need the same P50/P95/P99 summary view for kubelet startup metrics so runtime comparisons can use one summary artifact instead of manually inspecting raw Prometheus query output.

## What Changes

- Extend benchmark summary generation to include quantiled kubelet startup metrics collected from Prometheus-backed kube-burner output.
- Add summary JSON and CSV fields/rows for P50, P95, and P99 values for each configured kubelet startup metric family per runtime.
- Preserve existing pod latency summary behavior and raw metrics output.
- Fail summary generation with a clear error when required kubelet metric quantiles cannot be derived from collected data.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: summary outputs will include quantiled kubelet startup metrics in addition to existing pod latency quantiles.

## Impact

- `scripts/extract-results.py` will parse Prometheus-backed kubelet metric records and add derived quantiles to summary outputs.
- Summary fixtures and validation will need updates for the expanded JSON/CSV contract.
- Existing benchmark invocations continue to write local raw metrics; no new external dependencies or cluster components are required.
