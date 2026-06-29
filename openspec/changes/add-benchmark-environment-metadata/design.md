## Context

The benchmark suite already deploys an in-cluster Prometheus instance that scrapes kubelet `/metrics`, runs one kube-burner invocation for all runtime entries, and extracts aggregate JSON/CSV summaries from kube-burner local metrics. Current summaries preserve runtime keys, runtime class labels, pod latency quantiles, and kubelet startup metric quantiles, but they do not record the cluster and node environment that produced those values.

Some requested fields are available from existing paths, while others are not reliable Prometheus metrics. Node name and node labels can come through the kubelet scrape target relabeling. VM SKU can come from Kubernetes node labels when present, such as instance type labels. Kernel version may be available from kubelet/cAdvisor info metrics if retained. Container runtime version is reliably available from Kubernetes node status. Kata runtime version is not a standard kubelet metric and needs a runtime-specific source, such as host inspection through an installer/debug pod or Kata Deploy chart/image metadata.

## Goals / Non-Goals

**Goals:**

- Record benchmark environment metadata in each result root before summary extraction completes.
- Include capture-level and runtime node-pool-level metadata in `summary.json`.
- Include selected metadata columns in `summary.csv` so CSV-only workflows retain enough context to compare runs.
- Prefer existing Prometheus scrape data where it is reliable, while using Kubernetes node status or runtime-specific inspection for fields that metrics do not expose consistently.
- Keep extractor tests deterministic by supporting metadata fixture input.

**Non-Goals:**

- Build a general-purpose node inventory system.
- Require Azure Monitor, Log Analytics, or any external telemetry backend beyond the repository-managed Prometheus instance.
- Infer Kata runtime versions from latency metrics.
- Block local fixture extraction on live cluster access.

## Decisions

1. Capture metadata into a result-local JSON file before extraction.

   `run-benchmark.sh` will create an environment metadata file under `results/<RUN_ID>/`, then pass that file to `extract-results.py`. This keeps live cluster access out of the extractor and makes fixture tests straightforward. Alternative considered: make the extractor query the cluster directly. That would couple summary formatting to live cluster credentials and make deterministic tests harder.

2. Use a hybrid metadata source model.

   The capture helper will use Prometheus for metadata that is already scraped or can be retained safely, Kubernetes node objects for reliable node status fields, and runtime-specific inspection for Kata version. This avoids pretending every field is available from kubelet metrics. Alternative considered: use Prometheus only. That is attractive because the benchmark already depends on Prometheus, but containerd and Kata versions are not reliably represented by kubelet metrics.

3. Store JSON metadata once and repeat CSV metadata per metric row.

   JSON output will contain an `environment` object with capture details, metadata sources, runtime-to-node-pool attribution, warnings, and node pool metadata. CSV output will add stable columns such as `node_pool`, `vm_sku`, `kernel_version`, `containerd_version`, `kubelet_version`, and `kata_version`, repeated on each metric row for the corresponding runtime. Alternative considered: emit a separate metadata CSV. A separate file is normalized, but it makes single-file CSV comparison workflows easier to misuse.

4. Treat missing metadata as explicit unknowns by default, not a failed benchmark.

   A successful benchmark should not be discarded just because one environment field cannot be discovered in a specific AKS/runtime shape. Missing fields will be represented as `null` in JSON and empty CSV cells, with capture warnings recorded. A strict mode can be added if operators want missing metadata to fail validation. Alternative considered: fail by default. That would improve data quality but risks losing expensive benchmark runs due to non-critical metadata gaps.

5. Attribute metadata by runtime entry through node pool placement.

   Runtime entries already define placement through the static kube-burner config and runtime manifest alignment. Metadata will be summarized per runtime node pool so each runtime row can include the node pool context used by that runtime. The standard runtime uses the configured standard/system placement context from the suite config.

## Risks / Trade-offs

- Prometheus metadata availability varies by kubelet/cAdvisor version -> Mitigation: fall back to Kubernetes node status and make unavailable fields explicit.
- Kubernetes label names for VM SKU can differ by environment -> Mitigation: check known labels in priority order and document the selected source.
- Kata version collection may require privileged host access or may differ between Kata variants -> Mitigation: make Kata version source explicit and allow `null` when runtime-specific inspection is unavailable.
- Repeating metadata in every CSV row increases file width -> Mitigation: add only comparison-critical fields, while preserving the richer JSON environment object.
- Captured metadata can drift if taken after node upgrades during a long run -> Mitigation: capture immediately before benchmark execution and record a metadata `capturedAt` timestamp.
