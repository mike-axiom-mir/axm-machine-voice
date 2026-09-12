from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCAL_HTML = ROOT / "local" / "index.html"
MANIFEST = ROOT / "local" / "manifest.json"


class LocalSurfaceTests(unittest.TestCase):
    def test_local_surface_is_single_file_and_offline_by_default(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn("offline / no AI / no network", text)
        self.assertNotIn("https://", text)
        self.assertNotIn("http://", text)
        self.assertNotIn("fetch(", text)
        self.assertNotIn("WebSocket", text)

    def test_floorvoice_vocabulary_is_fixed_in_local_renderer(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        for phrase in (
            "I noticed something.",
            "These do not fit.",
            "There is another way.",
            "I cannot resolve this.",
            "I need something.",
            "This happened before.",
            "This is new.",
            "This worked.",
            "This did not work.",
            "Look here.",
        ):
            self.assertIn(phrase, text)

    def test_demo_is_explicitly_not_live(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn("not a live Machine Floor event", text)
        self.assertIn('source_mode: "bundled_demo"', text)
        self.assertIn("Response bridge inactive for the bundled demo.", text)

    def test_manifest_declares_offline_and_response_bridge_contract(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "axm-machine-voice")
        self.assertEqual(data["entry"], "local/index.html")
        self.assertFalse(data["network_required"])
        self.assertFalse(data["ai_required"])
        self.assertFalse(data["account_required"])
        self.assertFalse(data["cloud_required"])
        self.assertEqual(data["bridge"]["protocol"], "axm-machine-voice/local-bridge/0.1")
        self.assertIn("load-packet", data["bridge"]["accepts"])
        self.assertIn("response-status", data["bridge"]["accepts"])
        self.assertIn("response-action", data["bridge"]["emits"])

    def test_bridge_accepts_messages_only_from_actual_parent(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn('window.parent === window || event.source !== window.parent', text)
        self.assertIn('message.type === "load-packet"', text)
        self.assertIn('message.type === "response-status"', text)
        self.assertIn('type: "ready"', text)
        self.assertIn('type: "packet-rendered"', text)

    def test_response_actions_are_bounded_and_actor_is_not_self_asserted(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn('RESPONSE_ACTIONS = Object.freeze(["inspect", "compare", "acknowledge"])', text)
        self.assertIn('type: "response-action"', text)
        self.assertIn('targets: []', text)
        self.assertIn("Actor identity is supplied by the parent runtime", text)
        self.assertIn('currentPacket.next_operations.includes(action)', text)
        self.assertIn('currentSourceMode !== "embedded"', text)

        response_payload = text[text.index('type: "response-action"'):text.index('el("responseStatus").textContent = `Sent')]
        self.assertNotIn("actor", response_payload.lower())

    def test_each_response_has_local_id_and_confirmation_must_match_it(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn('const responseId = `local-response-${nextResponseNumber++}`', text)
        self.assertIn('pendingResponses.set(responseId, response)', text)
        self.assertIn('response_id: responseId', text)
        self.assertIn('const pending = pendingResponses.get(message.response_id)', text)
        self.assertIn('message.event_id !== pending.event_id || message.action !== pending.action', text)
        self.assertIn('pendingResponses.delete(message.response_id)', text)
        self.assertIn('pendingResponses.clear()', text)

    def test_response_status_does_not_claim_persistence_before_matching_parent_confirmation(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn("persistence is not claimed until the parent confirms this exact response", text)
        self.assertIn('RESPONSE_STATUSES = new Set(["received", "recorded", "rejected"])', text)
        self.assertIn("received by parent runtime; persistence not confirmed", text)
        self.assertIn("recorded by parent runtime", text)
        self.assertIn('typeof message.response_id !== "string"', text)


if __name__ == "__main__":
    unittest.main()
