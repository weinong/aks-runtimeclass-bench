## 1. Static Suite Inputs

- [x] 1.1 Add a checked-in kube-burner runtime class suite config that explicitly defines the standard baseline and static runtime class jobs.
- [x] 1.2 Add a checked-in runtime manifest whose runtime keys and labels match the static suite config.
- [x] 1.3 Ensure the static suite config uses a single obvious placeholder for the per-run metrics directory.

## 2. Benchmark Orchestration

- [x] 2.1 Update `scripts/run-benchmark.sh` to copy or prepare the static suite config under `results/<RUN_ID>/kube-burner.yml`.
- [x] 2.2 Update `scripts/run-benchmark.sh` to substitute only the per-run metrics directory placeholder before invoking kube-burner.
- [x] 2.3 Update `scripts/run-benchmark.sh` to copy the static runtime manifest under `results/<RUN_ID>/runtime-manifest.json`.
- [x] 2.4 Remove renderer usage from the benchmark and dry-run paths while preserving the printed kube-burner and extraction commands.

## 3. Validation And Cleanup

- [x] 3.1 Update Make validation targets to validate the static config and manifest instead of renderer output.
- [x] 3.2 Update or remove renderer-specific validation assertions that no longer apply.
- [x] 3.3 Remove `scripts/render-kube-burner-config.py` if it has no remaining callers.
- [x] 3.4 Update baseline validation to assert the copied static config, manifest, and summaries remain aligned.

## 4. Documentation And Verification

- [x] 4.1 Update README workflow, variables, and result file descriptions to describe the static suite config source of truth.
- [x] 4.2 Document the migration path for changing runtime topology by editing the static suite config and aligned manifest.
- [x] 4.3 Run `make validate` and confirm dry-run output still produces a self-contained result root.
