## Context

The repository now uses a static kube-burner suite config and a static runtime manifest as the source of truth for benchmark runtime entries. Cluster setup creates the benchmark AKS cluster, provisions runtime-specific node pools, and verifies the default AKS Kata runtime class `kata-vm-isolation` after the pod sandboxing node pool update. There is not yet a separate target for applying repository-managed Kubernetes components after the cluster exists.

The requested `kata-optimized` runtime class is a custom Kubernetes `RuntimeClass` that should use the same Kata handler as AKS pod sandboxing while overriding pod overhead with `overhead.podFixed.memory: 32Mi`. Kubernetes and AKS documentation use `memory` under `podFixed`; the requested `memoery` spelling is treated as a typo.

## Goals / Non-Goals

**Goals:**
- Add a reusable `make bootstrap-cluster` target for applying repository-managed Kubernetes components to the benchmark cluster.
- Create or update a `kata-optimized` runtime class from `make bootstrap-cluster`.
- Configure `kata-optimized` with handler `kata` and fixed pod memory overhead `32Mi`.
- Add `kata-optimized` to the checked-in kube-burner runtime suite and runtime manifest.
- Keep the optimized Kata benchmark scheduled to the existing Kata node pool unless implementation discovers a need for a distinct node pool.
- Update local validation so config, manifest, fixture summaries, and expected runtime keys include `kata-optimized`.

**Non-Goals:**
- Add a new AKS node pool solely for `kata-optimized`.
- Change the default `kata-vm-isolation` runtime class installed by AKS.
- Add dynamic runtime discovery or generated benchmark matrix logic.
- Change pod latency metric selection, result schema, kube-burner versioning, or benchmark iteration counts beyond adding the new job.

## Decisions

1. Add `bootstrap-cluster` as the Kubernetes component installation boundary.

   Add a Make target such as `bootstrap-cluster` that runs after cluster credentials are available and applies repository-managed Kubernetes resources. `make cluster-create` should either invoke this target or call the same bootstrap script so a fresh cluster receives required components automatically, while operators can rerun `make bootstrap-cluster` independently when components change.

   Alternative considered: keep applying custom resources directly inside `scripts/cluster-create.sh`. That works for a single runtime class, but it mixes Azure cluster provisioning with Kubernetes add-on installation and makes future components harder to reason about.

2. Manage `kata-optimized` explicitly through cluster bootstrap.

   Add a small checked-in manifest or explicit bootstrap apply step that creates the `RuntimeClass` with `apiVersion: node.k8s.io/v1`, `handler: kata`, and `overhead.podFixed.memory: 32Mi`. Run it from the bootstrap path after cluster credentials are available and after the pod sandboxing update that makes the Kata handler usable.

   Alternative considered: require users to apply the runtime class manually before benchmarking. That makes the benchmark matrix non-repeatable and does not satisfy the requirement that adding this runtime class is part of cluster setup.

3. Verify the custom runtime class and its overhead after applying it.

   Extend cluster validation beyond existence for `kata-optimized` by checking the runtime class handler and memory overhead. This catches typo-level mistakes in the manifest and prevents benchmark runs from silently targeting an incorrectly configured runtime class.

   Alternative considered: only verify object existence, matching current `kata-vm-isolation` validation. Existence alone is insufficient because the value being tested is the optimized overhead configuration.

4. Reuse the existing Kata placement settings for the optimized job.

   The optimized runtime class changes runtime overhead, not node placement. The kube-burner job should use `runtimeClass: "kata-optimized"`, a distinct `runtimeKey`, and the same `runtimeclass: "kata"` node selector and toleration as the existing Kata job.

   Alternative considered: create a separate `runtimeclass=kata-optimized` node label or node pool. That adds cluster topology without a scheduling requirement and would make comparisons less direct.

5. Keep static suite and manifest alignment as the benchmark contract.

   Add a new kube-burner job named `runtimeclass-pod-latency-kata-optimized` and a manifest entry `{ "key": "kata-optimized", "runtimeClass": "kata-optimized" }`. Update validation fixtures or assertions so aggregate summaries must include `standard`, `kata`, and `kata-optimized`.

   Alternative considered: teach the extractor to infer runtime keys from kube-burner job names. That reintroduces derived topology and weakens the explicit manifest contract.

## Risks / Trade-offs

- `32Mi` overhead may be too low for some Kata host-component usage -> Preserve the requested value for the optimized benchmark and document that this runtime exists to measure that specific configuration.
- The `kata` handler may not be available until AKS pod sandboxing is enabled and credentials are refreshed -> Run bootstrap after `az aks update` and `az aks get-credentials`; make `bootstrap-cluster` rerunnable for already-created clusters.
- Fixture metrics must include a third runtime or extractor validation will fail -> Update suite fixture data and baseline validation together with the static config and manifest.
- Reusing the Kata node pool means both Kata runtime classes compete for the same runtime pool during one benchmark invocation -> Accept because the existing suite already runs all jobs together and the runtime class difference should be isolated to pod overhead rather than node topology.
