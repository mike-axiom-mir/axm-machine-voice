from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ResidualLookContractTests(unittest.TestCase):
    def test_native_manifest_declares_residual_without_explanation_claim(self):
        manifest = json.loads((ROOT / "AXM_MODULE.json").read_text(encoding="utf-8"))
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        residual = capabilities["producer.residual-look"]
        self.assertIn("state.residual", residual["provides"])
        self.assertIn("state.expected", residual["accepts"])
        self.assertIn("state.observed", residual["accepts"])
        self.assertIn("tolerance", residual["accepts"])
        self.assertIn("does not infer cause", residual["description"])
        not_claimed = manifest["truth_boundary"]["not_claimed"]
        self.assertIn(
            "cause or novelty merely because an expected-vs-observed residual exceeds a supplied tolerance",
            not_claimed,
        )
        self.assertIn(
            "model invalidity or observation invalidity merely because a residual exceeds tolerance",
            not_claimed,
        )

    def test_readme_exposes_residual_producer_but_not_snapshot_yet(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("produce_residual_look", readme)
        self.assertIn("Look here.", readme)
        self.assertIn("residual producer is intentionally Python/API-only in this lane", readme)


if __name__ == "__main__":
    unittest.main()
