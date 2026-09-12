# Exact Conflict Producer v0.1

Machine Voice can now surface one narrow grounded conflict without deciding which side is correct.

Human FloorVoice rendering:

```text
These do not fit.
```

Producer id:

```text
exact-conflict/0.1
```

## What counts as a conflict

Two explicit assertions must share exactly the same:

```text
scope
subject
property
```

and carry different portable JSON-like values.

Example:

```text
scope:    current-run
subject:  door-7
property: open

assertion A: true   + evidence A
assertion B: false  + evidence B
```

That can surface a conflict.

These do **not** count as the same comparison target:

```text
different scope
or
different subject
or
different property
```

The producer does not infer that differently named references secretly mean the same thing.

## Evidence requirement

Every assertion must carry at least one evidence reference.

Missing evidence is invalid input, not a weak conflict and not normal silence.

## Value boundary

Assertion values must be portable JSON-like data:

```text
null
boolean
finite number
string
array
object with string keys
```

Python-only objects and non-finite numbers fail closed.

JSON numeric spellings that represent the same number, such as `1` and `1.0`, do not create a fake conflict. Booleans remain type-distinct from numbers, so `true` and `1` are different explicit values.

## Multiple conflicts

If supplied state contains several grounded conflicts, v0.1 chooses one deterministically by:

1. scope / subject / property reference keys;
2. assertion reference keys.

That is a selection rule for communication stability, not a ranking of importance.

## Proposal Map

A surfaced conflict maps:

```text
assertion A ── conflicts_with ──> assertion B
     │                              │
     ├─ in_scope ───────────────> scope
     ├─ about_subject ──────────> subject
     ├─ asserts_property ───────> property
     └─ supported_by ───────────> evidence
```

The claim stores both explicit values and:

```json
{"winner": null}
```

That is intentional.

## Truth boundary

The producer establishes only:

> Under the supplied state representation, two grounded assertions make incompatible explicit claims about the same exact scope, subject, and property.

It does **not** establish:

- which assertion is true;
- whether either evidence source is trustworthy in the external world;
- whether the contradiction is caused by sensor error, timing, bad state modelling, deception, or an unknown phenomenon;
- whether differently named references should really be considered equivalent;
- what action should resolve the disagreement.

Those questions belong to later inspection/comparison, not to the act of noticing the conflict.

## Runnable example

```bash
python examples/run_conflict_producer.py
```

This writes:

```text
examples/conflict_packet.generated.json
```

The example uses synthetic assertions and is not a live Machine Floor discovery. The resulting packet can be opened in the offline `local/index.html` renderer.
