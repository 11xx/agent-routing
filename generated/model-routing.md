<!-- GENERATED from routing/models.toml in ai-agent-routing.
     Regenerate with `agent-routing gen`; never hand-patch this file. -->

## Model Routing & Delegation

Standing defaults for complementary Claude and Codex orchestration. **Opus 5 is the head model** — it plans, orchestrates, delegates, and owns the final answer — and Sol is the technical peer and execution axis beneath it. Delegation uses the other subscription where its model or quota is a better fit. Only models normally available on the active subscriptions are routed. Availability history remains in `~/code/ai-agent-routing/eras/`.

### Glossary

- **Intelligence:** how complex a problem the model completes correctly, unsupervised.
- **Taste:** cleanliness of UI/UX, architectural code quality, API design, copy.

### Model matrix (deepswe v1.1, 113 tasks; roster measured 2026-07-25, deepseek-v4-pro added 2026-07-27: pass@1 / avg USD per task; out_tokens and steps recorded where they change a routing call)

| Model · effort | pass@1 | $ | out | Use |
| :--- | :--- | :--- | :--- | :--- |
| opus-5 · max | 74% | 11.84 | 118k | **prohibited: never select, including by explicit request. +1 point over high for +95% cost and 1.8x the output tokens, against a tier that already tops the roster** |
| opus-5 · xhigh | 73% | 9.07 | 92k | **prohibited: never select, including by explicit request. Identical pass@1 to high for +49% cost and 1.4x the tokens — it buys nothing measurable** |
| opus-5 · high | 73% | 6.08 | 64k | default lead tier and the roster ceiling: plan, orchestrate, delegate, synthesize, review. Nothing available scores higher, so a hard slice gets decomposed or given more context, never escalated upward |
| opus-5 · medium | 69% | 3.29 | 37k | quota-conscious lead tier: matches sol high's pass@1 at half the output tokens of opus-5 high. Use for routine leading and long sessions where the Claude window is the binding constraint |
| opus-5 · low | 58% | 1.66 | 20k | not a workhorse tier: dominated by sol medium (61% at $1.86) on both score and cash. Reach for it only when the codex pool is exhausted and Claude-side labor is the only option |
| gpt-5.6-sol · max | 73% | 8.39 | 60k | **prohibited: +2 points over xhigh for +78% cost, and opus-5 high matches it for less** |
| gpt-5.6-sol · xhigh | 71% | 4.70 | 41k | sol ceiling: the hardest delegated technical slice, or a rerun after high missed; not the default |
| gpt-5.6-sol · high | 69% | 3.47 | 28k | technical lead tier and the best pass@1-per-token row on the board: judgment-involving implementation, deep dives, adversarial review, whole-arc runs the head model delegates wholesale |
| gpt-5.6-sol · medium | 61% | 1.86 | 18k | escalation after low misses or when a planned slice retains limited implementation judgment; also the read-only review skim tier, and it dominates opus-5 low on both score and cash |
| gpt-5.6-sol · low | 45% | 1.07 | 11k | the delegated implementation workhorse, and the primary way an opus-5 head buys leverage: clear-spec slices, quick repo/system changes under observation, lookups, and assigned-worker tasks; never broad judgment, novel design, or underspecified changes |
| gpt-5.6-sol · ultra | — | — | — | **prohibited: never select, including by explicit request** |
| gpt-5.6-terra · high | 54% | 1.13 | — | explicit fallback only; not an ambient planned-slice or quota-window default |
| gpt-5.6-terra · xhigh | 60% | 2.13 | — | explicit Terra request needing more; upper effort scales, but remains outside normal routing |
| gpt-5.6-terra · max | 70% | 4.95 | — | explicit Terra ceiling only |
| gpt-5.6-luna · max | 67% | 3.03 | 73k | competent but inefficient: 2 points below sol high for less cash yet 2.6x the output tokens and 2.8x the steps. On the shared codex subscription that trade is probably bad, since quota is tokens rather than dollars; select only when paying API cash and latency does not matter |
| gpt-5.6-luna · xhigh | 57% | 1.54 | 45k | cheapest row above 50%; still token-hungry against sol medium (61% at 18k out). Explicit cash-constrained fan-outs only |
| gpt-5.6-luna · high | 44% | 0.78 | 26k | roughly sol low's score at 70% of the price but 2.4x the tokens; not an ambient substitute for the workhorse |
| gpt-5.6-luna · medium | 11% | 0.22 | 8.2k | bounded function-shaped calls only: classify, extract, aggregate, summarize one thing. The cliff disqualifies agentic or multi-file coding |
| gpt-5.6-luna · low | 2% | 0.07 | 3.1k | bounded function-shaped calls only |
| sonnet-5 | — | — | — | dominated and token-hungry; only as low-effort proxy shells (codex and pi agent types) |
| opus-4.8 | — | — | — | replaced by opus-5 on 2026-07-25 across every role it held; never select. Opus 5 beats it by 21 points at high (73% vs 52%) for $6.08 against $4.28, and its max tier (59%) loses to opus-5 low plus a delegate. |
| fable-5 | — | — | — | no subscription route: reachable only by direct credit billing, at a cost the user has ruled prohibitive. Never route to it, never offer it as an escalation, and do not treat 'still accessible' as available. opus-5 holds the taste/intent/orchestration seat it used to. |
| gpt-5.5 | — | — | — | every tier dominated by a cheaper 5.6 tier; never select |
| grok-4.5 | — | — | — | benchmarked but unreachable: no probed backend. high scores 54% at $2.42 / 36k out — the opus-4.8-high band the earlier estimate predicted, and dominated by sol medium (61% at $1.86). Activating it would add a cheap second-opinion voice, not a new capability tier |
| kimi-k3 | — | — | — | benchmarked but unreachable: no probed backend. max scores 69% at $4.65 / 81k out — sol-high band for more cash and 2.9x the tokens, better than the earlier variable-Fable-band guess. The strongest inactive row, and the one worth probing the OpenCode backend for |
| small-model-class | — | — | — | never for anything that ships. The class is no longer uniformly weak — gemini-3.6-flash high reaches 49% — but every row is dominated by a cheaper or better 5.6 tier, and the fast-and-cheap ones (kimi-k2.7-code 31%, glm-5.2 high 36%, gemini-3.1-pro 12%) are far below the floor for delegated work |
| deepseek-v4-pro · max | 8% | — | — | only as a briefed defect generator whose every finding a lead verifies against source before acting. Never the independent reviewer of record, never an implementer, never a planner |

