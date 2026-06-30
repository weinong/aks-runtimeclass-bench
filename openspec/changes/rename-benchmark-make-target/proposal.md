## Why

The benchmark workflow currently exposes the complete Prometheus port-forwarded run as `make benchmark-with-port-forward`, while `make benchmark` runs the lower-level benchmark script directly. This makes the primary benchmark command less discoverable and encourages operators to run a target that can fail when Prometheus is only available through the local port-forward workflow.

## What Changes

- Make `make benchmark` start the Prometheus port-forward, run the benchmark, and stop the port-forward through the existing wrapper script.
- Move the direct kube-burner invocation behind an internal or explicitly named target so validation and dry-run paths can still exercise it when needed.
- Remove or stop advertising the `benchmark-with-port-forward` Make target as the primary operator command.
- Update validation and help text to use the new primary benchmark target behavior.
- **BREAKING**: `make benchmark` changes from direct kube-burner execution to the full port-forward-managed benchmark workflow.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: The benchmark Make target requirement changes so `make benchmark` represents the complete operator benchmark workflow, including Prometheus port-forward lifecycle management.

## Impact

- Affected code: `Makefile`, benchmark validation targets, and any documentation or references that mention `benchmark-with-port-forward`.
- Affected scripts: existing benchmark scripts should be reused; no new dependency is expected.
- Affected user workflow: operators will run `make benchmark` for the full benchmark workflow.
