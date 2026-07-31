# Model era: Opus 5 as head model (2026-07-25 → )

Opus 5 replaced Opus 4.8 on the Claude subscription and took the seat Fable 5
held before its retirement. Unlike Fable, it is a normal subscription model,
so for the first time since 2026-07-12 the taste/intent/orchestration axis is
available by default rather than by exception.

## Role

- **Head model and default lead** — planning, orchestration, delegation, and
  synthesis. Every arc starts here and the final answer is owned here.
- **Taste and intent** — novel UX and copy, public API ergonomics,
  architectural taste, simplification, final user-facing review.
- **Reviewer** — the Claude-side tier of the reviewer line, and the only
  reviewer left when the Codex pool is exhausted.

## Where it lands on DeepSWE v1.1 (113 tasks, 2026-07-25)

| effort | pass@1 | $ | out tok | steps |
| :--- | :--- | :--- | :--- | :--- |
| max | 74% | 11.84 | 118k | 99 |
| xhigh | 73% | 9.07 | 92k | 89 |
| high | 73% | 6.08 | 64k | 73 |
| medium | 69% | 3.29 | 37k | 52 |
| low | 58% | 1.66 | 20k | 36 |

Opus 5 high is the strongest measured row in the roster: it beats Sol high
(69%) and Sol xhigh (71%), matches Sol max (73%) for less cash, and beats
Fable at every comparable effort for roughly a third of the price. That score
does not make it the routine route: medium delivers the Sol-high band for
roughly half the Claude-window cost and is the routing ceiling. High remains
available only when the user explicitly requests it.

**The scaling stops hard above high** — xhigh is +0 points for +49% cost and
max is +1 for +95%. Both are prohibited. This is the third time the pattern
has appeared (Fable above high, Sol above xhigh), which is why it is written as
a general rule rather than a per-model note.

## Character, where field use and benchmark disagree

The bench says Opus 5 dominates Fable outright. Field use says Fable held a
ceiling on genuinely novel hard reasoning that Opus 5, a smaller model, does
not reach. **Both are recorded, because they are not the same claim** — DeepSWE
scores bounded SWE tasks, not that ceiling. The practical consequence is
small, since no accessible model exposes it any more.

- It gains **more** from cheap workhorses than Fable did. Since the 2026-07-30
  price reset, the correct shape is decompose-and-delegate: bounded slices to
  Terra high, controlled fully pre-resolved trials to Luna high, and hard
  technical slices to Sol high or xhigh.
- Opus 5 medium is the routing ceiling. High is available but not recommended
  and is never an automatic escalation. A slice medium cannot land gets
  decomposed, given better context, or a sideways second opinion unless the
  user explicitly asks for high.
- Opus 5 low (58%) remains legitimate Claude-pool capacity when the Codex pool
  is constrained. It is not the normal delegated workhorse: Terra high carries
  that labor on the Codex pool, while Luna high remains probationary.
- Because it is the head model, it authors most planning and taste work. That
  makes the no-self-review rule load-bearing rather than ceremonial.

## Subscription quota — the measurement that anchors budgeting

Anthropic exposes no consumption meter, so the only instrument is the observed
share of a window a session of known size consumes.

| Model | Session | Share of one 5h Pro window |
| :--- | :--- | :--- |
| opus-5 | ~500k uncached tokens | ~15% (≈3.3M uncached tokens per window) |
| fable-5 | ~500k uncached tokens | ~30% (≈1.7M uncached tokens per window) |

Opus 5 does the same work for about half of Fable's quota. Both figures are
**uncached**; a cache-warm session stretches the window substantially, which
is the practical argument for one long single-context arc over repeated cold
re-derivation.

The Claude window is the scarcer of the two subscriptions and the one without
a meter, so the standing strategy is to keep the head model on judgment and
push specified labor to the Codex pool.

## Rules this era establishes

- Opus 5 medium is the default lead tier and routing ceiling. High remains
  available only by explicit user request; Opus 5 xhigh and max join Sol ultra
  and Sol max on the prohibited list.
- Subscription quota is model-weighted. On Claude this remains an observed
  ratio; on Codex it is now an explicit credit schedule. Opus 5 medium is the
  standing lead tier, while Terra high carries routine delegated work and Luna
  high receives controlled trials at much lower published Codex credit rates.
- Reviewer tiers are exactly opus-5 medium, sol high, and sol medium. When the
  Codex pool is exhausted, routine and behavior-affecting work may proceed on
  Opus 5's judgment, but a high-stakes verdict waits for the reset rather
  than being self-issued.
- Fable is retired and Opus 4.8 is superseded; neither is a fallback.

## Two futures stopped being estimates

Both remain unroutable — the OpenCode backend is still unprobed — but they now
have real rows instead of band guesses:

- **grok-4.5 high: 54% / $2.42 / 36k.** Exactly the Opus-4.8-high band the
  earlier estimate predicted, and dominated by Sol medium. Activating it would
  add a cheap second-opinion voice, not a capability tier.
- **kimi-k3 max: 69% / $4.65 / 81k.** Sol-high band — better than the earlier
  "Fable medium/high, variable" guess. The strongest inactive row, and the one
  that makes probing the OpenCode backend worth doing.
