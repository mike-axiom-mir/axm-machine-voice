# Local / Monolith Test Contract

This document defines the smallest integration surface for including AXM Machine Voice in a local AXM monolith test without adding cloud, account, AI, or network dependencies.

## Truth boundary

The local page is a renderer, not a discovery engine and not a validator of truth.

- A rendered packet is not automatically true.
- A surfaced proposal is not automatically adopted or canonical.
- FloorVoice text is selected only from the fixed vocabulary mapped to `packet.kind`.
- The bundled startup event is explicitly demo data and must never be presented as a live Machine Floor discovery.

## Entry point

Open:

```text
local/index.html
```

It works directly from local files in a browser. No build step or server is required.

The machine-readable module manifest is:

```text
local/manifest.json
```

## Local packet loading

The page can load a JSON StateTalk packet through its file picker. This is useful before a live producer is connected.

## Monolith bridge

A parent shell may embed `local/index.html` in an iframe and exchange messages with this protocol identifier:

```text
axm-machine-voice/local-bridge/0.1
```

### Child -> parent

When embedded, Machine Voice emits:

```json
{
  "protocol": "axm-machine-voice/local-bridge/0.1",
  "type": "ready",
  "version": "0.1"
}
```

After successfully rendering a supplied packet it emits:

```json
{
  "protocol": "axm-machine-voice/local-bridge/0.1",
  "type": "packet-rendered",
  "event_id": "example-event-id"
}
```

### Parent -> child

The parent may supply a canonical StateTalk packet:

```js
frame.contentWindow.postMessage({
  protocol: "axm-machine-voice/local-bridge/0.1",
  type: "load-packet",
  packet
}, "*");
```

The current local bridge intentionally performs only structural rendering checks. Producer-side grounding remains the responsibility of the Machine Voice core gate and the producer's evidence path.

## Next integration target

For the monolith test, the useful progression is:

1. include the module through `local/manifest.json`;
2. render the bundled demo and visibly retain its demo label;
3. pass a known-good StateTalk packet through the bridge;
4. verify the phrase, evidence, subjects, map relations, and raw packet match the packet exactly;
5. connect one real deterministic producer only after the renderer path is proven;
6. keep live-producer claims separate from demo data in screenshots, logs, and test reports.

The first live producer should be chosen for evidence quality, not spectacle. A small deterministic state conflict or alternative is a better first proof than a complicated pseudo-intelligent demonstration.
