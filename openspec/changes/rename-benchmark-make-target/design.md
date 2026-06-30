## Context

The Makefile currently has two benchmark entry points: `benchmark`, which directly invokes `scripts/run-benchmark.sh`, and `benchmark-with-port-forward`, which invokes `scripts/run-benchmark-with-port-forward.sh`. The wrapper script is the operator-friendly path when Prometheus is exposed through a local `kubectl port-forward`, but its long target name makes it feel secondary to the direct benchmark target.

## Goals / Non-Goals

**Goals:**

- Make `make benchmark` the primary operator target for a complete benchmark run with Prometheus port-forward lifecycle management.
- Preserve a Make-accessible direct benchmark path for the port-forward wrapper and validation logic.
- Keep the implementation limited to Make target wiring and repository references.

**Non-Goals:**

- Change benchmark scripts, kube-burner configuration, Prometheus manifests, or result extraction behavior.
- Add compatibility aliases unless implementation review finds an existing automated reference that still needs a transition path.

## Decisions

- Repoint `benchmark` to `scripts/run-benchmark-with-port-forward.sh` so the shortest documented command runs the complete workflow operators normally need.
- Introduce a clearly named lower-level Make target for direct `scripts/run-benchmark.sh` execution, such as `benchmark-direct`, so scripts and validation can still invoke the underlying benchmark without recursively calling the port-forward wrapper.
- Update help and validation references to avoid advertising `benchmark-with-port-forward` as the preferred command.
- Search repository documentation and automation for `benchmark-with-port-forward` references during implementation so stale commands are updated alongside the Makefile.

## Risks / Trade-offs

- Existing users may expect `make benchmark` to run without starting a port-forward -> Document and validate the changed behavior through the spec and help text.
- The port-forward wrapper may call `make benchmark` internally or otherwise assume direct target semantics -> Preserve a direct target and update the wrapper if it shells through Make.
- External users may still call `make benchmark-with-port-forward` -> Do not retain the alias unless repository evidence shows a concrete compatibility need.
