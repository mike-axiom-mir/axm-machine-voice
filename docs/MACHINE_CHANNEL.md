# Machine Channel v0.1

Machine Voice has a non-human command surface for monoliths, local tools, AIs, and other machines that need canonical results without opening FloorVoice.

Protocol:

```text
axm-machine-voice/machine-channel/0.1
```

The channel is deterministic, local, standard-library-only, and emits exactly one canonical JSON object on stdout per invocation.

## Snapshot command

One command accepts every explicitly supported snapshot schema:

```bash
python machine_voice.py snapshot examples/residual_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Currently supported snapshot schemas are:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
axm-machine-voice/unresolved-snapshot/0.1
axm-machine-voice/need-snapshot/0.1
axm-machine-voice/residual-snapshot/0.1
```

Routing is based only on the explicit `schema` id. Unsupported ids fail closed.

Snapshots may also be piped over stdin. `--active-ref` stays outside the snapshot so a snapshot cannot certify its own relevance.

Repeated `--seen-fingerprint` arguments suppress already-emitted semantics. A communication journal can provide prior fingerprints automatically:

```bash
python machine_voice.py snapshot examples/residual_snapshot.example.json \
  --active-ref activity:local-monolith-proof \
  --journal local/communication.jsonl
```

Only newly emitted communication is appended.

## Structured response command

```bash
python machine_voice.py respond local/communication.jsonl \
  --event-id residual-snapshot-example-001 \
  --actor human:local-user \
  --action inspect
```

The response command appends interaction structure to an already emitted journal event. It does not create a new StateTalk claim.

## Response contract

Every invocation returns exactly one JSON object.

Valid exit-code-0 states:

- `emitted` — a canonical StateTalk packet exists;
- `no_candidate` — the exact producer found nothing it is allowed to say;
- `rejected` — a candidate existed but the communication gate refused it;
- `recorded` — a structured response was appended to a valid journal event.

Invalid input uses exit code `2` and still returns the same versioned envelope with `status: invalid`.

No explanatory prose is mixed into stdout.

## Python integration

Generic callers can use:

```python
from axm_machine_voice import process_snapshot
```

Producer-specific callers can use:

```python
process_alternative_snapshot(...)
process_conflict_snapshot(...)
process_unresolved_snapshot(...)
process_need_snapshot(...)
process_residual_snapshot(...)
```

Journal-aware runtimes can additionally use `append_emission`, `append_response`, `emitted_fingerprints`, and `read_journal`.

## Truth boundary

The machine channel does not authenticate snapshot creators or response actors, prove evidence true, choose which side of a conflict is correct, turn a bounded unresolved search into global impossibility, turn a bounded inventory miss into global unavailability, turn a residual into a cause/novelty/model-failure claim, make proposals canonical, execute proposal contents, generate explanatory prose, or convert invalid state into a plausible guess.

Its job is narrower: preserve one deterministic versioned route from supplied state to canonical Machine Voice output, grounded silence/rejection, or an explicit structured interaction record.
