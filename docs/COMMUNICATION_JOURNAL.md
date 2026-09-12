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

Every emitted `event_id` is unique within one journal so a later response has one unambiguous communication target.

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

The `actor` field is a structured identity reference supplied by the caller. v0.1 does **not** authenticate that the claimed actor really produced the response.

## Hash-linked integrity chain

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
- record hash;
- unique emitted event ids.

This reliably catches accidental corruption, reordering, and edits where the hashes were not recomputed.

### Important truth boundary

This is **not cryptographic authentication against a writer with full file access**.

The chain uses ordinary unkeyed hashes. Someone able to rewrite the whole journal can also recompute those hashes. An intact tail can likewise be deleted while leaving the surviving prefix internally valid.

Stronger malicious-tamper or tail-deletion detection requires something outside this local journal, for example an externally anchored checkpoint/root hash, a signature, or another trusted state layer. v0.1 does not claim that protection.

## Writer model

v0.1 assumes a single journal writer at a time. Concurrent multi-process append coordination is not yet claimed.

That is adequate for the local monolith proof path. A later version can add an explicit single-writer service, lock protocol, or state-floor append authority if concurrent writers become real.

## Truth boundary

The journal does not:

- make a packet true because it was emitted;
- make a response correct because someone recorded it;
- authenticate a claimed response actor;
- convert silence into communication;
- infer why an actor responded;
- grant authority to the speaker or responder;
- prove an intact tail was never deleted;
- prove that a malicious writer could not rewrite and re-hash the complete local file;
- silently repair a corrupted chain.

If journal validation fails, journal-aware communication fails closed rather than discarding history and speaking as though nothing was previously emitted.
