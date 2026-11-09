# Model era: Fable 5.2 takes a visual seat, every tier reachable (2026-11-09 → )

Fable 5.1 sat on the roster as an explicit-only head-model candidate with no
seat. Fable 5.2 was released on 2026-11-09 at a lower price per token, and the
operator put it to work the same day on three design previews for tray, then
adopted the redesign and the identity whole. This era seats it for visual work
and retires Fable 5.1.

## The operator's direction

> make it explicit on all efforts. Medium and high are the preferred routings,
> low looks interesting but medium is a good increase for a relatively low cost
> increase, and high seems the reasonable ceiling where xhigh and max increase a
> lot in cost with diminishing returns. note those efforts observations of mine
> but keep all accessible.

> retire fable 5.1 obviously, 5.2 supercesed (and is cheaper)

## The curve

Artificial Analysis Intelligence Index v5.0.1, read on 2026-11-09 from each
tier's model page. The columns are the index, the cost per index task and the
output tokens spent on the whole index.

| Tier | Fable 5.2 | Opus 5.5 |
| :--- | :--- | :--- |
| low | 54 · $3.10 · 34.9M | 35 · $0.98 · 21.1M |
| medium | 56 · $3.80 · 41M | 48 · $2.45 · 42.5M |
| high | 62 · $9.08 · 85.3M | 52 · $3.46 · 56.1M |
| xhigh | 62 · $14.83 · 144M | 57 · $6.05 · 101M |
| max | 65 · $26.54 · 275M | 59 · $10.04 · — |

Read across, Fable 5.2 low scores above Opus 5.5 high for about the same cost,
medium sits a point under Opus xhigh for less, and high scores above Opus max
for less. Read down, medium buys two points over low for 23% more, high six more
for 2.4x, xhigh nothing for 63% more, and max three points for 2.9x with 3.2x
the output tokens. That is the shape the operator's direction describes. The
index is an aggregator scale and is recorded beside the matrix, never as pass@1;
no Datacurve row exists for either model.

## Prices

Read from Anthropic's Claude API reference on 2026-11-09: $8 input, $10
five-minute and $16 one-hour cache writes, $0.20 cache hits (0.025x), $40 output
per million; batch $4 / $20. Fable 5.1 was $10 / $50 with $0.25 cache hits.

## Seats

| Tier | Status | Route |
| :--- | :--- | :--- |
| low | explicit-only | by explicit request |
| medium | stable | `visual --variant medium` |
| high | stable | `visual`, the profile's default |
| xhigh | explicit-only | by explicit request |
| max | explicit-only | by explicit request |

`visual` is a new profile on the `claude` backend: visual and identity design,
meaning the look of an interface, mockups, palettes, marks and icons, delivered
as preview artifacts or a design spec. It is a writing shape, unlike the
read-only `design`, which keeps Opus 5.5 high for judgment on UX, copy, API
ergonomics and simplicity. Opus 5.5 also keeps the head, planning,
orchestration and copy; nothing in this direction moves those seats.

In the Anthropic pool, Fable 5.2 medium ranks 5, level with Opus 5.5 xhigh, and
high ranks 6, the top of the pool. A directed move from Opus xhigh to Fable
medium therefore reads as lateral, and to Fable high as an upgrade.

## Review tiers

Ranks and floors follow the Claude ladder as Opus 5.5 and Fable 5.1 carry it:
low and medium 1, high and xhigh 2, max 3. The index reads Fable 5.2 above
Opus 5.5 at every effort, but capability ranks here move on review evidence, not
on an aggregator score.

## Fable 5.1

Superseded and never selected. It costs more per token and never held a seat.
It leaves the Anthropic pool's served set and the `claude` backend's model
list, and keeps its row so the retirement is not relitigated.

## Quota

Unmeasured. Fable 5.1 was metered like Fable 5 and capped at half of a Max
plan's weekly allowance, which stays the working assumption for 5.2 until a
session measures it. The three design runs spent $24.09 at API prices over 246
turns.
