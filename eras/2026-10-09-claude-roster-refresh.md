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
