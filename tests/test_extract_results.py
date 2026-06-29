import csv
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


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def scrub_summary(summary):
    summary["generatedAt"] = "<generatedAt>"
    summary["sourceDirectory"] = "<sourceDirectory>"
    for run in summary.get("runs", []):
        run["sourceDirectory"] = "<sourceDirectory>"
    return summary


class ExtractResultsTests(unittest.TestCase):
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
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            actual_json = scrub_summary(json.loads((output_dir / "summary.json").read_text(encoding="utf-8")))
            expected_json = json.loads(
                (REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(actual_json, expected_json)

            actual_csv = read_csv(output_dir / "summary.csv")
            expected_csv = read_csv(REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.csv")
            self.assertEqual(actual_csv, expected_csv)

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
                ],
                check=False,
                cwd=REPO_ROOT,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required kubelet metric quantiles", result.stderr)
            self.assertIn("standard: kubelet_run_podsandbox_duration_seconds", result.stderr)

    def test_suite_summary_aggregates_duplicate_kubelet_histogram_buckets(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-histograms.json").read_text(encoding="utf-8"))
            kubelet_records = [
                record
                for record in kubelet_records
                if not (
                    record.get("metricName") == "kubeletRunPodSandboxDurationSeconds"
                    and record.get("jobName") == "runtimeclass-pod-latency-standard"
                )
            ]
            for upper_bound, node_a, node_b in [
                ("0.1", 30, 20),
                ("0.2", 55, 40),
                ("0.5", 59, 40),
                ("+Inf", 60, 40),
            ]:
                for node, value in [("node-a", node_a), ("node-b", node_b)]:
                    kubelet_records.append(
                        {
                            "metricName": "kubeletRunPodSandboxDurationSeconds",
                            "jobName": "runtimeclass-pod-latency-standard",
                            "labels": {
                                "__name__": "kubelet_run_podsandbox_duration_seconds_bucket",
                                "le": upper_bound,
                                "node": node,
                                "runtimeclass-bench-key": "standard",
                            },
                            "value": value,
                        }
                    )
            (input_dir / "kubelet-startup-histograms.json").write_text(
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

            actual_json = scrub_summary(json.loads((output_dir / "summary.json").read_text(encoding="utf-8")))
            expected_json = json.loads(
                (REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(actual_json, expected_json)

    def test_suite_summary_fails_when_kubelet_metric_record_has_no_runtime_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-histograms.json").read_text(encoding="utf-8"))
            kubelet_records.append(
                {
                    "metricName": "kubeletRunPodSandboxDurationSeconds",
                    "labels": {
                        "__name__": "kubelet_run_podsandbox_duration_seconds_bucket",
                        "le": "0.1",
                    },
                    "value": 1,
                }
            )
            (input_dir / "kubelet-startup-histograms.json").write_text(
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
            self.assertIn("kubelet metric record is missing runtime metadata", result.stderr)

    def test_suite_summary_returns_highest_finite_bucket_when_quantile_is_in_infinite_bucket(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-histograms.json").read_text(encoding="utf-8"))
            kubelet_records = [
                record
                for record in kubelet_records
                if not (
                    record.get("metricName") == "kubeletRunPodSandboxDurationSeconds"
                    and record.get("jobName") == "runtimeclass-pod-latency-standard"
                )
            ]
            for upper_bound, value in [("0.1", 10), ("0.2", 20), ("0.5", 30), ("+Inf", 100)]:
                kubelet_records.append(
                    {
                        "metricName": "kubeletRunPodSandboxDurationSeconds",
                        "jobName": "runtimeclass-pod-latency-standard",
                        "labels": {
                            "__name__": "kubelet_run_podsandbox_duration_seconds_bucket",
                            "le": upper_bound,
                            "runtimeclass-bench-key": "standard",
                        },
                        "value": value,
                    }
                )
            (input_dir / "kubelet-startup-histograms.json").write_text(
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
            standard_run = next(run for run in summary["runs"] if run["runtimeKey"] == "standard")
            metric = next(
                item
                for item in standard_run["kubeletMetricQuantiles"]
                if item["metricFamily"] == "kubelet_run_podsandbox_duration_seconds"
            )
            self.assertEqual(metric["P50"], 0.5)
            self.assertEqual(metric["P95"], 0.5)
            self.assertEqual(metric["P99"], 0.5)

    def test_suite_summary_supports_kube_burner_metric_name_histogram_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-histograms.json").read_text(encoding="utf-8"))
            kubelet_records = [
                record
                for record in kubelet_records
                if not (
                    record.get("metricName") == "kubeletRunPodSandboxDurationSeconds"
                    and record.get("jobName") == "runtimeclass-pod-latency-standard"
                )
            ]
            for timestamp, buckets in [
                ("2026-06-29T02:19:25.91Z", [("0.1", 100), ("0.2", 100), ("0.5", 100), ("+Inf", 100)]),
                ("2026-06-29T02:19:30.8Z", [("0.1", 150), ("0.2", 195), ("0.5", 199), ("+Inf", 200)]),
            ]:
                for upper_bound, value in buckets:
                    kubelet_records.append(
                        {
                            "metricName": "kubeletRunPodSandboxDurationSeconds",
                            "jobName": "runtimeclass-pod-latency-standard",
                            "labels": {
                                "instance": "aks-standard-000000",
                                "le": upper_bound,
                            },
                            "timestamp": timestamp,
                            "value": value,
                        }
                    )
            (input_dir / "kubelet-startup-histograms.json").write_text(
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

            actual_json = scrub_summary(json.loads((output_dir / "summary.json").read_text(encoding="utf-8")))
            expected_json = json.loads(
                (REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(actual_json, expected_json)

    def test_suite_summary_aggregates_label_only_records_by_timestamp_before_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-histograms.json").read_text(encoding="utf-8"))
            kubelet_records = [
                record
                for record in kubelet_records
                if not (
                    record.get("metricName") == "kubeletRunPodSandboxDurationSeconds"
                    and record.get("jobName") == "runtimeclass-pod-latency-standard"
                )
            ]
            for timestamp, values in [
                ("2026-06-29T02:19:25.91Z", {"0.1": [100, 50], "0.2": [100, 50], "0.5": [100, 50], "+Inf": [100, 50]}),
                ("2026-06-29T02:19:30.8Z", {"0.1": [130, 70], "0.2": [155, 90], "0.5": [159, 90], "+Inf": [160, 90]}),
            ]:
                for upper_bound, series_values in values.items():
                    for value in series_values:
                        kubelet_records.append(
                            {
                                "metricName": "kubeletRunPodSandboxDurationSeconds",
                                "jobName": "runtimeclass-pod-latency-standard",
                                "labels": {"le": upper_bound},
                                "timestamp": timestamp,
                                "value": value,
                            }
                        )
            (input_dir / "kubelet-startup-histograms.json").write_text(
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

            actual_json = scrub_summary(json.loads((output_dir / "summary.json").read_text(encoding="utf-8")))
            expected_json = json.loads(
                (REPO_ROOT / "tests" / "fixtures" / "expected-suite-summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(actual_json, expected_json)

    def test_suite_summary_fails_when_kubelet_counter_has_only_one_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            input_dir.mkdir()
            output_dir = Path(tmp) / "out"
            (input_dir / "pod-latency-quantiles.json").write_text(
                (SUITE_FIXTURE / "pod-latency-quantiles.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            kubelet_records = json.loads((SUITE_FIXTURE / "kubelet-startup-histograms.json").read_text(encoding="utf-8"))
            kubelet_records = [
                record
                for record in kubelet_records
                if not (
                    record.get("metricName") == "kubeletRunPodSandboxDurationSeconds"
                    and record.get("jobName") == "runtimeclass-pod-latency-standard"
                )
            ]
            for upper_bound, value in [("0.1", 50), ("0.2", 95), ("0.5", 99), ("+Inf", 100)]:
                kubelet_records.append(
                    {
                        "metricName": "kubeletRunPodSandboxDurationSeconds",
                        "jobName": "runtimeclass-pod-latency-standard",
                        "labels": {"le": upper_bound},
                        "timestamp": "2026-06-29T02:19:25.91Z",
                        "value": value,
                    }
                )
            (input_dir / "kubelet-startup-histograms.json").write_text(
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
            self.assertIn("requires at least two Prometheus samples", result.stderr)


if __name__ == "__main__":
    unittest.main()
