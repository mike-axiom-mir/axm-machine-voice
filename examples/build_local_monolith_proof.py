"""Build one offline HTML proof that drives the local renderer through its bridge.

Without `--snapshot`, the packet comes from the synthetic deterministic example.
With `--snapshot`, the supplied versioned state snapshot is validated, processed by the
real producer and communication gate, then embedded only when it actually emits.
Snapshot relevance is checked against independently supplied `--active-ref` values.

The proof parent also receives primitive `response-action` messages from the child and
returns `response-status=received`. It independently checks event id, response id,
action vocabulary, packet next_operations, and target shape before acknowledging.
It deliberately does not claim journal persistence; real persistence belongs to the
monolith/runtime actor + communication-journal path.
"""

from html import escape
from pathlib import Path
from typing import Any, Mapping
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(EXAMPLES))

from axm_machine_voice import (  # noqa: E402
    Ref,
    outcome_dict,
    packet_dict,
    process_alternative_snapshot,
)
from run_deterministic_producer import build_packet  # noqa: E402


BRIDGE_PROTOCOL = "axm-machine-voice/local-bridge/0.1"


def parse_ref_key(value: str) -> Ref:
    kind, separator, identifier = value.partition(":")
    if not separator or not kind.strip() or not identifier.strip():
        raise argparse.ArgumentTypeError("reference must use non-empty kind:id form")
    return Ref(kind, identifier)


def load_snapshot_outcome(path: Path, *, active_refs: tuple[Ref, ...]):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("Snapshot file must contain a JSON object")
    return process_alternative_snapshot(data, active_refs=active_refs)


def build_html(
    packet: Mapping[str, Any] | None = None,
    *,
    source_label: str = "synthetic state",
) -> str:
    if packet is None:
        packet = packet_dict(build_packet())

    # Prevent a future state/reference value containing a literal closing script tag
    # from escaping the inline JavaScript payload.
    packet_json = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    source_label_html = escape(source_label)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>AXM Machine Voice — Monolith Proof Harness</title>
  <style>
    :root {{ color-scheme: dark; font-family: system-ui, sans-serif; background:#090d12; color:#edf3f8; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; background:#090d12; }}
    header {{ padding:12px 16px; border-bottom:1px solid #24303d; display:flex; gap:12px; flex-wrap:wrap; align-items:center; }}
    strong {{ font-size:14px; }}
    .truth {{ color:#f0c36a; font-size:12px; }}
    #status {{ margin-left:auto; font:12px ui-monospace, monospace; color:#9eb0c0; }}
    iframe {{ display:block; width:100%; height:calc(100vh - 58px); border:0; }}
  </style>
</head>
<body>
<header>
  <strong>Monolith bridge proof</strong>
  <span class=\"truth\">{source_label_html} → real producer/gate → canonical packet → local renderer</span>
  <span id=\"status\">waiting for renderer</span>
</header>
<iframe id=\"voice\" src=\"index.html\" title=\"AXM Machine Voice local renderer\"></iframe>
<script>
(() => {{
  \"use strict\";
  const PROTOCOL = {json.dumps(BRIDGE_PROTOCOL)};
  const RESPONSE_ACTIONS = new Set([\"inspect\", \"compare\", \"acknowledge\"]);
  const packet = {packet_json};
  const frame = document.getElementById(\"voice\");
  const status = document.getElementById(\"status\");

  function responseAllowed(message) {{
    if (typeof message.response_id !== \"string\" || !message.response_id) return false;
    if (message.event_id !== packet.event_id) return false;
    if (!RESPONSE_ACTIONS.has(message.action)) return false;
    if (!Array.isArray(message.targets)) return false;
    if (message.action !== \"acknowledge\" && !packet.next_operations.includes(message.action)) return false;
    return true;
  }}

  function returnResponseStatus(message, responseStatus) {{
    frame.contentWindow.postMessage({{
      protocol: PROTOCOL,
      type: \"response-status\",
      response_id: message.response_id ?? null,
      event_id: message.event_id ?? null,
      action: message.action ?? null,
      status: responseStatus
    }}, \"*\");
  }}

  window.addEventListener(\"message\", event => {{
    if (event.source !== frame.contentWindow) return;
    const message = event.data;
    if (!message || message.protocol !== PROTOCOL) return;

    if (message.type === \"ready\") {{
      status.textContent = \"renderer ready — sending packet\";
      frame.contentWindow.postMessage({{ protocol: PROTOCOL, type: \"load-packet\", packet }}, \"*\");
      return;
    }}

    if (message.type === \"packet-rendered\") {{
      status.textContent = `rendered ${{message.event_id ?? \"unknown event\"}} — response bridge ready`;
      return;
    }}

    if (message.type === \"response-action\") {{
      if (!responseAllowed(message)) {{
        status.textContent = \"response rejected — proof validation failed\";
        returnResponseStatus(message, \"rejected\");
        return;
      }}

      status.textContent = `response ${{message.action}} received — proof only, not journaled`;
      returnResponseStatus(message, \"received\");
    }}
  }});
}})();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Optional versioned Machine Voice state snapshot JSON. No page is generated if it produces silence/rejection.",
    )
    parser.add_argument(
        "--active-ref",
        action="append",
        type=parse_ref_key,
        default=[],
        help="Independently supplied active runtime reference in kind:id form. Required at least once with --snapshot.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "local" / "monolith_proof.generated.html",
        help="Generated proof page. Keep it beside local/index.html unless you adjust the iframe path.",
    )
    args = parser.parse_args()

    packet = None
    source_label = "synthetic state"
    if args.snapshot is not None:
        if not args.active_ref:
            parser.error("--snapshot requires at least one independent --active-ref")
        outcome = load_snapshot_outcome(args.snapshot, active_refs=tuple(args.active_ref))
        if outcome.packet is None:
            print(json.dumps(outcome_dict(outcome), indent=2, ensure_ascii=False))
            return
        packet = packet_dict(outcome.packet)
        source_label = "snapshot-supplied state (external provenance not verified by renderer)"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(packet, source_label=source_label), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
