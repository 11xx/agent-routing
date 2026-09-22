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
