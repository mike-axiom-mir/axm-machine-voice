from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UnresolvedNativeContractTests(unittest.TestCase):
    def test_manifest_declares_bounded_unresolved_without_global_impossibility(self):
        manifest = json.loads((ROOT / "AXM_MODULE.json").read_text(encoding="utf-8"))
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        capability = capabilities["producer.bounded-unresolved"]

        self.assertIn("state.unresolved", capability["provides"])
        self.assertIn("state.attempt", capability["accepts"])
        self.assertIn("state.constraint", capability["accepts"])
        self.assertIn("does not claim no solution exists", capability["description"])
        self.assertEqual(
            capability["evidence_status"],
            "implemented_with_regression_tests_not_cross_module_verified",
        )
        self.assertIn(
            "global impossibility from a bounded unresolved search",
            manifest["truth_boundary"]["not_claimed"],
        )


if __name__ == "__main__":
    unittest.main()
