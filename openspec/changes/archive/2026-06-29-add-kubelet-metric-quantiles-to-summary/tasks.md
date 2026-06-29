## 1. Fixture And Contract Updates

- [x] 1.1 Add representative kube-burner Prometheus kubelet metric fixture data that includes runtime job metadata and histogram or quantile values for the configured kubelet startup metric families.
- [x] 1.2 Update expected `summary.json` fixture output to include `kubeletMetricQuantiles` for each runtime entry.
- [x] 1.3 Update expected `summary.csv` fixture output to include kubelet startup metric quantile rows while preserving runtime identity.

## 2. Summary Extraction

- [x] 2.1 Extend `scripts/extract-results.py` to discover configured kubelet startup metric records from raw kube-burner output.
- [x] 2.2 Add runtime attribution for kubelet metric records using the same runtime manifest and job metadata safeguards used for pod latency records.
- [x] 2.3 Compute P50, P95, and P99 values for each configured kubelet startup metric family per runtime from the collected Prometheus-backed data.
- [x] 2.4 Add kubelet startup metric quantiles to the JSON summary without changing existing pod latency quantile fields.
- [x] 2.5 Extend CSV summary writing so kubelet startup metric quantile rows are distinguishable from pod latency condition rows.
- [x] 2.6 Fail summary extraction with clear errors when required kubelet metric data is missing, incomplete, or cannot be attributed to a runtime.

## 3. Validation And Documentation

- [x] 3.1 Update `scripts/validate-benchmark-baseline.py` to validate kubelet startup metric quantiles in JSON and CSV summaries.
- [x] 3.2 Add or update tests/fixtures that exercise successful extraction and missing kubelet metric failure paths.
- [x] 3.3 Update README usage/output documentation to describe the new kubelet metric quantiles in benchmark summaries.
- [x] 3.4 Run the baseline validation and relevant extraction tests to verify the expanded summary contract.
