# DeepSeek V4.1 Flash implements a three-slice arc under an Opus lead (2026-09-18)

The first field arc on the V4.1 build. The roster row carried only the
predecessor's record, and the probation it describes exists because nothing had
measured the build in service. This measures it once. The seat does not move on
one arc; what changes is that the row now has evidence of its own to argue from.

## The round

One pi session, `deepseek-flash#max` through the `deepseek` provider, working on
`arc` — a ~50k-line Rust CLI it had not seen. Three stacked slices in one
worktree, briefs of 2 to 4 KB naming verified source anchors, scope ceilings,
named acceptance probes, and the negative properties each slice had to preserve.
The lead planned, reviewed and integrated; the executor wrote every line of the
diff.

Round one was dispatched by the operator directly; round two was a warm resume
of the same session through `agent-delegate`, carrying two blocking findings.

| slice | shape | outcome |
| :-- | :-- | :-- |
| bind a gate refusal to the change record | 21 files, refusal moved off the caller's cwd | approved, 1 non-blocking finding |
| a promotion command with provenance | 21 files, new CLI path + schema bumps | approved first pass |
| widen an adopt command, report what it holds | 14 files, new projection fields | changes-requested, 2 blocking; approved on repair |

Totals: 7 commits, ~2,100 lines across two rounds. Gates green at every
patchset it recorded — 954 CLI plus 97 unit tests, `clippy -D warnings`, `fmt`.
Round one ran about 25 minutes, round two about 9.

## What it did that the briefs did not ask for

- **Chose a better mechanism than the brief specified.** The brief said refuse
  inside one command; it made the condition a first-class blocker instead, so
  three commands that had to agree agree by construction rather than by a second
  implementation of the same check. The lead's own probe confirmed no path
  bypasses it.
- **Closed the same hole from a direction nobody named**, refusing a second
  route into the bad state.
- **Found and fixed a stale claim in a neighbouring message** that carried the
  same defect as the one it was sent to repair.
- **Argued a design call it was invited to argue**, and won it on the merits:
  told that a warning might beat a refusal, it chose refusal because nothing
  reverses the operation a warning would permit, and named the supported path
  for an operator who meant it.
- **Reported the cost of its own fix** — a test that reached the repaired state
  through the now-refused route had to be rebuilt on a different fixture, and it
  said so rather than letting the coverage quietly narrow.

## What it got wrong

Two blocking findings in one of three slices, both consequences of widening a
command: it left the new state reachable against an object that should have been
guarded, and it resolved one path by a convention that its own sibling command
resolved from the source of truth. One of the two traced to an omission in the
brief and was recorded against the brief rather than the executor. Both were
repaired on the first return, each with a probe that failed beforehand for the
predicted reason.

It also skipped two ceremony steps in round one — no brief recorded, no debt
filed — and filed both when told.

## The disclosure that matters most

Its first ceremony pass of round two recorded a patchset, its verifications, its
changelog and its debt against the **lead's** harness and session. Running as a
child of the lead's tool shell, identity detection resolved the outer harness.

It noticed, set the identity explicitly, redid the pass, and then *reported both
the error and the part that could not be undone* — the patchset record keeps the
wrong thread. It also named the root cause correctly, which the lead confirmed
in source and filed as a defect in the tool.

Nothing required it to disclose this. The predecessor's measured failure mode is
confident fabrication; volunteering an attribution error against itself is the
opposite behaviour, and it is the single most informative observation in this
arc.

## What this establishes, and what it does not

Establishes: on fully specified briefs with named probes, against an unfamiliar
codebase, this build produced correct work, followed the brief's explicit
constraints — including the sequencing constraint that one slice must not name a
flag a later slice introduces — argued rather than complied where invited, and
reported against its own interest. No fabricated identifier, API, or test result
appeared in anything the lead probed, and the lead probed every claim it made.

Does not establish: that it can be trusted unsupervised, that it approves
correctly, or that it holds over longer horizons. Every finding here was caught
by a lead who read the diff and ran the probes; the arc was three slices, not
thirty. The predecessor's instruction-following failure was not reproduced, but
one arc not reproducing a failure is weaker evidence than the arc that found it.

The probation stands and is now evidenced rather than inherited. A second arc,
ideally with a different shape — longer horizon, or a surface where a wrong
answer is not caught by a gate — is what would move the seat.
