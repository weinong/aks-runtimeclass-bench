## Context

The benchmark target should run a runtime class suite without requiring operators to pass `RUNTIME_CLASS`, `NODE_SELECTOR`, and `TOLERATIONS_JSON` for each runtime. The earlier per-runtime invocation approach produced a correct single top-level result, but required an extra aggregation step after running kube-burner separately for each runtime.

Kube-burner supports multiple jobs in one config. Generating a suite config with one job per runtime keeps the benchmark command to one kube-burner invocation and lets the extractor build one result directly from the single metrics directory.

## Goals / Non-Goals

**Goals:**
- Make `make benchmark` run the default runtime plus Kata by default without runtime-specific command-line overrides.
- Generate a kube-burner config containing one job per enabled runtime entry.
- Store one result root per benchmark invocation with raw metrics, generated config, runtime manifest, and combined JSON/CSV summaries.
- Keep runtime entries configurable so gVisor, Firecracker, and future runtime keys can be opted in without changing benchmark control flow.

**Non-Goals:**
- Changing pod latency quantiles or kube-burner measurement semantics.
- Automatically discovering Kubernetes `RuntimeClass` objects from the cluster.
- Running gVisor or Firecracker by default before they are ready in the target environment.

## Decisions

1. Generate `results/<RUN_ID>/kube-burner.yml` instead of using the static config directly.

   The generated config writes the same local metrics endpoint and global `podLatency` measurement, then emits one `jobs` entry per enabled runtime. Each job has runtime-specific `inputVars` for runtime class, node selector, tolerations, and a runtime key.

2. Use one kube-burner invocation for the full suite.

   `scripts/run-benchmark.sh` renders the suite config and runtime manifest, invokes kube-burner once, and then runs extraction once over the shared raw metrics directory.

3. Keep a runtime manifest for extraction.

   The manifest records runtime keys and runtime class labels expected in the final summary. The extractor groups kube-burner records by job metadata when present. Fixture data lacks job metadata, so tests use a fallback that applies the same fixture quantiles to each manifest runtime.

4. Keep pod names unique per runtime job.

   The pod template includes `runtimeKey` in pod names and labels to prevent multi-job naming collisions and provide an additional runtime identifier in workload objects.

## Risks / Trade-offs

- Kube-burner metric job metadata may vary by version. Mitigation: extractor checks several likely job fields and pod labels, and validation covers the generated config shape.
- Jobs in a single kube-burner config may run with different scheduling behavior than separate invocations. Mitigation: each runtime job uses a distinct namespace suffix and unique pod names.
- Fixture metrics do not include job identifiers. Mitigation: fallback behavior is limited to unkeyed records and keeps local validation deterministic.
