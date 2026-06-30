## 1. CSV Schema Update

- [x] 1.1 Remove aggregate CSV environment metadata fields from `scripts/extract-results.py`.
- [x] 1.2 Ensure aggregate CSV rows still include `run_id`, `runtime_key`, `runtime_class`, `metric_category`, `condition`, `metric_name`, `metric_family`, `unit`, `p50`, `p95`, and `p99`.
- [x] 1.3 Remove now-unused CSV environment helper code if it no longer serves another path.

## 2. Tests And Fixtures

- [x] 2.1 Update `tests/fixtures/expected-suite-summary.csv` to the slim aggregate CSV schema.
- [x] 2.2 Update extractor tests to assert JSON environment metadata remains present while CSV rows omit environment columns.
- [x] 2.3 Update baseline validation to stop requiring environment metadata columns in aggregate CSV.

## 3. Documentation And Verification

- [x] 3.1 Update README output documentation for the slim `summary.csv` schema and JSON/environment metadata source of environment context.
- [x] 3.2 Run the extractor test suite and repository validation target.
- [x] 3.3 Confirm OpenSpec validation passes for `slim-summary-csv`.
