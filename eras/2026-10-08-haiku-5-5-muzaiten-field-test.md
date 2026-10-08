# Haiku 5.5 xhigh and max on one playlist-import draft (2026-10-07)

An operator-directed first field test ran `claude-haiku-5-5` through Claude Code
at xhigh and max. Both arms received the same frozen, uncommitted muzaiten
playlist-import draft, signed base, brief, synthetic fixtures and 8 GiB memory
limit in separate worktrees. They ran sequentially and could not see each
other's result. The route was experimental and explicit; no profile selected
Haiku. A preceding xhigh pilot at 4 GiB was killed by a kernel-confirmed
memory-cgroup OOM while `clangd.main` consumed about 3.26 GiB. That pilot is
resource-failure evidence, not a model-quality sample.

| Observed measure | xhigh, 8 GiB | max, 8 GiB |
| :-- | --: | --: |
| End-to-end wall time | 29m19s | 48m27s |
| Claude-reported API duration | 18m25s | 23m32s |
| First content frame | 1.856s | 1.171s |
| Turns | 138 | 132 |
| Output tokens, including thinking | 199,040 / 123,969 | 329,670 / 247,656 |
| Cache-read input tokens | 19,993,841 | 26,732,932 |
| Claude-reported `total_cost_usd` | $1.63130909 | $2.45947088 |

The dollar fields are API-list-price equivalents reported by Claude Code, not
observed subscription spend. The supervisor's `first-output` event was
buffered until exit, so the native first-content-frame fields are the useful
startup observations. In this pair, max took 1.65 times the wall time, 1.28
times the API duration, twice the thinking tokens and 1.51 times the reported
cost. Compilation, cache order and exploratory paths differed; these ratios
are not an isolated effort-level effect.

Both arms found the draft test's `QTRY_VERIFY(tryAcquire())` error: the macro
re-evaluated and consumed a semaphore permit, producing seven false failures.
Both repaired it and passed their focused parser/dialog gates without compiler
warnings. Xhigh also preallocated preview rows and deferred status-column
resizing. In its synthetic 10k plain-match probe the largest GUI gap fell from
22,965 ms in the draft to 6 ms. Its additional edge and picker probes found
a remaining 4,071 ms picker-row gap, a 14,274 ms teardown, and two
entry-count differences among 24 edge fixtures. The lead inspected and
transferred the bounded preview/test edit into the still-open owning draft;
that dirty worktree passed its full local build and 82/82 tests. The playlist
feature was not integrated.

Max made no product-source edit. It measured a distinct option: attaching a
worker-produced `QTextDocument` with a GUI-side plain-text layout took 25 to
55 ms at 100k entries, compared with 174 to 384 ms for `setPlainText`, with
matching canonical text on four synthetic formats. Its first attachment
probe silently attached nothing because the document lacked
`QPlainTextDocumentLayout`; it corrected the probe and left the option for a
later product-contract decision. It did not run xhigh's 24 edge fixtures or
picker teardown probe. Both arms reported that the 100k editor stall and
picker behavior remain unresolved.

This is one matched xhigh-versus-max task, not a matched comparison against
Luna or DeepSeek. Their muzaiten lanes used different code, build costs and
acceptance boundaries. The field result supports Haiku as an explicit
exploratory or bounded executor with lead review; it does not warrant a new
default or review seat. Medium and high were not tested, quota weight was not
measured, and no independent review approved the unfinished playlist feature.

Evidence: muzaiten project journal
`20261007T223502Z-haiku-55-first-field-test-conclusion.md` and
`20261007T223448Z-playlist-import-haiku-field-handoff-handoff.md`, with the
frozen input, run reports, failed pilot, sources and checksums in their named
private evidence bundles.

## Historical lead provenance

Recorded model contexts establish the lead who inspected and transferred the
playlist edits as GPT-6 Sol xhigh. The intended GPT-6.1 model was not active
for that work. The lead's inspection is not an independent GPT-6.1 review;
the unfinished draft retains its acceptance holds. A later GPT-6.1 Sol xhigh
and Opus xhigh retrospective audit identified additional draft correctness
and lifetime findings, which remain separate from the measured effort trial.
