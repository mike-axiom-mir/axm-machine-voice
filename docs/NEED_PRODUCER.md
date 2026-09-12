# Bounded Need Producer v0.1

Human FloorVoice:

```text
I need something.
```

Producer id:

```text
bounded-need/0.1
```

## Meaning

The producer requires an explicit task, one named bounded inventory scope, one or more explicit required inputs, the supplied available inputs, and evidence for that inventory.

It can speak only when at least one required input is absent from the supplied inventory.

Example:

```text
task requires:
- config
- state-snapshot

bounded inventory contains:
- config

result:
I need something.
```

The packet names the missing input directly.

## Silence

If every explicit required input is present in the supplied inventory, this producer stays silent.

## Truth boundary

The producer establishes only:

> Inside this named supplied inventory scope, one or more explicit required input references are absent.

It does **not** establish:

- that the missing input is unavailable elsewhere;
- that the inventory is globally exhaustive;
- that the task has hidden requirements not supplied by the caller;
- that the task should proceed once the input appears;
- that inventory evidence is externally trustworthy merely because it is referenced.

The canonical claim therefore records:

```json
{
  "bounded_inventory_only": true,
  "global_unavailability_claimed": false
}
```

Unrelated inventory entries do not affect the semantic communication. This prevents the same missing requirement from becoming new speech merely because unrelated state changed.

## Runnable example

```bash
python examples/run_need_producer.py
```

The example uses synthetic state and is not a live Machine Floor discovery.
