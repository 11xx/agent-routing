## Model Routing & Delegation

Standing defaults for complementary Claude and Codex orchestration. **Opus 5
is the head model** — it plans, orchestrates, delegates, and owns the final
answer — and Sol is the technical peer and execution axis beneath it.
Delegation uses the other subscription where its model or quota is a better
fit. Only models normally available on the active subscriptions are routed.
Availability history remains in
`agent-routing eras`.

### Glossary

- **Intelligence:** how complex a problem the model completes correctly, unsupervised.
- **Taste:** cleanliness of UI/UX, architectural code quality, API design, copy.

### Model matrix (DeepSWE v1.1, 113 tasks, 2026-07-25: pass@1 / avg $ / output tokens)

| Model · effort | pass@1 | $ | out | Role |
| :--- | :--- | :--- | :--- | :--- |
| opus-5 · high | 73% | 6.08 | 64k | **Head model, default lead, and the roster ceiling.** Planning, orchestration, taste, inferred intent, novel UX/copy, API and architectural ergonomics, simplification, user-facing review; synthesizes delegated work. Nothing accessible scores higher, so its leverage is delegation — spend sol low on specified labor instead of doing it here. |
| opus-5 · medium | 69% | 3.29 | 37k | **Quota-conscious lead tier.** Matches Sol high's pass@1 at 58% of Opus 5 high's output tokens. Use for routine leading and long sessions where the Claude window binds. |
| opus-5 · low | 58% | 1.66 | 20k | Not a workhorse tier — dominated by Sol medium on both score and cash. Only when the Codex pool is exhausted. |
| opus-5 · xhigh / max | 73–74% | 9.07–11.84 | 92–118k | **Prohibited.** Never select either, including on explicit request: xhigh buys 0 points for +49% cost, max buys 1 point for +95%. |
| gpt-5.6-sol · xhigh | 71% | 4.70 | 41k | Sol ceiling: the hardest delegated technical slice, or a rerun after high missed. |
| gpt-5.6-sol · high | 69% | 3.47 | 28k | **Technical lead tier, and the best pass@1-per-token row on the board.** Correctness, feasibility, failure modes, deep dives, judgment-involving implementation, adversarial review; carries whole arcs delegated wholesale. |
| gpt-5.6-sol · medium | 61% | 1.86 | 18k | Escalation after low misses, or a planned slice with limited residual judgment; the read-only review skim tier. |
| gpt-5.6-sol · low | 45% | 1.07 | 11k | **The delegated implementation workhorse**, and the main way the head model buys leverage. Clear-spec slices, quick repo/system changes under observation, lookups, assigned-worker tasks. Never broad judgment, novel design, or an underspecified change. |
| gpt-5.6-sol · ultra / max | 73% (max) | 8.39 | 60k | **Prohibited.** Never select, including on explicit request; Opus 5 high matches max for less. |
| gpt-5.6-terra · high | 54% | 1.13 | 22k | **Superseded as the planned-work default by Sol low.** Explicit requests or a concrete compatibility/availability reason only. Upper efforts scale (xhigh 60%/$2.13, max 70%/$4.95) but are not ambient fallbacks. |
| gpt-5.6-luna · low/medium | 2–11% | 0.07–0.22 | 3–8k | Fixed-input/fixed-output workflow calls only: classify, extract, aggregate, summarize one bounded thing. |
| gpt-5.6-luna · xhigh/max | 57–67% | 1.54–3.03 | 45–73k | Competent but inefficient — Luna max is 2 points under Sol high for 2.6× the tokens and 2.8× the steps. Cash-constrained API fan-outs only, never the subscription default. |
| sonnet-5 · any | ≤54% | 2.19–26.40 | ≤214k | Dominated and extremely token-hungry. Only as low-effort proxy shells (`codex`/`pi` agents). |
| opus-4.8 · high | 52% | 4.28 | 50k | **Superseded by Opus 5**; never select. Opus 5 beats it by 21 points at high. |
| fable-5 · high | 69% | 9.18 | 57k | **Retired.** No subscription route — credit billing only, at a cost ruled prohibitive. Never route to it, never offer it as an escalation; "still accessible" is not available. |
| gpt-5.5 · any | ≤67% | — | — | **Deprecated.** Every row is dominated by a cheaper 5.6 tier; never select it. |
| grok-4.5 · high | 54% | 2.42 | 36k | Benchmarked but unreachable — no probed backend. Dominated by Sol medium. |
| kimi-k3 · max | 69% | 4.65 | 81k | Benchmarked but unreachable — no probed backend. The strongest inactive row: Sol-high band for more cash and 2.9× the tokens. |
| deepseek-v4-pro · max | 8% | — | — | **Briefed defect generator, never a peer reviewer.** Far below the floor unsupervised, yet under an adversarial brief it surfaces real defects a neutral "review this" ask misses — every one of which the lead must verify against source. Reachable through pi on quota independent of the codex pool, which is the only reason to reach for it. |
| small-model class | ≤49% | — | — | Never for anything that ships. Not uniformly weak any more (gemini-3.6-flash reaches 49%), but every row is dominated by a cheaper or better 5.6 tier. |

