# Communication Journal v0.1

Machine Voice keeps a separate append-only journal for communication that actually happened.

Protocol identifier:

```text
axm-machine-voice/communication-journal/0.1
```

This is **not** a diagnostic or telemetry log. Ordinary state transitions, rejected candidates, and normal silence do not become speech history.

The journal currently contains only:

- `emission` — a StateTalk packet that passed the communication gate;
- `response` — a structured human/machine response to a previously emitted event.

## Why it exists

Without a persistent communication history, the same grounded condition could light FloorVoice on every run. The journal lets the communication gate inherit previously emitted semantic fingerprints so repeated state becomes silence/rejection rather than noise.

It also creates the first primitive interaction trail:

```text
Floor emitted event
        ↓
human / AI / machine responded
        ↓
structured response record
```

The response is not free-form interpretation. It records an actor reference, an action such as `inspect` or `compare`, and optional target references.

## Snapshot use

```bash
python machine_voice.py snapshot examples/alternative_snapshot.example.json \
  --active-ref activity:local-monolith-proof \
  --journal local/communication.jsonl
```

On the first qualifying run, the packet emits and is appended.

Run the same state again with the same journal and the journal's prior fingerprint is automatically supplied to the normal communication gate. The second run is rejected as `duplicate_semantic_event` and **no second speech record is appended**.

`no_candidate`, `rejected`, and invalid inputs are not appended as emissions.

## Structured response

After an event was emitted:

```bash
python machine_voice.py respond local/communication.jsonl \
  --event-id snapshot-example-001 \
  --actor human:local-user \
  --action inspect \
  --target state:candidate-path-b
```

A response can only reference an event id that already exists as an `emission` record in that journal.

The action string is intentionally open. A future human, AI, game, or machine can use bounded actions appropriate to its interaction without rewriting old journal records.

## Tamper-evident chain

Every record contains:

```text
sequence
previous_hash
record_hash
```

The hash covers the entire record payload before `record_hash` is added. Reading the journal validates:

- protocol;
- record schema;
- contiguous sequence;
- previous-hash linkage;
- record hash.

Editing or reordering an existing retained record breaks validation.

### Important truth boundary

This is **tamper-evident, not tamper-proof**.

An intact tail can be deleted from a purely local file and the surviving prefix can still validate. Detecting tail deletion requires an external checkpoint/root hash stored somewhere outside that journal. v0.1 does not claim otherwise.

## Writer model

v0.1 assumes a single journal writer at a time. Concurrent multi-process append coordination is not yet claimed.

That is adequate for the local monolith proof path. A later version can add an explicit single-writer service, lock protocol, or state-floor append authority if concurrent writers become real.

## Truth boundary

The journal does not:

- make a packet true because it was emitted;
- make a response correct because someone recorded it;
- convert silence into communication;
- infer why an actor responded;
- grant authority to the speaker or responder;
- prove an intact tail was never deleted;
- silently repair a corrupted chain.

If journal validation fails, journal-aware communication fails closed rather than discarding history and speaking as though nothing was previously emitted.
