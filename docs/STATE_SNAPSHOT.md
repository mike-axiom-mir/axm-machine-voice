# State Snapshot Handoff v0.1

Machine Voice can now receive producer input as a versioned JSON state snapshot instead of requiring Python code changes.

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
communication gate
        ↓
StateTalk packet or silence
```

The adapter is intentionally strict. Unknown fields are rejected rather than ignored so a newer producer cannot accidentally send meaning that an older adapter silently drops.

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
- `rejected` — a candidate existed but the communication gate refused to emit it, for example because its semantic fingerprint was already seen.

Malformed or semantically ambiguous input raises an error instead of being converted into communication.

## Local monolith proof

Run the bundled snapshot through the same offline renderer used by the monolith proof:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/alternative_snapshot.example.json
```

Then open:

```text
local/monolith_proof.generated.html
```

The generated page labels snapshot provenance as externally supplied and **not verified by the renderer**. Rendering proves that the handoff path worked; it does not prove the external source was truthful.

## Truth boundary

The adapter does not infer missing evidence, hidden constraints, metric meaning, or source authenticity.

A future snapshot format that needs more meaning must use an explicit schema revision. Do not add fields and expect older readers to ignore them.
