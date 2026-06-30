## Why

Aggregate `summary.csv` currently repeats environment metadata such as VM SKU and runtime versions on every metric row, even though the same context is already captured in `environment-metadata.json` and preserved in `summary.json`. Slimming the CSV makes it easier to consume as a metric table while keeping detailed environment context in the canonical metadata outputs.

## What Changes

- **BREAKING** Remove repeated environment metadata columns from aggregate `summary.csv` rows.
- Keep aggregate CSV focused on metric identity and quantile values: run/runtime identity, metric category, pod condition or kubelet metric identity, unit, and P50/P95/P99.
- Preserve environment metadata in `environment-metadata.json` and `summary.json`; do not remove JSON run-level environment context.
- Update validation, fixtures, and documentation to describe the slimmer CSV schema.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: Change the aggregate CSV summary requirement so metric rows no longer include repeated environment metadata columns.

## Impact

- `scripts/extract-results.py` aggregate CSV writer and related helpers.
- CSV fixture expectations in `tests/fixtures/expected-suite-summary.csv`.
- Extractor and baseline validation tests that assert CSV environment metadata columns.
- README output documentation for `summary.csv`.
- OpenSpec requirement text for benchmark summaries.
