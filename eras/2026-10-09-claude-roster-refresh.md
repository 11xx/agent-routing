# Claude roster refresh: Haiku 5.5 takes the cheap subscription seat (2026-10-09)

Haiku 5.5 at high holds the `explore` and `extract` seats on the Claude
subscription, by operator direction, and nowhere else. The `opus` variant of
`explore` stays selectable with `--variant opus`. Two observations support the
refresh: an Artificial Analysis snapshot of all four Claude 5.x tiers, and a
field run of five read-only Haiku scouts. Neither replaces a launch-day figure;
each is recorded beside it with its evaluator and date.

## Why Claude subscription only

Haiku 5.5's list price rises five-fold for any prompt over 100k tokens, the
whole request included. A pi or OpenCode provider that bills the Claude API,
such as an `opencode-go` catalog entry, pays that surcharge and draws a paid
pool rather than the subscription the model is already covered by. Only the
`claude` backend with the `anthropic` provider routes it, and the Anthropic
pool is the only pool whose `serves` set names it.

## Price correction

[Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing),
read 2026-10-09, prices cache hits and refreshes as a multiple of base input:

| Model | Multiplier | Input $/M | Cache hit $/M | 5m cache write $/M | 1h cache write $/M | Output $/M |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Opus 5.5 | 0.05x | 4 | 0.20 | | | 20 |
| Sonnet 5.5 | 0.05x | 2 | 0.10 | 2.50 | 4 | 10 |
| Fable 5.1, Mythos 5.1 | 0.025x | 10 | 0.25 | | | 50 |
| Haiku 5.5, up to 100k prompt tokens | 0.1x | 0.10 | 0.01 | 0.125 | | 0.50 |
| Haiku 5.5, over 100k prompt tokens | 0.1x | 0.50 | 0.05 | 0.625 | | 2.50 |

The roster recorded Sonnet 5.5 at $0.20 per million cache hits, twice the
published rate. Opus 5.5, Fable 5.1 and Haiku 5.5 already matched.

## Artificial Analysis snapshot, 2026-10-08

