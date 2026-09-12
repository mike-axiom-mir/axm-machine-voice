# State Snapshot Handoff v0.1

Machine Voice can receive producer input as strict versioned JSON state snapshots instead of requiring Python code changes.

Supported schema identifiers:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
```

Complete examples:

```text
examples/alternative_snapshot.example.json
examples/conflict_snapshot.example.json
```

Portable JSON Schema descriptions:

```text
schemas/alternative-snapshot-0.1.schema.json
schemas/conflict-snapshot-0.1.schema.json
```

## Why this exists

The local/monolith integration needs a narrow machine-native handoff boundary:

```text
monolith / Machine Floor state
        ↓
versioned JSON snapshot
        ↓
strict schema-id router
        ↓
exact producer adapter
        ↓
deterministic producer
        ↓
communication gate  ← independently supplied active runtime context
        ↓
StateTalk packet or silence/rejection
```

The router never guesses which producer a snapshot belongs to from its filename or fields. The explicit `schema` value selects the exact adapter. Unsupported schema ids fail closed.

Adapters are intentionally strict. Unknown fields are rejected rather than ignored so a newer producer cannot accidentally send meaning that an older adapter silently drops.

## Declared relevance is not active context

Both snapshot types contain an `activity` reference. That is the producer's **declared relevance**: what the snapshot says its candidate relates to.

It is not allowed to certify that this activity is actually current.

The caller separately supplies one or more active runtime references. The normal communication gate compares the snapshot's declared relevance against those independently supplied references.

Therefore this remains possible for either producer:

```text
snapshot says: activity:A
runtime says:  activity:B
              ↓
REJECT: not_relevant_to_active_context
```

This separation is intentional. A speaker should not become relevant merely by claiming relevance.

## Alternative snapshot

Top-level shape:

```json
{
  "schema": "axm-machine-voice/alternative-snapshot/0.1",
  "event_id": "event-001",
  "source": {"kind": "machine-floor", "id": "main"},
  "activity": {"kind": "activity", "id": "current-work"},
  "cost_metric": {"kind": "metric", "id": "transition-steps"},
  "required_constraints": [],
  "current": {},
  "alternatives": [],
  "next_operations": ["inspect", "compare"]
}
```

Each option is exactly:

```json
{
  "ref": {"kind": "state", "id": "..."},
  "cost": 12,
  "preserves": [{"kind": "constraint", "id": "..."}],
  "evidence": [{"kind": "evidence", "id": "..."}]
}
```

`cost` has no universal meaning. `cost_metric` names the metric under which every option cost in that snapshot is compared.

If no strictly lower-cost alternative preserves every required constraint, the result is normal `no_candidate` silence.

## Conflict snapshot

Top-level shape:

```json
{
  "schema": "axm-machine-voice/conflict-snapshot/0.1",
  "event_id": "event-002",
  "source": {"kind": "machine-floor", "id": "main"},
  "activity": {"kind": "activity", "id": "current-work"},
  "assertions": [],
  "next_operations": ["inspect", "compare"]
}
```

Each assertion is exactly:

```json
{
  "ref": {"kind": "assertion", "id": "..."},
  "scope": {"kind": "scope", "id": "..."},
  "subject": {"kind": "state", "id": "..."},
  "property": {"kind": "property", "id": "..."},
  "value": true,
  "evidence": [{"kind": "evidence", "id": "..."}]
}
```

The exact-conflict producer can emit only when at least two grounded assertions share the same explicit scope, subject, and property but have different portable values. It does not decide which assertion is true.

If no exact comparable contradiction exists, the result is normal `no_candidate` silence.

## Shared reference object

Every reference object is exactly:

```json
{"kind": "...", "id": "..."}
```

No adapter infers aliases or hidden equivalence between differently named references.

## Outcomes

Both adapters return the same `SnapshotOutcome` states:

- `emitted` — a candidate survived its producer and the communication gate and has a canonical StateTalk packet;
- `no_candidate` — the supplied state contains nothing that producer is allowed to say; silence is normal;
- `rejected` — a candidate existed but the communication gate refused it, for example because its declared activity is not active or its semantic fingerprint was already seen.

Malformed or semantically ambiguous input raises an error instead of being converted into communication.

## Generic runtime API

A caller that accepts any currently supported snapshot can use:

```python
from axm_machine_voice import process_snapshot
```

The explicit schema id routes to the exact adapter.

Producer-specific callers can still use:

```python
process_alternative_snapshot(...)
process_conflict_snapshot(...)
```

The original `SNAPSHOT_SCHEMA` constant remains an alias for the alternative schema for backward compatibility.

## Machine command

The same zero-install command accepts either supported snapshot:

```bash
python machine_voice.py snapshot examples/alternative_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

or:

```bash
python machine_voice.py snapshot examples/conflict_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

The command returns the same versioned machine JSON outcome envelope regardless of producer type.

## Local monolith proof

Either snapshot can drive the same offline renderer:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/conflict_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Then open:

```text
local/monolith_proof.generated.html
```

The generated page labels snapshot provenance as externally supplied and **not verified by the renderer**. Rendering proves that the handoff path worked; it does not prove the external source was truthful.

For a real monolith integration, `--active-ref` is only a test-harness stand-in. The runtime should supply its actual active state/context directly when calling the adapter.

## Truth boundary

The snapshot layer does not infer:

- missing evidence;
- hidden constraints;
- metric meaning;
- assertion equivalence across differently named scope/subject/property refs;
- which side of a conflict is true;
- source authenticity;
- active relevance.

A future snapshot format that needs more meaning must use an explicit schema revision. Do not add fields and expect older readers to ignore them.
