# Model era: MiMo V2.6 enters on probation, Flash to be benchmarked (2026-09-22 → )

Two rows entered the roster together: Xiaomi MiMo V2.6 Flash and MiMo V2.6
Pro. Neither is measured anywhere on this matrix — no pass@1 row, no field
arc, no review round, no confirmed approval — so both enter as experimental
rows with a probationary tier, the footing `deepseek-flash` holds, and
neither is resolved by a profile. The operator's call is recorded alongside
them: **Flash is the row to try and benchmark going forward**, and Pro is
carried because it is similar to Flash and a little better on that same read.

## What the entry rests on

The two facts a roster row may carry without a measurement are availability
and price, and both were probed rather than quoted:

| Observation | Source |
| :--- | :--- |
| `mimo-v2.6-flash` answers through pi on `opencode-go` and bills at list (1,430 input tokens for $0.0002) | live probe, pi 0.87.0, `--provider opencode-go --model mimo-v2.6-flash --thinking max` |
| `mimo-v2.6-pro` answers the same way and bills at its own list rate ($0.00063 for the same prompt shape) | live probe, same session |
| Flash lists at 0.14 input / 0.28 output / 0.0028 cached per million; Pro at 0.435 / 0.87 / 0.0036 | provider catalog on `opencode-go`, corroborated by `openrouter` at identical rates |
| Both carry a 1.0M-token context and 131k maximum output on `opencode-go` and `openrouter` | provider catalog |
| pi's catalog maps no thinking levels for either model, and both reason anyway | provider catalog plus observed reasoning tokens in the probe replies |

The effort lever is the reason the rows declare a single `high` tier rather
than the ladder other rows carry. pi drops `xhigh` and `max` for a model whose
definition maps no levels and clamps a requested `max` to `high` without
reporting it, and a probe that asked for `off` and then `high` on the same
trivial prompt got the same reasoning-token count back. The declared tier
therefore names the level pi sends, not a lever anyone has watched move
anything; calibrating it is trial work, not entry work.

## Why no route was added

A roster row and a route are separate decisions, and only the first was made
here. The path to either model is an operator-directed selection —

`agent-routing validate --profile <shape> --backend pi --model
mimo-v2.6-flash --effort high --provider opencode-go --reason <text>
--allow-experimental`

— which records the execution shape, model, effort, pool, and reason against
the route version, so a trial's result is later read against the exact
selection that produced it. Three facts make that the right shape rather than
a profile variant:

- **Nothing is measured.** A profile is a standing default, and a standing
  default needs the field record this pair does not have. `deepseek-flash`
  earned its `generate` profile from a fabrication record plus two field
  arcs; MiMo has neither evidence nor verdict.
- **The pool is conditional.** The Go subscription is an optional,
  dollar-metered plan whose availability no manifest can observe. A model
  carried as a standing route on a payment state nothing degrades out of is a
  route that fails on a calendar event.
- **The selection is the trial record.** Probation ends on an arc, and the
  arc has to be attributable to a deliberate selection rather than to
  whatever a profile happened to resolve.

## Pools and siblings, as recorded

`opencode-go` is the routed pool: its `serves` set now names both rows, and
pi's backend contract names the invocation. The GOAT catalog also lists both
at zero marginal cost, but GOAT's closed set is Luna and GLM 5.3 Flash — a
pool is a capacity decision, not a price list, so widening it is a separate
operator act. `openrouter` carries both at list; it is a provider no pool
declares, and an undeclared pool is a refusal rather than an inference.

Three relatives exist and are not carried: `mimo-v2.6-pro-ultraspeed` at ten
times the list price, the free `mimo-v2.6-flash-free` tier on the `opencode`
provider (a 200k context and 32k output — smaller capacity, not a cheaper
price on the routed row), and the earlier V2.5 pair.

The Flash/Pro preference is the operator's and is recorded as a preference.
Nothing here measures the gap between them; Pro costs about three times
Flash's input and twice its output, and until a trial measures the pair the
roster can rank them only by price.

## What this pass deliberately leaves

- No pass@1 row, no field arc, no review round, and no approval for either
  model. Every column that would move a seat out of probation is empty, on
  purpose.
- No profile, no variant, and no default anywhere. Both rows are reached by
  naming them.
- The effort lever uncalibrated: one `high` tier, declared as the level pi
  sends. A trial that wants to know whether the lever matters is a trial,
  and its result belongs on the row.