Opus 5 replaced Opus 4.8 on 2026-07-25 and took the head-model seat Fable 5 held; Fable 5 is fully retired (credits-only direct billing, no subscription route). History in eras/

### Roles, character, and known weaknesses

**opus-5** — primary lead and default head model: planning, orchestration, taste, inferred intent, novel UX/copy, API and architectural ergonomics, simplification, and user-facing review; synthesizes delegated work and owns the final answer

  tops the roster: high beats every Sol tier including sol max, and beats Fable at every comparable effort for a fraction of the cost. Field evidence adds one thing the benchmark does not measure — it is a smaller model than Fable and lacks Fable's ceiling on genuinely novel hard reasoning. Both readings are true; deepswe measures bounded SWE tasks, not that ceiling. It gains more from cheap workhorses than Fable did, so decompose-and-delegate is how it earns its cost.
  - Weakness: stops scaling above high, harder than any other family: xhigh buys 0 points for +49% cost and max buys 1 point for +95%. Both are prohibited; high is the hard ceiling
  - Weakness: as head model it authors most planning and taste work, so the reviewer line matters more, not less: never let it review its own diff
  - Weakness: token-hungry relative to Sol at the same pass@1 (high: 64k out vs sol high 28k) — on the metered-free Claude subscription that is quota, so route specified labor to the codex pool

**gpt-5.6-sol** — technical peer and execution axis under an opus-5 head: correctness, feasibility, failure modes, deep technical dives, adversarial review, and long autonomous implementation arcs. The most token-efficient family on the board at every tier, which is why delegated labor lives here
  - Weakness: overbuild: state scope ceilings and 'no tests/refactors beyond those listed'
  - Weakness: over-determination: name exact targets, stop when they are absent, give explicit abort conditions, and prefer sandboxes for risky access; applies at low too

**gpt-5.6-terra** *(fallback)* — superseded by sol low as the planned-work default; select only by explicit request or for a concrete compatibility or availability reason

**gpt-5.6-luna** — cheapest family, with the steepest effort curve on the board: unusable at low/medium, competent at xhigh/max. Default use remains fixed-input/fixed-output workflow calls at low/medium; the upper tiers are a real budget option but lose to sol on tokens and steps

**sonnet-5** *(restricted)* — dominated and token-hungry; only as low-effort proxy shells (codex and pi agent types)

**opus-4.8** *(superseded)* — replaced by opus-5 on 2026-07-25 across every role it held; never select. Opus 5 beats it by 21 points at high (73% vs 52%) for $6.08 against $4.28, and its max tier (59%) loses to opus-5 low plus a delegate.

