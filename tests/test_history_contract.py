from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HistoryRepeatNovelContractTests(unittest.TestCase):
    def test_native_manifest_declares_history_without_global_novelty_claim(self):
        manifest = json.loads((ROOT / "AXM_MODULE.json").read_text(encoding="utf-8"))
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        history = capabilities["producer.history-repeat-novel"]
        self.assertIn("state.repeat", history["provides"])
        self.assertIn("state.novel", history["provides"])
        self.assertIn("history.scope", history["accepts"])
        self.assertIn("history.completeness", history["accepts"])
        self.assertIn("exact grounded prior match", history["description"])
        self.assertIn("complete-for-domain", history["description"])

        not_claimed = manifest["truth_boundary"]["not_claimed"]
        self.assertIn(
            "global or scientific novelty from absence in one supplied history scope",
            not_claimed,
        )
        self.assertIn(
            "authenticated completeness or chronological ordering of a supplied history scope",
            not_claimed,
        )

    def test_history_docs_keep_repeat_and_novelty_paired_and_producer_only_for_now(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "HISTORY_PRODUCER.md").read_text(encoding="utf-8")
        combined = readme + docs
        self.assertIn("produce_history_classification", combined)
        self.assertIn("This happened before.", combined)
        self.assertIn("This is new.", combined)
        self.assertIn("no match + incomplete history", combined)
        self.assertIn("global_novelty_claimed", combined)
        self.assertIn("history_scope_completeness_authenticated", combined)
        self.assertIn("history_ordering_authenticated", combined)
        self.assertIn("history producer is intentionally Python/API-only in this lane", readme)


if __name__ == "__main__":
    unittest.main()
