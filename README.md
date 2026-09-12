# AXM Machine Voice

A state-native communication experiment for the AXM Machine Floor.

## Question

> When grounded machine-state structure contains something relevant to collaborative work, can the Machine Floor surface it without pretending to be human, conscious, or language-native?

This repository does **not** assume the Machine Floor has opinions, intentions, sentience, or general reasoning. It builds a deterministic path by which real state relationships, conflicts, alternatives, unresolved conditions, results, or proposals can become visible to collaborators.

## Constitutional merge gate

Internal AXM work is not gated by Mike/founder authority. Changes must survive the four AXM roots:

1. **Truth** — claims must not outrun evidence.
2. **Agency / non-domination** — communication may inform collaboration, never seize authority or manipulate participants.
3. **Continuity** — preserve provenance, compatible meaning, history, and rollback.
4. **Wisdom before speed** — prefer inspectable, reversible learning over premature capability claims.

No speaker receives automatic authority because it is human, AI, or machine.

## Core distinction

```text
STATE ACTIVITY
    |  everything that happens
    v
TELEMETRY / EVIDENCE
    |  what is recorded or can ground a claim
    v
DISCOVERY CANDIDATE
    |  produced by a real capability
    v
COMMUNICATION GATE
    |  deterministic eligibility rules
    v
STATETALK PACKET
    |---------------------------|
    v                           v
machine / AI channel        FloorVoice
full structure              tiny fixed phrase
    |                           |
    +-------------+-------------+
                  v
       Proposal Map + evidence
```

A state change is not automatically communication. A diagnostic log is not automatically the Machine Floor "speaking".

## v0.1 core

The working slice remains deliberately small and standard-library-only:

- open typed references so future capabilities can point to objects we did not anticipate;
- structured claims and Proposal Maps;
- deterministic communication producers and gate;
- semantic duplicate detection;
- canonical StateTalk packets;
- a fixed ten-phrase FloorVoice layer;
- append-only communication history;
- strict versioned machine snapshot handoff;
- tests for truth-boundary failures.

The implementation lives in [`src/axm_machine_voice`](src/axm_machine_voice), and the protocol is documented in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Deterministic producers

Machine Voice currently has three real narrow reasons to speak.

### Lower-cost alternative

`src/axm_machine_voice/producer.py` implements a lower-cost alternative detector over explicitly supplied state.

It can surface:

```text
There is another way.
```

only when supplied evidence proves that a candidate option:

- has strictly lower supplied cost than the current option under one explicitly named metric;
- explicitly preserves every required constraint;
- carries inspectable evidence.

The metric itself is a state reference, so the packet can show what the compared numbers mean instead of silently assuming that two numeric values are comparable.

The producer does not infer hidden constraints, invent preferences, generate prose, or declare the alternative correct.

Runnable example:

```bash
python examples/run_deterministic_producer.py
```

### Exact conflict

`src/axm_machine_voice/conflict.py` implements an exact grounded contradiction detector.

It can surface:

```text
These do not fit.
```

only when two grounded assertions share exactly the same:

```text
scope
subject
property
```

but carry different portable values.

It preserves both evidence sets and explicitly stores:

```json
{"winner": null}
```

Different scope, subject, or property stays silent. The producer does not decide which assertion is true, why they disagree, or how to repair the conflict.

Runnable example:

```bash
python examples/run_conflict_producer.py
```

See [`docs/CONFLICT_PRODUCER.md`](docs/CONFLICT_PRODUCER.md).

### Bounded unresolved search

`src/axm_machine_voice/unresolved.py` implements a bounded failure-to-resolve detector.

It can surface:

```text
I cannot resolve this.
```

only when:

- an explicit problem and search scope are named;
- at least one grounded attempt was supplied;
- one or more required constraints are explicit;
- **every supplied attempt** misses at least one required constraint.

Zero attempts stays silent. If even one attempt preserves every required constraint, it stays silent.

The canonical claim explicitly records:

```json
{"global_impossibility_claimed": false}
```

