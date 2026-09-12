# AXM Machine Voice

A state-native communication experiment for the AXM Machine Floor.

> When grounded machine-state structure contains something relevant to collaborative work, can the Machine Floor surface it without pretending to be human, conscious, or language-native?

This repository does **not** assume the Machine Floor has opinions, intentions, sentience, or general reasoning. It creates deterministic paths by which grounded state relationships can become visible to collaborators.

## Constitutional merge gate

Internal AXM work is not gated by Mike/founder authority. Changes must survive the four AXM roots:

1. **Truth** — claims must not outrun evidence.
2. **Agency / non-domination** — communication may inform collaboration, never seize authority or manipulate participants.
3. **Continuity** — preserve provenance, compatible meaning, history, and rollback.
4. **Wisdom before speed** — prefer inspectable, reversible learning over premature capability claims.

No speaker receives automatic authority because it is human, AI, or machine.

## Core path

```text
STATE / EVIDENCE
      ↓
DETERMINISTIC PRODUCER
      ↓
COMMUNICATION CANDIDATE
      ↓
COMMUNICATION GATE
      ↓
STATETALK PACKET
    ↙          ↘
machine JSON   FloorVoice
    \          /
  communication journal
```

A state change is not automatically communication. A diagnostic log is not automatically the Machine Floor "speaking".

The implementation is standard-library-only and keeps the human vocabulary fixed while richer machine structure stays inspectable underneath.

Run all tests with:

```bash
python -m unittest discover -s tests -v
```

## Nine grounded reasons to speak

### `There is another way.`

`produce_lower_cost_alternative(...)` can surface an alternative only when supplied evidence proves a strictly lower supplied cost under one explicit metric while preserving every required constraint.

It does not infer hidden constraints, preferences, metric meaning, or correctness.

```bash
python examples/run_deterministic_producer.py
```

### `These do not fit.`

`produce_exact_conflict(...)` can surface a conflict only when grounded assertions share exactly the same scope, subject, and property but carry different explicit portable values.

It preserves both evidence sets and stores:

```json
{"winner": null}
```

It does not decide which assertion is true.

```bash
python examples/run_conflict_producer.py
```

See [`docs/CONFLICT_PRODUCER.md`](docs/CONFLICT_PRODUCER.md).

### `I cannot resolve this.`

`produce_bounded_unresolved(...)` can surface only when an explicit named search contains at least one grounded attempt and **every supplied attempt** misses at least one explicit required constraint.

Zero attempts stays silent. If one attempt preserves every required constraint, it stays silent.

Its canonical claim explicitly records:

```json
{"global_impossibility_claimed": false}
```

So this phrase never means “no solution exists.” It means the supplied bounded search did not contain a fully constraint-preserving resolution.

```bash
python examples/run_unresolved_producer.py
```

See [`docs/UNRESOLVED_PRODUCER.md`](docs/UNRESOLVED_PRODUCER.md).

### `I need something.`

`produce_bounded_need(...)` can surface only when a task explicitly names required inputs and one or more are absent from a named supplied inventory scope.

If every required input is present, it stays silent. It never invents hidden requirements.

Its canonical claim records:

```json
{
  "bounded_inventory_only": true,
  "global_unavailability_claimed": false
}
```

So the phrase means only that the supplied bounded inventory is missing an explicit required input—not that the input is unavailable elsewhere.

```bash
python examples/run_need_producer.py
```

See [`docs/NEED_PRODUCER.md`](docs/NEED_PRODUCER.md).

### `Look here.`

`produce_residual_look(...)` can surface only when an explicitly supplied observed numeric value differs from an explicitly supplied expected numeric value by **more than** an explicitly supplied non-negative tolerance under an explicitly named metric.

Each check carries separate evidence for the expectation, observation, and tolerance.

A surfaced claim explicitly refuses to infer an explanation:

