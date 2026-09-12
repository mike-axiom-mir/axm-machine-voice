from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .core import Ref, StateTalkPacket, canonical_json, packet_dict


JOURNAL_PROTOCOL = "axm-machine-voice/communication-journal/0.1"


def _hash_payload(payload: Mapping[str, Any]) -> str:
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _nonempty_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    missing = expected - actual
    unknown = actual - expected
    if missing:
        raise ValueError(f"{path} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{path} has unknown keys: {', '.join(sorted(unknown))}")


def _validate_ref(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    _exact_keys(value, {"kind", "id"}, path)
    return {
        "kind": _nonempty_text(value["kind"], f"{path}.kind"),
        "id": _nonempty_text(value["id"], f"{path}.id"),
    }


def _validate_record(record: Mapping[str, Any], *, expected_sequence: int, previous_hash: str | None) -> None:
    common = {"protocol", "sequence", "previous_hash", "type", "record_hash"}
    record_type = record.get("type")
    if record_type == "emission":
        expected = common | {"packet"}
    elif record_type == "response":
        expected = common | {"event_id", "actor", "action", "targets"}
    else:
        raise ValueError(f"journal record has unsupported type: {record_type!r}")

    _exact_keys(record, expected, f"journal[{expected_sequence}]")
    if record["protocol"] != JOURNAL_PROTOCOL:
        raise ValueError(f"journal record uses unsupported protocol: {record['protocol']!r}")

    sequence = record["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise ValueError(f"journal sequence must be an integer at sequence {expected_sequence}")
    if sequence != expected_sequence:
        raise ValueError(
            f"journal sequence mismatch: expected {expected_sequence}, got {sequence!r}"
        )
    if record["previous_hash"] != previous_hash:
        raise ValueError(f"journal previous_hash mismatch at sequence {expected_sequence}")

    supplied_hash = _nonempty_text(record["record_hash"], f"journal[{expected_sequence}].record_hash")
    payload = dict(record)
    payload.pop("record_hash")
    expected_hash = _hash_payload(payload)
    if supplied_hash != expected_hash:
        raise ValueError(f"journal record hash mismatch at sequence {expected_sequence}")

    if record_type == "emission":
        packet = record["packet"]
        if not isinstance(packet, Mapping):
            raise ValueError(f"journal[{expected_sequence}].packet must be an object")
        _nonempty_text(packet.get("event_id"), f"journal[{expected_sequence}].packet.event_id")
        _nonempty_text(packet.get("fingerprint"), f"journal[{expected_sequence}].packet.fingerprint")
    else:
        _nonempty_text(record["event_id"], f"journal[{expected_sequence}].event_id")
        _validate_ref(record["actor"], f"journal[{expected_sequence}].actor")
        _nonempty_text(record["action"], f"journal[{expected_sequence}].action")
        targets = record["targets"]
        if not isinstance(targets, list):
            raise ValueError(f"journal[{expected_sequence}].targets must be an array")
        for index, target in enumerate(targets):
            _validate_ref(target, f"journal[{expected_sequence}].targets[{index}]")


def read_journal(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Read and verify the complete append-only journal.

    The hash chain is tamper-evident, not tamper-proof: it detects edits/reordering of
    records that remain present, but no local file format can prove that an attacker did
    not delete an intact tail without an external checkpoint.
    """

    journal_path = Path(path)
    if not journal_path.exists():
        return ()

    records: list[dict[str, Any]] = []
    previous_hash: str | None = None
    with journal_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"journal contains blank line at {line_number}")
            value = json.loads(line)
            if not isinstance(value, Mapping):
                raise ValueError(f"journal line {line_number} must contain an object")
            record = dict(value)
            _validate_record(record, expected_sequence=line_number, previous_hash=previous_hash)
            records.append(record)
            previous_hash = record["record_hash"]

    event_ids = [
        record["packet"]["event_id"]
        for record in records
        if record["type"] == "emission"
    ]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("journal contains duplicate emitted event_id values")
    return tuple(records)


def emitted_fingerprints(path: str | Path) -> frozenset[str]:
    return frozenset(
        record["packet"]["fingerprint"]
        for record in read_journal(path)
        if record["type"] == "emission"
    )


def emitted_event_ids(path: str | Path) -> frozenset[str]:
    return frozenset(
        record["packet"]["event_id"]
        for record in read_journal(path)
        if record["type"] == "emission"
    )


def _append_payload(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    journal_path = Path(path)
    records = read_journal(journal_path)
    sequence = len(records) + 1
    previous_hash = records[-1]["record_hash"] if records else None

    record = {
        "protocol": JOURNAL_PROTOCOL,
        "sequence": sequence,
        "previous_hash": previous_hash,
        **payload,
    }
    record["record_hash"] = _hash_payload(record)

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(record) + "\n")
    return record


def append_emission(path: str | Path, packet: StateTalkPacket) -> dict[str, Any]:
    """Append one communication that actually passed the gate.

    Rejected candidates and normal silence are intentionally not journaled as speech.
    Event ids are unique within one journal so a later response cannot be ambiguous.
    """

    if packet.fingerprint in emitted_fingerprints(path):
        raise ValueError("journal already contains this emitted semantic fingerprint")
    if packet.event_id in emitted_event_ids(path):
        raise ValueError("journal already contains this emitted event_id")
    return _append_payload(path, {"type": "emission", "packet": packet_dict(packet)})


def append_response(
    path: str | Path,
    *,
    event_id: str,
    actor: Ref,
    action: str,
    targets: tuple[Ref, ...] = (),
) -> dict[str, Any]:
    """Append a structured response to a previously emitted communication.

    This records interaction, not free-form interpretation. The action vocabulary is
    intentionally open so future humans/machines can add bounded response actions
    without rewriting prior records.
    """

    event_id = _nonempty_text(event_id, "event_id")
    action = _nonempty_text(action, "action")
    if event_id not in emitted_event_ids(path):
        raise ValueError("response event_id does not reference an emitted journal event")

    return _append_payload(
        path,
        {
            "type": "response",
            "event_id": event_id,
            "actor": {"kind": actor.kind, "id": actor.id},
            "action": action,
            "targets": [{"kind": target.kind, "id": target.id} for target in targets],
        },
    )
