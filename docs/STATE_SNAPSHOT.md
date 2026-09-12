# State Snapshot Handoff v0.1

Machine Voice can receive producer input as a versioned JSON state snapshot instead of requiring Python code changes.

Schema identifier:

```text
axm-machine-voice/alternative-snapshot/0.1
```

A complete example lives at:

```text
examples/alternative_snapshot.example.json
```

## Why this exists

The local/monolith integration needs a narrow handoff boundary:

```text
monolith / Machine Floor state
        ↓
versioned JSON snapshot
        ↓
strict adapter
        ↓
deterministic producer
        ↓
communication gate  ← independently supplied active runtime context
        ↓
StateTalk packet or silence
```

The adapter is intentionally strict. Unknown fields are rejected rather than ignored so a newer producer cannot accidentally send meaning that an older adapter silently drops.

## Declared relevance is not active context

The snapshot contains an `activity` reference. That is the producer's **declared relevance**: what the snapshot says its candidate relates to.

It is not allowed to certify that this activity is actually current.

The caller must separately supply one or more active runtime references to `process_alternative_snapshot(..., active_refs=...)`. The normal communication gate compares the snapshot's declared relevance against those independently supplied references.

Therefore this must be possible:

```text
snapshot says: activity:A
runtime says:  activity:B
              ↓
REJECT: not_relevant_to_active_context
```

This separation is intentional. A speaker should not become relevant merely by claiming relevance.

## Required top-level fields

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

Every reference object is exactly:

```json
{"kind": "...", "id": "..."}
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

`cost` has no universal meaning. `cost_metric` names the metric under which all option costs in this snapshot are being compared.

## Outcomes

The adapter returns one of three states:

- `emitted` — a candidate survived the producer and communication gate and has a canonical StateTalk packet;
- `no_candidate` — the supplied state contained no strictly lower-cost alternative preserving every required constraint; silence is normal;
- `rejected` — a candidate existed but the communication gate refused to emit it, for example because its declared activity is not active or its semantic fingerprint was already seen.

Malformed or semantically ambiguous input raises an error instead of being converted into communication.

## Local monolith proof

Run the bundled snapshot through the same offline renderer used by the monolith proof. The active reference is passed separately from the snapshot:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/alternative_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Then open:

```text
local/monolith_proof.generated.html
```

The generated page labels snapshot provenance as externally supplied and **not verified by the renderer**. Rendering proves that the handoff path worked; it does not prove the external source was truthful.

For a real monolith integration, `--active-ref` is only a test-harness stand-in. The runtime should supply its actual active state/context directly when calling the adapter.

## Truth boundary

The adapter does not infer missing evidence, hidden constraints, metric meaning, source authenticity, or active relevance.

A future snapshot format that needs more meaning must use an explicit schema revision. Do not add fields and expect older readers to ignore them.
