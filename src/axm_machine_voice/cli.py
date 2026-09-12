from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from .core import Ref, canonical_json
from .journal import append_emission, append_response, emitted_fingerprints
from .snapshot import outcome_dict, process_alternative_snapshot


MACHINE_CHANNEL_PROTOCOL = "axm-machine-voice/machine-channel/0.1"


class MachineArgumentError(ValueError):
    pass


class MachineArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise MachineArgumentError(message)


def parse_ref_key(value: str) -> Ref:
    kind, separator, identifier = value.partition(":")
    if not separator or not kind.strip() or not identifier.strip():
        raise ValueError("reference must use non-empty kind:id form")
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


def _parser() -> MachineArgumentParser:
    parser = MachineArgumentParser(
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
        default=[],
        help="Independently supplied active runtime reference in kind:id form. Repeat as needed.",
    )
    snapshot.add_argument(
        "--seen-fingerprint",
        action="append",
        default=[],
        help="Previously emitted semantic fingerprint. Repeat to enforce duplicate suppression.",
    )
    snapshot.add_argument(
        "--journal",
        type=Path,
        help=(
            "Optional append-only communication journal. Prior emissions automatically "
            "suppress repeats; a new record is appended only when communication emits."
        ),
    )

    respond = subparsers.add_parser(
        "respond",
        help="Append one structured response to a communication already present in a journal.",
    )
    respond.add_argument("journal", type=Path, help="Communication journal JSONL path.")
    respond.add_argument("--event-id", required=True, help="Previously emitted event id.")
    respond.add_argument("--actor", required=True, help="Responder reference in kind:id form.")
    respond.add_argument("--action", required=True, help="Structured response action, e.g. inspect or compare.")
    respond.add_argument(
        "--target",
        action="append",
        default=[],
        help="Optional response target reference in kind:id form. Repeat as needed.",
    )
    return parser


def _envelope(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {"protocol": MACHINE_CHANNEL_PROTOCOL, **dict(payload)}


def _invalid(error: Exception) -> dict[str, Any]:
    return _envelope({
        "status": "invalid",
        "reasons": [type(error).__name__],
        "error": str(error),
        "fingerprint": None,
        "packet": None,
    })


def _snapshot_result(args: argparse.Namespace) -> dict[str, Any]:
    if not args.active_ref:
        raise ValueError("snapshot command requires at least one --active-ref")

    active_refs = tuple(parse_ref_key(value) for value in args.active_ref)
    if any(not value.strip() for value in args.seen_fingerprint):
        raise ValueError("--seen-fingerprint values must be non-empty")

    seen = set(args.seen_fingerprint)
    if args.journal is not None:
        seen.update(emitted_fingerprints(args.journal))

    snapshot = _read_snapshot(args.source)
    outcome = process_alternative_snapshot(
        snapshot,
        active_refs=active_refs,
        seen_fingerprints=frozenset(seen),
    )
    if args.journal is not None and outcome.packet is not None:
        append_emission(args.journal, outcome.packet)
    return _envelope(outcome_dict(outcome))


def _response_result(args: argparse.Namespace) -> dict[str, Any]:
    actor = parse_ref_key(args.actor)
    targets = tuple(parse_ref_key(value) for value in args.target)
    record = append_response(
        args.journal,
        event_id=args.event_id,
        actor=actor,
        action=args.action,
        targets=targets,
    )
    return _envelope({
        "status": "recorded",
        "reasons": [],
        "fingerprint": None,
        "packet": None,
        "journal_record": {
            "sequence": record["sequence"],
            "record_hash": record["record_hash"],
            "type": record["type"],
            "event_id": record["event_id"],
        },
    })


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()

    try:
        args = parser.parse_args(argv)
        if args.command == "snapshot":
            result = _snapshot_result(args)
        elif args.command == "respond":
            result = _response_result(args)
        else:  # parser currently prevents this path.
            raise MachineArgumentError(f"unsupported command: {args.command}")
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        result = _invalid(error)
        exit_code = 2

    # One canonical JSON object is the whole machine-facing response. No explanatory
    # prose is mixed into stdout, so callers never need to scrape human text.
    sys.stdout.write(canonical_json(result) + "\n")
    return exit_code
