from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CriterionOutcomeContractTests(unittest.TestCase):
    def test_native_manifest_declares_paired_outcome_without_global_claim(self):
        manifest = json.loads((ROOT / "AXM_MODULE.json").read_text(encoding="utf-8"))
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        outcome = capabilities["producer.criterion-outcome"]
        self.assertIn("state.success", outcome["provides"])
        self.assertIn("state.failure", outcome["provides"])
        self.assertIn("success.contract", outcome["accepts"])
        self.assertIn("criterion.observation", outcome["accepts"])
        self.assertIn("all-required", outcome["description"])

        not_claimed = manifest["truth_boundary"]["not_claimed"]
        self.assertIn(
            "global success or global failure from evaluation against one explicit criteria contract",
            not_claimed,
        )
        self.assertIn(
            "authenticity, authorship, or pre-attempt timing of a supplied success criteria contract",
            not_claimed,
        )

    def test_readme_exposes_paired_outcome_producer_and_supported_snapshot(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("produce_criterion_outcome", readme)
        self.assertIn("This worked.", readme)
        self.assertIn("This did not work.", readme)
        self.assertIn("axm-machine-voice/outcome-snapshot/0.1", readme)
        self.assertIn("examples/outcome_snapshot.example.json", readme)
        self.assertIn("examples/outcome_failure_snapshot.example.json", readme)

        start = readme.index("### `This worked.` / `This did not work.`")
        section = readme[start:]
        next_heading = section.find("\n### ", 4)
        if next_heading != -1:
            section = section[:next_heading]
        else:
            next_major = section.find("\n## ", 4)
            if next_major != -1:
                section = section[:next_major]
        self.assertNotIn("Python/API-only in this lane", section)
        self.assertIn("criteria_contract_preexistence_authenticated", section)


if __name__ == "__main__":
    unittest.main()
