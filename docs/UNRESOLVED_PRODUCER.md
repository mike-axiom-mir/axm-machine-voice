# Bounded Unresolved Producer v0.1

Machine Voice can surface one narrow bounded failure-to-resolve condition without claiming that no solution exists.

Human FloorVoice rendering:

```text
I cannot resolve this.
```

Producer id:

```text
bounded-unresolved/0.1
```

## What it means

The producer requires:

```text
problem
explicit search scope
one or more required constraints
one or more grounded attempts
```

It can speak only when **every supplied grounded attempt misses at least one required constraint**.

Example:

```text
required:
- offline-only
- output-preserved

attempt A preserves:
- offline-only

attempt B preserves:
- output-preserved

result:
I cannot resolve this.
```

The canonical claim records the named search scope and:

```json
{"global_impossibility_claimed": false}
```

## When it stays silent

Zero attempts:

```text
silence
```

The machine has not tried enough to claim bounded failure.

At least one attempt preserves every required constraint:

```text
silence
```

The bounded search contains a resolution, so this producer has nothing truthful to say.

## Evidence requirement

Every attempt must carry at least one evidence reference. Missing evidence is invalid input rather than an unresolved result.

Attempts and required constraints must use unique references. This prevents ambiguous rows and keeps semantic fingerprints stable.

## Deterministic continuity

The producer sorts:

- required constraint references;
- attempt references;
- evidence references used in the canonical packet.

Reordering semantically identical supplied state therefore does not create a new communication fingerprint.

## Proposal Map

Each attempt maps to:

```text
attempt ── attempted_for ───────> problem
attempt ── within_search_scope ─> search scope
attempt ── preserves_required ──> preserved required constraint
attempt ── missing_required ────> missing required constraint
attempt ── supported_by ────────> evidence
```

`missing_required` means only that the supplied attempt did not explicitly preserve that required constraint. It is not a claim that the attempt actively violated it.

## Truth boundary

The producer establishes only:

> Inside the explicitly named search scope, every supplied grounded attempt is missing at least one explicit required constraint.

It does **not** establish:

- that no solution exists;
- that the search scope was exhaustive;
- that more attempts would fail;
- that the required constraints are globally correct;
- that external evidence is trustworthy merely because it is referenced;
- why the attempts failed;
- what should be tried next.

Those questions belong to later inspection, comparison, broader search, or another capability.

## Runnable example

```bash
python examples/run_unresolved_producer.py
```

This writes:

```text
examples/unresolved_packet.generated.json
```

The example uses synthetic attempts and is not a live Machine Floor discovery. The resulting packet can be opened in the offline `local/index.html` renderer.
