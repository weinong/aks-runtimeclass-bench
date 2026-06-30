## 1. Runtime Topology

- [x] 1.1 Add baseline and optimized Kata node-pool configuration paths with distinct labels and taints from the system and existing Kata node pools.
- [x] 1.2 Update cluster creation, bootstrap, and validation logic so the default benchmark topology includes one dedicated node pool per runtime entry.
- [x] 1.3 Update the static kube-burner suite config so every runtime entry uses node selectors and tolerations aligned with its manifest attribution labels.
- [x] 1.4 Update `configs/runtime-manifest.json` to include one shared Prometheus attribution label key and the distinct label value expected for each runtime entry.

## 2. Prometheus Quantile Collection

- [x] 2.1 Replace the primary kubelet startup metrics profile with Prometheus `histogram_quantile()` queries for P50, P95, and P99 of each configured kubelet metric family.
- [x] 2.2 Ensure the queries group or filter by the runtime attribution label preserved from node-pool metadata.
- [x] 2.3 Add diagnostic raw-bucket collection guidance or a separate profile for troubleshooting missing, zero-observation, or `NaN` quantile results.

## 3. Summary Extraction

- [x] 3.1 Update `scripts/extract-results.py` to consume direct Prometheus quantile records and normalize them into the existing `kubeletMetricQuantiles` summary shape.
- [x] 3.2 Validate that every required runtime, metric family, and quantile has exactly one finite value or fail with an actionable error.
- [x] 3.3 Remove or demote Python histogram reconstruction from the primary summary path while keeping any needed fallback tests or helpers isolated.

## 4. Tests And Fixtures

- [x] 4.1 Update kube-burner fixture data to represent direct Prometheus quantile records with runtime attribution labels.
- [x] 4.2 Add tests for missing runtime attribution, duplicate attribution, node-selector/manifest attribution mismatches, missing quantiles, and `NaN` quantile values.
- [x] 4.3 Update expected JSON and CSV summary fixtures for the direct-quantile input shape.
- [x] 4.4 Run `make validate` and confirm the updated validation artifacts pass.

## 5. Documentation

- [x] 5.1 Document the dedicated node-pool requirement for runtime-attributed Prometheus quantiles.
- [x] 5.2 Update manual Prometheus verification examples to check kubelet metric families, attribution labels, and representative `histogram_quantile()` queries.
- [x] 5.3 Document the cost and contamination trade-offs of using exclusive runtime node pools.
