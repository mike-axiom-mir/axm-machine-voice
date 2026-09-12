from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BoundedNeedContractTests(unittest.TestCase):
    def test_native_manifest_declares_bounded_need_without_global_unavailability(self):
        manifest = json.loads((ROOT / "AXM_MODULE.json").read_text(encoding="utf-8"))
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        need = capabilities["producer.bounded-need"]
        self.assertIn("state.need", need["provides"])
        self.assertIn("input.required", need["accepts"])
        self.assertIn("inventory", need["description"])
        self.assertIn(
            "global unavailability from a bounded missing-input inventory",
            manifest["truth_boundary"]["not_claimed"],
        )

    def test_readme_exposes_need_as_producer_not_snapshot_yet(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("produce_bounded_need", readme)
        self.assertIn("I need something.", readme)
        self.assertIn("Python/API-only in this lane", readme)


if __name__ == "__main__":
    unittest.main()