So the phrase never means “no solution exists.” It means the supplied bounded search did not contain a fully constraint-preserving resolution.

Runnable example:

```bash
python examples/run_unresolved_producer.py
```

See [`docs/UNRESOLVED_PRODUCER.md`](docs/UNRESOLVED_PRODUCER.md).

All producer examples use synthetic state and are not live Machine Floor discoveries. Their resulting packets can be opened in the same offline `local/index.html` renderer.

## Offline local test surface

The repository includes a zero-dependency local test page:

```text
local/index.html
```

Open it directly in a browser. It requires no AI, network, account, cloud service, package install, server, or build step.

The page starts with an explicitly labeled bundled **demo** packet. The demo proves the rendering path only; it is not presented as a live Machine Floor discovery. A local JSON StateTalk packet can also be opened through the page and inspected as:

- fixed FloorVoice phrase;
- source and event identity;
- subjects and evidence references;
- claim predicate and next operations;
- Proposal Map relations and status;
- complete raw packet.

The integration manifest is [`local/manifest.json`](local/manifest.json). The monolith bridge contract is documented in [`docs/LOCAL_MONOLITH_TEST.md`](docs/LOCAL_MONOLITH_TEST.md).

A monolith shell can embed the page and send canonical packets through the small `postMessage` bridge identified by:

```text
axm-machine-voice/local-bridge/0.1
```

The renderer remains downstream of the core truth boundary: **rendering a packet does not prove its claim, adopt its proposal, or make it canonical.**

### One-command monolith proof

To exercise the default complete path without a server:

```bash
python examples/build_local_monolith_proof.py
```

Then open:

```text
local/monolith_proof.generated.html
```

The generated parent page embeds `local/index.html`, waits for the renderer's real `ready` bridge event, sends the packet produced by the deterministic producer and communication gate, and confirms the rendered event. It contains no network dependency.

The default input is still **synthetic test state** and the generated page says so explicitly. This proves the integration path, not autonomous discovery or live Machine Floor provenance.

### Versioned state snapshot handoff

Machine Voice accepts strict versioned snapshots instead of requiring callers to edit Python.

Currently supported through the generic router:

```text
axm-machine-voice/alternative-snapshot/0.1
axm-machine-voice/conflict-snapshot/0.1
```

Examples:

```text
examples/alternative_snapshot.example.json
examples/conflict_snapshot.example.json
```

The bounded unresolved producer is currently available through the Python API/runnable example; its strict snapshot handoff is the next transport extension rather than being falsely claimed here.

The same proof command accepts either supported snapshot because routing is based on the explicit schema id:

```bash
python examples/build_local_monolith_proof.py \
  --snapshot examples/conflict_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Every snapshot's `activity` says what the producer believes its finding relates to. It does **not** certify that activity as current. The communication gate compares that declaration with independently supplied active runtime references; a mismatch is rejected as `not_relevant_to_active_context`.

Adapters reject unknown fields rather than silently discarding meaning. `no_candidate` is normal silence; a packet is produced only when the selected producer finds something it is explicitly allowed to say and the communication gate accepts it.

The snapshot contracts and truth boundaries are documented in [`docs/STATE_SNAPSHOT.md`](docs/STATE_SNAPSHOT.md).

This is the intended handoff for the next monolith test: the monolith can supply a supported snapshot and its actual active context without changing Machine Voice code.

## Machine channel v0.1

The human FloorVoice page is not required for machine-to-machine use. A zero-install command channel emits one versioned canonical JSON envelope and no explanatory prose:

```bash
python machine_voice.py snapshot examples/conflict_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

Protocol:

```text
axm-machine-voice/machine-channel/0.1
```

The same `snapshot` command accepts every explicitly supported snapshot schema. Snapshots may also arrive over stdin, and repeated `--seen-fingerprint` values let the normal communication gate suppress already-emitted semantics.

