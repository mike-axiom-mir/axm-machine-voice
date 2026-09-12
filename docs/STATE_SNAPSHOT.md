# State Snapshot Handoff v0.1

Machine Voice receives producer input as strict versioned JSON state snapshots instead of requiring callers to edit Python.

Supported schema identifiers:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
axm-machine-voice/unresolved-snapshot/0.1
axm-machine-voice/need-snapshot/0.1
axm-machine-voice/residual-snapshot/0.1
```

Complete examples:

```text
examples/alternative_snapshot.example.json
examples/conflict_snapshot.example.json
examples/unresolved_snapshot.example.json
examples/need_snapshot.example.json
examples/residual_snapshot.example.json
```

Portable JSON Schema descriptions live under `schemas/` with matching names.

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

The router never guesses the producer from filenames or field similarity. The explicit `schema` value selects the exact adapter. Unsupported schema ids fail closed. Adapters reject unknown fields instead of silently discarding meaning.

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

The alternative snapshot names a cost metric, required constraints, a current option, alternatives, evidence, and next operations.

If no strictly lower-cost alternative preserves every required constraint, the result is normal `no_candidate` silence.

## Conflict snapshot

The conflict snapshot supplies grounded assertions with exact scope, subject, property, portable value, and evidence.

It can emit only when assertions share the same exact scope/subject/property but carry different explicit values. It does not decide which assertion is true. No exact comparable contradiction means normal `no_candidate` silence.

## Bounded unresolved snapshot

The unresolved snapshot names a problem, bounded search scope, required constraints, grounded attempts, and evidence.

It can emit only when at least one grounded attempt exists and every supplied attempt misses at least one required constraint. Zero attempts or any fully resolving attempt means normal `no_candidate` silence.

A surfaced packet keeps:

```json
{"global_impossibility_claimed": false}
```

## Bounded need snapshot

The need snapshot names a task, bounded inventory scope, explicit required inputs, available inputs, and inventory evidence.

It can emit only when one or more explicitly required inputs are absent from the supplied inventory. If every required input is present, the result is normal `no_candidate` silence.

A surfaced packet keeps:

```json
{
  "bounded_inventory_only": true,
  "global_unavailability_claimed": false
}
```

## Residual snapshot

```json
{
  "schema": "axm-machine-voice/residual-snapshot/0.1",
  "event_id": "event-005",
  "source": {"kind": "machine-floor", "id": "main"},
  "activity": {"kind": "activity", "id": "current-work"},
  "checks": [],
  "next_operations": ["inspect", "compare"]
}
```

Each residual check explicitly supplies:

```text
ref
subject
property
metric
expected numeric value
observed numeric value
non-negative tolerance
expected evidence
observed evidence
tolerance evidence
```

It can emit only when at least one supplied check satisfies:

```text
abs(observed - expected) > tolerance
```

Within tolerance, exactly at tolerance, or an empty check set are normal `no_candidate` silence.

A surfaced packet does not infer an explanation and preserves:

```json
{
  "cause": null,
  "cause_claimed": false,
  "novelty_claimed": false,
  "model_invalidity_claimed": false,
  "observation_invalidity_claimed": false
}
```

So `Look here.` means only that the supplied expected/observed comparison exceeded its supplied tolerance under its supplied metric.

## Shared reference object

Every reference object is exactly:

```json
{"kind": "...", "id": "..."}
```

No adapter infers aliases or hidden equivalence between differently named references.

## Outcomes

All five adapters return the same `SnapshotOutcome` states:

- `emitted` — a candidate survived its exact producer and the communication gate;
- `no_candidate` — the supplied state contains nothing that producer is allowed to say;
- `rejected` — a candidate existed but the communication gate refused it.

Malformed or semantically ambiguous input raises an error instead of being converted into plausible communication.

## Runtime API

Generic callers use:

```python
from axm_machine_voice import process_snapshot
```

Producer-specific callers may use:

```python
process_alternative_snapshot(...)
process_conflict_snapshot(...)
process_unresolved_snapshot(...)
process_need_snapshot(...)
process_residual_snapshot(...)
```

`SNAPSHOT_SCHEMA` remains an alias for the original alternative schema for backward compatibility.

## Machine command

The same zero-install command accepts all supported snapshots:

```bash
python machine_voice.py snapshot examples/residual_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

It returns the same versioned machine JSON outcome envelope regardless of producer type.

## Local monolith proof

Any supported snapshot can drive the same offline renderer:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/residual_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Rendering proves the handoff path worked. It does not prove the external source, evidence, expected model, observation, or tolerance was truthful/correct.

## Truth boundary

The snapshot layer does not infer missing evidence, hidden constraints/requirements, metric meaning, assertion aliases, which side of a conflict is true, global impossibility from a bounded search, global unavailability from a bounded inventory, cause/novelty/model invalidity/observation invalidity from a residual, source authenticity, or active relevance.

A future snapshot format that needs more meaning must use an explicit schema revision. Do not add fields and expect older readers to ignore them.