**fable-5** *(retired)* — no subscription route: reachable only by direct credit billing, at a cost the user has ruled prohibitive. Never route to it, never offer it as an escalation, and do not treat 'still accessible' as available. opus-5 holds the taste/intent/orchestration seat it used to.
  - Note: kept as a row so its retirement is not relitigated. Retirement costs nothing on the benchmark: opus-5 beats fable at every comparable effort (73% vs 69% high, 74% vs 70% max) for roughly a third of the cash and half the subscription quota. The user's field read that Fable held a ceiling on genuinely novel hard reasoning is not contradicted by this — deepswe measures bounded SWE tasks, not that ceiling — but no accessible model exposes it any more.

**gpt-5.5** *(deprecated)* — every tier dominated by a cheaper 5.6 tier; never select

**grok-4.5** *(inactive)* — benchmarked but unreachable: no probed backend. high scores 54% at $2.42 / 36k out — the opus-4.8-high band the earlier estimate predicted, and dominated by sol medium (61% at $1.86). Activating it would add a cheap second-opinion voice, not a new capability tier

**kimi-k3** *(inactive)* — benchmarked but unreachable: no probed backend. max scores 69% at $4.65 / 81k out — sol-high band for more cash and 2.9x the tokens, better than the earlier variable-Fable-band guess. The strongest inactive row, and the one worth probing the OpenCode backend for

**small-model-class** *(restricted)* — never for anything that ships. The class is no longer uniformly weak — gemini-3.6-flash high reaches 49% — but every row is dominated by a cheaper or better 5.6 tier, and the fast-and-cheap ones (kimi-k2.7-code 31%, glm-5.2 high 36%, gemini-3.1-pro 12%) are far below the floor for delegated work

**deepseek-v4-pro** *(restricted)* — candidate generator under a brief, never an adjudicator. Reachable through the pi backend on a deepseek login whose quota is independent of the codex pool, which is the only reason to reach for it: it is the reviewer of last resort when codex is exhausted and opus-5 would otherwise be reviewing its own diff

  far below the floor on autonomous work — 8% pass@1 places it under luna low/medium, not near sonnet — yet under an adversarial review brief it produced six real defects across eight changes that a neutral 'review this' ask from the same model missed entirely. The value came from the brief and from a lead who checked every claim, not from the model. Field-measured 2026-07-27
  - Weakness: writes confident, well-argued, entirely false findings: two of eight blocking claims in the measured run described an artifact of a malformed diff rather than the branch, with full failure scenarios attached
  - Weakness: cannot be trusted to notice that its input is wrong, which is the failure a peer-grade reviewer catches first
  - Weakness: recording its verdict through `--on-behalf-of` over-credits, because arc's `--model` field records the invoker's model and there is no field for the subject's
  - Note: cost per task on this benchmark is unmeasured here; published output pricing is cheap but that was not the deciding factor

### Subscription quota (measured, not inferred from API price)

- **method:** observed share of one rolling window consumed by a session of known token count
- **claude plan:** Pro $20, 5h rolling window
- **claude opus 5:** ~500k uncached tokens ~= 15% of one window, so roughly 3.3M uncached tokens per window
- **claude fable 5:** ~500k uncached tokens ~= 30% of one window when it was still on the subscription: opus-5 does the same work for about half the quota
- **caching:** these are UNCACHED figures; a cache-warm session stretches the window substantially, which is why long single-context arcs beat repeated cold re-derivation
- **codex pool:** chatgpt-codex subscription, shared by sol, terra, luna, and both the codex and pi backends; weighting per model is unmeasured, so never assume terra or luna conserves quota

### Routing rules

