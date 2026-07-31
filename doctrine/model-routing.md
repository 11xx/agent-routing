## Model Routing & Delegation

Standing defaults for complementary Claude and Codex orchestration. **Opus 5
is the head model** — it plans, orchestrates, delegates, and owns the final
answer — and Sol is the technical peer and execution axis beneath it.
Delegation uses the other subscription where its model or quota is a better
fit. Only models verified through current local backends are routed;
probationary API models are labeled experimental. Availability history remains
in `agent-routing eras`.

### Glossary

- **Intelligence:** how complex a problem the model completes correctly, unsupervised.
- **Taste:** cleanliness of UI/UX, architectural code quality, API design, copy.

### Model matrix (DeepSWE v1.1, 113 tasks; roster measured through 2026-07-27, pricing current 2026-07-30: pass@1 / avg $ / output tokens)

| Model · effort | pass@1 | $ | out | Role |
| :--- | :--- | :--- | :--- | :--- |
| opus-5 · high | 73% | 6.08 | 64k | **Available but not recommended.** Use only when the user explicitly requests high; never auto-route or escalate to it. Four points over medium costs +85% cash and does not fix the model's verification weakness. Medium remains the routing ceiling even for novel UX, copy, API shape, and taste. |
| opus-5 · medium | 69% | 3.29 | 37k | **The default lead tier and routing ceiling.** Matches Sol high's 69% at 37k output tokens against Opus 5 high's 64k — the same class of work for roughly half the window on a cost-shaped meter. Planning, orchestration, delegation, ceremony, review, cleanup, taste, novel UX/copy, and API shape stay here unless the user explicitly asks for high. |
| opus-5 · low | 58% | 1.66 | 20k | **A legitimate Claude-pool workhorse.** Not dominated by Sol medium — 58%/$1.66 against 61%/$1.86 is three points cheaper, not worse on both axes. It draws the Claude window, so it is capacity the Codex tiers cannot substitute for. Use for specified labor when the Claude window has room and the Codex pool is the constraint. |
| opus-5 · xhigh / max | 73–74% | 9.07–11.84 | 92–118k | **Prohibited.** Never select either, including on explicit request: xhigh buys 0 points for +49% cost, max buys 1 point for +95%. |
| gpt-5.6-sol · xhigh | 71% | 4.70 | 41k | **Explicit request only.** 2 points over high for +35% cash and +46% tokens — the same non-scaling shape that prohibits the tiers above it. High is the working ceiling; reach past it for a genuinely hard unplanned task or a rerun after high missed. |
| gpt-5.6-sol · high | 69% | 3.47 | 28k | **Technical lead tier, and the best pass@1-per-token row on the board.** Correctness, feasibility, failure modes, deep dives, judgment-involving implementation, adversarial review; carries whole arcs delegated wholesale. |
| gpt-5.6-sol · medium | 61% | 1.86 | 18k | Escalation from the Terra/Luna workhorses when a planned slice retains technical judgment; the read-only review skim tier. |
| gpt-5.6-sol · low | 45% | 1.07 | 11k | **No longer a default route.** Still the most output-token-efficient row, but Terra high now beats it by 9 points for less cash. Use only for a measured Sol-specific compatibility or output-length reason. |
| gpt-5.6-sol · ultra / max | 73% (max) | 8.39 | 60k | **Prohibited.** Never select, including on explicit request; Opus 5 high matches max for less. |
| gpt-5.6-terra · high | 54% | 0.90 | 22k | **The default delegated workhorse.** It beats Sol low by 9 points at 84% of its benchmark cash and subscription-credit cost. Use for bounded production work, including fully specified slices and work that retains ordinary implementation judgment. Terra xhigh (60%/$1.70) is an escalation; max (70%/$3.96) stays explicit-only. |
| gpt-5.6-luna · low/medium | 2–11% | 0.01–0.04 | 3–8k | Fixed-input/fixed-output workflow calls only: classify, extract, aggregate, summarize one bounded thing. The 80% cut does not repair the effort cliff. |
| gpt-5.6-luna · high | 44% | 0.16 | 26k | **Probationary pre-resolved executor.** Roughly Sol low's score for 15% of its benchmark cash and subscription-credit cost, but capability is unchanged and local field reliability is unmeasured. Use only for controlled, fully specified trials with exact probes and lead review. |
| gpt-5.6-luna · xhigh/max | 57–67% | 0.31–0.61 | 45–73k | Experimental cheap but slow planned-execution tiers. Luna max is 2 points under Sol high for roughly one-sixth of its cash and subscription-credit cost, but 2.6× the output tokens and 2.8× the steps. Use only in controlled trials with a settled brief, latency tolerance, and lead review. |
| sonnet-5 · any | ≤54% | 2.19–26.40 | ≤214k | Dominated and extremely token-hungry. Only as low-effort proxy shells (`codex`/`pi` agents). |
| opus-4.8 · high | 52% | 4.28 | 50k | **Superseded by Opus 5**; never select. Opus 5 beats it by 21 points at high. |
| fable-5 · high | 69% | 9.18 | 57k | **Retired.** No subscription route — credit billing only, at a cost ruled prohibitive. Never route to it, never offer it as an escalation; "still accessible" is not available. |
| gpt-5.5 · any | ≤67% | — | — | **Deprecated.** Every row is dominated by a cheaper 5.6 tier; never select it. |
| grok-4.5 · high | 54% | 2.42 | 36k | Benchmarked but unreachable — no probed backend. Dominated by Sol medium. |
| kimi-k3 · max | 69% | 4.65 | 81k | Benchmarked but unreachable — no probed backend. The strongest inactive row: Sol-high band for more cash and 2.9× the tokens. |
| deepseek-v4-flash · max | — | — | — | **Experimental bounded executor.** The official 0731 public-beta API is live through Pi on an independent pool. DeepSeek reports 54.4% using its own unreleased minimal harness, so that number is availability evidence rather than a pass@1 row comparable to the neutral matrix. Exact brief, probes, and lead review are mandatory. |
| deepseek-v4-pro · max | 8% | — | — | **Preview-only briefed defect generator, never a peer reviewer.** Its April endpoint remains callable, but the final Pro release has not shipped. Retain the measured defect-generation niche; use Flash for new bounded-executor experiments. |
| small-model class | ≤49% | — | — | Never for anything that ships. Not uniformly weak any more (gemini-3.6-flash reaches 49%), but every row is dominated by a cheaper or better 5.6 tier. |