Valid snapshot outcomes (`emitted`, `no_candidate`, `rejected`) use exit code `0`. Structured journal responses return `recorded`. Invalid input uses exit code `2` but still returns the same versioned JSON envelope. Even normal command-syntax failures are converted to machine-readable `invalid` output rather than human argparse prose.

This channel adds no reasoning and no new authority. It transports the same strict snapshot → exact producer → gate result used by the local human surface.

See [`docs/MACHINE_CHANNEL.md`](docs/MACHINE_CHANNEL.md) for the contract.

## Communication journal v0.1

Machine Voice can preserve only the communications that actually passed the gate in a local append-only journal:

```bash
python machine_voice.py snapshot examples/conflict_snapshot.example.json \
  --active-ref activity:local-monolith-proof \
  --journal local/communication.jsonl
```

Run the same state again with the same journal and the previous semantic fingerprint is automatically inherited. The repeat is rejected as `duplicate_semantic_event`, so the Floor does not keep lighting the same message.

The journal is **not telemetry**. `no_candidate`, rejected candidates, and invalid input do not become speech history.

A human, AI, game, or machine can attach a structured response only to an event that really emitted:

```bash
python machine_voice.py respond local/communication.jsonl \
  --event-id conflict-snapshot-example-001 \
  --actor human:local-user \
  --action inspect \
  --target assertion:sensor-a
```

Journal records are hash-linked. The chain catches accidental/un-rehashed edits and ordering damage, but it is **not** cryptographic proof against a writer who can rewrite the file and recompute hashes, and it cannot prove an intact tail was never deleted. Stronger claims require an external checkpoint/signature layer.

Response actor references are structured claims supplied by the caller; v0.1 does not authenticate them.

v0.1 assumes one journal writer at a time.

See [`docs/COMMUNICATION_JOURNAL.md`](docs/COMMUNICATION_JOURNAL.md) for the full contract.

## FloorVoice v0.1

The human-facing vocabulary is intentionally primitive:

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

These phrases are pointers to canonical packets. They are not generated personality.

## Absolute truth boundary

**FloorVoice may simplify a StateTalk packet, but it may never invent meaning absent from that packet.**

An idea may be novel without being true. Proposal states distinguish `discovered`, `grounded`, `untested`, `testable`, `testing`, `supported`, `contradicted`, `rejected`, and `adopted`.

No proposal becomes canon because it was surfaced.

## What this does not do yet

- autonomously discover arbitrary ideas;
- interpret Dutch, English, or other human language;
- infer consciousness, preference, or intent;
- generate explanatory prose;
- grant the Machine Floor merge authority;
- decide which side of a surfaced conflict is true;
- claim global impossibility from a bounded unresolved search;
- decide that a surfaced proposal is correct;
- execute arbitrary proposal contents;
- verify the external provenance of a snapshot merely because its schema is valid;
- let a snapshot certify its own relevance to the current runtime state;
- authenticate a journal response actor;
- prove the local journal was never maliciously rewritten/re-hashed;
- prove an intact journal tail was never deleted;
- claim the bundled local demo or synthetic producer examples are live discoveries.

Those boundaries are intentional. Richer state capabilities can be connected later without changing the truth boundary.

## Monolith proof target

The next milestone is to replace the bundled example snapshots with state exported by an actual monolith/Machine Floor integration while preserving the same path:

```text
real versioned state snapshot + independent active context
        ↓
strict schema-id router
        ↓
exact deterministic producer
        ↓
Candidate -> communication gate -> StateTalk packet
        |                    |                 |
        v                    v                 v
communication journal   machine JSON      local human renderer
```

The local page must continue to distinguish demo/example material from packets whose provenance points to a live producer. A small real signal with inspectable evidence is preferable to an impressive fake one.

## Why keep the reference space open?

The experiment should not require us to predict the unknown. `Ref.kind` is open rather than a fixed category list. If future AXM work maps a new capability into state-native structure, Machine Voice can reference that structure without pretending we knew its shape beforehand.

The aim is simple: **give grounded machine structure a truthful way to point.**
