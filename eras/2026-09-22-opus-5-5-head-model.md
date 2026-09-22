# Model era: Opus 5.5 as head model (2026-09-22 → )

Opus 5.5 replaced Opus 5 on the Claude subscription and took every seat Opus 5
held: head model and default lead, the Claude implementation and review tier,
and the taste axis. It is the first head-model change made without a row of
this matrix behind it. The seat moved on vendor evidence and operator
direction, and this record states exactly how much of each there is.

## What is known

- Released 2026-09-22 as `claude-opus-5-5`: 1M context, 128k maximum output,
  five effort levels (low, medium, high, xhigh, max). The API's default effort
  is medium, one level below Opus 5's.
- $4 input / $20 output / $0.20 cache read per million, against Opus 5's
  $5 / $25 / $0.50. The vendor states about 40% less than Opus 5 on typical
  workloads, the difference coming from fewer tokens per task as well as the
  lower price.
- Reachable on the subscription: `claude -p "Reply with exactly: ok" --model
  claude-opus-5-5 --effort medium --output-format json` answered `ok`, with
  `modelUsage` naming `claude-opus-5-5`, on 2026-09-22.
- Thinking cannot be disabled at any effort, and forced `tool_choice`
  (`any` / `tool`) returns a 400. A harness route that depended on either needs
  its own probe before it is trusted on this model.

## The vendor's launch table

These are the vendor's harnesses and scales. None of them is DeepSWE pass@1,
and none is entered in the pass@1 column. The published table names no effort
per cell.

| Benchmark | Opus 5.5 | Fable 5.1 | Opus 5 | GPT-6 Astra | GPT-5.6 Sol |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Terminal-Bench 4.0 | 66.4% | 55.8% | 52.3% | 57.9% | 37.3% |
| FrontierCode v1.1 (Main) | 54.4% | 50.3% | 48.0% | 53.3% | 47.5% |
| CursorBench 4.0 | 57.8% | 51.8% | 46.6% | — | 41.7% |
| GDPval-AA v2.1 (Elo) | 1846 | 1735 | 1708 | 1542 | 1588 |
| AutomationBench | 40.0% | 31.4% | 26.9% | 41.4% | 28.8% |
| Humanity's Last Exam, with tools | 67.7% | 65.6% | 63.6% | 57.2% | — |
| Terminal-Bench-Science 0.1 | 58.7% | 52.6% | 29.0% | 64.6% | 22.4% |
| OSWorld 2.0, partial | 81.8% | 80.7% | 74.0% | — | — |
| Chartography, with tools | 89.0% | 88.4% | 83.4% | — | — |

On every row it reports, the vendor puts Opus 5.5 ahead of Opus 5 and at or
above Fable 5.1. GPT-6 Astra leads on AutomationBench and
Terminal-Bench-Science. The Datacurve DeepSWE board had no Opus 5.5 row on the
day of release.

## What is not known, and how the roster encodes it

- **No effort tier is calibrated.** Opus 5's rows showed where that model
  stopped paying: medium 69%, high 73%, and nothing above high. Whether Opus 5.5
  has the same shape is the first thing a benchmark row should settle. Until
  then, medium is the default lead tier and routing ceiling because the
  operator chose it and it is the vendor's default. High, xhigh, and max are
  explicit-only rather than prohibited, since no measurement supports a
  prohibition; none of them is an escalation tier. Low is available but not
  routed.
- **No field calibration.** Opus 5's recorded weakness is confident action on
  unverified substrate, including overriding an explicit instruction over an
  assumed environment limit. That record belongs to the Opus 5 row. It is
  neither inherited by Opus 5.5 nor refuted. The Opus 5 generational
  calibration block is removed from the doctrine, as that block required when
  the seat changed.
- **No quota ratio.** Opus 5's ~15% of a window per ~500k uncached tokens is
  the working upper bound. The vendor reports raised five-hour limits on Pro,
  Max, and Team.

## Consequences recorded with the rows

- `opus-5.5` holds the head, implementation, review, explore, and design
  routes on the `claude` backend at medium.
- `opus-5` is `superseded`. Its measured rows stay as the predecessor
  calibration that Opus 5.5 is compared against, and its xhigh and max stay
  prohibited.
- `agent-routing check` reports every unroutable status (`superseded`,
  `retired`, `deprecated`, `inactive`, `restricted`) rather than answering
  "not prohibited" for a model that must never be selected.

## Owed

A DeepSWE row at low, medium, and high, when the board publishes one. A field
arc on the head seat. A quota observation on the subscription.
