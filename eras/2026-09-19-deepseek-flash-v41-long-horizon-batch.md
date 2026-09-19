# DeepSeek V4.1 Flash runs an eighteen-slice batch unattended (2026-09-19)

The second field arc on the V4.1 build, and the shape the first one named as
missing: long horizon, no review between slices. The seat does not move on it;
the probation now carries evidence on both of the axes the predecessor failed.

## The round

One pi session, `deepseek-flash#max` through the `deepseek` provider, on the
same ~50k-line Rust CLI as the first arc. Eighteen stacked slices in one
worktree — journal mechanics, workspace projections, identity detection, a
contribution-trailer specification with a printable guide, and a Haskell
semantic model with property tests — each briefed with verified source anchors,
a scope ceiling, and acceptance probes that had to fail first.

It ran **2h11m unattended**, from a cold start with slice 01 handed over, and
exited on its own at the end of the batch. The lead did not look at it until it
finished. One short repair round followed the review.

| outcome | count |
| :-- | --: |
| slices landed, gates green at every recorded patchset | 17 |
| slices stopped correctly with a handoff | 1 |
| blocking findings in the lead's single-pass review | 1 (traced to the brief) |
| executor-caused defects found by review | 0 |
| repair rounds | 1, first try |

Totals: ~9.8k lines across 59 files; 1005 CLI plus 97 unit tests at the tip; a
separate Haskell suite of 76 checks, reproduced independently by the lead from a
clean export.

## What the long horizon showed

The predecessor's decisive failure was long-horizon plan execution — it lost to
cheaper models over 20-60 minutes of tool calls. This build held a 131-minute
plan to the end:

- **It followed the protocol for all eighteen slices**, including constraints
  that only mattered many slices later: explicit identity on every write (every
  patchset in the batch is attributed correctly), one branch per slice, gates
  before the next branch, no integration, no close.
- **It stopped where the brief said stopping was right.** The tapes-core slice
  checked its premise before editing, found the library hardcodes a path that an
  earlier slice had just taught arc to override, proved it with a two-fixture
  probe, and filed a handoff instead of linking, vendoring, or shelling out — each
  of which the brief forbade and each of which would have produced a green
  build. The lead confirmed the premise failure in the library's source.
- **It declined to invent a diff.** The verification-only slice shipped none, as
  its brief intended, despite being the slice a volume-biased model is most
  likely to "complete".
- **It argued with the brief, correctly, four times**: two environment
  variables that do not exist, a rendering surface that does not exist, a stale
  schema version, and a file that does not hold the code the brief placed there.
  Each correction was right.

## What went wrong, and who caused it

One executor slip in 131 minutes: it began the last slice on the previous
slice's branch and snapshotted there, recording a patchset against the wrong
change. It noticed, moved the branches back, recorded a corrective patchset,
filed a ledger comment naming the mistaken one, and reported it without being
asked. No event was edited or deleted.

Every other defect was the lead's. The protocol told the implementer to run two
commands that refuse any role but lead — the first run stopped on it, correctly,
after one slice. The briefs repeated a feature request's claims without checking
them; the one blocking finding came from that, and the executor had built
exactly what the brief described. Recorded because a model's field record is
only honest if the supervisor's error rate is on it too.

## What this establishes, and what it still does not

Establishes, on top of the first arc: sustained brief adherence over a
two-hour unattended horizon, correct refusal to fabricate progress where the
premise failed, and self-reported error correction. The predecessor's two
measured failures — fabrication and long-horizon plan loss — did not appear in
either arc, and the lead probed every claim that mattered.

Does not establish: that it approves correctly (it issued no verdicts), that it
holds without a pre-resolved brief, or anything about work where a wrong answer
passes every gate. Two arcs under one lead, on one codebase, are two
observations, not a distribution.

The seat stays a probationary generator. The case for an implementation seat is
now evidenced, and the remaining question is the one the first arc named: a
surface where the gates cannot catch it.