**Every family stops paying before its top tier**, so "tops the bench" is never
a reason to select one. Opus 5 above high buys 0 points at xhigh for +49% and
1 point at max for +95%; Sol above xhigh buys 2 points for +78%; Fable above
high bought ≤1 point for 1.5–2.4×. Hard ceilings: **Opus 5 high, Sol xhigh** —
everything above them is prohibited, not merely discouraged.

Opus 5 tops the roster outright — high beats every Sol tier including Sol max,
and beats Fable at every comparable effort for roughly a third of the cash.
One thing the benchmark does not measure: it is a smaller model than Fable and
lacks Fable's ceiling on genuinely novel hard reasoning. Both readings hold —
DeepSWE scores bounded SWE tasks, not that ceiling — but no accessible model
exposes it any more. Because Opus 5 *is* the ceiling, there is no escalation
path above it: a slice it cannot land gets decomposed, given better context, or
a sideways second opinion from Sol high — never a higher effort tier.

Sol carries technical intelligence and long execution arcs. Its two field
weaknesses need active fencing: **overbuild** (it can turn a five-line change
into a large rewrite plus excessive tests — plans must state scope ceilings
and "no tests/refactors beyond those listed")
and **over-determination** (it may work around a missing target or blocker in
order to satisfy the literal goal — name exact targets, require a stop when
they are absent, and prefer sandboxes/VMs for risky access). These fences still
apply at low effort.

### Subscription quota (measured, not inferred from API price)

Neither vendor exposes a consumption meter, so observed ratios are the only
budgeting instrument. On the Claude **Pro $20** plan's 5h rolling window,
**~500k uncached tokens ≈ 15% of one window** — roughly **3.3M uncached tokens
per window**. Fable measured ~30% for the same 500k, so Opus 5 does the same
work for about half the quota. These are *uncached* figures: a cache-warm
session stretches the window substantially, which is why one long single-context
arc beats repeated cold re-derivation. The Codex pool is shared by Sol, Terra,
Luna, and both the codex and pi backends, with per-model weighting unmeasured.
The Claude window is the scarcer of the two — keep the head model on judgment
and push specified labor to the Codex pool.

**5.6 effort cliff:** the family degrades steeply on agentic work at low
effort, and Luna has the steepest curve on the board — 2% at low, 67% at max —
so never generalize one Luna tier's behavior from another. Sol low is an
intentional field-tested exception for tightly scoped, pre-resolved execution
under an orchestrator; it is not a cheap substitute for lead judgment. Luna
low/medium remains an exception only for bounded function-shaped calls with
small outputs. Do not assume Luna or Terra receives cheaper subscription quota
weighting or that prompt caches cross reasoning efforts (note: 5.6 bills
prompt-cache writes, so cache churn is no longer free).

