## 1. Make Target Wiring

- [ ] 1.1 Update `.PHONY` targets so `benchmark` remains the primary public target and a direct benchmark target exists for lower-level execution.
- [ ] 1.2 Repoint `benchmark` to invoke `scripts/run-benchmark-with-port-forward.sh`.
- [ ] 1.3 Add or update the direct benchmark target to invoke `scripts/run-benchmark.sh` without managing Prometheus port-forward lifecycle.
- [ ] 1.4 Remove or stop advertising `benchmark-with-port-forward` unless implementation review finds an in-repository compatibility need.

## 2. References And Validation

- [ ] 2.1 Update Makefile help text to describe `make benchmark` as the full port-forward-managed benchmark workflow.
- [ ] 2.2 Update validation targets so dry-run validation exercises the new `benchmark` behavior and the direct benchmark path where appropriate.
- [ ] 2.3 Search repository files for `benchmark-with-port-forward` and update stale references to the new target names.

## 3. Verification

- [ ] 3.1 Run `make validate-make` to verify Make target wiring.
- [ ] 3.2 Run `make validate-port-forward-targets` to verify the port-forward benchmark dry-run workflow.
- [ ] 3.3 Run `openspec status --change "rename-benchmark-make-target"` to confirm the change remains apply-ready.
