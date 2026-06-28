## Context

The benchmark currently renders `results/<RUN_ID>/kube-burner.yml` with `scripts/render-kube-burner-config.py` before each run. That renderer builds a runtime inventory from environment variables, emits one kube-burner job per runtime entry, and writes `runtime-manifest.json` for the extractor.

That flexibility was useful while the suite shape was still emerging, but the intended full suite is now mostly static: standard baseline plus the known runtime class jobs. Keeping the suite definition in code requires operators and reviewers to understand Make defaults, environment parsing, renderer behavior, and generated YAML before they can see the workload kube-burner actually runs.

## Goals / Non-Goals

**Goals:**
- Make the kube-burner suite definition a checked-in config file that is easy to inspect, diff, and run manually.
- Keep `make benchmark` and `make benchmark-dry-run` as the primary operator entry points.
- Preserve one result root per benchmark invocation, including the exact kube-burner config used, raw metrics, runtime manifest, and JSON/CSV summaries.
- Reduce custom rendering and validation logic where the benchmark shape is static.

**Non-Goals:**
- Automatically discovering Kubernetes `RuntimeClass` objects from the cluster.
- Preserving arbitrary runtime inventory generation through `BENCHMARK_RUNTIMES` and `<KEY>_*` environment variables.
- Changing pod latency measurements, extractor summary schema, kube-burner version management, or cluster lifecycle behavior.
- Expanding the default runtime set beyond the existing static suite intent.

## Decisions

1. Use a checked-in kube-burner suite config as the source of truth.

   Add a repository-managed kube-burner YAML file under a config-oriented path such as `configs/kube-burner-runtimeclass-suite.yml`. The file should explicitly define the standard baseline and runtime class jobs instead of deriving them from `BENCHMARK_RUNTIMES`.

   Alternative considered: keep the Python renderer and document the generated output more clearly. That preserves flexibility, but it does not address the core cognitive load because the workload remains an output of code rather than a reviewed artifact.

2. Keep per-run output self-contained by copying the static config into the result root.

   `scripts/run-benchmark.sh` should copy the checked-in config to `results/<RUN_ID>/kube-burner.yml` before invoking kube-burner. This preserves the current result contract and records the exact suite file used for the run.

   Alternative considered: pass the checked-in file directly to kube-burner. That is simpler, but the result directory would no longer contain the config artifact associated with the run.

3. Handle the per-run metrics directory with minimal substitution rather than full config generation.

   The only value that must vary per invocation is the local metrics output directory. Prefer a tiny, explicit substitution step in `run-benchmark.sh`, for example replacing a placeholder token in the copied config. This keeps runtime behavior obvious while avoiding a general-purpose renderer.

   Alternative considered: make kube-burner write to a static metrics directory and move outputs afterward. That risks collisions and makes dry-run behavior less transparent.

4. Replace generated runtime manifest with a static manifest aligned with the checked-in suite.

   Add a repository-managed manifest, for example `configs/runtime-manifest.json`, containing the runtime keys and labels expected by the extractor. Copy it into `results/<RUN_ID>/runtime-manifest.json` during benchmark setup.

   Alternative considered: derive the manifest by parsing the static kube-burner YAML. That adds another form of generation and would require YAML parsing or brittle text extraction.

5. Narrow benchmark configurability to workload knobs that still matter.

   Keep Make variables that do not alter the suite topology when they remain useful and easy to reason about. Remove or deprecate runtime-inventory variables such as `BENCHMARK_RUNTIMES`, `RUNTIME_CLASS`, `NODE_SELECTOR`, `TOLERATIONS_JSON`, and arbitrary `<KEY>_*` runtime expansion from the benchmark path.

   Alternative considered: keep all existing environment variables and substitute many fields into the static config. That would recreate the renderer in shell and weaken the advantage of a static suite.

## Risks / Trade-offs

- Reduced flexibility for ad hoc runtime entries -> Accept because the full benchmark suite is intentionally static; future suite topology changes should be reviewed as config changes.
- Placeholder substitution can be brittle if too many fields are added -> Limit substitution to the metrics directory and keep other suite values checked in.
- Existing users may rely on `BENCHMARK_RUNTIMES` or custom runtime keys -> Document the change and provide a clear migration path: edit or add a checked-in suite config for new runtime topology.
- Static config may drift from extractor manifest -> Validate both files together and include tests that ensure the expected runtime keys appear in summaries.
