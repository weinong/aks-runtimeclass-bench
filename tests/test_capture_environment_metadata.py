import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_METADATA = REPO_ROOT / "scripts" / "capture-environment-metadata.py"

spec = importlib.util.spec_from_file_location("capture_environment_metadata", CAPTURE_METADATA)
capture_environment_metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture_environment_metadata)


class CaptureEnvironmentMetadataTests(unittest.TestCase):
    def test_default_runtime_node_pool_names_match_dedicated_runtime_pools(self):
        runtime_manifest = {
            "runtimes": [
                {"key": "standard", "runtimeClass": "standard"},
                {"key": "kata", "runtimeClass": "kata-vm-isolation"},
                {"key": "kata-optimized", "runtimeClass": "kata-optimized"},
                {"key": "gvisor", "runtimeClass": "gvisor"},
                {"key": "firecracker", "runtimeClass": "kata-fc"},
            ]
        }

        self.assertEqual(
            capture_environment_metadata.default_runtime_node_pool_names(runtime_manifest),
            {
                "standard": "standard",
                "kata": "kata",
                "kata-optimized": "kataopt",
                "gvisor": "gvisor",
                "firecracker": "firecracker",
            },
        )

    def test_build_environment_metadata_from_nodes_and_machine_info(self):
        nodes = {
            "items": [
                {
                    "metadata": {
                        "name": "aks-sys-00000000-vmss000000",
                        "labels": {
                            "kubernetes.azure.com/agentpool": "sys",
                            "node.kubernetes.io/instance-type": "Standard_D8s_v5",
                        },
                    },
                    "status": {"nodeInfo": {"containerRuntimeVersion": "containerd://1.7.27", "kubeletVersion": "v1.31.8"}},
                },
                {
                    "metadata": {
                        "name": "aks-kata-00000000-vmss000000",
                        "labels": {
                            "agentpool": "kata",
                            "beta.kubernetes.io/instance-type": "Standard_D16s_v5",
                        },
                    },
                    "status": {"nodeInfo": {"containerRuntimeVersion": "containerd://1.7.28", "kubeletVersion": "v1.31.9"}},
                },
            ]
        }
        machine_info = {
            "data": {
                "result": [
                    {"metric": {"node": "aks-sys-00000000-vmss000000", "kernel_version": "5.15.0-sys"}},
                    {"metric": {"node": "aks-kata-00000000-vmss000000", "kernelVersion": "5.15.0-kata"}},
                ]
            }
        }
        runtime_manifest = {"runtimes": [{"key": "standard", "runtimeClass": "standard"}, {"key": "kata", "runtimeClass": "kata-vm-isolation"}]}

        metadata = capture_environment_metadata.build_environment_metadata(
            nodes,
            machine_info,
            runtime_manifest,
            captured_at="2026-06-29T00:00:00Z",
            runtime_node_pool_names={"standard": "sys", "kata": "kata"},
            kata_versions={"kata": "3.17.0"},
        )

        self.assertNotIn("cluster", metadata)
        self.assertEqual(metadata["runtimeNodePools"], {"standard": "sys", "kata": "kata"})
        by_pool = {pool["name"]: pool for pool in metadata["nodePools"]}
        self.assertEqual(by_pool["sys"]["vmSku"], "Standard_D8s_v5")
        self.assertEqual(by_pool["kata"]["vmSku"], "Standard_D16s_v5")
        self.assertEqual(by_pool["kata"]["kernelVersion"], "5.15.0-kata")
        self.assertEqual(by_pool["kata"]["containerdVersion"], "containerd://1.7.28")
        self.assertEqual(by_pool["kata"]["kubeletVersion"], "v1.31.9")
        self.assertEqual(by_pool["kata"]["kataVersion"], "3.17.0")

    def test_missing_optional_metadata_is_null_and_warned(self):
        nodes = {
            "items": [
                {
                    "metadata": {"name": "aks-firecracker-00000000-vmss000000", "labels": {"kubernetes.azure.com/agentpool": "firecracker"}},
                    "status": {"nodeInfo": {}},
                }
            ]
        }
        runtime_manifest = {"runtimes": [{"key": "firecracker", "runtimeClass": "kata-fc"}]}

        metadata = capture_environment_metadata.build_environment_metadata(
            nodes,
            {},
            runtime_manifest,
            captured_at="2026-06-29T00:00:00Z",
            runtime_node_pool_names={"firecracker": "firecracker"},
            kata_versions={},
        )

        node_pool = metadata["nodePools"][0]
        self.assertIsNone(node_pool["vmSku"])
        self.assertIsNone(node_pool["kernelVersion"])
        self.assertIsNone(node_pool["containerdVersion"])
        self.assertIsNone(node_pool["kubeletVersion"])
        self.assertIsNone(node_pool["kataVersion"])
        self.assertIn("node pool firecracker: VM SKU unavailable from node labels", metadata["warnings"])
        self.assertIn("runtime firecracker: Kata runtime version unavailable", metadata["warnings"])

    def test_missing_runtime_node_pool_is_warned(self):
        runtime_manifest = {"runtimes": [{"key": "kata", "runtimeClass": "kata-vm-isolation"}]}

        metadata = capture_environment_metadata.build_environment_metadata(
            {"items": []},
            {},
            runtime_manifest,
            captured_at="2026-06-29T00:00:00Z",
            runtime_node_pool_names={"kata": "kata"},
            kata_versions={},
        )

        self.assertIn("runtime kata: mapped node pool kata was not observed", metadata["warnings"])

    def test_mixed_node_pool_metadata_is_warned_and_deterministic(self):
        nodes = {
            "items": [
                {
                    "metadata": {
                        "name": "node-b",
                        "labels": {"kubernetes.azure.com/agentpool": "kata", "node.kubernetes.io/instance-type": "Standard_D16s_v5"},
                    },
                    "status": {"nodeInfo": {"containerRuntimeVersion": "containerd://1.7.28", "kubeletVersion": "v1.31.9"}},
                },
                {
                    "metadata": {
                        "name": "node-a",
                        "labels": {"kubernetes.azure.com/agentpool": "kata", "node.kubernetes.io/instance-type": "Standard_D8s_v5"},
                    },
                    "status": {"nodeInfo": {"containerRuntimeVersion": "containerd://1.7.27", "kubeletVersion": "v1.31.8"}},
                },
            ]
        }
        machine_info = {
            "data": {
                "result": [
                    {"metric": {"node": "node-b", "kernel_version": "5.15.0-b"}},
                    {"metric": {"node": "node-a", "kernel_version": "5.15.0-a"}},
                ]
            }
        }

        metadata = capture_environment_metadata.build_environment_metadata(
            nodes,
            machine_info,
            {"runtimes": [{"key": "kata", "runtimeClass": "kata-vm-isolation"}]},
            captured_at="2026-06-29T00:00:00Z",
            runtime_node_pool_names={"kata": "kata"},
            kata_versions={"kata": "3.17.0"},
        )

        node_pool = metadata["nodePools"][0]
        self.assertEqual(node_pool["vmSku"], "Standard_D16s_v5")
        self.assertEqual(node_pool["kernelVersion"], "5.15.0-b")
        self.assertEqual(node_pool["containerdVersion"], "containerd://1.7.28")
        self.assertEqual(node_pool["kubeletVersion"], "v1.31.9")
        self.assertIn("node pool kata: multiple VM SKU values observed: Standard_D16s_v5, Standard_D8s_v5", metadata["warnings"])
        self.assertIn("node pool kata: multiple kernel version values observed: 5.15.0-b, 5.15.0-a", metadata["warnings"])
        self.assertIn(
            "node pool kata: multiple containerd version values observed: containerd://1.7.28, containerd://1.7.27",
            metadata["warnings"],
        )
        self.assertIn("node pool kata: multiple kubelet version values observed: v1.31.9, v1.31.8", metadata["warnings"])

    def test_partially_missing_kubelet_version_is_warned(self):
        nodes = {
            "items": [
                {
                    "metadata": {
                        "name": "node-a",
                        "labels": {"kubernetes.azure.com/agentpool": "kata", "node.kubernetes.io/instance-type": "Standard_D8s_v5"},
                    },
                    "status": {"nodeInfo": {"containerRuntimeVersion": "containerd://1.7.27", "kubeletVersion": "v1.31.8"}},
                },
                {
                    "metadata": {
                        "name": "node-b",
                        "labels": {"kubernetes.azure.com/agentpool": "kata", "node.kubernetes.io/instance-type": "Standard_D8s_v5"},
                    },
                    "status": {"nodeInfo": {"containerRuntimeVersion": "containerd://1.7.27"}},
                },
            ]
        }

        metadata = capture_environment_metadata.build_environment_metadata(
            nodes,
            {},
            {"runtimes": [{"key": "kata", "runtimeClass": "kata-vm-isolation"}]},
            captured_at="2026-06-29T00:00:00Z",
            runtime_node_pool_names={"kata": "kata"},
            kata_versions={"kata": "3.17.0"},
        )

        self.assertIn("node pool kata: kubelet version unavailable for 1 node(s)", metadata["warnings"])

    def test_required_json_command_failure_exits(self):
        with self.assertRaises(SystemExit) as raised:
            capture_environment_metadata.run_json(["definitely-not-a-command"], required=True, description="node list")

        self.assertIn("failed to collect node list", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
