# Grounded Notice Producer v0.1

Machine Voice reserves the generic FloorVoice phrase:

```text
I noticed something.
```

for one narrow case: an explicitly named deterministic notice rule fired on an explicitly referenced observation, with evidence.

Producer id:

```text
grounded-notice/0.1
```

## Why this phrase is different

The other Machine Voice phrases carry specific semantics such as conflict, bounded need, residual, success/failure, repeat, or bounded novelty.

`I noticed something.` must not become a vague fallback for intuition, importance, surprise, anomaly, or unexplained machine preference.

v0.1 therefore acts as a generic **grounded detector handoff**, not a generic reasoning engine.

## Inputs

One `NoticeSignal` contains:

```text
observation ref
notice-rule ref
one or more subject refs
triggered = true | false
observation evidence ref
rule-definition evidence ref
trigger evidence ref
```

The producer also receives source, active/relevance reference, event id, and next operations.

## Emission rule

```text
triggered = false
      ↓
   silence

triggered = true
+ explicit observation
+ explicit rule
+ explicit evidence refs
      ↓
I noticed something.
```

The producer does not decide whether the upstream rule is a good rule. It preserves the rule and evidence so collaborators can inspect them.

## Absolute interpretation boundary

A notice packet explicitly records:

```json
{
  "triggered": true,
  "cause": null,
  "cause_claimed": false,
  "importance_claimed": false,
  "anomaly_claimed": false,
  "novelty_claimed": false,
  "success_claimed": false,
  "failure_claimed": false,
  "recommendation_claimed": false,
  "interpretation_claimed": false
}
```

So `I noticed something.` means only:

> The supplied deterministic notice rule is explicitly represented as having fired on the supplied observation, with supplied evidence.

It does **not** mean:

- this is important;
- this is anomalous;
- this is novel;
- this is a failure or success;
- a cause is known;
- an action is recommended;
- the Machine Floor has an intuition, feeling, preference, or unexplained concern.

## Prefer specific producers

When grounded state satisfies a narrower Machine Voice producer, that producer should be preferred over generic notice. Examples:

```text
explicit conflict      → These do not fit.
explicit residual      → Look here.
explicit missing input → I need something.
explicit recurrence    → This happened before.
```

v0.1 cannot independently prove that an upstream caller chose the most specific available producer. It records:

```text
specific_kind_preferred = true
```

as architecture guidance, not as an authenticated claim about the caller.

## Evidence and continuity

The notice packet preserves three explicit evidence references:

- observation evidence;
- rule-definition evidence;
- trigger-result evidence.

Subject order is normalized so reordering the same subjects does not create a new semantic fingerprint.

## Runnable producer example

```bash
python examples/run_notice_producer.py
```

The bundled example uses synthetic state. It is not a live Machine Floor observation.

## Strict snapshot transport

Protocol:

```text
axm-machine-voice/notice-snapshot/0.1
```

Complete example:

```text
examples/notice_snapshot.example.json
```

The snapshot carries only the explicit notice signal fields plus source, activity, event id, and next operations. It has no field for importance, anomaly, novelty, cause, success, failure, recommendation, or free-form interpretation. Unknown fields fail closed.

Machine channel:

```bash
python machine_voice.py snapshot examples/notice_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Offline renderer proof:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/notice_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

The transport changes no truth boundary:

```text
triggered = false → no_candidate silence
triggered = true  → grounded NOTICE candidate → gate
```

The snapshot cannot certify its own active relevance and cannot add interpretation absent from the producer packet.
