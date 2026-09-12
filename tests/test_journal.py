from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_machine_voice import (  # noqa: E402
    JOURNAL_PROTOCOL,
    Ref,
    append_emission,
    append_response,
    emitted_event_ids,
    emitted_fingerprints,
    process_alternative_snapshot,
    read_journal,
)


class CommunicationJournalTests(unittest.TestCase):
    def setUp(self):
        self.example = ROOT / "examples" / "alternative_snapshot.example.json"
        self.active = Ref("activity", "local-monolith-proof")

    def packet(self):
        snapshot = json.loads(self.example.read_text(encoding="utf-8"))
        outcome = process_alternative_snapshot(snapshot, active_refs=(self.active,))
        self.assertEqual(outcome.status, "emitted")
        return outcome.packet

    def test_emission_is_append_only_and_reloads_seen_fingerprint(self):
        packet = self.packet()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            record = append_emission(path, packet)
            records = read_journal(path)

            self.assertEqual(len(records), 1)
            self.assertEqual(record["protocol"], JOURNAL_PROTOCOL)
            self.assertEqual(record["sequence"], 1)
            self.assertIsNone(record["previous_hash"])
            self.assertEqual(record["type"], "emission")
            self.assertIn(packet.fingerprint, emitted_fingerprints(path))
            self.assertIn(packet.event_id, emitted_event_ids(path))

    def test_duplicate_emission_is_rejected(self):
        packet = self.packet()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            append_emission(path, packet)
            with self.assertRaisesRegex(ValueError, "already contains"):
                append_emission(path, packet)
            self.assertEqual(len(read_journal(path)), 1)

    def test_response_must_reference_real_emitted_event(self):
        packet = self.packet()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            append_emission(path, packet)
            response = append_response(
                path,
                event_id=packet.event_id,
                actor=Ref("human", "local-user"),
                action="inspect",
                targets=(packet.subjects[1],),
            )
            self.assertEqual(response["sequence"], 2)
            self.assertEqual(response["type"], "response")
            self.assertEqual(response["previous_hash"], read_journal(path)[0]["record_hash"])

            with self.assertRaisesRegex(ValueError, "does not reference"):
                append_response(
                    path,
                    event_id="never-emitted",
                    actor=Ref("human", "local-user"),
                    action="inspect",
                )

    def test_hash_chain_detects_silent_edit_of_old_record(self):
        packet = self.packet()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            append_emission(path, packet)
            append_response(
                path,
                event_id=packet.event_id,
                actor=Ref("human", "local-user"),
                action="inspect",
            )

            lines = path.read_text(encoding="utf-8").splitlines()
            first = json.loads(lines[0])
            first["packet"]["event_id"] = "silently-edited"
            lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_journal(path)

    def test_reordering_records_breaks_chain(self):
        packet = self.packet()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            append_emission(path, packet)
            append_response(
                path,
                event_id=packet.event_id,
                actor=Ref("machine", "monolith"),
                action="compare",
            )
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text(lines[1] + "\n" + lines[0] + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_journal(path)

    def test_journal_is_explicitly_not_tail_deletion_proof(self):
        packet = self.packet()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            append_emission(path, packet)
            append_response(
                path,
                event_id=packet.event_id,
                actor=Ref("human", "local-user"),
                action="acknowledge",
            )
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
            path.write_text(first_line + "\n", encoding="utf-8")
            # A local hash chain cannot prove that an intact tail was deleted without
            # some external checkpoint. The surviving prefix remains internally valid.
            self.assertEqual(len(read_journal(path)), 1)


if __name__ == "__main__":
    unittest.main()
