## 1. Metadata Contract and Fixtures

- [x] 1.1 Define the environment metadata JSON shape for capture timestamp, node pools, runtime attribution, metadata sources, and warnings.
- [x] 1.2 Add fixture environment metadata covering standard, Kata, optimized Kata, gVisor, and Firecracker runtime entries, including unavailable optional metadata cases.
- [x] 1.3 Update expected JSON and CSV summary fixtures to include environment metadata.

## 2. Metadata Capture

- [x] 2.1 Add a result-local metadata capture helper that writes environment metadata without changing summary extraction logic.
- [x] 2.2 Collect node pool and VM SKU metadata from Kubernetes node labels and/or node objects, using stable fallback ordering for known AKS labels.
- [x] 2.3 Collect kernel metadata from retained kubelet/cAdvisor metadata metrics when available.
- [x] 2.4 Collect containerd version from Kubernetes node status rather than requiring a Prometheus metric.
- [x] 2.5 Collect Kata runtime version from a runtime-specific source when available, and record it as unavailable with a warning when it cannot be discovered.
- [x] 2.6 Wire benchmark execution to capture metadata under the run result root and pass it to summary extraction.

## 3. Summary Extraction and Output

- [x] 3.1 Add an extractor option for loading environment metadata from a JSON file while preserving current fixture-only extraction behavior when omitted.
- [x] 3.2 Include the top-level `environment` object in aggregate JSON summaries when metadata is provided.
- [x] 3.3 Attach runtime node pool metadata to each JSON run entry based on runtime key or runtime manifest attribution.
- [x] 3.4 Extend aggregate CSV output with stable environment metadata columns repeated for each runtime metric row.
- [x] 3.5 Preserve explicit unavailable values as `null` in JSON and empty cells in CSV.

## 4. Prometheus and Documentation

- [x] 4.1 Update the repository-managed Prometheus retention rules and kube-burner metric profile only for metadata metrics needed by the capture flow.
- [x] 4.2 Document which metadata fields come from Prometheus, Kubernetes node status, Azure/AKS labels, and runtime-specific inspection.
- [x] 4.3 Update README result file documentation and manual verification steps for environment metadata.

## 5. Validation

- [x] 5.1 Add tests for summary extraction with fixture environment metadata.
- [x] 5.2 Add tests for missing optional metadata and metadata warnings.
- [x] 5.3 Update baseline validation for the new metadata files, JSON fields, and CSV columns.
- [x] 5.4 Run `make validate` and fix any regressions.
