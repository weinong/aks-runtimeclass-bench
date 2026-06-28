## Why

Operators currently need to pass `RUNTIME_CLASS`, `NODE_SELECTOR`, and `TOLERATIONS_JSON` to benchmark a runtime, and `make benchmark` emits separate result directories for the baseline and requested runtime. This makes the default workflow cumbersome and does not scale cleanly as additional runtime classes are added.

## What Changes

- Change `make benchmark` so the default invocation automatically runs the standard runtime plus every configured runtime class benchmark.
- Replace the single-runtime default flow with a generated kube-burner suite config containing one job per runtime.
- Produce one result for the benchmark invocation directly from the single kube-burner metrics output instead of aggregating separate runtime runs.
- Keep the runtime set configurable so future runtime classes can be added without changing the benchmark control flow.
- Update validation and documentation to describe the zero-argument benchmark workflow.

## Capabilities

### New Capabilities

### Modified Capabilities
- `runtimeclass-benchmark-suite`: Change benchmark execution requirements so a single `make benchmark` runs all configured runtime classes and writes one combined result.

## Impact

- Affected targets: `make benchmark`, `make benchmark-dry-run`, and local validation targets that assert benchmark behavior.
- Affected scripts: benchmark orchestration, kube-burner config rendering, result extraction, and validation helpers.
- Affected docs: README workflow, benchmark variables, result file descriptions, and manual verification steps.
- No new external service dependencies are expected.