```json
{
  "cause": null,
  "cause_claimed": false,
  "novelty_claimed": false,
  "model_invalidity_claimed": false,
  "observation_invalidity_claimed": false
}
```

Exactly at tolerance stays silent. Adding unrelated checks that remain inside tolerance does not create new speech.

```bash
python examples/run_residual_producer.py
```

See [`docs/RESIDUAL_LOOK_PRODUCER.md`](docs/RESIDUAL_LOOK_PRODUCER.md).

### `This worked.` / `This did not work.`

`produce_criterion_outcome(...)` is one paired producer so success and failure cannot drift onto different definitions.

v0.1 uses one explicit aggregation rule:

```text
all_required
```

`This worked.` can surface only when every explicitly required success criterion has a grounded satisfied observation.

`This did not work.` can surface when at least one explicitly required criterion has a grounded failed observation. Other criteria may still be unevaluated because one required failure is already enough to violate an all-required contract.

Partial positive evidence stays silent rather than becoming premature success.

Both outcomes are explicitly bounded to the supplied contract:

```json
{
  "global_success_claimed": false,
  "global_failure_claimed": false,
  "criteria_contract_authenticity_claimed": false,
  "criteria_contract_preexistence_authenticated": false
}
```

The exact packet contains only the fields relevant to its outcome; the two global flags are shown together here only to summarize the shared boundary.

```bash
python examples/run_outcome_producer.py
```

See [`docs/OUTCOME_PRODUCER.md`](docs/OUTCOME_PRODUCER.md).

Both outcome states also use the strict shared snapshot transport. The transport carries an explicit attempt, criteria contract, required criteria, grounded observations, and evidence; it does not authenticate who authored the contract or whether it truly existed before the attempt.

### `This happened before.` / `This is new.`

`produce_history_classification(...)` is one paired producer so recurrence and novelty share the same exact pattern definition and explicit comparison domain.

A grounded exact prior match can surface `This happened before.` even when the supplied history is incomplete.

`This is new.` has a stronger burden: no exact match **and** an explicit `complete_for_domain = true` history scope. No match in incomplete history stays silent.

Bounded novelty explicitly records:

```json
{
  "history_scope_complete_for_domain_claimed": true,
  "history_scope_completeness_authenticated": false,
  "history_ordering_authenticated": false,
  "global_novelty_claimed": false,
  "scientific_novelty_claimed": false,
  "outside_scope_novelty_claimed": false
}
```

So `This is new.` means only that no exact equivalent exists in the supplied history scope that is explicitly claimed complete for that pattern domain. It does not mean the pattern is globally or scientifically novel.

```bash
python examples/run_history_producer.py
```

See [`docs/HISTORY_PRODUCER.md`](docs/HISTORY_PRODUCER.md).

Both history states now also use the strict shared snapshot transport. The same `history-snapshot/0.1` schema carries current pattern, bounded history scope, historical entries, and evidence; transport cannot authenticate completeness or chronological ordering.

All bundled producer examples use synthetic state and are not live Machine Floor discoveries.

## Versioned state snapshot handoff

All seven deterministic producers use one strict schema-id-routed snapshot transport:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
axm-machine-voice/unresolved-snapshot/0.1
axm-machine-voice/need-snapshot/0.1
axm-machine-voice/residual-snapshot/0.1
axm-machine-voice/outcome-snapshot/0.1
axm-machine-voice/history-snapshot/0.1
```

Examples:

```text
examples/alternative_snapshot.example.json
examples/conflict_snapshot.example.json
examples/unresolved_snapshot.example.json
examples/need_snapshot.example.json
examples/residual_snapshot.example.json
examples/outcome_snapshot.example.json
examples/outcome_failure_snapshot.example.json
examples/history_snapshot.example.json
examples/history_novel_snapshot.example.json
```

The caller supplies active runtime context separately. A snapshot cannot certify its own relevance.

Unknown schema ids or unknown fields fail closed rather than being guessed or silently dropped.

History support is additive: the package/CLI use a thin history-aware wrapper, while the prior six schemas still delegate unchanged to the earlier proven router.

See [`docs/STATE_SNAPSHOT.md`](docs/STATE_SNAPSHOT.md) and the portable schemas under [`schemas/`](schemas/).

## Machine channel

One zero-install command accepts every supported snapshot schema:

```bash
python machine_voice.py snapshot examples/history_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Protocol:

