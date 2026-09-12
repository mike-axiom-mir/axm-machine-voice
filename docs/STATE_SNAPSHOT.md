# State Snapshot Handoff v0.1

Machine Voice receives producer input as strict versioned JSON state snapshots instead of requiring callers to edit Python.

Supported schema identifiers:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
axm-machine-voice/unresolved-snapshot/0.1
```

Complete examples:

```text
examples/alternative_snapshot.example.json
examples/conflict_snapshot.example.json
examples/unresolved_snapshot.example.json
```

Portable JSON Schema descriptions:

```text
schemas/alternative-snapshot-0.1.schema.json
schemas/conflict-snapshot-0.1.schema.json
schemas/unresolved-snapshot-0.1.schema.json
```

## Shared handoff

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

The router never guesses the producer from filenames or field similarity. The explicit `schema` value selects the exact adapter. Unsupported schema ids fail closed.

Adapters reject unknown fields instead of silently discarding meaning.

## Declared relevance is not active context

Every supported snapshot contains an `activity` reference. That says what the snapshot declares its result relates to; it does **not** prove that activity is current.

The caller separately supplies active runtime references. Therefore this remains valid:

```text
snapshot says: activity:A
runtime says:  activity:B
              ↓
REJECT: not_relevant_to_active_context
```

A speaker cannot make itself relevant merely by claiming relevance.

## Alternative snapshot

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

Each option supplies a reference, numeric cost under the explicitly named metric, preserved constraints, and evidence. If no strictly lower-cost alternative preserves every required constraint, the result is normal `no_candidate` silence.

## Conflict snapshot

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

Each assertion names an exact scope, subject and property, carries a portable value, and includes evidence. It can emit only when grounded assertions share the same exact scope/subject/property but carry different values. It does not decide which assertion is true.

If no exact comparable contradiction exists, the result is normal `no_candidate` silence.

## Bounded unresolved snapshot

```json
{
  "schema": "axm-machine-voice/unresolved-snapshot/0.1",
  "event_id": "event-003",
  "source": {"kind": "machine-floor", "id": "main"},
  "activity": {"kind": "activity", "id": "current-work"},
  "problem": {"kind": "problem", "id": "candidate-route"},
  "search_scope": {"kind": "search-scope", "id": "run-01"},
  "required_constraints": [],
  "attempts": [],
  "next_operations": ["inspect", "compare"]
}
```

Each attempt supplies a reference, the required constraints it explicitly preserves, and evidence.

The bounded-unresolved producer can emit only when:

- at least one grounded attempt is supplied;
- required constraints are explicit;
- every supplied attempt misses at least one required constraint.

Zero attempts is normal `no_candidate` silence. If any attempt preserves all required constraints, that is also normal `no_candidate` silence.

A surfaced unresolved packet explicitly preserves the boundary:

```json
{"global_impossibility_claimed": false}
```

So `I cannot resolve this.` means only that the named supplied search did not contain a fully constraint-preserving resolution. It never means no solution exists globally.

## Shared reference object

Every reference object is exactly:

```json
{"kind": "...", "id": "..."}
```

No adapter infers aliases or hidden equivalence between differently named references.

## Outcomes

All three adapters return the same `SnapshotOutcome` states:

- `emitted` — a candidate survived its exact producer and the communication gate;
- `no_candidate` — the supplied state contains nothing that producer is allowed to say;
- `rejected` — a candidate existed but the communication gate refused it.

Malformed or semantically ambiguous input raises an error instead of being converted into plausible communication.

## Generic runtime API

```python
from axm_machine_voice import process_snapshot
```

The explicit schema id routes to the exact adapter.

Producer-specific callers can still use:

```python
process_alternative_snapshot(...)
process_conflict_snapshot(...)
process_unresolved_snapshot(...)
```

`SNAPSHOT_SCHEMA` remains an alias for the original alternative schema for backward compatibility.

## Machine command

The same zero-install command accepts all supported snapshots:

```bash
python machine_voice.py snapshot examples/unresolved_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

It returns the same versioned machine JSON outcome envelope regardless of producer type.

## Local monolith proof

Any supported snapshot can drive the same offline renderer:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/unresolved_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Then open:

```text
local/monolith_proof.generated.html
```

Rendering proves the handoff path worked. It does not prove the external source or evidence was truthful.

## Truth boundary

The snapshot layer does not infer missing evidence, hidden constraints, metric meaning, assertion aliases, which side of a conflict is true, global impossibility from a bounded search, source authenticity, or active relevance.

A future snapshot format that needs more meaning must use an explicit schema revision. Do not add fields and expect older readers to ignore them.
