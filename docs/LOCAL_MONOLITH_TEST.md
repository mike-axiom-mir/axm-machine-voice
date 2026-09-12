# Local / Monolith Test Contract

This document defines the smallest integration surface for including AXM Machine Voice in a local AXM monolith test without adding cloud, account, AI, or network dependencies.

## Truth boundary

The local page is a renderer and primitive interaction surface, not a discovery engine and not a validator of truth.

- A rendered packet is not automatically true.
- A surfaced proposal is not automatically adopted or canonical.
- FloorVoice text is selected only from the fixed vocabulary mapped to `packet.kind`.
- The bundled startup event is explicitly demo data and must never be presented as a live Machine Floor discovery.
- A clicked human response does not authenticate who clicked it.
- The local page does not claim a response is journaled until the parent runtime confirms `recorded` for the exact response id/event/action that the child actually sent.

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

The page can load a JSON StateTalk packet through its file picker. This is useful for inspection, but locally loaded/standalone packets do not activate the monolith response bridge.

## Monolith bridge

A parent shell may embed `local/index.html` in an iframe and exchange messages with this protocol identifier:

```text
axm-machine-voice/local-bridge/0.1
```

The child accepts bridge messages only from its actual `window.parent`. When opened standalone it does not accept bridge-driving messages from arbitrary windows.

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

When the human chooses a primitive response, the child creates a local response id and emits only interaction intent:

```json
{
  "protocol": "axm-machine-voice/local-bridge/0.1",
  "type": "response-action",
  "response_id": "local-response-1",
  "event_id": "example-event-id",
  "action": "inspect",
  "targets": []
}
```

The child deliberately sends **no actor identity**. The parent/runtime owns the actual session/user context and must supply actor identity independently if it records the response in the communication journal.

Current local response actions are fixed to:

```text
inspect
compare
acknowledge
```

`inspect` and `compare` are enabled only when the current StateTalk packet explicitly contains that value in `next_operations`. `acknowledge` is a human response and does not claim a machine recommendation.

The parent must independently validate the same conditions. UI disabling is not treated as authorization.

### Parent -> child

The parent may supply a canonical StateTalk packet:

```js
frame.contentWindow.postMessage({
  protocol: "axm-machine-voice/local-bridge/0.1",
  type: "load-packet",
  packet
}, "*");
```

After handling a valid `response-action`, the parent can return one of three bounded statuses:

```json
{
  "protocol": "axm-machine-voice/local-bridge/0.1",
  "type": "response-status",
  "response_id": "local-response-1",
  "event_id": "example-event-id",
  "action": "inspect",
  "status": "received"
}
```

Allowed `status` values:

- `received` — parent accepted the interaction message, but persistence is not confirmed;
- `recorded` — parent/runtime confirms the structured response was persisted;
- `rejected` — parent/runtime rejected the response.

These are terminal statuses for that response id in v0.1. A parent must not send `recorded` for a response that it previously finalized as `received` or `rejected`.

The child accepts a status only when `response_id`, `event_id`, and `action` match a response it actually sent for the currently rendered packet. Unsolicited or mismatched confirmations are ignored.

The local page does not accept arbitrary free-text status explanations as truth. It renders only these bounded states.

## Parent validation requirements

Before returning `received` or `recorded`, the parent/runtime should independently verify:

```text
response_id is present
        +
event_id == currently supplied packet
        +
action is inspect / compare / acknowledge
        +
targets is an array
        +
inspect/compare exists in packet.next_operations
```

The bundled proof harness implements these checks even though the child already performs its own UI checks. This preserves the rule that neither side becomes authoritative merely because the other side sent a message.

## Journal handoff

For real persistence the parent/runtime should map a valid `response-action` to the communication-journal API or machine command while independently supplying the actor reference:

```text
response-action from child
        +
runtime actor identity
        ↓
append_response(...)
        ↓
response-status: recorded
```

The proof harness in `examples/build_local_monolith_proof.py` intentionally stops one step earlier. It returns `response-status: received` and labels the interaction **proof only, not journaled**. That demonstrates the bridge without pretending browser-only proof data reached persistent state.

## Current integration target

For the monolith test, the useful progression is now:

1. include the module through `local/manifest.json`;
2. render the bundled demo and visibly retain its demo label;
3. pass a canonical StateTalk packet through the parent-only bridge;
4. verify the phrase, evidence, subjects, map relations, and raw packet match exactly;
5. verify only grounded packet `next_operations` enable `inspect`/`compare`;
6. send one primitive `response-action` back to the parent without actor identity;
7. independently validate the response id/event/action/targets in the parent;
8. have the real runtime attach actor identity and persist it through the communication journal;
9. return `response-status: recorded` only after persistence succeeds for that exact response;
10. keep demo, proof-only, and live-producer claims distinct in screenshots, logs, and test reports.

A small real signal with inspectable evidence is preferable to an impressive fake one.
