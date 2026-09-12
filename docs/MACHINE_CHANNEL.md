# Machine Channel v0.1

Machine Voice has a non-human command surface for monoliths, local tools, AIs, and other machines that need the canonical result without opening the FloorVoice page.

Protocol identifier:

```text
axm-machine-voice/machine-channel/0.1
```

The channel is deterministic, local, standard-library-only, and emits exactly one canonical JSON object on stdout per invocation.

## Zero-install snapshot use

From the repository root:

```bash
python machine_voice.py snapshot examples/alternative_snapshot.example.json \
  --active-ref activity:local-monolith-proof
```

The snapshot can also be piped over stdin:

```bash
cat examples/alternative_snapshot.example.json | \
python machine_voice.py snapshot - \
  --active-ref activity:local-monolith-proof
```

`--active-ref` is intentionally outside the snapshot. It represents the caller/runtime's independently supplied active state and prevents the snapshot from certifying its own relevance.

Repeat `--active-ref` when multiple references are active.

Previously emitted semantic fingerprints can be supplied with repeated `--seen-fingerprint` arguments so duplicate communication is rejected by the normal gate.

A persistent communication journal can supply prior fingerprints automatically and append only newly emitted communication:

```bash
python machine_voice.py snapshot examples/alternative_snapshot.example.json \
  --active-ref activity:local-monolith-proof \
  --journal local/communication.jsonl
```

## Structured response command

A human, AI, game, or other machine can record a structured response to an event that exists in the communication journal:

```bash
python machine_voice.py respond local/communication.jsonl \
  --event-id snapshot-example-001 \
  --actor human:local-user \
  --action inspect \
  --target state:candidate-path-b
```

The response command does not create a new StateTalk claim. It appends interaction structure to the journal.

## Response contract

Every normal or invalid invocation returns exactly one JSON object.

Example emitted envelope:

```json
{
  "protocol": "axm-machine-voice/machine-channel/0.1",
  "status": "emitted",
  "reasons": [],
  "fingerprint": "...",
  "packet": {"version": "0.1"}
}
```

Valid protocol outcomes use exit code `0`:

- `emitted` — a canonical StateTalk packet exists;
- `no_candidate` — the producer found nothing that qualified, so silence is the correct result;
- `rejected` — a candidate existed but the communication gate refused it, for example because it was irrelevant or duplicated;
- `recorded` — a structured response was appended to a valid journal event.

A `recorded` result includes a `journal_record` summary containing its sequence, hash, type, and referenced event id.

Invalid input uses exit code `2` and still returns the same versioned envelope with:

```json
{
  "protocol": "axm-machine-voice/machine-channel/0.1",
  "status": "invalid",
  "reasons": ["..."],
  "error": "...",
  "fingerprint": null,
  "packet": null
}
```

No explanatory prose is mixed into stdout. Callers do not need to scrape human text.

## Python integration

Installed/importing runtimes can bypass the process boundary and call:

```python
from axm_machine_voice import process_alternative_snapshot
```

with independently supplied `active_refs`.

Journal-aware runtimes can additionally use:

```python
from axm_machine_voice import (
    append_emission,
    append_response,
    emitted_fingerprints,
    read_journal,
)
```

The CLI does not add reasoning semantics. It transports the same strict snapshot adapter, deterministic producer, communication gate, and explicit journal operations used elsewhere.

## Truth boundary

The machine channel does **not**:

- authenticate who created a snapshot;
- prove referenced evidence is truthful;
- make a proposal canonical;
- execute proposal contents;
- generate human language;
- convert invalid state into a plausible guess;
- make a recorded response correct merely because it was appended.

Its job is narrower: preserve a deterministic, versioned route from supplied state to canonical Machine Voice output, grounded silence/rejection, or an explicit structured interaction record.
