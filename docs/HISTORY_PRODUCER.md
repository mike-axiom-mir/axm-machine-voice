# History Repeat / Novel Producer v0.1

Machine Voice can surface two paired history phrases from one exact bounded comparison rule:

```text
This happened before.
This is new.
```

Producer id:

```text
history-repeat-novel/0.1
```

## Why one paired producer

Repeat and novelty must share one definition of pattern equality and one explicit history domain. Splitting them into unrelated producers would allow `same` and `new` to drift onto different comparison rules.

v0.1 therefore compares one grounded current portable pattern signature against one supplied prior-history scope in exactly one explicit pattern domain.

## Inputs

The producer receives:

```text
current pattern ref
pattern domain
portable JSON-like signature
current evidence
history scope ref
complete_for_domain = true | false
history-scope evidence
zero or more historical entries
active/relevance reference
next operations
```

Each historical entry contains:

```text
historical entry ref
non-negative integer position
same explicit pattern domain
portable JSON-like signature
evidence
```

History entry references and positions must be unique. A differently named domain is not silently treated as equivalent.

## Exact pattern comparison

Pattern comparison is deterministic and portable. JSON-like values are compared recursively. Numeric spellings such as `1` and `1.0` are equivalent; booleans remain distinct from numbers.

No fuzzy similarity, embedding distance, semantic-language guess, or inferred aliasing is used in v0.1.

## Repeat

`This happened before.` can surface when at least one supplied historical entry in the same domain has an exactly equivalent signature.

History does **not** need to be complete for recurrence: one grounded match is enough.

When several supplied entries match, v0.1 selects the earliest supplied entry by:

```text
position
then Ref.key
```

The repeat packet explicitly records:

```json
{
  "history_ordering_authenticated": false,
  "outside_scope_recurrence_claimed": false
}
```

So recurrence means only:

> The current supplied pattern exactly matches one supplied entry represented as prior history in the same explicit domain.

The producer does not independently authenticate that the supplied ordering is chronologically correct.

## Novelty

`This is new.` has a deliberately stronger burden.

It can surface only when:

1. no supplied historical entry in the same explicit domain has an exactly equivalent signature; and
2. the supplied history scope explicitly claims `complete_for_domain = true`.

If there is no exact match but the scope is incomplete, the result is normal silence.

```text
no match + incomplete history
        ↓
   no candidate
```

A bounded novelty packet explicitly records:

```json
{
  "history_scope_complete_for_domain_claimed": true,
  "history_scope_completeness_authenticated": false,
  "history_ordering_authenticated": false,
  "global_novelty_claimed": false,
  "scientific_novelty_claimed": false,
  "outside_scope_novelty_claimed": false
}
```

So novelty means only:

> No exact equivalent exists in the supplied history scope that is explicitly claimed complete for this comparison domain.

It does **not** mean nobody has ever seen the pattern, that the pattern is scientifically novel, or that it is new outside that bounded supplied history.

## Completeness and ordering truth boundary

v0.1 does not independently authenticate:

- whether the supplied history is actually complete;
- whether its ordering is truly chronological;
- whether historical entries were modified later;
- whether the supplied evidence is truthful;
- whether the chosen pattern domain is the best domain;
- whether exact signature equality is the right real-world similarity rule.

Stronger claims require an external provenance/checkpoint/signature layer.

## Continuity

For recurrence, only the earliest exact supplied match is used in the semantic packet. Adding a later matching entry therefore does not create a new repeat fingerprint for the same current pattern and earliest prior match.

For novelty, the complete supplied comparison set is relevant evidence because absence is being asserted across that bounded set.

Signature object keys and numeric representation are normalized for deterministic comparison and fingerprint continuity.

## History provider boundary

The producer does not assume history comes from Machine Voice's own communication journal. A journal, game state archive, Walmi experience store, simulation log, deterministic calculation history, or another machine may become a history provider if it can supply this grounded contract.

This keeps `history` separate from one implementation of memory.

## Runnable example

```bash
python examples/run_history_producer.py
```

The bundled example produces one synthetic repeat packet and one synthetic bounded-novelty packet. It is not a live Machine Floor discovery.

## Transport boundary

v0.1 producer review comes first. A strict versioned history snapshot should be added only after this paired producer independently passes review and CI, following the same pattern as the earlier Machine Voice capabilities.
