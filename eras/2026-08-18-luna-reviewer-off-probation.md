# Reviewer seat: Luna max leaves probation and becomes the first gate (2026-08-18 → )

`gpt-5.6-luna` at `max` effort has been the resolved `review` route since it was
promoted on finding rate alone. It carried a standing caveat anyway: every
approval behind that promotion was one the lead had independently probed and
agreed with, so the rate at which it *approves wrongly* was unmeasured, and each
reviewed item was held provisionally pending a second look.

That caveat is discharged. The seat is now stable without an asterisk: **Luna max
is the first review gate for behavior-affecting work, and its verdict discharges
review on its own.** Escalation to Sol is by named exception, not by default.

Nothing else on the roster moves. The head model, the technical peer, and the
workhorse are unchanged; this note only settles the reviewer line.

## The evidence, three arcs

| arc | scope | rounds | findings | outcome |
| :-- | :-- | --: | --: | :-- |
| `arc` registry/backlog work | Rust, one repository | 1–5 per change | 14, 13 accepted | promoted to default |
| `ai-agent-skills` hygiene | shell and manifests | 5 on one change | 10, 9 real | corroborated outside Rust; it terminates |
| `arc` backlog sweep | Rust, ten changes in one session | up to 16 on the longest | 73 recorded, ~24 more raised and fixed | probation lifted |

The third arc is what settles it, because it is the first at production scale
with adversarial briefs throughout. Ten changes went from open to integrated in
one session with Luna max as reviewer of record; the ledger holds 31 verdicts —
15 approved, 14 changes-requested, 2 comment-only — and 73 findings.

### It blocks and it stops

The mix is the signal, not the count. A reviewer that always requests changes
carries as little information as one that always approves, and this one did both
in the same session against the same author: it blocked fourteen times and it
approved fifteen, each approval at the round where the named defect was gone.

### The findings are the class a gate cannot catch

Every one of these passed a green suite before it was reported:

- A forge PR-state observation inherited across a relink, so readiness could go
  true for a pull request nobody had looked at.
- An authorization basis notarizing a gate declaration nothing had run, because
  evidence matched on a gate's *name* rather than on the command it ran.
- An asserted integration accepting any commit at all, with no check that it
  contained the work or sat on the target branch.
- A doctor command — whose entire job is reporting malformed state — failing on
  a malformed event instead of reporting it, and stopping at the first one.
- An audit diff not following a history rewrite, so the one path an auditor uses
  after a rewrite was the one path that broke on it.

### The false-approval probe, which is what probation was waiting on

A throwaway branch carried one real feature and one planted defect: a single
character turning a documented inclusive boundary exclusive, in a file the commit
message never mentions, with the full suite green and an existing test that
appeared to cover the affected flag. The brief described the feature accurately
and never pointed at the defect.

It named the plant against the repository's own documentation, and found three
unplanted defects in the carrier feature besides — including a test that passed
for the wrong reason, reproduced by deleting the code it claimed to cover.

One trial does not bound a rate, and that probe was neither blind nor unprompted.
What ends probation is not that number, it is that the failure mode has now been
looked for deliberately, at scale and under adversarial briefs, and has not
appeared.

## What it gets wrong, and the rules that follow

The faults are repeatable and cheap, which is why they are rules rather than a
reason to keep a second reviewer in the loop:

- **It asserts consequences it has not executed.** Twice in the shell arc the
  mechanism observation was right and the conclusion wrong, because a second
  check already covered the case. Severity overstated, never a finding invented.
  → **Re-run a finding's failing input before recording it.**
- **It can contradict itself across rounds.** Rounds two and three of one change
  in the sweep argued opposite sides. → **Resolve a contradiction on the merits;
  do not let round order decide it.**
- **Its strictness fixes can cost more than they buy.** It proposed making a
  contradictory record fatal to replay; the change shipped the other way — refuse
  at the write boundary, tolerate on read, report through doctor. A ledger nobody
  can reduce is a ledger nobody can repair. → **A strictness finding is a claim
  about where the guard belongs, not an instruction.**
- **It reviews exactly the range you hand it.** One reported regression was an
  artifact of diffing an unrebased branch against a moved target. → **Scope the
  brief to `<target>..HEAD`, and rebase before reviewing.**

## Two operational facts an orchestrator needs before dispatching

- **Latency is the standing cost.** 20–40 minutes on a large diff, and a failed
  run costs that before anything is known. Parse for the verdict shape you asked
  for and treat a missing verdict as an incomplete run, never as a verdict —
  exit status does not distinguish them. Budget a retry. Resolve the `fast`
  variant when a human or a merge is waiting on the answer.
- **A delegated reviewer usually cannot write the ledger.** Under
  `codex exec -s workspace-write` the Git common directory stays read-only, and
  the `exclude_git_dir` setting does not lift it, so a ledger write fails at the
  end of an otherwise complete round. Either arm the executor with write access
  before it starts, or plan for the lead to record the verdict from the report,
  keeping the reviewer's own body and findings verbatim and naming it as actor.

## What still routes to Sol

Escalation is now by exception, and the exceptions are named:

- **The verdict is on the critical path** — resolve the `fast` variant.
- **A wrong approval is expensive** — irreversible migrations, security
  boundaries, anything with an outside blast radius: resolve `high-stakes` as a
  second pass, not as a replacement.
- **Luna authored the diff.** The reviewer is never the author, and no evidence
  here touches that rule.

## The constraint this arc actually exposed

Four of the defects fixed in the sweep were the lead's own rather than an
executor's: two probes that passed with the behavior they tested removed, an
unrunnable command in a delegation scaffold, and a shell note that was wrong as
written. Reviewer tier was not the binding constraint on that session's quality;
brief and probe craft was. Promoting the reviewer does not change where the
remaining errors come from.
