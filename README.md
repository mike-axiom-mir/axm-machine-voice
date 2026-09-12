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

## v0.1

The first working slice is deliberately small and standard-library-only:

- open typed references so future capabilities can point to objects we did not anticipate;
- structured claims and Proposal Maps;
- a deterministic communication gate;
- semantic duplicate detection;
- canonical StateTalk packets;
- a fixed ten-phrase FloorVoice layer;
- append-only JSONL event logging;
- tests for truth-boundary failures.

The implementation lives in [`src/axm_machine_voice`](src/axm_machine_voice), and the protocol is documented in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

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

- discover ideas by itself;
- interpret Dutch, English, or other human language;
- infer consciousness, preference, or intent;
- generate explanatory prose;
- grant the Machine Floor merge authority;
- decide that a surfaced proposal is correct;
- execute arbitrary proposal contents.

Those boundaries are intentional. Discovery producers and richer state capabilities can be connected later without changing the truth boundary.

## Why keep the reference space open?

The experiment should not require us to predict the unknown. `Ref.kind` is open rather than a fixed category list. If future AXM work maps a new capability into state-native structure, Machine Voice can reference that structure without pretending we knew its shape beforehand.

The aim is simple: **give grounded machine structure a truthful way to point.**
