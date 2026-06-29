SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
.EXPORT_ALL_VARIABLES:

# Azure resource configuration.
AZURE_SUBSCRIPTION ?=
RESOURCE_GROUP ?= rg-aks-runtimeclass-bench
CLUSTER_NAME ?= aks-runtimeclass-bench
LOCATION ?= westus3
VM_SIZE ?= Standard_D8s_v5
KUBERNETES_VERSION ?=
CLUSTER_EXTRA_ARGS ?=

# AKS node pool topology. Runtime-specific extra args intentionally stay
# configurable because gVisor and Firecracker flags can be environment-specific.
SYSTEM_NODEPOOL_NAME ?= sys
SYSTEM_OS_SKU ?= AzureLinux
RUNTIME_OS_SKU ?= AzureLinux
KATA_NODEPOOL_NAME ?= kata
KATA_RUNTIME_CLASS ?= kata-vm-isolation
KATA_NODE_LABELS ?= runtimeclass=kata
KATA_NODE_TAINTS ?= runtimeclass=kata:NoSchedule
KATA_NODEPOOL_EXTRA_ARGS ?= --workload-runtime KataVmIsolation
KATA_OPTIMIZED_RUNTIME_CLASS ?= kata-optimized
KATA_OPTIMIZED_RUNTIME_OVERHEAD_MEMORY ?= 32Mi
PROMETHEUS_MANIFEST ?= manifests/prometheus/prometheus.yml
PROMETHEUS_NAMESPACE ?= runtimeclass-bench-prometheus
PROMETHEUS_SERVICE_NAME ?= prometheus
PROMETHEUS_SYSTEM_NODE_SELECTOR_KEY ?= kubernetes.azure.com/agentpool
PROMETHEUS_SYSTEM_NODE_SELECTOR_VALUE ?= $(SYSTEM_NODEPOOL_NAME)
PROMETHEUS_ROLLOUT_TIMEOUT ?= 5m
PROMETHEUS_LOCAL_PORT ?= 9090
PROMETHEUS_REMOTE_PORT ?= 9090
PROMETHEUS_PORT_FORWARD_ADDRESS ?= 127.0.0.1
PROMETHEUS_PORT_FORWARD_TIMEOUT ?= 30s
GVISOR_NODEPOOL_NAME ?= gvisor
GVISOR_RUNTIME_CLASS ?= gvisor
GVISOR_NODE_LABELS ?= runtimeclass=gvisor
GVISOR_NODE_TAINTS ?= runtimeclass=gvisor:NoSchedule
GVISOR_NODEPOOL_EXTRA_ARGS ?=
FIRECRACKER_NODEPOOL_NAME ?= firecracker
FIRECRACKER_RUNTIME_CLASS ?= kata-fc
FIRECRACKER_NODE_LABELS ?= runtimeclass=firecracker
FIRECRACKER_NODE_TAINTS ?= runtimeclass=firecracker:NoSchedule
FIRECRACKER_NODEPOOL_EXTRA_ARGS ?=
KATA_DEPLOY_CHART ?= oci://quay.io/kata-containers/kata-deploy-charts/kata-deploy
TEARDOWN_SCOPE ?= cluster

# kube-burner installation.
KUBE_BURNER_VERSION ?= v2.7.3
KUBE_BURNER_OS ?= auto
KUBE_BURNER_ARCH ?= auto
TOOLS_DIR ?= tools

# Benchmark workload configuration.
POD_TEMPLATE ?= templates/runtimeclass-pod.yml
KUBE_BURNER_CONFIG ?= configs/kube-burner-runtimeclass-suite.yml
KUBE_BURNER_PROMETHEUS_ENDPOINT ?= http://$(PROMETHEUS_PORT_FORWARD_ADDRESS):$(PROMETHEUS_LOCAL_PORT)
KUBE_BURNER_PROMETHEUS_METRICS_CONFIG ?= configs/kubelet-startup-metrics.yml
RUNTIME_MANIFEST ?= configs/runtime-manifest.json
BENCHMARK_TIMEOUT ?= 4h
KUBE_CONTEXT ?=
OUTPUT_DIR ?= results
RUN_ID ?= runtimeclass-$(shell date -u +%Y%m%dT%H%M%SZ)
CSV_OUTPUT ?= true
DRY_RUN ?= 0

.PHONY: help cluster-create bootstrap-cluster cluster-delete kube-burner-install prometheus-port-forward benchmark benchmark-with-port-forward benchmark-dry-run validate validate-make validate-shell validate-config validate-port-forward-targets validate-runtime-install-images test-extract validate-benchmark-baseline clean-results

