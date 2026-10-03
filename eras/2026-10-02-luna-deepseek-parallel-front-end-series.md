# GPT-6 Luna and DeepSeek V4.1 Flash on the Arc Backlog front-end series (2026-10-02)

Ten implementation slices across four repositories: Arc Backlog in Python,
Tapes and Arc in Rust, and an agent-harnesses deployment script in Python.
Every brief was reviewed by GPT-6.1 Sol high before dispatch; Sol high also
reviewed every patchset. The lead checked each finding against source before
returning it as a bounded round.

## The round

Luna max on `opencode-go` through Pi was not a usable lane. Bare
`400 {"model":"gpt-6-luna"}` errors appeared first, followed by the
provider's upstream token rate limit. It stopped six parallel lanes, then two,
then one lane running alone, while the subscription's dollar windows remained
unspent.

Luna max on Codex was reliable, with the workspace-write sandbox limiting its
repository actions. The lead committed the resulting diffs. The sandbox also
could not bind sockets or write the system temporary directory, so the lead
ran the HTTP and temporary-directory tests outside it. Rust gates stopped on
GPG-dependent tests.

DeepSeek V4.1 Flash ran at max on `opencode-go` through Pi. Its lanes began
from a clean worktree except where it completed Luna's deploy draft.

| Slice | Implementer | Review rounds to approval | Findings that held up |
| :-- | :-- | --: | :-- |
| S1 arc report /4 | Luna (Go → Codex) | 1 | One minor test assertion |
| S4a debt rows | Luna (Go → Codex) | 1 | None |
| S2 serve | Luna (Go → Codex) | 2 | Collector launch after shutdown (partly brief-shaped), prune tie-break, weak tests |
| S6a edition tool | Luna (Codex) | 2 plus rebase check | Unicode digits in `\d`, CRLF size bypass, image in heading (three majors), weak test |
| S6b edition render | Luna (Codex) | 3 | Edition not confined to site mode (major), nanosecond precision; round two's unbounded fraction was brief-shaped |
| S0 tapes launch | Luna (Go → Codex) | One lead repair plus 2 | Lead gates found leaking fixtures and a clippy failure; Sol found four missed schema bumps and weak tests |
| S3a reader | DeepSeek (clean start) | 2 | Case-sensitive scheme check (major), weak nesting test |
| S5 deploy | DeepSeek (finished Luna's draft) | 2 | `json.dumps` surrogates (major; false premise in the brief), three minors |
| S3b reader wiring | DeepSeek | 2 | GC trusted any digest (major), three minors, a docstring |
| S8 drop Sites | DeepSeek | 1 | None |

## Observations

### DeepSeek V4.1 Flash

- Fabricated no identifier in anything the lead probed.
- Mutation-checked its regression tests against pre-fix code without being
  asked.
- Reported false premises and contradictions in briefs precisely, including a
  worktree parent directory, a test/probe conflict, and absolute paths for
  Firefox.
- Committed in clean per-finding slices.
- Reported measured overflow widths and counts instead of unsupported claims.

### GPT-6 Luna on Codex

- Correct and literal.
- Its blind spots were whole-suite effects: fixtures placed in shared test
  roots, a clippy limit, and a schema family it did not enumerate. The Codex
  sandbox hid these because its gates stopped early.

### GPT-6.1 Sol high as reviewer

- Every finding checked out against source, except a trailer rule it applied
  too literally three times.
- Its re-reviews were fast and exact.
