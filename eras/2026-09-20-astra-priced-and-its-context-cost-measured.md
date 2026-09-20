# 2026-09-20 — Astra is priced, and its context cost is measured

Astra carried a row with no price from the September releases onward, because
it was announced before it was published. The vendor page now gives $10 input,
$1 cached input, $12.50 cache write, and $50 output per million, with Batch and
Flex at half and Fast at double. A long-context surcharge above 272,000 input
tokens doubles input and cache rates and applies 1.5x to output, and it
reprices the whole request rather than the excess.

Against Luna that is exactly 50x on input and cached input and 41.7x on output.
The ratio is the point: Luna's token volume and Astra's are not comparable
quantities, and a comparison that sums tokens across the two inverts its own
answer.

## The cost arc

Folded from every Codex rollout on the operator's machine in which Astra served
requests: 25 sessions, 2,924 Astra requests, 768M input tokens. Per-request
token series come from each rollout's `token_count` records, attributed to the
`(model, effort)` serving them by segmenting on `turn_context` boundaries.

Astra does not manage context. It runs the widest of any model measured — 262k
billed per request against Luna's 211k and Sol's 126k — and never prunes:
growth was monotonic in every session, ending above 300k in 40% of them. The
cache hit rate is 97-98% throughout, so the waste presents as efficiency and
nothing in a session surfaces it.

The surcharge turns that into a cliff Astra sits astride. 42.3% of its requests
crossed 272k and carried 66% of all input tokens; the penalty alone was 38.1%
of the corpus bill, $618 of $1,622 at list. The share rises with effort: 16.0%
of requests over the threshold at low, 42.0% at medium, 59.4% at high.

Replaying the corpus under a working-context cap, with the cliff modelled:
a 200k cap costs 65% less and a 120k cap 73% less. Most of the win is in
staying under 272k at all.

One effort effect is worth separating from cost. `apply_patch` is 16.3% of
Astra's tool calls at low, 8.3% at medium, and 0.8% at high. Raising its effort
moves it away from writing anything, which is a reason to route it to high for
reading and judgment and not to get a change made.

## What this does not settle

Capability. No pass@1 exists for Astra and nothing here produces one; the
efficiency read on medium was formed on capability and is untouched. A cost arc
promotes no route, and Astra remains experimental with no automatic profile
naming it.

The context re-send multiplier itself is not distinctive — Luna carries the
same ~50x, and Sol, Terra and gpt-5.5 carry milder ones — so the finding is not
that Astra behaves unusually. It is that identical behaviour at 50x the rate
costs 50x as much, and that Astra's habit of running wide contexts puts it over
a threshold the cheaper tiers never reach.

## What it argues for

A bound on session shape rather than on effort. Every automatic profile names a
`(model, effort)` pair, and effort is not the lever here: low, medium and high
share the multiplier and differ mainly in how often they cross the cliff. The
operator's best-measured Codex workflow — Astra plans, Luna implements — is the
shape the roster should protect, spending Astra's rate on judgment and Luna's
volume on execution against a specified plan.
