# State Snapshot Handoff v0.1

Machine Voice receives producer input as strict versioned JSON state snapshots instead of requiring callers to edit Python.

Supported schema identifiers:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
axm-machine-voice/unresolved-snapshot/0.1
axm-machine-voice/need-snapshot/0.1
axm-machine-voice/residual-snapshot/0.1
axm-machine-voice/outcome-snapshot/0.1
```

Complete examples include:

```text
examples/alternative_snapshot.example.json
examples/conflict_snapshot.example.json
examples/unresolved_snapshot.example.json
examples/need_snapshot.example.json
examples/residual_snapshot.example.json
examples/outcome_snapshot.example.json
examples/outcome_failure_snapshot.example.json
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

The caller separately supplies active runtime references. A speaker cannot make itself relevant merely by claiming relevance.

## Alternative snapshot

Names a cost metric, required constraints, a current option, alternatives, evidence, and next operations. If no strictly lower-cost alternative preserves every required constraint, the result is normal `no_candidate` silence.

## Conflict snapshot

Supplies grounded assertions with exact scope, subject, property, portable value, and evidence. It can emit only when assertions share the same exact scope/subject/property but carry different explicit values. It does not decide which assertion is true.

## Bounded unresolved snapshot

Names a problem, bounded search scope, required constraints, grounded attempts, and evidence. It can emit only when at least one grounded attempt exists and every supplied attempt misses at least one required constraint. Zero attempts or any fully resolving attempt means normal silence.

A surfaced packet keeps:

```json
{"global_impossibility_claimed": false}
```

## Bounded need snapshot

Names a task, bounded inventory scope, explicit required inputs, available inputs, and inventory evidence. It emits only when one or more required inputs are absent from the supplied inventory.

A surfaced packet keeps:

```json
{
  "bounded_inventory_only": true,
  "global_unavailability_claimed": false
}
```

## Residual snapshot

Supplies exact expected/observed/tolerance numeric comparisons plus separate evidence for expectation, observation, and tolerance.

It can emit only when at least one check satisfies:

```text
abs(observed - expected) > tolerance
```

Within tolerance, exactly at tolerance, or an empty check set are normal silence. A surfaced packet does not infer cause, novelty, model invalidity, or observation invalidity.

## Criterion outcome snapshot

Protocol:

```text
axm-machine-voice/outcome-snapshot/0.1
```

The snapshot supplies:

```text
attempt
attempt evidence
criteria contract
one or more required criteria
criteria-contract evidence
zero or more criterion observations
next operations
```

Each observation is exactly:

```json
{
  "criterion": {"kind": "criterion", "id": "..."},
  "observation": {"kind": "criterion-observation", "id": "..."},
  "satisfied": true,
  "evidence": [{"kind": "evidence", "id": "..."}]
}
```

The snapshot does **not** carry an aggregation-rule field. The producer fixes v0.1 to:

```text
all_required
```

Therefore:

```text
all required criteria grounded true  → SUCCESS → This worked.
any required criterion grounded false → FAILURE → This did not work.
partial all-positive evidence          → no_candidate silence
```

The success/failure meaning remains bounded to the supplied contract. Transport does not authenticate who authored the contract, whether it was modified later, or whether it truly existed before the attempt.

A success packet explicitly denies global success and contract-authenticity/timing claims. A failure packet explicitly denies global failure and the same authenticity/timing claims.

## Shared reference object

Every reference object is exactly:

```json
{"kind": "...", "id": "..."}
```

No adapter infers aliases or hidden equivalence between differently named references.

## Outcomes

All six adapters return the same `SnapshotOutcome` states:

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
process_outcome_snapshot(...)
```

`SNAPSHOT_SCHEMA` remains an alias for the original alternative schema for backward compatibility.

## Machine command

The same zero-install command accepts all supported snapshots:

```bash
python machine_voice.py snapshot examples/outcome_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

It returns the same versioned machine JSON outcome envelope regardless of producer type.

## Local monolith proof

Any supported snapshot can drive the same offline renderer:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/outcome_failure_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Rendering proves the handoff path worked. It does not prove the external source, evidence, criteria contract, or contract timing/authorship claim was truthful/correct.

## Truth boundary

The snapshot layer does not infer missing evidence, hidden constraints/requirements, metric meaning, assertion aliases, which side of a conflict is true, global impossibility from a bounded search, global unavailability from a bounded inventory, cause/novelty/model invalidity/observation invalidity from a residual, global success/failure from one criteria contract, criteria-contract authenticity/authorship/pre-attempt timing, source authenticity, or active relevance.

A future snapshot format that needs more meaning must use an explicit schema revision. Do not add fields and expect older readers to ignore them.