[Slopalytics](https://slopalytics.com) republishes Artificial Analysis data;
this snapshot has `fetchedAt` 2026-10-08T02:04:01.676Z. Index is Intelligence
Index points. Cost/task is USD per index task, tokens/task are output plus
reasoning tokens, speed is output tokens per second, time is seconds per task,
and prices are list input / output per million.

| Variant | Index | Cost/task | Tokens/task | Speed | Time | In/Out $/M |
|---|---:|---:|---:|---:|---:|---|
| Haiku 5.5 low | 29.45 | 0.024 | 17286 | 178 | 62 | 0.10 / 0.50 |
| Haiku 5.5 medium | 34.46 | 0.047 | 32813 | 137 | 139 | 0.10 / 0.50 |
| Haiku 5.5 high | 37.82 | 0.079 | 55388 | 160 | 212 | 0.10 / 0.50 |
| Haiku 5.5 xhigh | 41.25 | 0.124 | 89394 | 187 | 293 | 0.10 / 0.50 |
| Haiku 5.5 max | 43.40 | 0.213 | 162164 | 242 | 426 | 0.10 / 0.50 |
| Sonnet 5.5 low | 35.87 | 0.345 | 14253 | 101 | 90 | 2 / 10 |
| Sonnet 5.5 medium | 40.84 | 0.483 | 20938 | 102 | 126 | 2 / 10 |
| Sonnet 5.5 high | 46.75 | 0.884 | 37327 | 104 | 227 | 2 / 10 |
| Sonnet 5.5 xhigh | 51.90 | 2.012 | 74810 | 107 | 428 | 2 / 10 |
| Sonnet 5.5 max | 56.00 | 5.461 | 197430 | 129 | 968 | 2 / 10 |
| Opus 5.5 low | 42.31 | 0.551 | 10151 | 79 | 82 | 4 / 20 |
| Opus 5.5 medium | 51.24 | 1.336 | 25745 | 76 | 205 | 4 / 20 |
| Opus 5.5 high | 53.58 | 1.823 | 35584 | 76 | 282 | 4 / 20 |
| Opus 5.5 xhigh | 55.99 | 3.459 | 65667 | 80 | 514 | 4 / 20 |
| Opus 5.5 max | 57.62 | 5.982 | 119166 | 95 | 784 | 4 / 20 |
| Fable 5.1 low | 46.82 | 2.371 | 21562 | 54 | 251 | 10 / 50 |
| Fable 5.1 medium | 48.92 | 2.983 | 27888 | 54 | 318 | 10 / 50 |
| Fable 5.1 high | 51.15 | 3.913 | 38054 | 58 | 408 | 10 / 50 |
| Fable 5.1 xhigh | 53.20 | 5.978 | 60538 | 58 | 635 | 10 / 50 |
| Fable 5.1 max | 53.35 | 7.630 | 78111 | 66 | 739 | 10 / 50 |

The snapshot labels the highest tier of each model without an effort suffix.
The 2026-10-07 candidate note called the Haiku row "max with fallback". The
label is unexplained in both snapshots: neither says what the fallback is or
how it affects the score, so the max rows are read as the evaluator's top tier
and no more.

### Against the launch-day figures

The launch-day figures stay where they were recorded. Where the two readings
differ, both stand, dated:

| Row | Launch day (2026-09-28 Sonnet, 2026-10-07 Haiku) | Snapshot (2026-10-08) |
| :--- | :--- | :--- |
| Sonnet 5.5 low | 36 / $0.41 | 35.87 / $0.345 |
| Sonnet 5.5 medium | 41 / $0.59 | 40.84 / $0.483 |
| Sonnet 5.5 high | 47 / $1.08 | 46.75 / $0.884 |
| Sonnet 5.5 xhigh | 52 / $2.74 | 51.90 / $2.012 |
| Sonnet 5.5 max | 56 / $7.60 | 56.00 / $5.461 |
| Haiku 5.5 xhigh | 41.25 / $0.124 | 41.25 / $0.124 |
| Haiku 5.5 max | 43.40 / $0.213 | 43.40 / $0.213 |

Sonnet's index points agree to rounding while its cost per task falls 16 to 28
percent at every tier. The snapshot gives no reason, and the launch-day
Sonnet read carried a prerelease structured-output caveat. Haiku's launch-day
read had only xhigh and max; the snapshot adds low through high, and its speed
and time. Haiku high is 37.82 at $0.079 per task, level with Luna max (38.12 at
$0.068) and just under DeepSeek V4.1 Flash max (39.46 at $0.265); those two are
2026-10-07 proxy figures, not part of this snapshot.

## Field data: five read-only Haiku 5.5 high scouts (2026-10-09)

Five read-only explore scouts at Haiku 5.5 high, through
`agent-delegate run --profile explore --backend claude`, operator-directed,
mapped one source tree for a planning lead.

| Scout | Wall time | Turns | Tool calls | Output tokens | Cache read | Cache write | API-equivalent cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| entry points | 307s | 60 | 59 | 62269 | 3225821 | 190371 | $0.381 |
| actor consumers | 253s | 53 | 52 | 45676 | 3499778 | 155911 | $0.307 |
| lookup diagnostics | 285s | 53 | 52 | 56826 | 2548767 | 163969 | $0.297 |
| cross-repo | 242s | 51 | 50 | 51005 | 2232975 | 134334 | $0.236 |
| tests and gates | 288s | 56 | 55 | 58189 | 3325507 | 145687 | $0.299 |

The API-equivalent cost is the harness's list-price calculation. These runs
drew the Claude subscription, not an API bill.

- All five completed with status 0. Each produced a 15-24 KB report with
  file:line citations.
- The lead verified every load-bearing fact before it entered a plan. Two of
  five scouts misread one validator: they claimed a value was refused, but it
  is accepted because it parses as `Name <email>`. The two scouts covering the
  same fact from other angles were right, and one CLI probe settled it.
  Overlapping lanes on a load-bearing fact catch a single misread; a fact one
  scout alone states is a lead to verify, not an established fact.
- Each scout also reported a surprise, an observation that contradicted its
  brief, and most surprises were correct. A validator runs on replay, so
  tightening it breaks reads; a lineage read error reads as "no subagent".
- Read-only Claude runs were launched in plan mode, so every report went to the
  harness's plan directory instead of the brief's path. That is a delegation
  mechanism, not a model fault.

Five scouts at $0.236 to $0.381 each come to $1.52 in list-price equivalent.
Each read 2.2 to 3.5 million cached tokens over 50 to 60 turns, so a scout's
prompts routinely grow large, which is where an API-billed route would pay the
five-fold surcharge above 100k prompt tokens.

## What stays open

- No DeepSWE row exists for Haiku 5.5; high is seated on field evidence and an
  evaluator's index, not a calibrated pass@1.
- Subscription quota weight per scout is unmeasured; the cost figures above are
  list-price equivalents.
- The 'max with fallback' label remains unexplained.

## Implementation and scout runs on the Claude subscription, 2026-10-09

With GPT routes unavailable, one lead (Opus 5.5 xhigh) ran a nine-change series across arc, agent-delegate, agent-routing, agent-harnesses and tapes on Claude models only. Each brief named exact targets, gates and file ownership, and each run committed, gated and snapshotted its own work. The lead read every diff and integrated with recorded `independent-review` debt; no independent reviewer ran, so these rows measure landing, not defect escape.

| Run | Model | Shape | Wall | Turns | Output tokens | API-equivalent | Outcome |
|---|---|---|---:|---:|---:|---:|---|
| arc placeholder refusals | Opus 5.5 xhigh | multi-area, new module, 7 write sites | 1731s | 135 | 111560 | $8.82 | all gates green at first snapshot |
| — rebase plus two same-class gaps | Opus 5.5 xhigh, warm resume | follow-up | 601s | 36 | 23821 | ~$2.93 | clean rebase, both gaps closed |
| arc lookup reasons | Opus 5.5 xhigh | multi-area, event field | 1533s | 106 | 92295 | $6.71 | all gates green at first snapshot |
| agent-delegate unfenced runs | Opus 5.5 xhigh | flag removal across 4 commands | 1362s | 102 | 96721 | $7.51 | green; flagged the downstream `--tools` consumer before it broke |
| arc trailer projection | Opus 5.5 xhigh | projection, CLI flags, advisory | 1145s | 104 | 79561 | $5.86 | green at first snapshot |
| — rebase | Opus 5.5 xhigh, warm resume | follow-up | 306s | 8 | 2461 | ~$0.49 | clean |
| agent-routing roster refresh | Sonnet 5.5 high | manifest data and prose | 227s | 29 | 21937 | $0.79 | green; correct deviations from a brief premise (no `stable` status value; pool rank shift) |
| tapes exact-lookup mismatch | Sonnet 5.5 high | single defect, 4 callers | 386s | 28 | 16828 | $0.54 | 7/7 gates; tests failed first |
| agent-harnesses Pi access | Sonnet 5.5 high | TypeScript consumer change | 109s | 10 | 9467 | $0.31 | 4/4 gates |
| arc tapes pin move | Sonnet 5.5 high | dependency pin | 487s | 33 | 13923 | $0.59 | green; found the pinned rev on no remote and a reason-bound defect the new reader exposed |
| — rebase | Sonnet 5.5 high, warm resume | follow-up | 230s | 5 | 1420 | ~$0.07 | clean |
| tapes pin-move scout | Haiku 5.5 high | read-only explore | 278s | 44 | 56145 | $0.35 | accurate API diff; flagged an unverified OpenCode schema column the pin move then checked |

"API-equivalent" is the harness's list-price calculation for a run that drew the subscription; a warm resume reports a cumulative total, so its row gives the difference. The Sonnet tasks were smaller than the Opus slices, so the cost and time gap is not a matched comparison. What it does show: Sonnet 5.5 high landed four bounded briefs on the first snapshot, each with sensible, reported deviations, and Opus 5.5 xhigh landed four multi-area slices the same way. A matched comparison (same brief, both models) is still what would move a route.

## History repair runs, 2026-10-09

The same lead then repaired placeholder trailers across thirteen repositories' histories, signed every unsigned commit, and pushed after a leak review. Sonnet 5.5 took the implementation and data work by operator direction; Haiku 5.5 high took the reading and sweep work.

| Run | Model | Shape | Wall | Turns | Output tokens | API-equivalent | Outcome |
|---|---|---|---:|---:|---:|---:|---|
| recovery maps | Sonnet 5.5 high | ledger evidence across 13 repositories into per-commit edit files | 500s | 51 | 48027 | $1.58 | 160 lines decided; spot-checked events matched; the data files were right but the report's prose miscounted one model (102 of 103 claimed as GPT-6 Sol; 14 were 6.1) |
| arc commit retention | Sonnet 5.5 xhigh | danger-path feature across rewrite, doctor, bundles and release | 1525s | 130 | 130263 | $4.99 | green at first snapshot; widened retention from pins to ledger-cited commits, a correct call the brief had not made |
| arc per-commit trailer edits | Sonnet 5.5 xhigh, warm resume | rewrite input format and applier | 771s | 37 | 60846 | ~$2.34 | green; it left the new module out of arc's danger classification, which the lead added afterwards |
| arc forge slice 2 review fixes | Sonnet 5.5 xhigh | finished an interrupted Sol fix (uncommitted partial diff) across observation identity, generation continuity and readiness tests | 1093s | 67 | 60006 | $2.04 | green; kept the partial work it judged correct, added negative controls, and chose fail-closed for typed against legacy links, documenting the choice |
| leak review, 34 slices | Haiku 5.5 high | read one ~300 KB patch slice or one repository's messages | 5-81s each, median 38s | median 10 tool calls | 205290 total | $3.73 total | no high or medium findings; low findings verified by the lead; one real subagent id found, already public |

Haiku read each slice in a few large reads, about 120-150k tokens per scout, which is why a full slice finished in under a minute. Sonnet xhigh landed two danger-path arc changes on their first snapshot. In both of its recorded slips (a miscounted summary, a missed classification) the data or code itself was right, and the lead's verification caught the slip.

## Accounting adoption runs, 2026-10-12

Three Opus 5.5 xhigh executors were finishing the work-cost accounting series (three stacked tapes changes, plus arc and agent-delegate adopting them) when they hit the Claude account's session limit. All three stopped at about 880s with a 429 `usage_limit_reached`. Each left partial work, and Sonnet 5.5 high continued it by operator direction. The lead (Opus 5.5 xhigh) reviewed every return, with Haiku 5.5 high scouts doing the censuses. The cross-lab reviewer was out of quota, so each change integrated with recorded same-family review debt.

| Run | Model | Shape | Wall | Turns | Output tokens | API-equivalent | Outcome |
|---|---|---|---:|---:|---:|---:|---|
| three executors | Opus 5.5 xhigh | tapes chain; arc and agent-delegate adoptions | 872-883s each | 65-81 | 50592-86492 | $4.31-6.32 each | all stopped by the session limit; partial work kept and handed on |
| tapes chain | Sonnet 5.5 high | commit an Opus/Sol partial unchanged, rebase a stacked change, build a new per-counter coverage design | 1578s | 125 | 65106 | $2.89 | 7/7 gates on all three; the new design was approved, with minor gaps filed. It rebased onto a sibling fixer's in-flight commits correctly |
| arc adoption | Sonnet 5.5 high | continue a half-built Opus aggregation, docs, class sweep | 486s | 57 | 32934 | $1.48 | green; approved with no findings |
| agent-delegate adoption | Sonnet 5.5 high | continue an Opus partial, Pi consumption, cross-harness totals | 1884s | 86 | 66222 | $2.25 | green, but one blocking defect: an unmeasured run of a harness with no measured session vanished from the new totals, and a test pinned the defect as healthy |
| D8 human output fix | Sonnet 5.5 high | one renderer across about 9 text sites, plus test-table hardening | 1020s | 62 | 37858 | $1.46 | resolved both findings; approved |
| arc final re-pin | Sonnet 5.5 high | replace prose-count completeness with tapes' typed reasons | 798s | 64 | 46648 | $1.71 | green; approved. It named every expectation that moved toward complete and the tapes fact behind it |
| agent-delegate fix and re-pin | Sonnet 5.5 high | blocking fix, overflow fix, typed-completeness re-pin | 1018s | 61 | 38400 | $1.43 | green; approved |
| 11 review scouts | Haiku 5.5 high | read-only censuses: derived-figure sites, reason origins, test coverage, privacy, changed expectations | 136-424s | 14-59 | 29979-88917 | $2.67 total | one scout's claim led the lead to the one blocking agent-delegate defect, and two overlapping scouts found the D8 test-table gaps; one disputed claim (an unreadable record surfacing as read-window) was checked and judged correct by design |

Sonnet high landed six continuation and fix briefs, all green, in 8-31 minutes at $1.43-2.89 each. The lead's review found one blocking defect across them, in agent-delegate. Continuing another model's uncommitted partial worked when the brief listed that model's progress notes as claims to verify. In the D8 case, the Opus notes claimed a human-output rework that the tree did not contain; the lead's read caught it, and the fix went to a Sonnet run. Haiku scouts at $0.03-0.63 each gave the lead census evidence to check each executor's class sweep against.

## Close-out runs, 2026-10-12

The same series was closed out: its todos, the `ineligible-review` debt kind across arc and agent-routing, and two pre-existing defects its sweeps found. Each run was Sonnet 5.5 high, with a lead review and integration under same-family debt.

| Run | Shape | Wall | Turns | Output tokens | API-equivalent | Outcome |
|---|---|---:|---:|---:|---:|---|
| tapes close-out, two stacked changes | coverage gaps, typed unrecognized-usage, per-reader accounting bases, per-event key amounts with a union rule | 1673s | 157 | 149184 | $5.97 | 7/7 on both. The new reason was checked against real Claude, Codex and Pi recordings with no false positives. The sweep found 3 pre-existing defects |
| arc debt kind | danger-path: a new debt kind across about 46 match sites, assessment input, audit-only discharge | 1208s | 88 | 68443 | $2.51 | green on 2,102 CLI and 362 unit tests. A reasoned deviation: verdicts never clear the kind, because they carry no assessment |
| agent-routing assess | pairwise assessment and an opt-in ineligible resolve, in Python | 195s | 22 | 20052 | $0.55 | 3/3; the sample assessments matched the decision exactly |
| agent-routing identities | additive identity list | 68s | 12 | 5217 | $0.20 | 3/3 |
| arc final pin | typed reason, audit/assessment binding | 862s | 70 | 31666 | $1.23 | green |
| agent-delegate final pin | per-harness basis rule, typed reason replacing a raw-count rule | 1023s | 39 | 19731 | $0.76 | 4/4 |
| tapes read robustness | typed reconcile failures, a local OpenCode bad row | 381s | 49 | 27083 | $1.05 | 7/7. It reported honestly the row shapes it did not cover, which were then filed |
| pool research | read-only web and bundle research | 258s | 21 | 24157 | $0.46 | answers with dated sources, and inference labelled as inference |

None of these runs drew a blocking finding from the lead. Across both 2026-10-12 rounds, 14 Sonnet high runs produced 1 blocking defect, in round one, and each run reported its own deviations. The danger-path arc change at high effort went green at its first snapshot, as the two xhigh danger-path runs recorded above did.

## The obligations-spend-assurance series, 2026-10-12

A second full series ran on Sonnet 5.5 high implementers, with Haiku 5.5 high scouts and an Opus 5.5 xhigh lead that reviewed every change. No cross-family reviewer was available, so each change integrated under `ineligible-review` debt (same family). The account hit its session limit twice. Interrupted lanes were continued by fresh Sonnet runs in the same worktrees, with the earlier run's work marked as claims to verify.

| Lane shape | Runs | Session cost | Lead findings sent back | Outcome |
|---|---:|---:|---|---|
| agent-routing `frontier`, padded families, consumer lint floor (Python) | 2 | $1.22 | count only review seats | integrated |
| arc danger-path debt work: standing, dry-run plan, `Implemented-by` in independence | 6 | $0.34–1.87 each | an unreadable range must not clear `ineligible-review`; `--expect-basis` must flag a debt the plan never saw | integrated |
| arc forge blockers: custody handles, staged export, novel-only import, frontier views, held commits, recorded-context admission | 7 | $0.15–1.93 each | classify five unclassified sources | integrated; arc pushed |
| arc features: participant cost, cost by commit with git notes, dated review assurance | 4 | $2.26–2.93 each | blame cache keyed per change, not per HEAD | integrated |
| arc Sol blocking findings in three lanes (journal, store/history, identity/output) | 3 | $0.83–3.45 each | none; one fmt-only commit folded into its parents | integrated |
| tapes child/tail identity, summary overlap B, OpenCode rows | 4 | $0.30–1.59 each | report when the copy check only sampled ids | integrated |
| agent-delegate run end at exit, pin bump, peer identity, pending-never-absence | 6 | $0.53–4.18 each | a Codex resume must degrade, not fail; timing tests must not depend on machine speed | integrated |
| arc-model re-pin (Haskell, clean room) | 1 | $5.43 | none | integrated; 0 disagreements across 1,669 differential cases |
| scouts: backlog survey, 131-finding triage, second pass, confirmation | 49 | $2.09 total | — | 69 dispositions recorded on two concurring reads |

**Totals:** 27 Sonnet sessions $45.95 and 49 Haiku sessions $2.09, all at list price. The lead's own session is excluded: the harness wrote no per-request prices for it.

**What the trial showed:**
- **Findings.** Sonnet high delivered every lane green. The lead's reads raised 10 findings, each fixed in one follow-up round. Five were in the "absent is not zero" class (an unread, sampled or unanswered fact read as complete), which the briefs named and the executors still missed at one site each.
- **Self-reporting.** Executors reported their own untested edges honestly, and three filed real design gaps instead of patching around them.
- **Lead-side cost.** Rebase conflicts between parallel arc lanes cost two lead interventions. Lint-only intermediate commits needed folding twice.
- **Report capture.** Twice a run's final message was a monitor notice rather than the report. Read the report from the run log when the final message is not it.
