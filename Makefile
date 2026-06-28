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
GVISOR_NODEPOOL_NAME ?= gvisor
GVISOR_RUNTIME_CLASS ?= gvisor
GVISOR_NODE_LABELS ?= runtimeclass=gvisor
GVISOR_NODE_TAINTS ?= runtimeclass=gvisor:NoSchedule
GVISOR_NODEPOOL_EXTRA_ARGS ?=
FIRECRACKER_NODEPOOL_NAME ?= firecracker
FIRECRACKER_RUNTIME_CLASS ?= firecracker
FIRECRACKER_NODE_LABELS ?= runtimeclass=firecracker
FIRECRACKER_NODE_TAINTS ?= runtimeclass=firecracker:NoSchedule
FIRECRACKER_NODEPOOL_EXTRA_ARGS ?=
TEARDOWN_SCOPE ?= cluster

# kube-burner installation.
KUBE_BURNER_VERSION ?= v2.7.3
KUBE_BURNER_OS ?= auto
KUBE_BURNER_ARCH ?= auto
TOOLS_DIR ?= tools

# Benchmark workload configuration.
CONFIG_FILE ?= config/runtimeclass-pod-latency.yml
POD_TEMPLATE ?= templates/runtimeclass-pod.yml
RUNTIME_CLASS ?=
NODE_SELECTOR ?=
TOLERATIONS_JSON ?= []
BASELINE_NODE_SELECTOR ?=
BASELINE_TOLERATIONS_JSON ?= []
POD_COUNT ?= 35
POD_REPLICAS ?= 1
POD_IMAGE ?= mcr.microsoft.com/oss/v2/kubernetes/pause:3.10.2
POD_COMMAND_JSON ?= []
POD_CPU_REQUEST ?= 10m
POD_MEMORY_REQUEST ?= 32Mi
POD_CPU_LIMIT ?= 100m
POD_MEMORY_LIMIT ?= 128Mi
BENCHMARK_NAMESPACE ?= runtimeclass-bench
BENCHMARK_QPS ?= 20
BENCHMARK_BURST ?= 20
BENCHMARK_CLEANUP ?= true
BENCHMARK_WAIT_WHEN_FINISHED ?= true
BENCHMARK_POD_WAIT ?= true
BENCHMARK_TIMEOUT ?= 4h
KUBE_CONTEXT ?=
OUTPUT_DIR ?= results
RUN_ID ?= runtimeclass-$(shell date -u +%Y%m%dT%H%M%SZ)
CSV_OUTPUT ?= true
DRY_RUN ?= 0

.PHONY: help cluster-create cluster-delete kube-burner-install benchmark benchmark-dry-run validate validate-make validate-shell validate-config test-extract validate-benchmark-baseline clean-results

help:
	@printf 'AKS runtime class benchmark targets:\n'
	@printf '  make cluster-create        Create/update AKS cluster and runtime node pools\n'
	@printf '  make cluster-delete        Delete cluster or resource group resources\n'
	@printf '  make kube-burner-install   Install kube-burner under $(TOOLS_DIR)/\n'
	@printf '  make benchmark             Run kube-burner and extract JSON/CSV summaries\n'
	@printf '  make benchmark-dry-run     Render benchmark inputs and print the commands\n'
	@printf '  make validate              Run local syntax, rendering, and extractor checks\n'
	@printf '\nCommon overrides:\n'
	@printf '  RESOURCE_GROUP=%s CLUSTER_NAME=%s LOCATION=%s VM_SIZE=%s\n' '$(RESOURCE_GROUP)' '$(CLUSTER_NAME)' '$(LOCATION)' '$(VM_SIZE)'
	@printf '  RUNTIME_CLASS=%s NODE_SELECTOR=%s POD_COUNT=%s OUTPUT_DIR=%s\n' '$(RUNTIME_CLASS)' '$(NODE_SELECTOR)' '$(POD_COUNT)' '$(OUTPUT_DIR)'

cluster-create:
	@scripts/cluster-create.sh

cluster-delete:
	@scripts/cluster-delete.sh

kube-burner-install:
	@scripts/install-kube-burner.sh

benchmark:
	@scripts/run-benchmark.sh

benchmark-dry-run:
	@$(MAKE) benchmark DRY_RUN=1

validate: validate-make validate-shell validate-config test-extract validate-benchmark-baseline

validate-make:
	@$(MAKE) --dry-run help >/dev/null
	@$(MAKE) --dry-run benchmark DRY_RUN=1 >/dev/null

validate-shell:
	@bash -n scripts/*.sh
	@python3 -m py_compile scripts/*.py

validate-config:
	@mkdir -p results/validation
	@scripts/render-user-data.py > results/validation/user-data.yml
	@test -s results/validation/user-data.yml
	@test -s $(CONFIG_FILE)
	@test -s $(POD_TEMPLATE)

test-extract:
	@mkdir -p results/validation
	@scripts/extract-results.py tests/fixtures/kube-burner-metrics --output-dir results/validation --run-id fixture --runtime-class kata-vm-isolation

validate-benchmark-baseline:
	@rm -rf results/validation-baseline
	@mkdir -p results/validation-baseline
	@$(MAKE) benchmark DRY_RUN=1 OUTPUT_DIR=results/validation-baseline RUN_ID=fixture RUNTIME_CLASS=kata-vm-isolation NODE_SELECTOR=runtimeclass=kata TOLERATIONS_JSON='[{"key":"runtimeclass","operator":"Equal","value":"kata","effect":"NoSchedule"}]' >/dev/null
	@$(MAKE) benchmark DRY_RUN=1 OUTPUT_DIR=results/validation-baseline RUN_ID=fixture-default RUNTIME_CLASS= >/dev/null
	@scripts/extract-results.py tests/fixtures/kube-burner-metrics --output-dir results/validation-baseline/fixture-standard --run-id fixture-standard
	@scripts/extract-results.py tests/fixtures/kube-burner-metrics --output-dir results/validation-baseline/fixture-kata-vm-isolation --run-id fixture-kata-vm-isolation --runtime-class kata-vm-isolation
	@python3 scripts/validate-benchmark-baseline.py --output-dir results/validation-baseline --run-id fixture --runtime-class kata-vm-isolation --baseline-only-run-id fixture-default

clean-results:
	@rm -rf results/*
	@touch results/.gitkeep
