# 2026-09-20 — Astra is priced, and its context cost is measured

Astra carried a row with no price from the September releases onward, because
it was announced before it was published. The vendor page now gives $10 input,
$1 cached input, $12.50 cache write, and $50 output per million, with Batch and
Flex at half and Fast at double. A published long-context surcharge above 272,000
input tokens doubles input and cache rates and applies 1.5x to output for the
whole request — but it is an API list-price term and does not reach the Codex
subscription, where measured burn is flat across that threshold.

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

On the Codex subscription that cost is linear, which is worse for a caller than
a cliff would be: there is no threshold whose crossing announces itself.
Measured burn is 0.368 points per million input tokens in the 200-272k band,
0.425 just above it, and 0.386 above 500k — flat within noise, across 1,506
clean intervals. 42.3% of Astra's requests ran above 272k and carried 66% of
all input tokens, and none of that volume cost a premium; it simply cost, every
turn, at the highest rate on the board.

Replaying the corpus under a working-context cap: a 200k cap costs 44% less and
a 120k cap 57% less, entirely from carrying less rather than from avoiding any
penalty.

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
costs 50x as much.

## What it argues for

A bound on session shape rather than on effort. Every automatic profile names a
`(model, effort)` pair, and effort is not the lever here: low, medium and high
share the multiplier and differ mainly in how often they cross the cliff. The
operator's best-measured Codex workflow — Astra plans, Luna implements — is the
shape the roster should protect, spending Astra's rate on judgment and Luna's
volume on execution against a specified plan.
