## Context

The repository currently provisions a benchmark AKS cluster with system, Kata, gVisor, and Firecracker node pools. Only the Kata pool receives AKS-supported pod sandboxing through `--workload-runtime KataVmIsolation`, and bootstrap only manages the custom `kata-optimized` RuntimeClass. The default kube-burner suite measures `standard`, `kata`, and `kata-optimized`, leaving the gVisor and Firecracker node pools unused by default.

The upstream OpenSandbox AKS deploy examples provide two runtime installation patterns relevant here. gVisor is installed by applying a Kubernetes manifest that creates `RuntimeClass/gvisor` with handler `runsc` and a privileged installer DaemonSet scoped to the gVisor node pool. Firecracker is installed as a Kata Containers configuration: Helm installs Kata Deploy with only the `fc` shim enabled, creates `RuntimeClass/kata-fc`, configures devmapper on Firecracker nodes, and pre-pulls images into the devmapper snapshotter.

## Goals / Non-Goals

**Goals:**

- Make `make bootstrap-cluster` install repository-managed gVisor and Firecracker-backed Kata runtime support after cluster credentials are configured.
- Keep runtime installation scoped to the dedicated gVisor and Firecracker node pools created by the cluster lifecycle scripts.
- Use `kata-fc` as the actual Firecracker RuntimeClass name.
- Add gVisor and Firecracker entries to the static kube-burner suite and runtime manifest so one default benchmark invocation covers all five runtime keys.
- Keep the result key `firecracker` separate from the Kubernetes RuntimeClass value `kata-fc` for readable benchmark output.

**Non-Goals:**

- Make gVisor or Firecracker a generally supported AKS production feature.
- Replace AKS-supported `kata-vm-isolation` for the existing Kata benchmark.
- Add dynamic runtime matrix generation or per-runtime benchmark control flow.
- Implement rollback of node host mutations beyond deleting Kubernetes installer resources or deleting/reimaging runtime node pools.
- Add image-building, registry, or OpenSandbox server deployment behavior from the upstream repository.

## Decisions

### Decision: Vendor Minimal Runtime Manifests

Add repository-managed manifests under runtime-specific deploy directories rather than fetching raw manifests from GitHub during bootstrap.

Rationale: Bootstrap should be reproducible, inspectable, and dry-run friendly. Vendoring also avoids network dependency and upstream drift changing benchmark behavior unexpectedly.

Alternatives considered:

- Fetch upstream manifests at bootstrap time. Rejected because it makes benchmark setup depend on external availability and mutable upstream content.
- Reimplement everything inline in `bootstrap-cluster.sh`. Rejected because the Firecracker path is large enough that separate manifests are easier to review and maintain.

### Decision: Firecracker Uses RuntimeClass `kata-fc`

Use `FIRECRACKER_RUNTIME_CLASS ?= kata-fc` and configure benchmark pods with `runtimeClassName: kata-fc`.

Rationale: Upstream Firecracker support is a Kata Containers Firecracker shim deployment, not a standalone `firecracker` runtime handler. Keeping the Kubernetes RuntimeClass aligned with upstream avoids inventing an alias that could hide the runtime's actual implementation.

Alternatives considered:

- Create `RuntimeClass/firecracker`. Rejected because it diverges from upstream and obscures that Firecracker is reached through Kata's `fc` shim.

### Decision: Keep Benchmark Key `firecracker`

Keep the runtime manifest entry as `key: firecracker` and `runtimeClass: kata-fc`.

Rationale: Benchmark result keys describe the experiment in human terms, while runtimeClass values must match Kubernetes resources. This matches the existing `standard` key pattern, where the key is an output label rather than a Kubernetes RuntimeClass resource.

Alternatives considered:

- Use `key: kata-fc`. Rejected because the benchmark matrix should compare runtime families, and `firecracker` is clearer in summaries.

### Decision: Bootstrap Installs and Verifies RuntimeClasses

Extend bootstrap to install gVisor and Firecracker resources, wait for installer DaemonSets, and verify `RuntimeClass/gvisor` and `RuntimeClass/kata-fc` exist before the benchmark runs.

Rationale: `make cluster-create` already invokes bootstrap after credentials are available, so fresh clusters and re-bootstrap flows should converge on the same runtime-ready state.

Alternatives considered:

- Add separate `gvisor-install` and `firecracker-install` Make targets only. Rejected because the user explicitly wants these installed in bootstrap and because benchmark defaults should not require extra manual runtime setup.

## Risks / Trade-offs

- Firecracker installation mutates managed node host files and restarts containerd -> keep it scoped to the dedicated Firecracker node pool and document that reimage/delete is the clean rollback path.
- Firecracker requires Helm and a reachable Kata Deploy chart -> validate `helm` before non-dry-run Firecracker installation and expose the chart URL as a Make variable.
- Installer DaemonSets can report rollout success before containerd restart fully settles -> keep explicit waits and RuntimeClass verification, and consider smoke pods only if runtime readiness proves unreliable.
- Upstream gVisor installer uses `latest` release assets -> vendor the manifest but preserve the upstream behavior initially; pinning a gVisor release can be a later hardening change.
- Benchmark pause image may need Firecracker/devmapper pre-pull behavior -> align Firecracker pre-pull with the benchmark container image or document the default image constraint.

## Migration Plan

1. Add vendored gVisor and Firecracker runtime deploy manifests based on the upstream OpenSandbox AKS deploy examples.
2. Add Make defaults for `KATA_DEPLOY_CHART` and set `FIRECRACKER_RUNTIME_CLASS` to `kata-fc`.
3. Extend bootstrap to render/apply manifests, wait for installers, and verify `gvisor` and `kata-fc` RuntimeClasses.
4. Add `gvisor` and `firecracker` kube-burner jobs to the static suite config with matching node selectors and tolerations.
5. Add matching runtime manifest entries and update baseline validation fixtures and expectations.
6. Update README setup and verification guidance.

Rollback for a failed runtime installation is to delete the installer namespaces/resources and delete or reimage the affected dedicated runtime node pool. For Firecracker specifically, removing Kubernetes resources does not fully revert host containerd/devmapper mutations.

## Open Questions

- Should Firecracker pre-pull include only the benchmark pause image, or also keep the upstream `python:3.12-slim` smoke image for optional manual testing?
- Should bootstrap run smoke pods for gVisor and Firecracker, or is RuntimeClass existence plus installer rollout enough for the default benchmark flow?
