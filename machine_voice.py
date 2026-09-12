"""Zero-install launcher for the Machine Voice machine channel.

Example:
    python machine_voice.py snapshot examples/alternative_snapshot.example.json \
        --active-ref activity:local-monolith-proof
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
source = str(ROOT / "src")
if source not in sys.path:
    sys.path.insert(0, source)

from axm_machine_voice.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
