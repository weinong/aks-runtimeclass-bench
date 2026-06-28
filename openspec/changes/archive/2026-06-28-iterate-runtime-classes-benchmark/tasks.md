## 1. Runtime Inventory

- [x] 1.1 Add Make/script configuration for an enabled benchmark runtime inventory that includes standard, Kata, gVisor, and Firecracker defaults.
- [x] 1.2 Parse each runtime entry into a stable key, runtime class value, node selector, and tolerations JSON in the benchmark orchestration script.
- [x] 1.3 Preserve operator override support for changing the enabled runtime inventory without editing benchmark control flow.

## 2. Benchmark Execution

- [x] 2.1 Update `scripts/run-benchmark.sh` so one `make benchmark` invocation iterates all enabled runtime entries by default.
- [x] 2.2 Render one kube-burner suite config with the correct runtime class, selector, and tolerations for each runtime job.
- [x] 2.3 Store raw metrics, rendered config, runtime manifest, and summaries under a single `results/<RUN_ID>` result root.
- [x] 2.4 Ensure dry-run mode prints the kube-burner command and creates inspectable rendered config without invoking kube-burner.

## 3. Aggregate Results

- [x] 3.1 Add extraction logic that groups single-run kube-burner metrics by runtime job into top-level `summary.json`.
- [x] 3.2 Add extraction logic that writes runtime-keyed rows into top-level `summary.csv` when CSV output is enabled.
- [x] 3.3 Fail extraction with a clear error when expected runtime metrics are missing or malformed.

## 4. Validation and Documentation

- [x] 4.1 Update validation helpers to assert the default dry-run creates one result root containing a generated suite config for standard and configured runtime entries.
- [x] 4.2 Update fixture-based validation to verify aggregate JSON/CSV summaries include all runtime entries.
- [x] 4.3 Update `README.md` workflow, variables, result layout, and manual verification steps for the zero-argument `make benchmark` flow.
- [x] 4.4 Run `make validate` and fix any regressions.
