## 1. Cluster Bootstrap

- [x] 1.1 Add a configurable `kata-optimized` runtime class name and overhead value to the cluster setup defaults.
- [x] 1.2 Add a reusable `bootstrap-cluster` Make target for applying repository-managed Kubernetes components to an existing benchmark cluster.
- [x] 1.3 Add a bootstrap script or manifest path that creates or updates the `kata-optimized` RuntimeClass with handler `kata` and `overhead.podFixed.memory: 32Mi`.
- [x] 1.4 Ensure `make cluster-create` invokes the same bootstrap path after cluster credentials are configured so fresh clusters receive required Kubernetes components automatically.
- [x] 1.5 Extend bootstrap validation to verify `kata-optimized` exists with handler `kata` and memory overhead `32Mi`.
- [x] 1.6 Preserve existing `kata-vm-isolation` validation and cluster node pool topology.

## 2. Benchmark Suite Matrix

- [x] 2.1 Add a `runtimeclass-pod-latency-kata-optimized` job to `configs/kube-burner-runtimeclass-suite.yml` targeting `runtimeClass: "kata-optimized"`.
- [x] 2.2 Configure the optimized job with `runtimeKey: "kata-optimized"` and the existing Kata node selector and toleration.
- [x] 2.3 Add a matching `kata-optimized` entry to `configs/runtime-manifest.json`.
- [x] 2.4 Ensure the prepared benchmark config and runtime manifest remain aligned for `standard`, `kata`, and `kata-optimized`.

## 3. Tests And Fixtures

- [x] 3.1 Update benchmark baseline validation expectations to include `kata-optimized`.
- [x] 3.2 Extend kube-burner suite fixture metrics with `runtimeclass-pod-latency-kata-optimized` quantiles for all required pod latency conditions.
- [x] 3.3 Update or add validation assertions that the prepared config contains the optimized runtime class and placement settings.
- [x] 3.4 Run `make validate` and fix any config, fixture, or extractor regressions.

## 4. Documentation

- [x] 4.1 Update README runtime key documentation to describe `kata-optimized`.
- [x] 4.2 Update manual verification steps to include `make bootstrap-cluster`, the custom `kata-optimized` RuntimeClass, and expected summary coverage.