**Every family stops paying before its top tier**, so "tops the bench" is never
a reason to select one. Opus 5 above high buys 0 points at xhigh for +49% and
1 point at max for +95%; Sol above xhigh buys 2 points for +78%; Fable above
high bought ≤1 point for 1.5–2.4×. The routing ceilings are **Opus 5
medium and Sol xhigh**. Opus 5 high remains available only by explicit user
request; Opus 5 xhigh/max and Sol ultra/max are prohibited.

Opus 5 high tops the roster on score, but medium is the routing ceiling. High
is not an escalation tier: it remains available only when the user explicitly
requests that effort. A slice medium cannot land gets decomposed, given better
context, or a sideways second opinion from Sol high instead of an automatic
effort increase.

**What the benchmark does not measure, and the field does.** Opus 5 is strong
at following a specified order and weak at checking the substrate it acts on.
Measured over one long session (2026-07-27/28): it assumed `org-babel` expands
`#+INCLUDE` and that cross-file noweb references resolve — neither is true, and
both fail *silently*, one of them into four live harness instruction files; it
read a `grep | head -6` as a complete set and briefed an executor with five of
twelve call sites; it wrote `arc $cmd` unquoted under zsh twice, so two probes
measured nothing and a wrong conclusion was drawn from one before the shell
behaviour was noticed; and it delegated ledger-writing work into a sandbox that
cannot write the ledger, a constraint recorded in its own memory.

