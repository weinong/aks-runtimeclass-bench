## Context

The benchmark suite writes three related result artifacts for aggregate runs:

- `environment-metadata.json` captures full environment context for the invocation.
- `summary.json` preserves top-level environment metadata and per-runtime environment entries.
- `summary.csv` flattens metric rows for spreadsheet and downstream data-processing use.

Today, aggregate CSV rows repeat node pool, VM SKU, kernel, containerd, kubelet, and Kata version fields for every pod latency and kubelet metric row. Those values are not primary metric dimensions and are already available in the JSON artifacts, so the CSV schema is wider and noisier than necessary.

## Goals / Non-Goals

**Goals:**

- Make aggregate `summary.csv` a metric-focused table with stable columns for runtime identity, metric identity, unit, and P50/P95/P99 values.
- Keep complete environment metadata available in `environment-metadata.json` and `summary.json`.
- Update tests, validation, fixtures, docs, and specs so the new CSV contract is explicit.

**Non-Goals:**

- Do not change pod latency or kubelet metric quantile extraction.
- Do not remove environment metadata from JSON outputs.
- Do not introduce dynamic CSV schemas that omit columns only when values are invariant.
- Do not add a separate environment CSV in this change.

## Decisions

- Remove all repeated environment columns from aggregate `summary.csv`: `node_pool`, `vm_sku`, `kernel_version`, `containerd_version`, `kubelet_version`, and `kata_version`.
  - Rationale: a fixed slim schema is easier to document and validate than run-dependent column pruning.
  - Alternative considered: remove only invariant columns such as VM SKU. Rejected because invariance can vary by run and would make the schema data-dependent.
- Keep `runtime_key` and `runtime_class` in CSV rows.
  - Rationale: these are metric identity dimensions needed to compare runtimes directly in CSV-only workflows.
- Keep JSON environment output unchanged.
  - Rationale: consumers that need environment context should use the structured metadata source rather than duplicated flattened fields.
- Treat the CSV schema change as breaking.
  - Rationale: downstream scripts may reference removed column names and should fail visibly during migration.

## Risks / Trade-offs

- Existing CSV-only consumers lose direct environment columns -> Mitigation: document that environment context remains in `environment-metadata.json` and `summary.json` and can be joined by runtime key or node-pool attribution when needed.
- Baseline validation might stop checking that environment capture happened -> Mitigation: keep JSON/environment metadata assertions in extractor tests and leave environment capture validation separate from metric CSV shape.
- Users may want a standalone fully enriched CSV later -> Mitigation: defer a separate enriched export or environment CSV until there is concrete demand.
