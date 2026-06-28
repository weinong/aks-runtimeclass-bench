## Why

The runtime class benchmark suite is intentionally small and mostly static, but the current benchmark path hides the kube-burner workload behind a custom Python renderer. Making the suite config a checked-in artifact reduces cognitive load, makes benchmark intent easier to review, and removes generation logic that is no longer buying enough flexibility.

## What Changes

- Replace generated kube-burner suite YAML with a repository-managed static suite config for the standard runtime baseline and runtime class jobs.
- Keep per-run benchmark outputs under `results/<RUN_ID>/`, including a copy of the suite config used for that invocation.
- Replace generated runtime manifest behavior with a static or directly checked-in runtime manifest aligned with the static suite.
- Simplify validation so it verifies the checked-in suite config and manifest instead of testing renderer output.
- Remove or stop using the custom kube-burner config renderer when running the benchmark.
- Preserve existing benchmark output summaries and extractor behavior for standard and runtime class results.

## Capabilities

### New Capabilities

### Modified Capabilities
- `runtimeclass-benchmark-suite`: Benchmark execution shall use a checked-in static kube-burner suite config rather than generating the suite config at runtime.

## Impact

- Affected targets: `make benchmark`, `make benchmark-dry-run`, `make validate`, and config validation targets.
- Affected scripts: benchmark orchestration, renderer usage/removal, result extraction inputs, and validation helpers.
- Affected docs: README workflow, benchmark variables, result file descriptions, and manual verification steps.
- No new external dependencies are expected.
