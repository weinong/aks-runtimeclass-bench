## 1. Benchmark Orchestration

- [x] 1.1 Refactor benchmark execution so the existing kube-burner invocation can be run for one runtime at a time.
- [x] 1.2 Update `make benchmark` to run a default-runtime baseline with `RUNTIME_CLASS` unset before any explicit runtime class benchmark.
- [x] 1.3 Skip duplicate execution when `RUNTIME_CLASS` is unset so `make benchmark` runs the default baseline exactly once.
- [x] 1.4 Ensure baseline and explicit runtime runs use distinct run IDs or output directories.

## 2. Baseline Behavior

- [x] 2.1 Ensure the baseline run renders pods without a `runtimeClassName` field.
- [x] 2.2 Ensure the baseline JSON summary records `runtimeClass` as `standard`.
- [x] 2.3 Ensure the baseline CSV summary records `runtime_class` as `standard`.
- [x] 2.4 Keep explicit runtime summaries labeled with the requested runtime class.

## 3. Documentation And Verification

- [x] 3.1 Update README usage and result layout documentation to explain that `make benchmark` always includes the default baseline.
- [x] 3.2 Update `make benchmark-dry-run` or validation coverage to verify baseline-plus-selected-runtime orchestration.
- [x] 3.3 Run `make validate` and confirm both default-runtime and explicit runtime validation paths pass.
