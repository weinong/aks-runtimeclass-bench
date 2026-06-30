import csv
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACT_RESULTS = REPO_ROOT / "scripts" / "extract-results.py"
SUITE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "kube-burner-suite-metrics"
RUNTIME_MANIFEST = REPO_ROOT / "configs" / "runtime-manifest.json"
ENVIRONMENT_METADATA = REPO_ROOT / "tests" / "fixtures" / "environment-metadata.json"
SUMMARY_CSV_FIELDS = [
    "run_id",
    "runtime_key",
    "runtime_class",
    "metric_category",
    "condition",
    "metric_name",
    "metric_family",
    "unit",
    "p50",
    "p95",
    "p99",
]
ENVIRONMENT_CSV_FIELDS = ["node_pool", "vm_sku", "kernel_version", "containerd_version", "kubelet_version", "kata_version"]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def scrub_summary(summary):
    summary["generatedAt"] = "<generatedAt>"
    summary["sourceDirectory"] = "<sourceDirectory>"
    for run in summary.get("runs", []):
        run["sourceDirectory"] = "<sourceDirectory>"
    return summary


def read_expected_suite_summary():
    summary = json.loads((REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.json").read_text(encoding="utf-8"))
    return scrub_summary(summary)


class ExtractResultsTests(unittest.TestCase):
    def test_suite_summary_includes_environment_metadata_when_provided(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(SUITE_FIXTURE),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                    "--environment-metadata",
                    str(ENVIRONMENT_METADATA),
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["environment"]["schemaVersion"], "runtimeclass-benchmark-environment/v1")
            self.assertNotIn("cluster", summary["environment"])
            self.assertIn("runtime firecracker: Kata runtime version unavailable", summary["environment"]["warnings"])

            by_key = {run["runtimeKey"]: run for run in summary["runs"]}
            self.assertEqual(by_key["standard"]["environment"]["nodePool"], "standard")
            self.assertEqual(by_key["standard"]["environment"]["kubeletVersion"], "v1.31.8")
            self.assertEqual(by_key["kata"]["environment"]["kataVersion"], "3.17.0")
            self.assertEqual(by_key["kata-optimized"]["environment"]["nodePool"], "kataopt")
            self.assertIsNone(by_key["firecracker"]["environment"]["kernelVersion"])
            self.assertIsNone(by_key["firecracker"]["environment"]["kataVersion"])

            rows = read_csv(output_dir / "summary.csv")
            self.assertEqual(list(rows[0]), SUMMARY_CSV_FIELDS)
            for field in ENVIRONMENT_CSV_FIELDS:
                self.assertNotIn(field, rows[0])

    def test_suite_summary_includes_kubelet_metric_quantiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(SUITE_FIXTURE),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                    "--environment-metadata",
                    str(ENVIRONMENT_METADATA),
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            actual_json = scrub_summary(json.loads((output_dir / "summary.json").read_text(encoding="utf-8")))
            expected_json = read_expected_suite_summary()
            self.assertEqual(actual_json, expected_json)

            actual_csv = read_csv(output_dir / "summary.csv")
            expected_csv = read_csv(REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.csv")
            self.assertEqual(actual_csv, expected_csv)

    def test_suite_summary_without_environment_metadata_keeps_existing_json_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            command = [
                sys.executable,
                str(EXTRACT_RESULTS),
                str(SUITE_FIXTURE),
                "--output-dir",
                str(output_dir),
                "--run-id",
                "fixture",
                "--runtime-manifest",
                str(RUNTIME_MANIFEST),
            ]
            subprocess.run(command, check=True, cwd=REPO_ROOT)

            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertNotIn("environment", summary)
            self.assertNotIn("environment", summary["runs"][0])

    def test_suite_summary_fails_when_kubelet_metrics_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            missing_input_dir = Path(tmp) / "input"
            missing_input_dir.mkdir()
            (missing_input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(missing_input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                    "--environment-metadata",
                    str(ENVIRONMENT_METADATA),
                ],
                check=False,
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required kubelet metric quantiles", result.stderr)
            self.assertIn("standard: kubelet_run_podsandbox_duration_seconds", result.stderr)

    def test_suite_summary_fails_when_kubelet_metric_record_has_no_runtime_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-quantiles.json").read_text(encoding="utf-8"))
            kubelet_records[0]["labels"] = {}
            (input_dir / "kubelet-startup-quantiles.json").write_text(
                json.dumps(kubelet_records, indent=2) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                    "--environment-metadata",
                    str(ENVIRONMENT_METADATA),
                ],
                check=False,
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("kubelet metric record is missing Prometheus runtime attribution", result.stderr)

    def test_suite_summary_fails_when_runtime_attribution_is_duplicated_in_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            manifest = Path(tmp) / "runtime-manifest.json"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (input_dir / "kubelet-startup-quantiles.json").write_text(
                (SUITE_FIXTURE / "kubelet-startup-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            manifest_data = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
            manifest_data["runtimes"][0]["prometheusAttribution"] = {
                "labelKey": "runtimeclass",
                "labelValue": "standard",
            }
            manifest_data["runtimes"][1]["prometheusAttribution"] = copy.deepcopy(
                manifest_data["runtimes"][0]["prometheusAttribution"]
            )
            manifest.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(manifest),
                    "--environment-metadata",
                    str(ENVIRONMENT_METADATA),
                ],
                check=False,
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate Prometheus runtime attribution value", result.stderr)

    def test_suite_summary_fails_when_direct_kubelet_quantile_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-quantiles.json").read_text(encoding="utf-8"))
            kubelet_records = [
                record
                for record in kubelet_records
                if not (
                    record.get("metricName") == "kubeletRunPodSandboxDurationSecondsP95"
                    and record.get("labels", {}).get("runtimeclass") == "standard"
                )
            ]
            (input_dir / "kubelet-startup-quantiles.json").write_text(
                json.dumps(kubelet_records, indent=2) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                ],
                check=False,
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "missing required kubelet metric quantiles: standard: kubelet_run_podsandbox_duration_seconds P95",
                result.stderr,
            )

    def test_suite_summary_fails_when_direct_kubelet_quantile_is_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-quantiles.json").read_text(encoding="utf-8"))
            kubelet_records[0]["value"] = "NaN"
            (input_dir / "kubelet-startup-quantiles.json").write_text(
                json.dumps(kubelet_records, indent=2) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                ],
                check=False,
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be finite", result.stderr)

    def test_suite_summary_uses_latest_direct_kubelet_quantile_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-quantiles.json").read_text(encoding="utf-8"))
            duplicate = copy.deepcopy(kubelet_records[0])
            duplicate["timestamp"] = "2026-06-30T03:28:42Z"
            duplicate["value"] = 0.123
            kubelet_records[0]["timestamp"] = "2026-06-30T03:28:27Z"
            kubelet_records.append(duplicate)
            (input_dir / "kubelet-startup-quantiles.json").write_text(
                json.dumps(kubelet_records, indent=2) + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(EXTRACT_RESULTS),
                    str(input_dir),
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "fixture",
                    "--runtime-manifest",
                    str(RUNTIME_MANIFEST),
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            standard = next(run for run in summary["runs"] if run["runtimeKey"] == "standard")
            sandbox = next(
                item
                for item in standard["kubeletMetricQuantiles"]
                if item["metricFamily"] == "kubelet_run_podsandbox_duration_seconds"
            )
            self.assertEqual(sandbox["P50"], 0.123)


if __name__ == "__main__":
    unittest.main()