help:
	@printf 'AKS runtime class benchmark targets:\n'
	@printf '  make cluster-create        Create/update AKS cluster and runtime node pools\n'
	@printf '  make bootstrap-cluster     Apply repository-managed Kubernetes components\n'
	@printf '  make cluster-delete        Delete cluster or resource group resources\n'
	@printf '  make kube-burner-install   Install kube-burner under $(TOOLS_DIR)/\n'
	@printf '  make prometheus-port-forward  Forward local Prometheus traffic to the in-cluster service\n'
	@printf '  make benchmark             Run kube-burner and extract JSON/CSV summaries\n'
	@printf '  make benchmark-with-port-forward  Start Prometheus port-forward, run benchmark, then stop it\n'
	@printf '  make benchmark-dry-run     Prepare benchmark inputs and print the commands\n'
	@printf '  make validate              Run local syntax, config, and extractor checks\n'
	@printf '\nCommon overrides:\n'
	@printf '  RESOURCE_GROUP=%s CLUSTER_NAME=%s LOCATION=%s VM_SIZE=%s\n' '$(RESOURCE_GROUP)' '$(CLUSTER_NAME)' '$(LOCATION)' '$(VM_SIZE)'
	@printf '  KUBE_BURNER_CONFIG=%s RUNTIME_MANIFEST=%s OUTPUT_DIR=%s\n' '$(KUBE_BURNER_CONFIG)' '$(RUNTIME_MANIFEST)' '$(OUTPUT_DIR)'

cluster-create:
	@scripts/cluster-create.sh

bootstrap-cluster:
	@scripts/bootstrap-cluster.sh

cluster-delete:
	@scripts/cluster-delete.sh

kube-burner-install:
	@scripts/install-kube-burner.sh

prometheus-port-forward:
	@scripts/prometheus-port-forward.sh

benchmark:
	@scripts/run-benchmark.sh

benchmark-with-port-forward:
	@scripts/run-benchmark-with-port-forward.sh

benchmark-dry-run:
	@$(MAKE) benchmark DRY_RUN=1

validate: validate-make validate-shell validate-config validate-port-forward-targets validate-runtime-install-images test-extract validate-benchmark-baseline

validate-make:
	@$(MAKE) --dry-run help >/dev/null
	@$(MAKE) --dry-run bootstrap-cluster DRY_RUN=1 >/dev/null
	@$(MAKE) --dry-run benchmark DRY_RUN=1 >/dev/null

validate-shell:
	@bash -n scripts/*.sh
	@python3 -m py_compile scripts/*.py

validate-config:
	@mkdir -p results/validation
	@test -s $(KUBE_BURNER_CONFIG)
	@test -s $(RUNTIME_MANIFEST)
	@test -s $(POD_TEMPLATE)

validate-port-forward-targets:
	@test -s scripts/prometheus-port-forward.sh
	@test -s scripts/run-benchmark-with-port-forward.sh
	@test -x scripts/prometheus-port-forward.sh
	@test -x scripts/run-benchmark-with-port-forward.sh
	@$(MAKE) prometheus-port-forward DRY_RUN=1 >/dev/null
	@rm -rf results/validation-port-forward
	@$(MAKE) benchmark-with-port-forward DRY_RUN=1 OUTPUT_DIR=results/validation-port-forward RUN_ID=fixture >/dev/null
	@rm -rf results/validation-port-forward

validate-runtime-install-images:
	@python3 scripts/validate-runtime-install-images.py

test-extract:
	@mkdir -p results/validation
	@scripts/extract-results.py tests/fixtures/kube-burner-metrics --output-dir results/validation --run-id fixture --runtime-class kata-vm-isolation

validate-benchmark-baseline:
	@rm -rf results/validation-baseline
	@mkdir -p results/validation-baseline
	@$(MAKE) benchmark DRY_RUN=1 OUTPUT_DIR=results/validation-baseline RUN_ID=fixture >/dev/null
	@scripts/extract-results.py tests/fixtures/kube-burner-suite-metrics --output-dir results/validation-baseline/fixture --run-id fixture --runtime-manifest results/validation-baseline/fixture/runtime-manifest.json
	@python3 scripts/validate-benchmark-baseline.py --output-dir results/validation-baseline --run-id fixture --prometheus-manifest "$(PROMETHEUS_MANIFEST)" --prometheus-metrics-profile "$(KUBE_BURNER_PROMETHEUS_METRICS_CONFIG)" --prometheus-endpoint "$(KUBE_BURNER_PROMETHEUS_ENDPOINT)"

clean-results:
	@rm -rf results/*
	@touch results/.gitkeep