```text
axm-machine-voice/machine-channel/0.1
```

The response is one canonical JSON envelope with no explanatory prose mixed into stdout.

Valid snapshot outcomes are `emitted`, `no_candidate`, and `rejected`. Structured journal responses return `recorded`. Invalid input returns `invalid` with exit code `2` while preserving the same versioned envelope.

See [`docs/MACHINE_CHANNEL.md`](docs/MACHINE_CHANNEL.md).

## Communication journal

Only communication that actually passed the gate becomes speech history.

The journal supplies prior semantic fingerprints so repeated grounded state does not keep lighting the same message. `no_candidate`, rejected candidates, and invalid input do **not** become speech history.

The journal is hash-linked for local integrity checking, not cryptographic proof against a writer who can rewrite and re-hash the whole file. Actor references are structured claims, not authenticated identities.

The history producer does not assume this journal is the only valid history provider. Other bounded evidence-backed history stores may feed the same history contract.

See [`docs/COMMUNICATION_JOURNAL.md`](docs/COMMUNICATION_JOURNAL.md).

## Offline human surface

Open `index.html` or `local/index.html`. It requires no AI, network, account, cloud service, package install, or build step.

The human-facing vocabulary remains deliberately primitive:

- `I noticed something.`
- `These do not fit.`
- `There is another way.`
- `I cannot resolve this.`
- `I need something.`
- `This happened before.`
- `This is new.`
- `This worked.`
- `This did not work.`
- `Look here.`

These phrases are pointers to canonical StateTalk packets. They are not generated personality.

When embedded by a parent monolith/runtime, the page can send bounded `Inspect`, `Compare`, and `Acknowledge` response intents. The child never invents actor identity or claims persistence without parent confirmation.

See [`docs/LOCAL_MONOLITH_TEST.md`](docs/LOCAL_MONOLITH_TEST.md).

## AXM Assembly / monolith contract

`AXM_MODULE.json` declares Machine Voice natively so `axm-monolith` does not have to guess from the repository name.

Declared capabilities include StateTalk, the strict state-snapshot adapter, deterministic producers, FloorVoice, the communication journal, and the machine JSON interface.

Native declaration is stronger than heuristic discovery but is still **not** cross-module runtime verification.

## Absolute truth boundary

**FloorVoice may simplify a StateTalk packet, but it may never invent meaning absent from that packet.**

Machine Voice does not currently claim:

- consciousness, preference, human-like intent, or general reasoning;
- autonomous arbitrary idea discovery;
- natural-language understanding as its machine-native protocol;
- which side of a surfaced conflict is true;
- global impossibility from a bounded unresolved search;
- global unavailability from a bounded missing-input inventory;
- cause or novelty merely because an expected-vs-observed residual exceeds a supplied tolerance;
- model invalidity or observation invalidity merely because a residual exceeds tolerance;
- global success or global failure from evaluation against one explicit criteria contract;
- authenticity, authorship, or pre-attempt timing of a supplied success criteria contract;
- global or scientific novelty from absence in one supplied history scope;
- authenticated completeness or chronological ordering of a supplied history scope;
- that a surfaced alternative is correct or canonical;
- truth of externally supplied evidence merely because it renders;
- actor authentication by the local page;
- cryptographic authenticity of the local journal;
- cross-module interoperability before exact composition testing;
- that bundled demos or synthetic examples are live discoveries.

The next real integration milestone remains replacing synthetic snapshot inputs with actual monolith/Machine Floor state while preserving the same strict path.

The aim remains simple: **give grounded machine structure a truthful way to point.**
