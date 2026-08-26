# The pairing that governs spend: Luna implements, Sol reviews, and review is the bill (2026-08-26 → )

Nothing on the roster moves. This note records a measured cost shape, in the
`gpt-5.6` era and expected to be re-measured when the next generation lands.
The prediction attached to it is that **Luna stays the implementation
workhorse** across that boundary — the seat is about price-to-competence at a
fully specified task, which is the most durable property on this roster. Where
review lands is the part likely to move.

## The pairing, as used

`gpt-5.6-luna#max` implements in parallel from a fully specified brief;
`gpt-5.6-sol` reviews what Luna authored, because the reviewer is never the
author. That second clause is not a preference — it is the standing rule
meeting the standing default, and it has a price nothing currently states.

## The measurement

One `arc` session, nine codex runs. Rates derived from each tier's
`usd_per_task` normalized by its `out_tokens`.

| role | route | rate | runs | tokens | cost | share |
| :-- | :-- | --: | --: | --: | --: | --: |
| implementation | `luna#max` | ~$8/M | 4 | 1,127k | ~$9 | 8% |
| review | `sol#high` | ~$124/M | 5 | 862k | ~$107 | 92% |

Review held 43% of the tokens and 92% of the cost. One `sol#high` pass costs
about nine `luna#max` implementation slices.

The absolute dollars are soft: a codex run reports total tokens rather than
output tokens, and a read-heavy review carries proportionally more input than a
write-heavy implementation does, so applying an output rate to both overstates
review's figure. The ordering is not soft. At ~15x the rate, review dominates
under any correction that leaves the tiers where they are.

**Counting runs or tokens hides this completely.** By token count review looks
like the smaller half, and the conclusion drawn from that count — that
implementation is the expensive shape — is backwards by an order of magnitude.
Spend is rate times volume. Nothing else is spend.

## What this exposes in the current routing

`review` resolves to `luna#max`, and the two Sol variants are named exceptions:
`fast` when a verdict is on the critical path, `high-stakes` as a *second* pass
where a wrong approval is expensive. The third exception —
[Luna authored the diff](2026-08-18-luna-reviewer-off-probation.md) — names Sol
without naming which Sol, and it is the exception that fires most often, because
Luna is also the implementation workhorse. **Routing Luna to implement routes
review off the cheap tier by construction.** That coupling is the finding here.

Per token the two Sol tiers are close (`medium` ~$103/M, `high` ~$124/M); per
task they are not (`$1.86` against `$3.47`), because `medium` reaches its answer
in fewer tokens. So the tier choice is worth roughly 1.9x and the Luna→Sol step
is worth 12–15x. **Effort tuning inside Sol is the small lever; how many Sol
passes run is the large one.**

## The rules that follow

- **Batch review by default.** One pass over N related changes, not N passes.
  For defects that span changes it is also the more precise shape: the most
  serious finding in this session was one change breaking a predicate a
  different change relied on, which no per-change reviewer would look for.
- **Per-change review is an opt-in with a stated price.** It buys depth on one
  intricate change, and a verdict before the next change is written when the
  next depends on this one being right. Name the cost where it is chosen.
- **Count passes before buying them.** Five `sol#high` passes ran here where
  one would have done: ~$107 against ~$37, on the step that was already 92% of
  the bill. The split rested on an assumed context limit that was wrong by a
  factor of sixteen and checkable in one command.
- **A closed review window has no substitute.** `review` seats on codex and pi
  only, and a lead cannot review what it authored or gated. Implementation
  reroutes; a verdict waits. Spend a closing window on verdicts that gate
  unmerged work before audits of already-integrated work.
- **A killed reviewer loses everything.** Two sweeps died on the usage limit
  mid-analysis: no report, no partial work, ~293k tokens gone. A killed
  implementer leaves a dirty worktree that is usually most of the slice.

## What would re-open this

A generation boundary. The rates, the 15x gap, and the review-dominates
conclusion are all `gpt-5.6`-era facts. If a later Luna-class tier is seatable
as reviewer of work it did not author, or a later Sol-class tier lands near
Luna's rate, the coupling above dissolves and this note should be superseded
rather than amended.