Every one was caught before shipping — by diffing, by testing, or by an
executor's stop condition — and none by the model noticing unprompted. The
reasoning was sound each time; the substrate was unchecked. Two consequences
for routing: **do not run it unattended on work whose substrate it has not
verified**, and treat a plan or brief it produces as needing its premises
checked against source before delegation, which is cheap and catches most of
this class.

<!-- GENERATIONAL: Opus 5 era, opened 2026-07-25. Delete this block whole when
     the head-model seat changes. It calibrates one model generation's quirks,
     not standing policy — every frontier release needs its own, and carrying a
     previous model's calibration forward is worse than carrying none. The
     standing rule this specialises lives in the shared instructions as
     "Before you depend on it, run it". -->

**Opus 5 calibration (2026-07).** It acts with high confidence on unverified
substrate, and the confidence is indistinguishable from the well-founded kind
from the inside — so any instruction keyed on *feeling* unsure is inert against
it. Three consequences while this model holds the seat:

- The shared verify-before-depending triggers are not optional for it.
- Treat a plan or brief it authors as needing every premise checked against
  source before delegation. Cheap, and it catches most of the class: in one
  measured session three delegated runs each stopped on a lead-authored brief
  defect before writing any code.
- Do not run it unattended on work whose substrate it has not verified. Keep
  executor stop conditions aggressive; they, not its judgement, are what
  actually caught every instance.

<!-- END GENERATIONAL -->

Orchestration mechanics are a separate weak axis. A proxy subagent it spawned
improvised a poll loop on a status file the harness never writes, and hung —
fatal in an unattended run. Drive long delegations with a directly backgrounded
call, never through a proxy agent free to invent its own wait.

**Two co-equal leads, not one default.** Opus 5 medium and Sol high both score
69% at roughly the same cash, on *different quota pools* — Claude and Codex.
They are not alternatives to choose between; they are independent capacity, and
defaulting to one wastes the other. Route by which window has headroom, and by
the axis in question: Sol for correctness, feasibility, and failure modes, Opus
for taste, novel UX and copy, and API shape.

Sol carries technical intelligence and long judgment-bearing execution arcs.
Terra now carries routine delegated labor; Luna high remains a probationary
executor for controlled trials. Sol's two field
weaknesses need active fencing: **overbuild** (it can turn a five-line change
into a large rewrite plus excessive tests — plans must state scope ceilings
and "no tests/refactors beyond those listed")
and **over-determination** (it may work around a missing target or blocker in
order to satisfy the literal goal — name exact targets, require a stop when
they are absent, and prefer sandboxes/VMs for risky access). These fences still
apply at low effort.

### Subscription quota (observed on Claude, published as credits on Codex)

Anthropic exposes no consumption meter, so observed ratios remain the Claude
budgeting instrument. On the Claude **Pro $20** plan's 5h rolling window,
**~500k uncached tokens ≈ 15% of one window** — roughly **3.3M uncached tokens
per window**. Fable measured ~30% for the same 500k, so Opus 5 does the same
work for about half the quota. These are *uncached* figures: a cache-warm
session stretches the window substantially, which is why one long single-context
arc beats repeated cold re-derivation.

OpenAI publishes the Codex weighting directly. Per million
input/cached-input/output tokens, Sol costs **125/12.5/750 credits**, Terra
**50/5/300**, and Luna **5/0.5/30**. The corresponding Plus estimates are
Sol 10–100, Terra 25–200, and Luna 250–2,000 local messages per five-hour
window. Actual use still varies with context, reasoning, tools, retrieval, and
caching; the published ranges are estimates rather than exact transforms of
the token-credit schedule. Credits are exactly 25 times API dollars at every
token class for all three models, so the old "token-counted or cost-weighted?"
uncertainty is closed: task-level Codex credits track the benchmark cash column
exactly. The Claude window remains the scarcer pool — keep the head model on
judgment and push specified labor to Terra or controlled Luna trials.

