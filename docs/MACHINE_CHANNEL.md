# Machine Channel v0.1

Machine Voice has a non-human command surface for monoliths, local tools, AIs, and other machines that need the canonical result without opening the FloorVoice page.

Protocol identifier:

```text
axm-machine-voice/machine-channel/0.1
```

The channel is deterministic, local, standard-library-only, and emits exactly one canonical JSON object on stdout per invocation.

## Zero-install use

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

## Response contract

Every normal or invalid snapshot invocation returns exactly one JSON object.

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
- `rejected` — a candidate existed but the communication gate refused it, for example because it was irrelevant or duplicated.

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

The CLI does not add new semantics. It is only a transport around the same strict snapshot adapter, deterministic producer, and communication gate used elsewhere.

## Truth boundary

The machine channel does **not**:

- authenticate who created a snapshot;
- prove referenced evidence is truthful;
- make a proposal canonical;
- execute proposal contents;
- generate human language;
- convert invalid state into a plausible guess.

Its job is narrower: preserve a deterministic, versioned route from supplied state to canonical Machine Voice output or grounded silence/rejection.
