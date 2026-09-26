# GPT-6 Luna max and DeepSeek V4.1 Flash as parallel workhorses (2026-09-25)

The first field arc for `gpt-6-luna` and the fourth for DeepSeek V4.1 Flash,
run as a deliberate side-by-side: one lead, one protocol, six lanes of real
backlog work in a 60k-line Rust CLI and its session-reader library, three
lanes each. It was planned as a comparison and became a partial one, because
a Codex service outage ended every codex run about two hours in; DeepSeek
then took over two of Luna's lanes mid-flight.

## The round

Both routes came from `agent-routing resolve implement`: `implement` on codex
(`gpt-6-luna` max, `openai-codex`) and `implement:deepseek-go` on pi
(`deepseek-v4.1-flash` max, `opencode-go`). Every lane went through
`agent-delegate` with its own worktree, an arc change per slice, one shared
protocol, a lane brief carrying settled designs and failing-first probes, and
an explicit invitation to dispute. The lead was Claude Code on
claude-opus-5-5#high, reviewing each slice diff-by-diff and sending findings
back into the same warm session.

| lane | executor | slices | wall clock | review outcome |
| :-- | :-- | --: | :-- | :-- |
| integration edges | DeepSeek | 4 | 50 min | approved on first read; one pathspec note accepted as risk |
| gate evidence and links | DeepSeek | 2 | 45 + 15 + 7 min | two major findings, repaired in one round; one rebase round |
| tapes remote reads | DeepSeek | 1 | 45 + 12 min | one minor finding, repaired in one round |
| identity (continued) | DeepSeek | 3 | 57 min | approved; took over the lead's uncommitted work |
| replicas (continued) | DeepSeek | 2 | 35 min | approved on first read |
| identity | Luna | 1 tapes change | 30 + 12 min | stopped correctly on a missing library behaviour; one brief-caused blocking finding, repaired in one round |
| replicas | Luna | 1 of 3 | ~110 min, then outage | one design gap, repaired by the lead |
| contribution | Luna | 1 of 3, second 80% | ~110 min, then outage | store-format bump against the repo's own schema rules, repaired by the lead |

DeepSeek landed twelve changes; Luna landed two, plus most of a third the lead
finished. The outage (repeated `refresh_token_invalidated`, a fresh login
revoked within two minutes, then a usage limit) says nothing about Luna's
capability, and it cut the Luna sample short: this is not a head-to-head
result.

## What review found

- **DeepSeek's two major findings were brief-shaped.** An environment probe
  hashed stderr and ignored its exit status, and it had no time bound; the
  brief said "a command whose output identifies the environment" and nothing
  about failure or duration. Both were repaired with fail-first tests in one
  15-minute round.
- **DeepSeek argued three designs against the brief and won all three.**
  Running the remote replica's own `export` instead of rebuilding a bundle
  from lossy session JSON; identifying the owning harness by which ancestor
  introduced its session variable, with evidence that process names do not
  work (Claude's process name is a version string); and restoring a read
  bound the lead had deleted from its own adapter, from a field the lead had
  missed.
- **DeepSeek took over interrupted work cleanly.** Handed the lead's
  uncommitted migration, it fixed the lead's two mistakes, corrected three
  unrealistic fixtures with the harness formats as evidence rather than
  bending the library, and credited both authors in the commit trailers.
- **DeepSeek volunteered two things nobody asked for.** It root-caused a
  flaky test in another crate to a shared `PATH` race and fixed it, and it
  disclosed its own attribution slip on one patchset.
- **Luna's executor-side slip was one of repository convention.** It bumped
  the store format and added a full-ledger scan on every store open for two
  optional fields, where the repository's schema rules keep the version for
  exactly that case. Its interrupted external-verdict work was otherwise
  sound: five new tests written afterwards passed against it unchanged.
- **Luna stopped where the brief told it to.** It found a real gap in the
  session library, filed the fix in the library's own repository, and
  stopped rather than reimplementing it locally.

## What the audit found afterwards

An adversarial `gpt-6-sol#high` audit of the five changes the lead wrote,
repaired, or approved returned changes-requested on all five, with eight
findings, four critical. The worst were a lead-settled authority design that
let two replicas integrate at once, and an external approval overriding a local
refusal that the lead had approved in Luna's code. The executor lanes the lead
reviewed diff-by-diff did not produce findings of that class.

## What it changes

Nothing on either seat. DeepSeek V4.1 Flash's probationary implementer record
now spans four arcs and twelve more changes, with no fabricated identifier and
every disputed design settled in its favour. Luna's GPT-6 build still has no
completed field arc, only two clean-enough slices and an outage. The lesson
the arc does support is the lead's: land the lead's own work on debt, and
buy an adversarial audit before the series closes.
