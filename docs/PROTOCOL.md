# StateTalk / Machine Voice protocol v0.1

## What this protocol is

StateTalk is a minimal canonical envelope for surfacing grounded machine-state findings to collaborators. It is designed to let human, AI, and machine participants inspect the *same underlying event* at different resolutions without making natural language the source of truth.

The protocol does not discover ideas. Discovery belongs to whichever real capability produced a candidate: a comparator, simulator, constraint checker, search process, game player, state analyser, or future capability.

Machine Voice only answers:

1. Is this candidate grounded enough and relevant enough to surface?
2. What exact structural packet should collaborators receive?
3. What tiny fixed human phrase may point at that packet without inventing meaning?

## Event path

```text
producer capability
      |
      v
Candidate (not speech)
      |
      v
communication gate
      | reject -> stays telemetry/evidence only
      |
      v
StateTalkPacket
      |------------------------|
      v                        v
machine / AI channel      FloorVoice
full packet               fixed phrase
      |                        |
      +-----------+------------+
                  v
          Proposal Map / evidence
```

## Canonical objects

### Ref

```json
{"kind":"state","id":"enemy-arrival"}
```

`kind` is intentionally open. A future capability may introduce a kind this repository did not predict. This keeps the protocol from turning today's human categories into tomorrow's hard wall.

### Claim

```json
{
  "predicate":"arrives_before",
  "arguments":[
    {"kind":"state","id":"enemy-arrival"},
    {"kind":"state","id":"player-cover-arrival"}
  ],
  "value":true
}
```

Claims are structured. The canonical layer does not require explanatory prose.

### Proposal Map

A Proposal Map is a graph of typed references and relations. It is deliberately generic enough to point at files, states, functions, simulations, rules, geometry, future capability objects, or anything else with a stable reference.

The map does **not** make a proposal true. `status` distinguishes discovery from support.

### StateTalkPacket

A packet contains:

- protocol version;
- event id;
- communication kind;
- source reference;
- subject references;
- structured claim;
- evidence references;
- active-context relevance references;
- permitted / suggested next operations;
- semantic fingerprint;
- optional Proposal Map;
- optional metadata.

The semantic fingerprint excludes `event_id` and metadata so the same semantic event cannot bypass duplicate detection simply by being emitted with a new id.

## Deterministic communication gate v0.1

A candidate is eligible only when all current conditions are true:

1. it identifies at least one subject;
2. it carries at least one evidence reference;
3. at least one relevance reference intersects the active collaborative context;
4. it exposes at least one next operation such as `inspect`, `compare`, or `test`;
5. the same semantic event has not already been emitted.

These conditions do **not** prove the candidate true. They prove only that it has enough grounded and actionable structure to be worth surfacing.

Later versions may refine the gate from experiment evidence. They should not silently widen it.

## FloorVoice

FloorVoice v0.1 uses a closed phrase table:

| Kind | Phrase |
|---|---|
| notice | I noticed something. |
| conflict | These do not fit. |
| alternative | There is another way. |
| unresolved | I cannot resolve this. |
| need | I need something. |
| repeat | This happened before. |
| novel | This is new. |
| success | This worked. |
| failure | This did not work. |
| look | Look here. |

No names, values, explanations, confidence language, emotional language, or generated prose are inserted into these phrases. To learn *what* the phrase refers to, inspect the packet.

## Truth boundary

- Telemetry is not speech.
- A candidate is not speech.
- An emitted packet is not proof of truth.
- A proposal is not canon.
- A machine-readable relation is not evidence of consciousness or subjective opinion.
- A fixed human phrase is a pointer, not a personality.
- Human attention or approval must not rewrite the factual history of the event.

## Governance

For internal AXM work the merge gate is the four roots, not founder authority:

- Truth
- Agency / non-domination
- Continuity
- Wisdom before speed

A human, AI, or machine participant may surface a grounded contribution. None receives authority merely from category or capability.
