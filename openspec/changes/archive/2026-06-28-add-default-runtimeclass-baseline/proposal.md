## Why

The benchmark suite already supports rendering and summarizing a run with no `runtimeClassName`, but operators must remember to run that default-runtime case separately. Making the default runtime an automatic baseline for `make benchmark` ensures every sandboxed runtime measurement has a comparable standard-runtime result from the same benchmark workflow.

## What Changes

- Update `make benchmark` so it always includes a default-runtime baseline run with `RUNTIME_CLASS` unset.
- When `RUNTIME_CLASS` is set to a sandboxed runtime, run both the default baseline and the selected runtime benchmark.
- When `RUNTIME_CLASS` is unset, run only the default baseline and avoid duplicating the same benchmark.
- Store baseline and selected-runtime outputs in distinct per-run locations so summaries are not overwritten.
- Update validation coverage to verify the baseline behavior and preserve explicit runtime coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: Add requirements for benchmark execution to include the default runtime as an automatic baseline alongside explicit runtime class runs.

## Impact

- Updates benchmark execution orchestration in Make targets or supporting scripts.
- Updates validation/test targets to cover automatic baseline execution.
- May change result directory layout or run ID naming for `make benchmark` when a non-default runtime is selected.
- No AKS provisioning, kube-burner dependency, or benchmark summary schema changes are expected.
