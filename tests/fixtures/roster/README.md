# Fixture roster

A frozen copy of the routing data (`routing/*.toml`) and the doctrine table
`bin/lint-routing` checks against it (`doctrine/model-routing.md`). The tests
read this copy, never the live `routing/`, so a roster edit can never break a
test: the live roster is its own truth, guarded by `bin/lint-routing`.

`tests/roster.py` builds the tree the tests run against: this data beside
copies of the repository's `bin/`, `lib/`, `templates/` and guide. Its model
ids are fixture names; a test may lean on any of them because they never move.

This copy changes only with a schema change, a new key or table the code
reads. Make the change here in the same commit as the code, and keep the copy
passing `bin/lint-routing` when placed beside the code.

The dated capability tests (`--as-of`, `ladder --history`) read the
repository's own committed history at fixed past instants, which no roster
edit rewrites.
