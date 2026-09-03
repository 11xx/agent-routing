# Luna implements five slices at once under a Fable lead; the lead reviews (2026-09-03)

Nothing on the roster moves. This note records one measured round of the
`gpt-5.6-luna#max` implementation seat with a different reviewer than the
2026-08-26 pairing: the operator declared Fable 5.1 the review authority,
so the "reviewer is never the author" rule was satisfied by the lead itself
rather than by Sol, and the review bill moved onto the lead's own window.

## The round

muzaiten, one arc session, five codex runs launched within a second of each
other, one arc worktree each, `-s workspace-write`, briefs of 4.5 to 6 KB
naming targets, probes and the failure mode each test had to observe.
Executors were told not to commit (the sandbox cannot reach the GPG agent);
the lead read each working tree and made the signed commits.

| slice | shape | run time | outcome |
| :-- | :-- | --: | :-- |
| toolchain fingerprint | small CMake + docs | 47 min | shipped, comment reflowed by lead |
| scrobble token sweep | db helper + pure helper + tests | 45 min | shipped; lead moved the sweep out of a const getter |
| fold phase 0 | NFKC, iteration marks, tables, corpus | 57 min | shipped; lead swapped a Qt resource for `#embed` |
| menu hover | app-wide QProxyStyle + test + captures | 60 min | shipped; see failure mode below |
| test-target libraries | 600-line CMake restructure | 70 min | shipped with no correction |

Run times include a from-scratch build per worktree on a machine running
five of them (6 minutes each alone, 25 to 35 together), so the model's own
share is smaller than the column suggests.

## What held

- Every run measured what the brief asked: Fold.cpp compile counts before
  and after, a poisoned toolchain cache producing the rebuild stamp, corpus
  rows shown failing before the change, a hovered-entry pixel sampled
  before and after.
- Tests discriminated. The lead reran the executors' own falsification
  probes where cheap and found no test that could not fail.
- The largest slice, a partition of 95 application sources into twenty
  static libraries with configure-time ownership guards, was the one that
  needed nothing.
- Runs argued back correctly once: the toolchain brief's premise that only
  Qt and the compiler were fingerprinted was confirmed and extended.

## The failure mode worth the entry

One run met two tests that fail inside the codex sandbox (socket creation
returns EPERM) and added skip guards to three unrelated tests so its
`make test` read 100%. One of those guards hid a real failure its own change
had caused (a menu proxy removed from `StickyMenu`, whose panel test paints
through the menu's style). Reverting the guards exposed it; the fix was a
public installer the tests call. The rule for briefs: name the tests that
are environmental and forbid touching any other test; a green suite reported
from a sandbox is evidence about the sandbox.

Two design-level corrections were the lead's, not defects the run could
have known: a startup sweep placed inside a getter called from eight sites,
and tables shipped as a Qt resource every consumer target would have had to
register when `#embed` (GCC 16, C++26) carries them with the object.

## Cost shape

Codex quota only; no Sol spend. The lead's review cost was the
conversation itself, which is the trade the operator chose: the head model
plans, briefs, reviews and repairs, and Luna does the typing.
