# Haiku 5.5 xhigh on a three-reader muzaiten backlog triage (2026-10-08)

Three concurrent operator-directed `claude-haiku-5-5#xhigh` Claude Code runs
classified one frozen muzaiten inventory. One owned five open Arc changes, one
owned twelve open journal todos, and one owned seven feature requests plus
sixteen handoff/plan/discussion artifacts and stray worktree context. Each
used the experimental `explore` route, a 5 GiB limit, a unique ignored report
path, and read-only task instructions. All exited 0 without an OOM, build,
tracked edit, Arc mutation, journal status change or review verdict.

| Lane | End-to-end wall | Claude API duration | First content frame | Turns | Output / thinking tokens | Reported `total_cost_usd` |
| :-- | --: | --: | --: | --: | --: | --: |
| Open Arc changes | 337.1s | 332.9s | 0.750s | 31 | 75,954 / 59,553 | $0.31199278 |
| Open todos | 472.1s | 467.5s | 0.562s | 59 | 108,129 / 78,153 | $0.46217523 |
| Requests and context | 488.8s | 478.8s | 0.648s | 62 | 107,844 / 81,888 | $0.57845984 |

The combined API-list-price-equivalent field was $1.35262785. It is not
subscription spend. The three scopes differ, so their costs and durations
are operational observations rather than a within-model speed ranking. No
Luna or DeepSeek ran the same frozen classification briefs.

The readers covered every assigned open artifact and found concrete source
facts: the radio Arc patchset was empty despite a reviewer-lane label; the
scanner Stage 1 draft missed its hard timing gate; 24 of 36 Japanese seed keys
were single-character; the journal's shipped and residual fold/radio work
needed deduplication. Their source pointers and untouched reports were kept.

The lead made material corrections before publishing an actionable list. One
reader promoted an old credential-stop handoff into a current build gate even
though the operator later resumed work and signed builds passed. Another
mistook nineteen consumed todo files for new drift and proposed replacing a
physical-route assertion with a status event, although the status only
reported endpoint availability and seven private-graph runs had passed. A
third repeated an older installation conclusion: the installed binaries were
actually byte-identical to current master. Its inference that the old fold
pause still covered every residual slice was stronger than the later broad
authorization establishes. These are lifecycle, evidence-order and boundary
errors, not omissions of assigned rows.

The sample strengthens Haiku xhigh's case for fast, partitioned read-only
reconnaissance with a lead who reconciles live state and source. It does not
make Haiku the last model to decide whether an item is ready, change a
routing seat, or prove independent-review quality. The [playlist task
trial](2026-10-08-haiku-5-5-muzaiten-field-test.md) remains the only matched
xhigh/max comparison; this swarm adds a different read-only task shape.

Evidence: muzaiten project journal
`20261008T032959Z-haiku-open-work-triage-conclusion-conclusion.md`, with
frozen input, reader reports, lead corrections, exact run metrics and
checksums in the named private evidence bundle.
