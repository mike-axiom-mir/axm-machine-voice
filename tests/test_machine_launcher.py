from pathlib import Path
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "machine_voice.py"
EXAMPLE = ROOT / "examples" / "alternative_snapshot.example.json"
PROTOCOL = "axm-machine-voice/machine-channel/0.1"


class MachineLauncherTests(unittest.TestCase):
    def run_launcher(self, *args):
        return subprocess.run(
            [sys.executable, str(LAUNCHER), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_zero_install_launcher_emits_one_json_envelope(self):
        result = self.run_launcher(
            "snapshot",
            str(EXAMPLE),
            "--active-ref",
            "activity:local-monolith-proof",
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["protocol"], PROTOCOL)
        self.assertEqual(data["status"], "emitted")

    def test_launcher_syntax_failure_stays_on_json_channel(self):
        result = self.run_launcher("unknown")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, "")
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["protocol"], PROTOCOL)
        self.assertEqual(data["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