- **effort cliff:** the 5.6 family degrades steeply on agentic work at low effort; sol low is the field-tested exception for tightly scoped pre-resolved execution under an orchestrator, and luna low/medium remains the exception for bounded function-shaped calls. Luna's curve is the steepest on the board (2% low to 67% max), so never generalize a luna tier's behavior from another
- **non scaling tops:** every family stops paying before its top tier, so 'tops the bench' is never a reason to select one. opus-5 above high: +0 points at xhigh for +49%, +1 at max for +95%. sol above xhigh: +2 points at max for +78%. fable above high: <=1 point for 1.5-2.4x. Hard ceilings are opus-5 high and sol xhigh; everything above them is prohibited
- **prohibited:** never select, including on explicit request: opus-5 xhigh, opus-5 max, sol ultra, sol max. Hard ceilings are opus-5 high and sol xhigh
- **delegation effort:** priced by residual risk after the gate, not by handoff ambiguity: sol low is the default when the brief is source-verified and bounded AND the lead can name a final-head command whose outcome discriminates each material risk. Escalate to medium or high when the brief still leaves an architecture, API, or semantic choice to the executor, or when no such discriminating command exists. xhigh is the hard Sol ceiling; Sol ultra and max are prohibited; terra is explicit fallback only. Migrations, schema/breaking changes, destructive operations, and security keep the high-stakes floor regardless of how well specified they are
- **acceptance probes:** the mechanism that makes the floor safe: every brief delegated to a low tier names acceptance probes as runnable commands, and the executor records each at the final head with `arc verify --command` so the evidence lands in the ledger. Loudness is constructed by the lead, not bought with a higher tier — naming a probe requires knowing the required behavior, not predicting the executor's mistake. Caveat to state rather than gloss: readiness consults declared gates only, so ad hoc probe evidence never gates and never turns green; the convention is reviewer-enforced, and a reviewer who assumes the tool is checking will stop checking
- **floor failure response:** pre-registered so the reflex does not decide it: if a low-authored semantic defect passes its named probe and first review, or two of THE NEXT SIX low changes need extra verdict rounds for executor-caused defects, the remedy is to make acceptance probes declarable so they gate — NOT to buy a higher tier. An absent or non-discriminating probe is a machinery gap; escalation is the fallback only if declarable probes exist and the defect recurs anyway. The cohort is the next six, fixed at adoption, not a rolling window
- **floor measurement:** the trigger above is only evaluable if the data is recorded: each delegated change records which tier implemented it, and every review round is classified brief-caused, executor-caused, or integration-staleness. Only executor-caused rounds count against the floor. This is observational, not a controlled experiment — cause is not a structured verdict field and there is no high-tier counterfactual
- **head model:** opus-5 high leads: it plans, orchestrates, delegates, and synthesizes. It is also the roster ceiling — nothing accessible scores higher — so there is no escalation path above it. A slice it cannot land gets decomposed, better context, or a sideways second opinion from sol high, never a higher effort tier. Its leverage comes from spending sol low on specified labor rather than doing that labor itself
- **quota window:** the Claude window is the scarcer of the two and has no meter: keep the head model on judgment and push specified labor to the codex pool. Subscription quota is output tokens, not dollars, and opus-5 high spends 64k per task against sol high's 28k for the same class of result — so the cash column understates how much a Claude-side tier costs the window. Drop to opus-5 medium (37k out, same pass@1 as sol high) for routine leading in a long session. Start assigned implementation on sol low; Sol ultra and max are prohibited; fast mode is deliberate, never ambient
- **user facing:** opus-5 writes or reviews novel user-facing work: UX, copy, API shape, and final polish. Sol may implement against an already-settled design system, but novel design and final polish stay on the Claude taste axis
- **review generation:** defect generation and defect adjudication are separable and priced differently. Generation can run on a model far below the reviewer floor if it is given an adversarial brief — one that names the failure mode gates cannot catch, enumerates the defect classes to sweep, and refuses a bare 'no issues' by requiring each ruled-out class to name the file and reasoning. Adjudication cannot: every finding from a sub-floor generator is a candidate until a reviewer-tier model or the lead confirms it against source. Measured 2026-07-27: deepseek-v4-pro at 8% pass@1 produced six confirmed defects and two fully fabricated blocking claims in the same run. This does not add a reviewer tier and does not change who may issue a verdict
- **review:** the verdict never comes from the model that authored the diff; reviewer tiers are exactly opus-5 high, sol high, and sol medium (sol low never reviews; sol xhigh authors, it does not review). opus-5-authored work: routine/docs none, behavior-affecting a sol medium read-only skim, high-stakes (migrations, schema/breaking, destructive, security) sol high mandatory. sol-authored work: opus-5 as lead reviews the diff, high-stakes adds a second sol high pass. When codex quota is exhausted, opus-5 high is the only reviewer left and a high-stakes verdict waits for the reset rather than being self-issued. Inactive futures grok-4.5 and kimi-k3 join the line only when activated

These are **defaults, not limits**, except where a model or effort is explicitly prohibited. Judge output rather than rank alone. Machine-readable form of this matrix and the delegation mechanism rules: run `agent-routing models` / `agent-routing delegation` (no path needed). Mechanism-routing prose canon: `agent-routing mechanism`. Never route work through harness-native subagent defaults; invoke executors explicitly with stated model, effort, and a curated brief.

