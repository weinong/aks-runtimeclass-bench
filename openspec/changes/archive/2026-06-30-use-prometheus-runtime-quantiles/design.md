## Context

The benchmark suite currently asks kube-burner to collect raw kubelet startup histogram families and then reconstructs P50, P95, and P99 in `scripts/extract-results.py`. That keeps raw data available, but it duplicates Prometheus `histogram_quantile()` behavior in Python.

Live validation against the benchmark cluster showed these label constraints:

- `kubelet_run_podsandbox_duration_seconds_bucket` has `runtime_handler`, but `kata-vm-isolation` and `kata-optimized` both use handler `kata`.
- `kubelet_pod_start_sli_duration_seconds_bucket` and `kubelet_pod_start_total_duration_seconds_bucket` do not have `runtime_handler`.
- Prometheus preserves node labels such as `agentpool`, `runtimeclass`, and `node` because the scrape config labelmaps Kubernetes node labels.

Therefore, Prometheus can calculate accurate histogram quantiles, but runtime-entry attribution must come from exclusive node-pool placement rather than `runtime_handler` alone.

## Goals / Non-Goals

**Goals:**

- Use Prometheus `histogram_quantile()` expressions as the primary source for kubelet startup P50, P95, and P99 values.
- Make every benchmark runtime entry map to a distinct node pool and a distinct Prometheus-preserved node label.
- Preserve the current aggregate summary shape: every runtime entry has P50/P95/P99 values for each configured kubelet startup metric family.
- Fail clearly when direct Prometheus quantile records are missing, `NaN`, or cannot be attributed to exactly one runtime entry.

**Non-Goals:**

- Replacing kube-burner pod latency measurements.
- Requiring kubelet metrics to expose Kubernetes `runtimeClassName`; current kubelet metrics do not provide that label consistently.
- Building a long-term dashboard or recording-rule system.
- Changing the meaning of the optimized Kata RuntimeClass itself.

## Decisions

### Attribute runtime entries by dedicated node-pool labels

Each benchmark runtime entry, including the `standard` baseline, should be scheduled onto exactly one dedicated node pool, and each runtime-specific node pool should carry a stable label that Prometheus preserves. The existing `runtimeclass`/`agentpool` node labels are sufficient for `kata`, `gvisor`, and `firecracker`; this change should add distinct baseline and optimized Kata node-pool identities rather than placing `standard` on shared system nodes or placing `kata` and `kata-optimized` on the same `runtimeclass=kata` pool.

Each runtime manifest entry should declare the Prometheus attribution label key and value expected for that runtime entry. All runtime entries should use the same attribution label key so the kubelet startup PromQL can group direct quantile output with `sum by (le, <runtime label>)`, and each runtime entry should use a distinct attribution label value. Benchmark validation and summary extraction should treat missing attribution labels, duplicate attribution label values across runtime entries, and mismatches between runtime manifest attribution and suite node selectors as configuration errors.

Alternative considered: group by `runtime_handler`. This was rejected because `kata-vm-isolation` and `kata-optimized` both use `runtime_handler="kata"`, while pod-start SLI and total duration metrics have no `runtime_handler` label at all.

Alternative considered: rely only on kube-burner job windows. This can work if jobs run serially and no unrelated pod churn occurs, but node-pool labels make the query output self-attributing and easier to validate.

### Let Prometheus compute kubelet startup quantiles

The kubelet startup metrics profile should define PromQL queries using `histogram_quantile(<quantile>, sum by (le, <runtime label>) (increase(<family>_bucket{...}[{{ .elapsed }}s])))` for P50, P95, and P99. The extractor should normalize these direct quantile records into the existing JSON/CSV summary contract instead of reconstructing quantiles from raw buckets.

Alternative considered: keep Python bucket reconstruction. This remains useful as a diagnostic fallback, but it duplicates Prometheus behavior and increases maintenance risk around counter resets and scrape gaps.

### Keep raw histogram diagnostics separate from summary inputs

Direct quantile records should be the canonical summary source. Raw histogram collection may remain available as a diagnostic profile or validation guidance so operators can debug missing, zero-observation, or `NaN` quantiles without changing the summary contract.

Alternative considered: remove raw histogram visibility entirely. This was rejected because benchmark windows can legitimately produce `NaN` when a node pool has no observations, and raw buckets help distinguish no data from query mistakes.

## Risks / Trade-offs

- Dedicated baseline and optimized Kata node pools increase cluster cost and provisioning time -> keep node counts fixed at one for runtime-specific pools and document the cost trade-off.
- Node-pool labels can be contaminated by unrelated pods scheduled on benchmark pools -> keep runtime taints/selectors and document that benchmark pools should be exclusive during runs.
- Direct PromQL queries can return `NaN` when the selected window has zero observations -> validate query output before summary generation and fail with actionable runtime/metric names.
- Changing metric names from family-level records to quantile records can break existing fixtures -> update tests and fixtures alongside extractor behavior.

## Migration Plan

Existing result directories remain historical outputs. New benchmark runs after this change require dedicated baseline and optimized Kata node pools plus updated runtime manifest/config alignment. Rollback is to restore the raw histogram metrics profile and Python quantile reconstruction while keeping the extra node pools harmless but unnecessary.

## Open Questions

- Should raw histogram diagnostics be collected by default in the same benchmark run or provided as a separate troubleshooting profile?
