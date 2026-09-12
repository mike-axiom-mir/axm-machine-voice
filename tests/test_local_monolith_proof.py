from pathlib import Path
import argparse
import unittest

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import (  # noqa: E402
    BRIDGE_PROTOCOL,
    build_html,
    load_snapshot_outcome,
    parse_ref_key,
)
from axm_machine_voice import Ref, packet_dict  # noqa: E402


class LocalMonolithProofTests(unittest.TestCase):
    def test_generated_harness_is_offline_and_uses_real_bridge_contract(self):
        html = build_html()
        self.assertIn(BRIDGE_PROTOCOL, html)
        self.assertIn('src="index.html"', html)
        self.assertIn("deterministic-producer-demo-001", html)
        self.assertIn("synthetic state", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_harness_sends_packet_only_after_renderer_ready(self):
        html = build_html()
        ready_at = html.index('message.type === "ready"')
        send_at = html.index('type: "load-packet"')
        self.assertLess(ready_at, send_at)

    def test_harness_receives_primitive_response_without_claiming_journal_persistence(self):
        html = build_html()
        self.assertIn('message.type === "response-action"', html)
        self.assertIn('type: "response-status"', html)
        self.assertIn('status: responseStatus', html)
        self.assertIn('returnResponseStatus(message, "received")', html)
        self.assertIn("proof only, not journaled", html)
        self.assertNotIn("human:local-user", html)

    def test_parent_independently_validates_response_event_id_action_targets_and_response_id(self):
        html = build_html()
        self.assertIn('typeof message.response_id !== "string" || !message.response_id', html)
        self.assertIn('message.event_id !== packet.event_id', html)
        self.assertIn('RESPONSE_ACTIONS.has(message.action)', html)
        self.assertIn('Array.isArray(message.targets)', html)
        self.assertIn('message.action !== "acknowledge" && !packet.next_operations.includes(message.action)', html)
        self.assertIn('response_id: message.response_id ?? null', html)
        self.assertIn('returnResponseStatus(message, "rejected")', html)

    def test_inline_packet_is_canonical_producer_output_not_bundled_renderer_demo(self):
        html = build_html()
        self.assertIn('"producer":"lower-cost-alternative/0.2"', html)
        self.assertIn('"cost_metric":"metric:transition-steps"', html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)

    def test_versioned_snapshot_can_drive_same_harness_with_runtime_context(self):
        snapshot_path = ROOT / "examples" / "alternative_snapshot.example.json"
        outcome = load_snapshot_outcome(
            snapshot_path,
            active_refs=(Ref("activity", "local-monolith-proof"),),
        )
        self.assertEqual(outcome.status, "emitted")
        html = build_html(
            packet_dict(outcome.packet),
            source_label="snapshot-supplied state (external provenance not verified by renderer)",
        )
        self.assertIn("snapshot-example-001", html)
        self.assertIn("snapshot-supplied state", html)
        self.assertIn('"source":{"kind":"machine-floor","id":"snapshot-example"}', html)

    def test_snapshot_declared_activity_does_not_override_runtime_context(self):
        snapshot_path = ROOT / "examples" / "alternative_snapshot.example.json"
        outcome = load_snapshot_outcome(
            snapshot_path,
            active_refs=(Ref("activity", "different-work"),),
        )
        self.assertEqual(outcome.status, "rejected")
        self.assertIn("not_relevant_to_active_context", outcome.reasons)

    def test_active_ref_parser_preserves_colons_inside_identifier(self):
        self.assertEqual(parse_ref_key("activity:game:001"), Ref("activity", "game:001"))
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_ref_key("missing-separator")


if __name__ == "__main__":
    unittest.main()
