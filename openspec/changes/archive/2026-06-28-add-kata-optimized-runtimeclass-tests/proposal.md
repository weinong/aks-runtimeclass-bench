## Why

The benchmark suite currently measures the standard runtime and the existing Kata runtime class, but it does not cover the optimized Kata runtime class shape that uses a fixed pod memory overhead. Adding this runtime to cluster setup and the static benchmark suite makes optimized Kata startup latency visible in the same run as the existing baseline and Kata measurements.

## What Changes

- Add a reusable `bootstrap-cluster` Make target for applying repository-managed Kubernetes components to the benchmark cluster.
- Use `bootstrap-cluster` to install the `kata-optimized` Kubernetes `RuntimeClass`.
- Configure the new runtime class with `overhead.podFixed.memory: 32Mi`.
- Verify the new runtime class exists as part of cluster bootstrap validation.
- Add a checked-in kube-burner suite job targeting `runtimeClassName: kata-optimized`.
- Add a matching runtime manifest entry so extraction and aggregate summaries include `kata-optimized` results.
- Update validation and documentation to keep the static suite config, runtime manifest, and expected runtime keys aligned.

## Capabilities

### New Capabilities

### Modified Capabilities

- `runtimeclass-benchmark-suite`: The benchmark suite shall provide a reusable cluster bootstrap target, install the `kata-optimized` runtime class through that target, and collect benchmark results for it alongside existing runtime entries.

## Impact

- Affected cluster lifecycle/bootstrap code: Make targets, cluster setup handoff, bootstrap script or manifests, and variables that define runtime class names and placement metadata.
- Affected benchmark inputs: `configs/kube-burner-runtimeclass-suite.yml` and `configs/runtime-manifest.json`.
- Affected validation/tests: config/manifest alignment checks, extractor fixture expectations, and any tests that assert the default runtime matrix.
- Affected docs: README runtime list and manual verification steps.
