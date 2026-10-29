# DeepSeek V4.1 Flash 1017 max on the mahaf engine series (2026-10-28 to 2026-10-29)

The first field arc of the 1017 build. `deepseek-v4.1-flash#max` ran through
Pi 1.4.0 on the OpenCode Go pool, as `--provider opencode-go --model
deepseek-v4.1-flash`. The endpoint is a rolling alias; the expected build was
DeepSeek-V4.1-Flash-1017 and no provider-reported identity was recorded. An
Opus 5.5 lead briefed every lane with exact targets, a scope ceiling and named
acceptance probes. GPT-6.1 Sol at xhigh reviewed the integrated work
independently, in batches. Costs are Pi's per-session estimates, not
subscription spend.

## Work and outcomes

57 lanes ran from 2026-10-28 05:36 to 2026-10-29 03:23 UTC:
- slices of a Haskell application engine: operation layer, permission and
  approval checks, wire codecs, a store lease, an operation registry, runtime
  discovery, private interaction streams;
- C socket and transport code;
- fixes for Sol's review findings;
- harness and check scripts;
- one arc (Rust) change and its arc-model (Haskell) re-pin.

Seven to eight lanes ran at once.

| Measure | Value |
| :-- | :-- |
| Lanes that exited 0 | 52 of 57 |
| Wall time of a successful lane | median 46 min, p90 92 min, max 303 min |
| Pi-estimated cost, 51 measured lanes | $8.64 in total; median $0.156, max $0.494 per lane |
| Tokens, same 51 lanes | 13.8M uncached input, 1.23B cache-read input, 4.77M output (2.89M of it reasoning) |

Of the five non-zero exits:
- one was a lane killed at its 6 GiB cap after an unbounded `find /` and a bare
  ghci with scratch in tmpfs;
- three were upstream capacity refusals from the Go endpoint (`429
  ttft_admission_refused`, "the cell is at capacity"), all within an hour while
  seven or eight lanes ran. Each lane was resumed once and finished;
- one was a lead-cancelled relaunch.

## Quality under independent review

Sol 6.1 xhigh reviewed the integrated DeepSeek changes in single-reviewer batches:

| Batch | Changes | Changed lines | Approved | Changes requested | Defects still on main |
| :-- | --: | --: | --: | --: | --: |
| d01 | 11 | 2,631 | 8 | 3 | 5 |
| d02 | 12 | 5,730 | 7 | 5 | 8 |
| d03 | 7 | 7,281 | 2 | 5 | 11, three of them high |

The defects cluster in a few classes:
- concurrency: an approve and a cancel racing so that both succeed;
- resource lifetimes: a listening descriptor never closed, a lease descriptor
  leaked on cancellation;
- unchecked narrowing: a chunk offset that wrapped to zero;
- deadlines bypassed by a blocking write after `poll`;
- private input echoed on an ordinary error path;
- self-confirming tests: an approval compared with itself, with the test's
  expected value built from the same grant.

Sol named no fabricated identifier.

The arc change, a ledger-based review-independence rule in Rust, took eight
Sol rounds and seven DeepSeek fix rounds before approval.

Every finding sent back to a fix lane was reproduced before it was fixed, and
none proved false. Each fix shipped a check that failed on the base, or on a
named faulty variant, for the stated reason. The lanes also kept their own
failures apart from the environment's:
- a check failing only under long harness paths was shown to fail on main, and
  its repair was kept in a separate commit;
- a lane-only acceptance failure was named rather than fixed;
- all four premises of one review batch were confirmed before any edit.

## Weaknesses observed

- **No sense of time budget.** One fix lane ran 303 minutes. About four hours
  went to an aimed-interruption test of its own that deadlocked the GHC
  runtime: it held an unsafe foreign call while a Haskell thread was thrown
  to. The lane then dropped the test and covered the gap by masking.
- **Unbounded search.** The 6 GiB kill came from searching `/`. That matches
  the September build's unbounded-search stall. No lane repeated it once the
  rules confined search to the worktree.
- **Concurrency is the go-pool limit.** Seven or eight concurrent max lanes
  drew three capacity refusals in an hour.

Reading: at max, with a fully specified brief and a cross-lab reviewer, 1017
delivers reviewable engine work at about $0.16 a lane. Its blind spots are the
classes above, which an independent reviewer at or above Sol's tier catches. It
is not the last model to touch shipped work.

Evidence: the mahaf project journal (the roadmap handoff, the engine and M7
plan's evidence, and the review todos filed per batch), and the batch reports
under the lead's review directory.