- GOAT and `openrouter` unrouted, and the ultraspeed and free variants
  uncatalogued as capacities. Each is a pool or price decision of its own.

## Field observation: wall-clock latency (2026-09-22, the same day)

The operator's read on Flash was blunt — it is slow, and slow is what counts
when several harnesses queue on one slot — so it was measured rather than
agreed with, then re-measured when a preference question turned on it.
Identical prompts, one machine, `--thinking high` on both MiMo rows,
`max` on deepseek-flash.

One 60-item formatting prompt, run three times per row:

| run | mimo-v2.6-flash | mimo-v2.6-pro | deepseek-flash | gpt-5.6-luna low | gpt-5.6-luna max |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 763.6s · 40,310 reasoning tokens | 33.5s · 1,007 | 33.6s · 7,960 | 17.9s · 67 | capped 240s, unfinished |
| 2 | 153.4s · 7,269 (†) | killed at the 20-min cap mid-reasoning, ~29k thinking tokens streamed (†) | 57.3s · 922 | — | capped 300s, unfinished |
| 3 | 17.5s · 67 | 131.6s · 5,029 | — | — | — |

(†) run 2 of the two MiMo rows ran concurrently; the rest ran sequentially.

Smaller cells, one to two runs each: trivial "reply ok" — flash 1.83s and
2.05s, pro 10.15s, deepseek 1.14s. 20-item HTTP list — flash 4.4s / 292
tokens, deepseek 3.0s / 639. Small file-write task with doctests — flash
25.9s, pro 31.8s. Observed decode rate: ~50–66 tok/s (flash), ~49.6 (pro),
~213–264 (deepseek).

Three facts fall out, and they route differently.

**The blowup is reasoning volume at slow decode, not provider queueing.**
The token rate held near 54 tok/s through the 763.6s run while the row
emitted 40,310 reasoning tokens to format a list. The same prompt shape
answered in 17.5s on another run, so a queue sized on the median meets the
tail instead.

**The tail is the pair's, not Flash's.** Two of three runs blew up on each
MiMo row, and Pro's worst — still streaming at the twenty-minute cap —
outlasted Flash's worst. Paying Pro's ~3x price buys no measured speed;
between the two rows the tie-breaker is capability, which is unmeasured on
both. The operator's preference is therefore open rather than settled: Flash
was the designated benchmark subject at entry, and the operator expects to
try Pro more after the latency question — for capability reasons, since the
latency premise the preference rested on is not supported.

**The tail follows the effort lever as much as the model.** Luna low finished
the prompt in 17.9s where luna max did not finish within five minutes on two
capped runs — the same asymmetry the roster already records as Luna's effort
cliff, arriving here as wall-clock rather than pass@1.

The session that filed these rows is the field half of the same
observation: created 13:33:54Z, first roster commit 14:03:21Z — 29.4
minutes for one bounded two-row entry, of which at least 25.3 minutes was
Flash generating across 50 assistant turns, with tool execution across the
whole span well under a minute. Across all 71 assistant turns of the
session: median 19.8s, mean 29.3s, ninetieth percentile 61.2s, worst 147.9s,
and 75% of the session's output tokens were reasoning (75,944 of 101,804).
Cash was never the axis: the whole session billed $0.2402 on Flash, and the
same token mix at Pro's list prices computes to $0.3862 — fifteen cents
against a wall-clock spread of twenty minutes.

Consequences recorded with the rows: latency joins price in `[policy]`, each
MiMo tier `use` says to run it where the queue behind the slot is empty, and
both rows carry their own measured latency cells.

Limitations, so the numbers are read at their weight:

- One machine, one day, three runs per MiMo cell and one or two per other.
  Queue position and cache state at each call were not controlled, and one
  run pair (†) was concurrent.
- Luna max did not complete the prompt inside 240s and 300s caps, with zero
  observable output — pi buffers to completion — so that cell records a
  non-completion, not a mechanism. Whether it was reasoning volume or a
  transport stall is unmeasured; luna low on the same prompt took 17.9s.
- The Codex-side comparator arrived late: the Codex OAuth token had been
  invalidated earlier in the day (`refresh_token_invalidated`) and was
  re-authenticated by the operator before the Luna cells could run.
- The interactive figures come from the session's own message timestamps;
  the probe figures are separate single calls outside it.
