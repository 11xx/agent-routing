# Model era: DeepSeek becomes generation-only (2026-08-01 → )

DeepSeek V4 Flash 0731 reached general availability on 2026-07-31 and was
briefly carried as a probationary bounded executor on the strength of its
vendor-reported score. Independent field testing published the next day moved
it off the implementation axis entirely. Both DeepSeek models are now
generators; neither implements, and neither reviews.

## Why the seat moved

The model is fast, cheap, holds a million tokens of context, and genuinely
codes better than its own preview and than many other models. None of that was
the deciding factor, because the same testing measured how it fails.

| Observation | Consequence |
| :--- | :--- |
| 84% hallucination rate on Artificial Analysis's benchmark (V4 Pro preview: 94%) | Output is a candidate, never a fact |
| Fabricated an answer on **every** run of an agentic Splunk CTF question, across max and high reasoning and temperatures 1.0 → 0.6 | Not a sampling artifact; no temperature setting buys trust |
| Once echoed the prompt's own example key as the found secret; once invented a key absent from the searched data | Plausible-looking identifiers are the failure surface |
| Ignored the first explicit instruction of a detailed plan (a dependency version pin) | **A pre-resolved brief is no protection — the brief is what it disregarded** |
| Wrote materially more code and more tests than better-scoring models while scoring worse | Volume is not effort; review cost scales against you |
| Scored below Tencent Hi3 at both efforts on a long-horizon plan-execution task — Hi3's *low* beat its *high* — reproduced across two harnesses | Not a harness artifact |

Comparable models tested the same way (Qwen3 27B, Hi3, MiniMax, Inkling) did
not fabricate on that question.

The instruction-following failure is what closed the executor question. The
delegation ladder makes cheap tiers safe by pre-resolving the brief and naming
acceptance probes, and that machinery assumes the executor reads the brief. A
model that discards the plan's first line cannot be made safe by writing a
better plan.

## What it is good for

The traits that make it a bad implementer make it a good generator. Breadth is
cheap when tokens are cheap and context is large: produce many candidates,
sweep many options, draft much more than will survive, and let a lead or
reviewer-tier model extract what holds and discard what does not. Volume with a
known-untrustworthy floor is useful precisely when something else adjudicates.

This is the same generation-versus-adjudication split already recorded for the
V4 Pro preview, which produced six real defects and two fabricated blocking
claims in one run. Generation tolerates a low floor; adjudication does not.

## Routing consequences

- The `implement:deepseek` variant was removed. A new `generate` profile
  carries the model instead — the one profile whose output is raw material
  rather than a deliverable, and the first whose base route is experimental,
  so it fails closed without an explicit opt-in.
- Never the implementer of record, never a reviewer, never a planner, never a
  default route, and never the last model to touch shipped work.
- Every claim and identifier it emits is unverified until checked against
  source, because it fabricates confidently rather than visibly.

Evidence is independent single-reviewer field testing rather than a neutral
same-harness benchmark, and is recorded as such. It agrees with the vendor's
own framing on speed and coding strength while contradicting the implication
that the scores make it trustworthy.
