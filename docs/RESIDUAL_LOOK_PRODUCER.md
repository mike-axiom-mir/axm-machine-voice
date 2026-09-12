# Residual Look Producer v0.1

Machine Voice can surface one narrow expected-vs-observed numeric residual without inventing an explanation.

Human FloorVoice rendering:

```text
Look here.
```

Producer id:

```text
residual-look/0.1
```

## What it means

Each supplied check explicitly names:

```text
check reference
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

A check qualifies only when:

```text
abs(observed - expected) > tolerance
```

Exactly at tolerance remains silent.

If several checks exceed tolerance, v0.1 includes all of them in deterministic `Ref.key` order.

## Canonical claim boundary

A surfaced packet records the supplied values, computed absolute residual, supplied tolerance, and excess over tolerance.

It also explicitly records:

```json
{
  "cause": null,
  "cause_claimed": false,
  "novelty_claimed": false,
  "model_invalidity_claimed": false,
  "observation_invalidity_claimed": false
}
```

So `Look here.` does **not** mean:

- a new phenomenon was discovered;
- the prediction model is wrong;
- the observation is wrong;
- the residual has a known cause;
- the residual is scientifically anomalous;
- the supplied tolerance is globally correct.

It means only that the supplied observation differs from the supplied expectation by more than the supplied tolerance under the supplied metric.

## Evidence

Every check requires three grounded evidence sets:

- evidence for the expectation;
- evidence for the observation;
- evidence for the supplied tolerance/threshold.

Missing evidence is invalid input, not a weak `Look here.` event.

## Continuity

Only checks that exceed tolerance enter the semantic packet. Adding unrelated checks that remain inside tolerance therefore does not create repeat speech.

Check order and evidence-reference order are normalized deterministically. Numeric inputs are normalized to finite floats so `1` and `1.0` do not create different semantic communication.

## Proposal Map

Each exceeded check maps to its subject, property, metric, and three evidence classes:

```text
check ── about_subject ───────────> subject
check ── checks_property ─────────> property
check ── measured_by ─────────────> metric
check ── expected_supported_by ───> evidence
check ── observed_supported_by ───> evidence
check ── tolerance_supported_by ──> evidence
```

## Truth boundary

The producer establishes only:

> Under the supplied metric, the supplied observed numeric value differs from the supplied expected numeric value by more than the supplied non-negative tolerance.

It does not interpret the cause or meaning of that residual.

## Runnable producer example

```bash
python examples/run_residual_producer.py
```

This writes:

```text
examples/residual_packet.generated.json
```

## Versioned snapshot handoff

The producer also accepts strict state through:

```text
axm-machine-voice/residual-snapshot/0.1
```

Example:

```text
examples/residual_snapshot.example.json
```

The same generic machine command handles it:

```bash
python machine_voice.py snapshot examples/residual_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

The same communication journal can suppress repeated residual semantics, and the same offline monolith proof can render the resulting `Look here.` packet.

The snapshot remains strict: unknown fields fail closed, active relevance is supplied independently by the runtime, and the transport does not upgrade a residual into an explanation.

All bundled residual examples use synthetic state. They are not live Machine Floor observations or scientific discoveries.
