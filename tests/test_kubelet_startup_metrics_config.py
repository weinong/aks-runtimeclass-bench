import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS_PROFILE = REPO_ROOT / "configs" / "kubelet-startup-metrics.yml"


class KubeletStartupMetricsConfigTests(unittest.TestCase):
    def test_elapsed_template_does_not_append_seconds_unit(self):
        profile = METRICS_PROFILE.read_text(encoding="utf-8")

        self.assertNotRegex(profile, re.compile(r"\{\{\s*\.elapsed\s*\}\}s"))

    def test_queries_filter_active_runtime_series(self):
        profile = METRICS_PROFILE.read_text(encoding="utf-8")

        self.assertEqual(profile.count('runtimeclass="__PROMETHEUS_RUNTIMECLASS__"'), 9)
        self.assertNotIn('runtimeclass!=""', profile)
        self.assertNotIn(".jobName", profile)


if __name__ == "__main__":
    unittest.main()
