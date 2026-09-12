from pathlib import Path
import unittest

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

from build_local_monolith_proof import BRIDGE_PROTOCOL, build_html  # noqa: E402


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

    def test_inline_packet_is_canonical_producer_output_not_bundled_renderer_demo(self):
        html = build_html()
        self.assertIn('"producer":"lower-cost-alternative/0.2"', html)
        self.assertIn('"cost_metric":"metric:transition-steps"', html)
        self.assertNotIn("demo-only-not-a-live-semantic-fingerprint", html)


if __name__ == "__main__":
    unittest.main()
