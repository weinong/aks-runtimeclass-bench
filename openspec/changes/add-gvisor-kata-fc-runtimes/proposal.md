## Why

The benchmark cluster already provisions dedicated gVisor and Firecracker node pools, but bootstrap does not install those runtime handlers and the default benchmark matrix only measures standard, Kata, and optimized Kata. Adding gVisor and Kata Firecracker makes the default suite match the intended runtime topology and produces comparable pod latency results for all runtime pools.

## What Changes

- Bootstrap installs gVisor runtime support on the gVisor node pool using the upstream OpenSandbox gVisor installer pattern.
- Bootstrap installs Firecracker-backed Kata support on the Firecracker node pool using the upstream OpenSandbox Kata Deploy `fc` shim and devmapper setup pattern.
- Firecracker benchmark pods use Kubernetes `runtimeClassName: kata-fc`.
- The default kube-burner runtime matrix adds `gvisor` and `firecracker` entries alongside `standard`, `kata`, and `kata-optimized`.
- Result manifests and validation expect five runtime keys: `standard`, `kata`, `kata-optimized`, `gvisor`, and `firecracker`.
- Documentation explains the runtime installation behavior, including that `firecracker` is a benchmark key and `kata-fc` is the actual RuntimeClass.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `runtimeclass-benchmark-suite`: Bootstrap and default benchmark requirements change to install and test gVisor plus Firecracker-backed Kata through `kata-fc`.

## Impact

- Affected files include `Makefile`, `scripts/bootstrap-cluster.sh`, `configs/kube-burner-runtimeclass-suite.yml`, `configs/runtime-manifest.json`, validation fixtures, baseline validation, and `README.md`.
- New repository-managed deploy manifests are expected for gVisor and Firecracker runtime installation.
- Bootstrap will depend on `kubectl`; Firecracker installation will also depend on Helm-compatible `helm` being available unless the implementation vendors another install path.
- Firecracker installation mutates managed node host containerd and devmapper state on the dedicated Firecracker node pool; it should remain scoped to disposable benchmark nodes.
