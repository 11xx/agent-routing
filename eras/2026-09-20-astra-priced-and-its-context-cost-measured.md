# 2026-09-20 — Astra is priced, and its context cost is measured

Astra carried a row with no price from the September releases onward, because
it was announced before it was published. The vendor page now gives $10 input,
$1 cached input, $12.50 cache write, and $50 output per million, with Batch and
Flex at half and Fast at double. A published long-context surcharge above
272,000 input tokens changes the API list-price terms for direct API requests;
it is not a Codex subscription charge.

Against Luna those are published API-rate ratios: exactly 50x on input and
cached input and 41.7x on output. They do not measure subscription spend; the
Codex observations below use separate quota records.

## The cost arc

Folded from every Codex rollout on the operator's machine in which Astra served
requests: 25 sessions, 2,924 Astra requests, 768M input tokens. Per-request
token series come from each rollout's `token_count` records, attributed to the
`(model, effort)` serving them by segmenting on `turn_context` boundaries.

Astra does not manage context. In this corpus, its billed request contexts were
the widest measured — 262k per request against Luna's 211k and Sol's 126k —
and the records show no pruning: growth was monotonic in every session, ending
above 300k in 40% of them. The reported cache-hit aggregate stayed at 97-98%;
that aggregate does not identify how long any individual item remained cached
or establish an exact token lifetime.

In the Codex subscription, quota burn showed no visible discontinuity at the API
threshold in this corpus. Measured burn was 0.368 points per million input
tokens in the 200-272k band, 0.425 just above it, and 0.386 above 500k — flat
within noise, across 1,506 clean intervals. 42.3% of Astra's requests ran above
272k and carried 66% of all input tokens; the observed records show no
subscription premium for that volume. These are subscription observations, not
a repricing of API list rates, and they do not establish a general billing
rule. The API surcharge does not justify a Codex context cap.

Replaying the corpus under a working-context cap is a counterfactual simulation:
a 200k cap costs 44% less and a 120k cap 57% less in that replay, entirely from
carrying less rather than from avoiding a penalty. Those percentages are not
promises or established optima; the replay did not measure summary generation,
cache effects, re-reading, task quality, or recovery costs.

One observed tool mix is worth separating from cost. `apply_patch` is 16.3% of
Astra's tool calls at low, 8.3% at medium, and 0.8% at high. Those frequencies
describe this corpus's actions; they do not establish implementation capability,
show that high is better at reading or judgment, or justify routing high to get a
change written. No controlled Astra implementation comparison or pass@1 exists.

## What this does not settle

Capability. No pass@1 exists for Astra and nothing here produces one; the
efficiency read on medium was formed on capability and is untouched. The field
arc measures context and quota behavior, not implementation quality. A cost arc
promotes no route, and Astra remains experimental with no automatic profile
naming it.

The context re-send multiplier itself is not distinctive — Luna carries the
same ~50x, and Sol, Terra and gpt-5.5 carry milder ones — so the finding is not
that Astra behaves unusually. The 50x comparison is a published API-rate
comparison, not a claim that Astra consumes 50x the Codex subscription quota.

## What it argues for

A bounded session shape rather than an effort rule or automatic context cap.
The intended workflow is bounded Astra planning and review followed by bounded
implementation through the current `implement` profile, which resolves to Luna
max. This is a workflow description, not a capability or savings guarantee; it
does not promote Astra or add a classifier.

Whether that handoff occurs is instruction-owned: an explicit session
instruction to implement locally or not delegate overrides the default, and the
instruction layer owns recognizing that override. Routing data does not infer or
encode it.
