import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PREPARE_RUNTIME_CONFIGS = REPO_ROOT / "scripts" / "prepare-runtime-configs.py"


class PrepareRuntimeConfigsTests(unittest.TestCase):
    def test_generates_one_config_and_metrics_profile_per_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            subprocess.run(
                [
                    sys.executable,
                    str(PREPARE_RUNTIME_CONFIGS),
                    "--suite-config",
                    str(REPO_ROOT / "configs" / "kube-burner-runtimeclass-suite.yml"),
                    "--runtime-manifest",
                    str(REPO_ROOT / "configs" / "runtime-manifest.json"),
                    "--metrics-template",
                    str(REPO_ROOT / "configs" / "kubelet-startup-metrics.yml"),
                    "--output-dir",
                    str(output_dir),
                    "--raw-dir",
                    str(output_dir / "raw"),
                    "--prometheus-endpoint",
                    "http://127.0.0.1:9090",
                ],
                check=True,
                cwd=REPO_ROOT,
            )

            manifest = json.loads((REPO_ROOT / "configs" / "runtime-manifest.json").read_text(encoding="utf-8"))
            runtime_keys = [runtime["key"] for runtime in manifest["runtimes"]]
            self.assertEqual((output_dir / "runtime-keys.txt").read_text(encoding="utf-8").splitlines(), runtime_keys)
            for key in runtime_keys:
                rendered_config = output_dir / "kube-burner" / f"{key}.yml"
                metrics_profile = output_dir / "prometheus-metrics" / f"{key}.yml"
                self.assertTrue(rendered_config.is_file(), f"missing rendered config for {key}")
                self.assertTrue(metrics_profile.is_file(), f"missing metrics profile for {key}")

                config_text = rendered_config.read_text(encoding="utf-8")
                self.assertIn(f"name: runtimeclass-pod-latency-{key}", config_text)
                self.assertNotIn("__PROMETHEUS_METRICS_CONFIG__", config_text)
                self.assertIn(str(metrics_profile), config_text)

                metrics_text = metrics_profile.read_text(encoding="utf-8")
                self.assertNotIn("__PROMETHEUS_RUNTIMECLASS__", metrics_text)
                self.assertIn(f'runtimeclass="{key}"', metrics_text)


if __name__ == "__main__":
    unittest.main()
