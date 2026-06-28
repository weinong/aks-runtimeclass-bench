## 1. Runtime Install Assets

- [ ] 1.1 Add repository-managed gVisor installer and optional smoke pod manifests based on upstream OpenSandbox AKS deploy assets.
- [ ] 1.2 Add repository-managed Firecracker runtime assets based on upstream OpenSandbox AKS deploy assets, including Kata `fc` values, devmapper installer, pre-pull manifest, and optional smoke pod manifest.
- [ ] 1.3 Ensure runtime manifests use placeholders for configured gVisor and Firecracker node pool names.

## 2. Bootstrap Integration

- [ ] 2.1 Add Make defaults needed by bootstrap, including `KATA_DEPLOY_CHART` and `FIRECRACKER_RUNTIME_CLASS ?= kata-fc`.
- [ ] 2.2 Extend `scripts/bootstrap-cluster.sh` to render and apply the gVisor installer to the configured gVisor node pool.
- [ ] 2.3 Extend `scripts/bootstrap-cluster.sh` to install Kata Deploy with the Firecracker `fc` shim and apply devmapper/pre-pull resources to the configured Firecracker node pool.
- [ ] 2.4 Add non-dry-run validation for `RuntimeClass/gvisor` handler `runsc` and `RuntimeClass/kata-fc` handler `kata-fc`.
- [ ] 2.5 Preserve dry-run behavior by printing the commands and rendered-apply flow without mutating a cluster.

## 3. Benchmark Matrix

- [ ] 3.1 Add a gVisor kube-burner job to `configs/kube-burner-runtimeclass-suite.yml` with `runtimeClass: gvisor`, gVisor node selector, and gVisor toleration.
- [ ] 3.2 Add a Firecracker kube-burner job to `configs/kube-burner-runtimeclass-suite.yml` with runtime key `firecracker`, `runtimeClass: kata-fc`, Firecracker node selector, and Firecracker toleration.
- [ ] 3.3 Add `gvisor` and `firecracker` entries to `configs/runtime-manifest.json`, with Firecracker mapped to `kata-fc`.
- [ ] 3.4 Update validation fixtures and baseline validation expectations for five default runtime entries.

## 4. Documentation and Verification

- [ ] 4.1 Update README prerequisites, workflow, runtime key list, and manual verification steps for gVisor and Firecracker-backed Kata.
- [ ] 4.2 Run `make validate` and resolve any local validation failures.
- [ ] 4.3 Run `make benchmark-dry-run` and confirm the rendered suite includes `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker` jobs.
- [ ] 4.4 Document any manual AKS verification that cannot be completed locally, including expected `kubectl get runtimeclass gvisor kata-fc` checks.
