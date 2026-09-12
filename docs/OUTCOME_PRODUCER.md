# Criterion Outcome Producer v0.1

Machine Voice can surface two paired outcome phrases from one explicit success contract:

```text
This worked.
This did not work.
```

Producer id:

```text
criterion-outcome/0.1
```

## Why one paired producer

Success and failure must be evaluated against the **same criteria contract**. Splitting them into unrelated producers would allow the meaning of "worked" and "did not work" to drift apart.

v0.1 therefore supports exactly one aggregation rule:

```text
all_required
```

Every required criterion must be satisfied for success. One grounded failed required criterion is enough to establish failure relative to that contract.

## Inputs

The producer receives:

```text
attempt
attempt evidence
criteria contract
one or more required criterion references
criteria-contract evidence
zero or more criterion observations
active/relevance reference
next operations
```

Each `CriterionObservation` contains:

```text
criterion
observation reference
satisfied = true | false
observation evidence
```

A supplied observation may evaluate only a criterion declared in the contract. Each criterion may be evaluated at most once in one producer call.

## Success

`This worked.` can surface only when **every explicitly required criterion** has one grounded observation with:

```text
satisfied = true
```

Partial positive evidence stays silent.

The success packet explicitly records:

```json
{
  "aggregation_rule": "all_required",
  "global_success_claimed": false,
  "criteria_contract_authenticity_claimed": false,
  "criteria_contract_preexistence_authenticated": false
}
```

So success means:

> The supplied attempt satisfies every criterion in the supplied all-required success contract.

It does not mean the attempt was universally good, had no side effects, satisfied hidden goals, or succeeded under every possible definition.

## Failure

`This did not work.` can surface when **at least one explicitly required criterion** has a grounded observation with:

```text
satisfied = false
```

The other criteria do not need to be fully evaluated for this bounded failure claim because one required failure is enough to violate an all-required contract.

The failure packet explicitly records:

```json
{
  "aggregation_rule": "all_required",
  "global_failure_claimed": false,
  "all_other_criteria_required_for_failure_claim": false,
  "criteria_contract_authenticity_claimed": false,
  "criteria_contract_preexistence_authenticated": false
}
```

So failure means:

> The supplied attempt failed at least one required criterion in the supplied all-required success contract.

It does not mean the attempt was worthless, universally failed, produced no useful result, or should not be retried.

## Incomplete evidence

If observations are all positive but one or more required criteria are still unevaluated, the producer returns normal silence.

```text
some criteria true + others unknown
              ↓
          no candidate
```

A grounded false criterion is different:

```text
one required criterion false
              ↓
           failure
```

because that is already enough to violate the all-required contract.

## Contract timing and authenticity

The architecture is intended for success criteria to be declared before outcome evaluation. However, v0.1 does **not** independently authenticate:

- who authored the criteria contract;
- whether the contract was modified later;
- whether it truly existed before the attempt;
- whether its criteria were appropriate.

The producer treats the supplied contract and its evidence as the bounded evaluation basis. Stronger provenance/timing guarantees require an external signed or checkpointed layer.

## Continuity

For success, all required grounded observations enter the semantic packet.

For failure, only the grounded failed observations enter the failure-specific semantic claim. Later discovering that other criteria passed therefore does not create a new failure fingerprint for the same failed criteria.

Criterion order, evidence order, and input order are normalized deterministically.

## Proposal Map

The packet keeps the relationship structure inspectable:

```text
attempt ── evaluated_against ─────────> criteria contract
criteria contract ── requires_success_criterion ──> criterion
attempt ── supported_by ──────────────> evidence
criteria contract ── supported_by ────> evidence
observation ── outcome_for_attempt ───> attempt
observation ── satisfies_criterion ───> criterion
observation ── fails_criterion ───────> criterion
observation ── supported_by ──────────> evidence
```

## Runnable producer example

```bash
python examples/run_outcome_producer.py
```

The bundled producer example uses synthetic state and writes both a success and failure packet. It is not a live Machine Floor result.

## Strict snapshot transport

Protocol:

```text
axm-machine-voice/outcome-snapshot/0.1
```

Success and failure use the **same** snapshot schema. Complete examples:

```text
examples/outcome_snapshot.example.json
examples/outcome_failure_snapshot.example.json
```

The snapshot carries the explicit attempt, attempt evidence, criteria contract, required criteria, criteria evidence, grounded observations, and next operations. It does **not** contain a configurable aggregation rule; `all_required` remains fixed by the producer.

Machine channel:

```bash
python machine_voice.py snapshot examples/outcome_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Offline renderer proof:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/outcome_failure_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

The transport changes no truth boundary. It does not authenticate contract authorship, contract timing, evidence truth, or active relevance. Active relevance remains independently supplied by the runtime.
