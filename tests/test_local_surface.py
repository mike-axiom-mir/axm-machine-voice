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

    def test_manifest_declares_offline_contract(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "axm-machine-voice")
        self.assertEqual(data["entry"], "local/index.html")
        self.assertFalse(data["network_required"])
        self.assertFalse(data["ai_required"])
        self.assertFalse(data["account_required"])
        self.assertFalse(data["cloud_required"])
        self.assertEqual(data["bridge"]["protocol"], "axm-machine-voice/local-bridge/0.1")

    def test_bridge_supports_parent_packet_without_network_dependency(self):
        text = LOCAL_HTML.read_text(encoding="utf-8")
        self.assertIn('message.type !== "load-packet"', text)
        self.assertIn('type: "ready"', text)
        self.assertIn('type: "packet-rendered"', text)
        self.assertIn('window.parent === window || event.source !== window.parent', text)


if __name__ == "__main__":
    unittest.main()
