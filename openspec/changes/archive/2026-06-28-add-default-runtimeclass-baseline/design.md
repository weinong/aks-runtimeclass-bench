## Context

The current benchmark suite can render pods without `runtimeClassName` when `RUNTIME_CLASS` is empty, and the extractor already maps an empty runtime class to `standard` in summaries. However, `make benchmark` currently runs only the runtime selected by the caller. If an operator runs a sandboxed runtime benchmark without also running a default-runtime benchmark, the results lack a baseline for comparison.

This change makes the default runtime baseline part of benchmark execution. It should reuse the existing single-run behavior for each runtime, orchestrate one or two runs depending on `RUNTIME_CLASS`, and avoid changing cluster lifecycle, kube-burner configuration semantics, or the summary schema.

## Goals / Non-Goals

**Goals:**

- Make `make benchmark` always produce a default-runtime baseline with `RUNTIME_CLASS` unset.
- When an explicit runtime class is requested, produce both default-runtime and requested-runtime outputs from the same benchmark invocation.
- Avoid duplicate execution when `RUNTIME_CLASS` is unset and the requested benchmark is already the default runtime.
- Keep per-runtime outputs separate so summaries and raw metrics do not overwrite each other.
- Add local validation coverage for the automatic baseline behavior.

**Non-Goals:**

- Provision or validate AKS node pools for the default runtime.
- Introduce a new test framework or external dependency.
- Change the summary schema or rename the existing `standard` runtime label.
- Automatically benchmark every known sandboxed runtime; only the selected runtime and required baseline are in scope.

## Decisions

- Split benchmark execution into an orchestration layer and a single-runtime run path. The existing `scripts/run-benchmark.sh` logic can remain the single-runtime path, while `make benchmark` or a small wrapper decides whether to run baseline only or baseline plus selected runtime.
- Use `RUNTIME_CLASS` unset for the baseline run. This preserves the existing pod template behavior that omits `runtimeClassName` and keeps extractor summaries labeled as `standard`.
- Use distinct run IDs or subdirectories for baseline and selected runtime runs. For example, a caller-provided `RUN_ID` can become `<RUN_ID>-standard` and `<RUN_ID>-<runtime>` for the underlying single-runtime invocations.
- Keep `make benchmark-dry-run` aligned with `make benchmark` by showing the same baseline-plus-selected-runtime plan without invoking kube-burner.
- Extend `make validate` with deterministic local checks for the orchestration behavior, rendered baseline input, and standard summary label.

## Risks / Trade-offs

- `make benchmark` will take longer for explicit runtime classes because it runs the default baseline first -> Document the behavior and skip the second run when the requested runtime is already default.
- Existing consumers may expect one result directory per `RUN_ID` -> Use predictable suffixes or subdirectories and document the layout.
- Baseline scheduling may need a different node selector than sandboxed runtimes -> Keep baseline runtime class unset and allow baseline selector/toleration defaults to be empty unless explicit baseline-specific overrides are added during implementation.
- Multi-run orchestration can make failure handling ambiguous -> Fail the overall benchmark if either baseline or selected runtime run fails, leaving completed run artifacts for inspection.
- Generated validation artifacts may expand under `results/validation*` -> Use dedicated validation subdirectories and keep them ignored like existing result outputs.
