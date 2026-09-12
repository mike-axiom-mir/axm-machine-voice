from pathlib import Path
import json
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "AXM_MODULE.json"
PYPROJECT = ROOT / "pyproject.toml"


class MonolithNativeContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.capabilities = {item["id"]: item for item in self.manifest["capabilities"]}

    def test_manifest_has_required_native_shape(self):
        self.assertEqual(self.manifest["schema_version"], "0.1")
        self.assertEqual(self.manifest["module"]["name"], "axm-machine-voice")
        self.assertIsInstance(self.manifest["capabilities"], list)
        self.assertGreater(len(self.manifest["capabilities"]), 0)

    def test_manifest_declares_state_native_handoff_for_monolith(self):
        adapter = self.capabilities["adapter.state-snapshot"]
        state_talk = self.capabilities["communication.state-talk"]
        producer = self.capabilities["producer.lower-cost-alternative"]

        self.assertIn("state.snapshot", adapter["accepts"])
        self.assertIn("state.context", adapter["accepts"])
        self.assertIn("communication.state-talk", state_talk["provides"])
        self.assertIn("transition.proposal", producer["provides"])
        self.assertIn("state.constraint", producer["accepts"])

    def test_floorvoice_is_declared_as_local_communication_not_audio(self):
        floorvoice = self.capabilities["interface.floorvoice"]
        self.assertIn("interface.local", floorvoice["provides"])
        self.assertIn("communication.response.intent", floorvoice["provides"])
        self.assertIn("communication.state-talk", floorvoice["accepts"])

        serialized = json.dumps(self.manifest).lower()
        self.assertNotIn("artifact.audio", serialized)
        self.assertNotIn('"audio"', serialized)

    def test_machine_and_human_surfaces_share_state_talk_without_claiming_cross_module_verification(self):
        machine = self.capabilities["interface.machine-json"]
        journal = self.capabilities["communication.journal"]
        self.assertIn("communication.state-talk", machine["provides"])
        self.assertIn("communication.state-talk", journal["accepts"])
        for capability in self.manifest["capabilities"]:
            self.assertEqual(
                capability["evidence_status"],
                "implemented_with_regression_tests_not_cross_module_verified",
            )

    def test_pyproject_exposes_inspector_visible_python_entrypoint(self):
        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        scripts = data["project"]["scripts"]
        self.assertEqual(scripts["axm-machine-voice"], "axm_machine_voice.cli:main")

    def test_manifest_keeps_unknown_future_integration_outside_current_claim(self):
        not_claimed = self.manifest["truth_boundary"]["not_claimed"]
        self.assertIn("cross-module interoperability before exact composition testing", not_claimed)
        self.assertIn("general autonomous idea discovery", not_claimed)


if __name__ == "__main__":
    unittest.main()
