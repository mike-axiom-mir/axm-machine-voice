# Bounded Unresolved Snapshot v0.1

Protocol id:

```text
axm-machine-voice/unresolved-snapshot/0.1
```

This snapshot feeds the bounded unresolved producer through the same generic Machine Voice transport as the alternative and conflict producers.

Required meaning:

- one explicit problem reference;
- one explicit search-scope reference;
- one or more explicit required constraints;
- zero or more grounded attempts;
- evidence on every supplied attempt;
- independently supplied active runtime context outside the snapshot.

It emits `I cannot resolve this.` only when at least one grounded attempt is supplied and every supplied attempt misses at least one required constraint.

Zero attempts is normal silence. Any fully constraint-preserving attempt is normal silence.

A surfaced packet explicitly records:

```json
{"global_impossibility_claimed": false}
```

So this protocol never claims that no solution exists outside the named supplied search scope.
