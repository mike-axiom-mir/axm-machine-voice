from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GroundedNoticeContractTests(unittest.TestCase):
    def test_native_manifest_declares_notice_without_interpretation_claims(self):
        manifest = json.loads((ROOT / "AXM_MODULE.json").read_text(encoding="utf-8"))
        capabilities = {item["id"]: item for item in manifest["capabilities"]}
        notice = capabilities["producer.grounded-notice"]
        self.assertIn("state.notice", notice["provides"])
        self.assertIn("notice.rule", notice["accepts"])
        self.assertIn("notice.trigger", notice["accepts"])
        description = notice["description"].lower()
        for term in ("importance", "anomaly", "novelty", "cause", "success", "failure", "recommendation", "interpretation"):
            self.assertIn(term, description)

        not_claimed = manifest["truth_boundary"]["not_claimed"]
        self.assertIn(
            "importance, anomaly, novelty, cause, success, failure, recommendation, or interpretation merely because a generic notice rule fired",
            not_claimed,
        )

    def test_docs_keep_notice_as_grounded_detector_handoff_and_producer_only_for_now(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "NOTICE_PRODUCER.md").read_text(encoding="utf-8")
        combined = readme + docs
        self.assertIn("produce_grounded_notice", combined)
        self.assertIn("I noticed something.", combined)
        self.assertIn("generic grounded-detector handoff", combined.lower())
        self.assertIn('"importance_claimed": false', combined)
        self.assertIn('"anomaly_claimed": false', combined)
        self.assertIn('"interpretation_claimed": false', combined)
        self.assertIn("notice producer is intentionally Python/API-only in this lane", readme)


if __name__ == "__main__":
    unittest.main()
