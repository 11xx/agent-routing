# DeepSeek V4.1 Flash runs a parallel batch off the Go pool (2026-09-22)

The third field arc on the V4.1 build, and the first with a different shape from
the other two. Those were one long session each on a single Rust CLI; this was
eight independent changes across six repositories, seven of them dispatched at
once, on a different pool, reviewed one by one as they landed. The seat does not
move on it, but its generator footing was relaxed for this batch by operator
direction, and the evidence below is what that relaxation bought.

## The round

The route was `implement:deepseek-go`, which reaches the model through pi on the
OpenCode Go subscription as `deepseek-v4.1-flash` at max effort. Every run went
through `agent-delegate` with an arc change, its own worktree, and a brief
carrying verified source anchors, a failing-first acceptance probe, named gates,
and an explicit invitation to dispute. The lead was Claude Code on
claude-opus-5-5#medium. Codex's weekly window was exhausted, so no second model
reviewed.

| run | repository | shape | wall clock | cost | first review |
| :-- | :-- | :-- | --: | --: | :-- |
| routing | ai-agent-routing | guide text + doctrine test (Python) | 5.3 min | $0.053 | approved |
| harness-status | harness-status | new subcommand + tests (Rust) | 4.0 min | $0.033 | approved |
| delegate-guide | ai-agent-delegate | guide text + tests (Rust) | 6.3 min | $0.048 | approved; one sentence repaired, brief-caused |
| arc | arc | guide section + test (Rust) | 9.2 min | $0.067 | approved |
| subagent | ai-agent-harnesses | tool description + refactor + test (TypeScript) | 12.4 min | $0.064 | approved |
| delegate-watch | ai-agent-delegate | concurrency fix + tests (Rust) | 15.6 min | $0.121 | approved |
| tapes | tapes | three features, 19 files, +857/−104 (Rust) | 25.1 + 5.6 min | $0.303 | changes requested once |
| directed | ai-agent-delegate | CLI mode + validation + env scrub, 12 files, +1,525/−56 (Rust) | 19.2 min | $0.187 | approved |

Total **$0.88** for eight changes and one repair round, about 102M tokens, nearly
all cache reads. The seven parallel runs finished within 25 minutes of dispatch;
the whole batch, including the sequential eighth, took 36.

## What review found

- **Seven of eight approved on first read.** The eighth, tapes, carried the only
  executor-caused defect. A turn-duration distribution sampled only records that
  carried text, 22 of the session's 96 model requests. It passed the executor's
  own probe and was caught by the lead running the build against real data. It
  was repaired in one 5.6-minute resumed round, with a fixture that failed first.
- **It disputed two of the lead's premises and was right both times.** Claude Code
  does report `claude -p` runs to harness-status, which the lead confirmed with
  an authenticated run; and the state set the brief named was wrong. The one
  sentence the lead repaired was a false premise the executor had faithfully
  copied from the lead's own request (that pi can background a shell call).
- **It declined out-of-scope work with reasons.** It left a quota fence out of a
  guide, and justified a 303-word section against a 250-word target by listing
  what it had already cut.
- **It disclosed against itself.** It reported an accidental empty snapshot and
  an inherited identity it had not caught at first. Four runs independently
  noticed that `arc env` inside the executor reported the lead's session, and
  declared their own identity explicitly for their ledger writes. One diagnosed
  the leak, and the directed-selection run fixed it.
- **The largest change held under live probing.** Directed model selection
  refused a prohibited tier, an unknown model, a conflicting variant, and an
  incomplete group before launch. A live directed run recorded the full selection
  provenance, and the omitted continuation paths were reported rather than
  papered over.
- **No fabricated identifier, API, flag, or test result** appeared in anything the
  lead probed, across four languages.

## What it does not show

- **Approval.** It issued no verdicts, so whether it approves what it should not
  is still untested.
- **Brief-less work.** Every run had a verified brief with a failing-first probe.
- **The footing.** On seven of the eight changes, its code was the last edit that
  shipped, with only the lead's review between it and integration. That is the
  generator footing relaxed by operator direction for this batch. It is evidence
  about what the relaxation cost here, which was one semantic defect caught in
  review; it is not a standing change to the seat.
- **The hosting posture.** The Go pool refused this model's predecessor on
  2026-08-01 pending a China-hosting data-residency opt-in, and served V4.1 on
  2026-09-22 without refusing. So the opt-in is in effect for this workspace,
  and the operator directed six repositories' context there. That is the
  operator's decision, recorded as a fact; nothing on this row takes it for them.