### Routing rules

- **Head model and technical peer:** Opus 5 high leads — planning, orchestration, taste, ambiguous intent, novel UX/copy, API and architectural ergonomics, simplification, and landing-quality review — and synthesizes delegated work into the final answer. It is also the roster ceiling, so there is no escalation above it: decompose, add context, or take a sideways second opinion instead. Sol high is the technical peer: correctness, feasibility, failure modes, detailed instruction-following, and long-running coding arcs, at the best pass@1-per-token on the board. The current harness owns the answer regardless of who was consulted.
- **Consult by question axis, not harness identity:** `/consultant` routes correctness, feasibility, failure modes, and execution plans to Sol; a Claude-side lead rarely needs to consult outward on taste, because the head model already holds that axis. A lead may auto-consult only after local analysis exposes one concrete high-impact uncertainty. Architecture, migration, or risk alone is not a trigger. One call is the default; use `/multi-wargame` or an explicit user request for a panel.
- **Delegated workhorse:** clear-spec implementation, quick fixes, system work, bounded refactors, and assigned-worker tasks route to **gpt-5.6-sol low via the codex CLI**. Escalate to medium only after low misses or the slice retains limited judgment; use high for broad, judgment-bearing, or long-running work. Read-only exploration and runtime/UI verification also delegate well.
- **Executor backends:** the codex CLI is the default route to GPT models and the write-mode default (real OS sandbox). The pi CLI (`pi -p`) is the verified alternate backend: provider-plural (today only the openai-codex login), no OS sandbox (read-only ≈ `--tools read,grep,find,ls`, which excludes bash), final-message-only stdout, and the **same Codex subscription pool** — never a quota fallback for codex limits. Select pi when the codex CLI itself is the blocker or the lead has no codex access. Backend contracts and the probe checklist for onboarding new harnesses (opencode: unprobed): the `[[backend]]` tables in `agent-routing delegation` and the executor-backends section of `agent-routing mechanism`.
- **Delegation effort is priced by residual risk after the gate**, not by how ambiguous the handoff feels. **Sol low is the default** when the brief is source-verified and bounded *and* you can name a final-head command whose outcome discriminates each material risk. Escalate to sol **medium** or **high** when the brief still leaves an architecture, API, or semantic choice to the executor, or when no such discriminating command exists; **xhigh is the hard ceiling** — the one genuinely hard unplanned task, planning passes, whole-arc `/goal` runs, or a rerun after high missed the bar. Sol **ultra** and **max** are prohibited, including on explicit request. Terra is explicit fallback only, not the next automatic tier. Migrations, schema and breaking changes, destructive operations, and security keep the high-stakes floor however well specified they are.
- **Acceptance probes are what make that floor safe.** Gates catch compile, regression, and lint failures; diff review catches overbuild. Neither sees a plausible implementation of the *wrong semantics*, which is the one failure mode that stays green — and buying a higher tier does not reliably catch it either. So name the probes in the brief as runnable commands, and have the executor record each at the final head with `arc verify --command`, putting the evidence in the ledger. Loudness is something the lead **constructs**, not something a tier buys: naming a probe requires knowing the required behavior, not predicting the executor's mistake. A brief whose material risk has no such command is not ready to delegate. State the limit honestly — readiness consults declared gates only, so probe evidence is recorded and reviewable but never gating, and a reviewer who assumes the tool is checking will stop checking.
- **Verify a brief's premises before delegating, not after.** Open every path and symbol the brief names and check each claim against source. On the rescue chain, three of six first attempts blocked on unverified brief claims and all four review-stopping findings were faithful implementations of *incomplete briefs* rather than execution errors; no executor tier would have prevented them, and brief quality is the binding constraint on the whole floor. (Those were major findings riding `changes-requested` verdicts — their structured `blocking` field was false, so the stop came from the verdict, not the finding.) If the floor does fail — a low-authored semantic defect passing its named probe and first review, or two of **the next six** low changes needing extra rounds for executor-caused defects — the remedy is to make probes declarable so they gate, **not** to buy a higher tier. Evaluating that trigger requires the data: record which tier implemented each delegated change, and classify every review round brief-caused, executor-caused, or integration-staleness.
- **Quota-window strategy:** the Claude window is the scarcer of the two and has no meter, so keep the head model on judgment and push specified labor to the Codex pool. Subscription quota is *output tokens*, not dollars, and Opus 5 high spends 64k per task against Sol high's 28k for a comparable result — the cash column understates what a Claude-side tier costs the window. Drop to Opus 5 medium (37k out, Sol high's pass@1) for routine leading in a long session. Start assigned implementation on sol low and spend sol high only where judgment or long-horizon persistence earns it. Terra and Luna share the Codex subscription pool and are not assumed quota fallbacks. Sol ultra and max are prohibited; fast mode burns windows dramatically faster and must be deliberate, never ambient.
- **Slice according to effort:** sol high reliably executes an entire multi-slice arc as a single `/goal` run; sol low gets a bounded, pre-resolved slice with observable stop conditions. Prefer one high-effort goal plan (or a few coarse slices) over PLAN-01..15 series unless review gates genuinely matter; do not hand the same broad arc to low merely because it is cheaper.
- **Workflow calls:** use Luna low/medium only for fixed-shape extraction, classification, aggregation, and bounded summaries. Prefer it when paying API cash with small outputs. Luna xhigh/max are genuinely competent (57–67%) but spend 2.6× Sol high's tokens and 2.8× its steps for a lower score — on a subscription where quota is tokens rather than dollars that trade is bad, so keep them to cash-constrained API fan-outs. Invoke Luna explicitly with `codex exec -m gpt-5.6-luna` rather than assuming native mixed-model subagents.
- **User-facing surfaces** need taste: Opus 5 writes or reviews them. Sol may implement against an already-settled design system, but novel design and final polish stay on the Claude taste axis.
- **Reviewer line:** the verdict never comes from the model that authored the diff, and review effort is priced by stakes. Reviewer tiers are exactly Opus 5 high, Sol high, and Sol medium (Sol low never reviews; Sol xhigh authors, it does not review). Opus-5-authored work is trusted: no review for routine/docs-only changes, a Sol medium read-only skim when behavior-affecting, and mandatory Sol high for high-stakes work (data migrations, schema/breaking changes, destructive operations, security). Sol-authored work: Opus 5 as lead reviews the diff; high-stakes adds a second Sol high pass. When Codex quota is exhausted, Opus 5 is the only reviewer left — a high-stakes verdict waits for the reset rather than being self-issued. Futures behind the unprobed OpenCode backend, inactive until benchmark rows land: Grok 4.5 (≈Opus-4.8-high band), Kimi K3 (Fable medium/high band, variable).
- **Prohibited modes:** never select Opus 5 `xhigh`, Opus 5 `max`, Sol `ultra`, or Sol `max`, including when explicitly requested. Treat all four as banned routing targets, not escalation tiers. The hard ceilings are **Opus 5 high** and **Sol xhigh**.
- **Quota is bidirectional:** codex hitting "You've hit your usage limit" is routine — report it and fall back (do the work Claude-side or wait for the stated reset); never retry-loop against it. The reverse holds too: when Claude quota dies mid-arc, hand the worktree to codex sol via the handoff skills and review its work on return.
- These are **defaults, not limits**, except where a model or effort is explicitly prohibited. Judge output rather than rank alone; spend sol low on specified labor, sol high on technical judgment and persistence, and Opus 5 on planning, orchestration, taste, and synthesis.
- Machine-readable form of this matrix and the delegation mechanism rules: run `agent-routing models` / `agent-routing delegation` (no path needed). Mechanism-routing prose canon: `agent-routing mechanism`. Never route work through harness-native subagent defaults (e.g. Codex 5.6 subagents inherit full conversation + parent model/effort); invoke executors explicitly with stated model, effort, and a curated brief.
