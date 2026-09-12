from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from .core import Ref, canonical_json
from .snapshot import outcome_dict, process_alternative_snapshot


def parse_ref_key(value: str) -> Ref:
    kind, separator, identifier = value.partition(":")
    if not separator or not kind.strip() or not identifier.strip():
        raise argparse.ArgumentTypeError("reference must use non-empty kind:id form")
    return Ref(kind, identifier)


def _read_snapshot(source: str) -> Mapping[str, Any]:
    if source == "-":
        text = sys.stdin.read()
    else:
        text = Path(source).read_text(encoding="utf-8")

    value = json.loads(text)
    if not isinstance(value, Mapping):
        raise ValueError("snapshot input must contain a JSON object")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axm-machine-voice",
        description="Machine-facing deterministic StateTalk interface.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser(
        "snapshot",
        help="Process one versioned alternative snapshot and emit one JSON outcome.",
    )
    snapshot.add_argument(
        "source",
        help="Snapshot JSON path, or '-' to read the snapshot from standard input.",
    )
    snapshot.add_argument(
        "--active-ref",
        action="append",
        type=parse_ref_key,
        required=True,
        help="Independently supplied active runtime reference in kind:id form. Repeat as needed.",
    )
    snapshot.add_argument(
        "--seen-fingerprint",
        action="append",
        default=[],
        help="Previously emitted semantic fingerprint. Repeat to enforce duplicate suppression.",
    )
    return parser


def _invalid(error: Exception) -> dict[str, Any]:
    return {
        "status": "invalid",
        "reasons": [type(error).__name__],
        "error": str(error),
        "fingerprint": None,
        "packet": None,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.command != "snapshot":  # argparse currently prevents this path.
        parser.error(f"unsupported command: {args.command}")

    try:
        snapshot = _read_snapshot(args.source)
        outcome = process_alternative_snapshot(
            snapshot,
            active_refs=tuple(args.active_ref),
            seen_fingerprints=frozenset(args.seen_fingerprint),
        )
        result = outcome_dict(outcome)
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        result = _invalid(error)
        exit_code = 2

    # One canonical JSON object is the whole machine-facing response. No explanatory
    # prose is mixed into stdout, so callers never need to scrape human text.
    sys.stdout.write(canonical_json(result) + "\n")
    return exit_code