**5.6 effort cliff:** the family degrades steeply on agentic work at low
effort, and Luna has the steepest curve on the board — 2% at low, 67% at max.
Never generalize one Luna tier's behavior from another. Luna low/medium remain
bounded function-shaped calls; high and above remain probationary
planned-execution tiers until controlled field evidence lands. Prompt caches do
not cross reasoning efforts, and 5.6 bills cache writes, so cache churn is not
free.

### Routing rules

- **Head model and technical peer:** Opus 5 **medium** leads at the routing ceiling. High remains available only when the user explicitly requests that effort; it is never an automatic route or escalation, buying only 4 points for +85% cash while leaving the verification weakness intact. The lead's axis is planning, orchestration, taste, ambiguous intent, novel UX/copy, API and architectural ergonomics, simplification, and landing-quality review — and synthesizes delegated work into the final answer. If medium misses, decompose, add context, or take a sideways second opinion instead of raising effort. Sol high is the technical peer: correctness, feasibility, failure modes, detailed instruction-following, and long-running coding arcs, at the best pass@1-per-token on the board. The current harness owns the answer regardless of who was consulted.
- **Consult by question axis, not harness identity:** `/consultant` routes correctness, feasibility, failure modes, and execution plans to Sol; a Claude-side lead rarely needs to consult outward on taste, because the head model already holds that axis. A lead may auto-consult only after local analysis exposes one concrete high-impact uncertainty. Architecture, migration, or risk alone is not a trigger. One call is the default; use `/multi-wargame` or an explicit user request for a panel.
- **Delegated workhorse:** bounded production work, including fully pre-resolved slices and work retaining ordinary implementation judgment, routes to **Terra high**. Luna high is a probationary pre-resolved executor for controlled trials, not an ambient default. Escalate to **Sol medium** when technical judgment remains and **Sol high** for broad, judgment-bearing, high-stakes, or long-running work. Sol low is no longer ambient because Terra high dominates it on score and benchmark cash.
- **Executor backends:** the codex CLI is the default route to GPT models and the write-mode default (real OS sandbox). The pi CLI (`pi -p`) is the verified provider-plural alternate: its `openai-codex` route shares the Codex pool, while its live `deepseek` route uses independent API billing. Pi has no OS sandbox (read-only ≈ `--tools read,grep,find,ls`, which excludes bash) and emits only the final message. Select it for clean-room provider plurality, a lead without Codex access, or experimental DeepSeek work; use Codex for GPT writes unless its CLI is the blocker. Backend contracts and the probe checklist for onboarding new harnesses (opencode: unprobed): `agent-routing delegation` and `agent-routing mechanism`.
- **Delegation effort is priced by residual risk after the gate**, not by how ambiguous the handoff feels. **Terra high** is the default for source-verified bounded work, from fully pre-resolved slices through ordinary implementation judgment. Luna high is available only as a controlled pre-resolved trial until field evidence establishes reliability. Escalate to Sol **medium** or **high** when the brief leaves deeper architecture, API, or semantic choice, or when no discriminating command exists; **Sol xhigh is the hard ceiling**. Sol **ultra** and **max** are prohibited. Migrations, schema and breaking changes, destructive operations, and security keep the Sol-high floor however well specified they are.
- **Acceptance probes are what make the executor floor safe.** Gates catch compile, regression, and lint failures; diff review catches overbuild. Neither sees a plausible implementation of the *wrong semantics*, which is the one failure mode that stays green. Every implementation brief routed below the Sol-high floor names runnable probes, and the executor records each at the final head with `arc verify --command`. Loudness is something the lead constructs, not something a tier buys. A brief whose material risk has no such command is not ready to delegate. Readiness consults declared gates only, so probe evidence is recorded and reviewable but never gating; the reviewer still checks it.
- **Verify a brief's premises before delegating, not after.** Open every path and symbol the brief names and check each claim against source. On the rescue chain, three of six first attempts blocked on unverified brief claims and all four review-stopping findings were faithful implementations of *incomplete briefs* rather than execution errors; no executor tier would have prevented them. If the floor does fail — a workhorse-authored semantic defect passing its named probe and first review, or two members of the fixed next-six workhorse cohort needing extra rounds for executor-caused defects — make probes declarable so they gate, not merely buy a higher tier. Record the exact model and effort and classify every review round as brief-caused, executor-caused, or integration-staleness. Changing the workhorse does not reset the cohort.
- **Quota-window strategy:** the Claude window remains the scarcer pool. Keep Opus on judgment and push specified labor to Codex. OpenAI's published schedule prices every model at 25 credits per API dollar, so benchmark cash ratios transfer directly to task-level credits; official Plus estimates are Sol 10–100, Terra 25–200, and Luna 250–2,000 local messages per five hours. Start bounded implementation on Terra high, trial pre-resolved work on Luna high, and spend Sol where technical judgment or token-efficient persistence earns its rate. Codex fast mode consumes 2.5× credits; Claude fast mode burns its window substantially faster. Both stay deliberate, never ambient.
- **Slice according to effort:** Sol high reliably executes an entire multi-slice arc as a single `/goal` run. Terra high gets bounded slices and may retain ordinary implementation judgment; Luna high gets only controlled, fully pre-resolved trials with observable stop conditions. Prefer one high-effort goal plan (or a few coarse slices) over PLAN-01..15 series unless review gates genuinely matter; do not hand a broad ambiguous arc to a cheaper executor merely because its credit rate is low.
- **Workflow calls:** Luna low/medium remain fixed-shape extraction, classification, aggregation, and bounded summaries. Luna high and above are probationary planned-execution tiers: cheap in API cash and subscription credits, but field reliability is unmeasured and their long outputs and step counts remain material. Use controlled trials with settled briefs, latency tolerance, exact probes, and lead review; never use them as leads or reviewers. Invoke Luna explicitly with `codex exec -m gpt-5.6-luna`.
- **User-facing surfaces** need taste: Opus 5 writes or reviews them. Sol may implement against an already-settled design system, but novel design and final polish stay on the Claude taste axis.
- **Reviewer line:** the verdict never comes from the model that authored the diff, and review effort is priced by stakes. Reviewer tiers are exactly Opus 5 medium, Sol high, and Sol medium; Luna, Terra, Sol low, Sol xhigh, and both DeepSeek models never review. Opus-5-authored work: no review for routine/docs-only changes, a Sol medium read-only skim when behavior-affecting, and mandatory Sol high for high-stakes work. GPT- or DeepSeek-authored work: Opus 5 medium as lead reviews the diff; high-stakes GPT work adds a second Sol high pass, while high-stakes work never routes to experimental DeepSeek. When Codex quota is exhausted, Opus 5 medium is the only reviewer left — a high-stakes verdict waits for the reset rather than being self-issued.
- **Prohibited modes:** never select Opus 5 `xhigh`, Opus 5 `max`, Sol `ultra`, or Sol `max`, including when explicitly requested. Treat all four as banned routing targets, not escalation tiers. The routing ceilings are **Opus 5 medium** and **Sol xhigh**; Opus 5 high is available but not recommended and requires an explicit user request.
- **Quota is bidirectional:** codex hitting "You've hit your usage limit" is routine — report it and fall back (do the work Claude-side or wait for the stated reset); never retry-loop against it. The reverse holds too: when Claude quota dies mid-arc, hand the worktree to codex sol via the handoff skills and review its work on return.
- These are **defaults, not limits**, except where a model or effort is explicitly prohibited. Judge output rather than rank alone; spend Terra high on bounded labor, trial Luna high on fully specified work, Sol on technical judgment and persistence, and Opus 5 on planning, orchestration, taste, and synthesis.
- Machine-readable form of this matrix and the delegation mechanism rules: run `agent-routing models` / `agent-routing delegation` (no path needed). Mechanism-routing prose canon: `agent-routing mechanism`. Never route work through harness-native subagent defaults (e.g. Codex 5.6 subagents inherit full conversation + parent model/effort); invoke executors explicitly with stated model, effort, and a curated brief.
