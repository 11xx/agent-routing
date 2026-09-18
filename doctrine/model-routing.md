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

### Model matrix (DeepSWE v1.1, 113 tasks; roster measured through 2026-09-02, pricing current 2026-07-30: pass@1 / avg $ / output tokens)

| Model · effort | pass@1 | $ | out | Role |
| :--- | :--- | :--- | :--- | :--- |
| opus-5 · high | 73% | 6.08 | 64k | **Available but not recommended.** Use only when the user explicitly requests high; never auto-route or escalate to it. Four points over medium costs +85% cash and does not fix the model's verification weakness. Medium remains the routing ceiling even for novel UX, copy, API shape, and taste. |
| opus-5 · medium | 69% | 3.29 | 37k | **The default lead tier and routing ceiling.** Matches Sol high's 69% at 37k output tokens against Opus 5 high's 64k — the same class of work for roughly half the window on a cost-shaped meter. Planning, orchestration, delegation, ceremony, review, cleanup, taste, novel UX/copy, and API shape stay here unless the user explicitly asks for high. |
| opus-5 · low | 58% | 1.66 | 20k | **Available but not routed.** It is a legitimate Claude-pool workhorse, but rarely saves enough of the scarce Claude window to beat sending bounded labor to much cheaper Luna max. Claude implementation defaults to medium; use low only through an explicit future route justified by a measured capacity need. |
| opus-5 · xhigh / max | 73–74% | 9.07–11.84 | 92–118k | **Prohibited.** Never select either, including on explicit request: xhigh buys 0 points for +49% cost, max buys 1 point for +95%. |
| fable-5.1 · high | — | — | — | **Head-model candidate, unmeasured; explicit selection only.** On the subscription since 2026-09-01 (Pro and Max, Claude Code and the first-party backend), which is the fact the Fable 5 retirement turned on. No Datacurve row, no quota ratio on this plan, no generational calibration; no profile names it. Two facts stand against reseating on launch evidence even once it measures: it is metered like Fable 5, which drew roughly twice the window Opus 5 draws for the same tokens, and it is capped at half of a Max plan's weekly allowance, so it cannot be the only head model whatever it scores. A person selecting it interactively is a choice the harness records and the roster does not make. |
| gpt-5.6-sol · xhigh | 71% | 4.70 | 41k | **Explicit request only.** 2 points over high for +35% cash and +46% tokens — the same non-scaling shape that prohibits the tiers above it. High is the working ceiling; reach past it for a genuinely hard unplanned task or a rerun after high missed. |
| gpt-5.6-sol · high | 69% | 3.47 | 28k | **Technical lead tier, and the best pass@1-per-token row on the board.** Correctness, feasibility, failure modes, deep dives, judgment-involving implementation, adversarial review; carries whole arcs delegated wholesale. |
| gpt-5.6-sol · medium | 61% | 1.86 | 18k | Escalation from the Terra/Luna workhorses when a planned slice retains technical judgment; the read-only review skim tier. |
| gpt-5.6-sol · low | 45% | 1.07 | 11k | **No longer a default route.** Still the most output-token-efficient row, but Terra high now beats it by 9 points for less cash. Use only for a measured Sol-specific compatibility or output-length reason. |
| gpt-5.6-sol · ultra / max | 73% (max) | 8.39 | 60k | **Prohibited.** Never select, including on explicit request; Opus 5 high matches max for less. |
| gpt-5.6-terra · high | 54% | 0.90 | 22k | **The former default delegated workhorse.** It beats Sol low by 9 points at 84% of its benchmark cash and subscription-credit cost. The current `implement` profile uses Luna max for bounded production work. Terra xhigh (60%/$1.70) is an escalation; max (70%/$3.96) stays explicit-only. |
| gpt-5.6-luna · low/medium | 2–11% | 0.01–0.04 | 3–8k | Fixed-input/fixed-output workflow calls only: classify, extract, aggregate, summarize one bounded thing. The 80% cut does not repair the effort cliff. |
| gpt-5.6-luna · high | 44% | 0.16 | 26k | **Probationary pre-resolved executor.** Roughly Sol low's score for 15% of its benchmark cash and subscription-credit cost, but capability is unchanged and local field reliability is unmeasured. Use only for controlled, fully specified trials with exact probes and lead review. |
| gpt-5.6-luna · xhigh | 57% | 0.31 | 45k | Experimental cheap but slow planned-execution tier, and below Sol medium — reach past high to max rather than stopping here. Controlled trials only, with a settled brief and lead review. |
| gpt-5.6-luna · max | 67% | 0.61 | 73k | **The stable bounded-implementation and review tier.** 6 points over Sol medium at a third of its cost, 2 under Sol high for a sixth of it. Read-only review is where 2.6× the output tokens and 2.8× the steps buy thoroughness against a diff nobody waits on. Not a lead or interactive work: a large-diff round runs 20–40 minutes. |
| sonnet-5 · any | ≤54% | 2.19–26.40 | ≤214k | Dominated and extremely token-hungry. Only as low-effort proxy shells (`codex`/`pi` agents). |
| opus-4.8 · high | 52% | 4.28 | 50k | **Superseded by Opus 5**; never select. Opus 5 beats it by 21 points at high. |
| fable-5 · high | 69% | 9.18 | 57k | **Retired.** Superseded on the subscription by Fable 5.1; the 5.0 retirement was for cost and is not relitigated by a successor. Never route to it, never offer it as an escalation; "still accessible" is not available. |
| gpt-5.5 · any | ≤67% | — | — | **Deprecated.** Every row is dominated by a cheaper 5.6 tier; never select it. |
| grok-4.6 · xhigh | 67% | 5.50 | 71k | Benchmarked but unprobed. Luna max's score at nine times Luna's cash; reachable through pi on openrouter or opencode-go, neither probed for it and neither pool serving it. Field-placed with the short-horizon models on the previous generation. A second-opinion voice, not a new tier. |
| kimi-k3 · max | 69% | 4.65 | 81k | Benchmarked but unprobed. Sol-high band for more cash and 2.9× the tokens, and independently field-credited with holding a long autonomous arc — the axis pass@1 cannot see, and why it outranks the other inactive rows for a probe. Reachable through pi on providers no pool serves. |
| gemini-3.8-flash · high | 74% | 2.36 | 143k | **Benchmarked but unprobed, and the row that re-prices the top of the board:** Opus 5 max's score for a fifth of its cash, Sol max's for less than a third. The shape is many cheap steps — 166 per task, the most of any frontier row — so it is cheap per token and slow per task, which matters for interactive work and not at all for a review nobody waits on. Third Flash in six weeks (47%, 65%, 74% on the same board), the steepest direction of travel on the roster. Reachable through pi on openrouter, unprobed; introductory pricing doubles on 2027-01-01. The seat it would contest is review. |
| glm-5.3 · max | 69% | 3.99 | 80k | Benchmarked but unprobed. The routed Flash tier's frontier sibling: six points over Flash for seventeen times the cash, which is Sol-over-Luna's shape on a pool that is not already paid for. Reachable through pi on opencode-go or commandcode, both refusing by pool policy. No route until a field arc shows a slice Flash cannot land that this can. |
| muse-spark-1.2 · xhigh | 55% | 3.70 (free on the contributor tier) | 99k | **Probationary adversarial reviewer, never the reviewer of record alone.** The Datacurve board measures it at 55% — the Opus 4.8 band the third-party index predicted, which Sol medium dominates — so the capability estimate is confirmed, not changed, and the seat rests on the field arc alone. Free through pi on the opencode contributor tier. Field-measured 2026-08-23 on one review arc: it graded a defect BLOCKING that a second independent reviewer, same diff and same brief, graded merely medium — and the stricter grade was right. The defect was a derived view built on the newest verdict rather than the gating one, so any later record silently dropped an outstanding obligation; it reasoned there from the diff alone with no repository access. Willingness to grade BLOCKING is the trait worth routing for. Costs: roughly twice the peer's output on the same task, much of it re-quoting the diff; and seven independent discussion positions all returning `amend`, exactly as the other probationary model did on the same seven questions — two unrelated models hedging alike says something about the prompt, not about either model. No approval of its has been confirmed by anyone, so the reviewer failure that matters is untested. Pairs well with glm-5.3-flash specifically (entered this matrix as the stealth `ox-alpha` route): each found what the other missed. Hosted-only, 1M context; the 21×-cheaper contributor tier is paid for in training rights over your code. Superseded by 1.3 on 2026-09-02, which inherits nothing here until measured. |
| muse-spark-1.3 · xhigh | — (75% on an aggregator board, not this scale) | 1.25 / 4.25 per M list | — | **Released, unmeasured here; the review seat stays on 1.2.** Same list and contributor prices as 1.2. Tops the mini-swe-agent aggregator board, which scores Opus 5 at 68.8% where this matrix measures 74%, so the figure is third-party and stays out of the pass@1 column. No Datacurve row. Reachable through pi on openrouter and on the commandcode contributor route, which no pool serves. A successor inherits a predecessor's weaknesses — verbosity, the uniform `amend` hedge, no confirmed approval — and not its record; measure it on the review arc 1.2 was before it takes the seat. |
| deepseek-flash · max | — (V4 Flash 0731: 53% / $0.46) | 0.30 / 1.20 per M list | — (0731: 108k) | **Steered generator, probationary on the build in service.** The live build is V4.1 Flash, served under the unversioned `deepseek-flash` id the provider keeps across point releases and reached through pi as `--provider deepseek --model deepseek-flash`. The Datacurve board's 53% for $0.46 measured the 0731 build it replaces; V4.1 lists at twice the input and four times the output price and has no row of its own here. Every field observation on this model is the predecessor's: independent testing of 0731 had it inventing answers on every run of an agentic task across all efforts and temperatures, ignoring a plan's first explicit instruction, and writing far more code than better-scoring models — which is why a pre-resolved brief bought no safety on *that* build. The family's releases have each been reported stronger than the last, and none of that is measured here either, so the seat is probation rather than a verdict: routed for generation, and lifted by a field arc on V4.1 — a bounded slice with named acceptance probes, read for instruction adherence and for fabricated identifiers — not by a fresh vendor number. Until that arc exists, use it to produce raw material a lead mines, keep it off the last edit of anything that ships, and check every identifier it emits against source. Steer it with style exemplars rather than prohibitions — its raw output is functional and graceless, and showing it the target is what fixes that. DeepSeek's own 54.4% came from an unreleased minimal harness and is availability evidence, not a comparable pass@1. Hosted pools differ in retention posture, not capability — the opencode-go route stays unrouted until the operator takes its China-hosting opt-in, which is their act and not a posture this roster records — and because the weights are open, running it locally removes the third party entirely. It is also the practical route for authorized security work, where hosted frontier models refuse or degrade; authorization is the operator's to establish. |
| deepseek-v4-pro · max | 63% | 1.67 | 106k | **Briefed defect generator, never a peer reviewer.** Generally available since 2026-08-13 as the 0813 build, which the Datacurve board measures at 63% for $1.67 — between GLM 5.3 Flash and Luna max on score, at three times Luna's cash. The April preview measured 8%; the independent row retires that number and not the family's fabrication record, because the GA build has no field record here and a 55-point jump is a reason to run one, not to skip it. Reachable through pi on deepseek, openrouter, opencode, and opencode-go; unprobed. Both DeepSeek models remain generators only; neither implements. |
| glm-5.3-flash · max / high | 63% (max, measured) | 0.24 (max) | 73k | **Cheap-lane implementer and adversarial reviewer.** The Datacurve board ran it at max — 63% for $0.24, Luna max's score at two fifths of Luna's cash — while the routed tier is high, where the field record is; whether max buys anything over high on this model is unmeasured. Z.AI GLM 5.3 Flash, disclosed 2026-08-29 as the model behind the stealth `ox-alpha` route; the rows are merged. Reached through pi on `commandcode` or `openrouter`, provider always explicit because a bare model name is ambiguous across both and aborts the run. Field-measured 2026-08-29 over a full implementation arc: a fork lifecycle command built in an unfamiliar Rust codebase — ~450 lines plus tests, journal integration, an integration refusal, a policy classification — then thirteen independent review findings repaired across five rounds, ending green at 73 + 672 tests with every repair verified by probe. It argues: it showed twice that a finding was worse than stated, said unprompted that its own fix was the weaker of two defensible options, declined a fragile heuristic with reasons, and caught its own acceptance probe passing before and after a change, rewrote it to fail for the right reason, and reported having done so. Equivalent to Luna max in taste and capability; Luna follows a brief and an instruction more literally. **Route by shape and by price:** GLM when the slice's shape is still in question or when cost matters, Luna when the slice is tightly specified with a named gate. Pair them so each reviews the other — independent providers, independent quota, so a cheap implement-and-review loop needs no expensive tier and the author never reviews its own diff. Per-task cost unmeasured here; per-million prices are about a quarter of Luna max's input and under half its output, so it lands well below Luna max's $0.61 per task. The third-party 63.4% that circulated for high matches the board's max figure and is recorded beside it, not as it. **Three caveats.** No independent row for the routed high tier, and no measured approval — every round here had it repairing findings rather than issuing verdicts, so whether it approves what it should not is untested. The seven-of-seven `amend` hedge from 2026-08-23 was never retested. And the operational hazard is the one that bites: three of seven long-brief dispatches never started, holding a socket and never reaching the model, one for two hours; a healthy run writes its session file in about nine seconds, so never route it onto a critical path without a first-artifact watchdog. |
| small-model class | ≤65% | — | — | Never for anything that ships. Not uniformly weak any more (qwen3.8-max xhigh 57%, gemini-3.7-flash high 65%), but every row is dominated by a cheaper or better routed tier; Gemini 3.8 Flash left the class on its own row. |
| gpt-6-astra · low/medium/high/xhigh/max | — | — | — | **Available but unprobed.** Operator evidence says low/medium may cover Sol-max-class work, medium looks most efficient, and high is the deliberate try-harder tier. These are hypotheses, not pass@1 or cost data: use only by explicit direct selection and record a field arc before adding a profile. Higher efforts remain uncalibrated. |

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

**Task distance is a routing axis the pass@1 column cannot carry.** A model's
error is set at the start, in how it reads what the target actually is, and the
longer the arc the further a small misreading compounds. The same
misinterpretation that is harmless over a five-line change lands somewhere
unrecognisable at the end of an unattended hour — plausibly complete, green on
its gates, and not what was asked for. Cheap tiers are therefore safe over short
distances almost regardless of how well they interpret, which is why bounded
slices route down and broad ambiguous arcs do not; and the cost of an
underspecified target is paid in proportion to arc length, so specification
effort belongs where the arc is long rather than where the task is hard. This is
the same quantity the delegation ladder prices as residual risk after the gate.
Naming the axis keeps the reason legible at the moment a cheap tier looks
tempting for a long run.

**Two co-equal leads, not one default.** Opus 5 medium and Sol high both score
69% at roughly the same cash, on *different quota pools* — Claude and Codex.
They are not alternatives to choose between; they are independent capacity, and
defaulting to one wastes the other. Route by which window has headroom, and by
the axis in question: Sol for correctness, feasibility, and failure modes, Opus
for taste, novel UX and copy, and API shape.

Sol carries technical intelligence and long judgment-bearing execution arcs.
Luna max now carries the stable bounded-implementation and review seats. Terra
remains a measured roster tier but is no longer the default profile route. Luna
high remains benchmarked but is not routed:
max gains 23 pass@1 points while its $0.61 benchmark cost remains below Terra
high's $0.90. Sol's two field
weaknesses need active fencing: **overbuild** (it can turn a five-line change
into a large rewrite plus excessive tests — plans must state scope ceilings
and "no tests/refactors beyond those listed")
and **over-determination** (it may work around a missing target or blocker in
order to satisfy the literal goal — name exact targets, require a stop when
they are absent, and prefer sandboxes/VMs for risky access). These fences still
apply at low effort.

### Subscription quota (observed on Claude, published as credits on Codex)

Anthropic exposes no consumption meter, so observed ratios remain the Claude
budgeting instrument. The ratios were observed on the **Pro $20** plan's 5h
rolling window and transfer to Max as ratios, not as window sizes:
**~500k uncached tokens ≈ 15% of one window** — roughly **3.3M uncached tokens
per window**. Fable 5 measured ~30% for the same 500k, so Opus 5 does the same
work for about half the quota; Fable 5.1 is metered like Fable 5 and capped at
half of a Max plan's weekly allowance, and its own ratio is unmeasured. These are *uncached* figures: a cache-warm
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
judgment and push specified labor to Luna max through the Codex pool.

**5.6 effort cliff:** the family degrades steeply on agentic work at low
effort, and Luna has the steepest curve on the board — 2% at low, 67% at max.
Never generalize one Luna tier's behavior from another. Luna low/medium remain
bounded function-shaped calls; high and xhigh remain non-stable
planned-execution tiers until controlled field evidence lands, while max is
stable for bounded implementation and review. Prompt caches do not cross
reasoning efforts, and 5.6 bills cache writes, so cache churn is not free.

### Routing rules

- **Choose a task shape, then resolve it:** delegation callers choose `extract`, `explore`, `implement`, `execute`, `review`, `design`, or `generate` according to the work; Arc owns implementation planning and bounded briefs rather than a separate plan skill; `interactive` owns Pi's parent-session default. `generate` is the one profile whose output is raw material rather than a deliverable — nothing resolved there is the last model to touch shipped work. `agent-routing resolve <profile> --backend <backend> --json` supplies the current provider, model, effort, stability, and route version. The resolver never classifies prompt text. Probationary and experimental routes require explicit opt-in, a whole profile as much as a variant. Consumer skills and Pi agent definitions keep backend or role behavior and do not pin the roster.
- **Head model and technical peer:** the active head seat leads at its current routing ceiling; the current roster records which model and effort hold that default. The lead's axis is planning, orchestration, taste, ambiguous intent, novel UX/copy, API and architectural ergonomics, simplification, and landing-quality review — and synthesizes delegated work into the final answer. If the current lead effort misses, decompose, add context, or take a sideways second opinion instead of raising effort automatically. The technical peer seat covers correctness, feasibility, failure modes, detailed instruction-following, and long-running coding arcs. The current harness owns the answer regardless of who was consulted.
- **Consult by question axis, not harness identity:** correctness, feasibility, failure modes, and execution plans go to Sol; a Claude-side lead rarely needs to consult outward on taste, because the head model already holds that axis. Where the project has a journal, record the opinion as an `arc journal position` on a discussion artifact — the stance carries the consulted harness and model identity and a tally can count it, which an ephemeral review owned by nobody cannot. Where there is no journal, or where repository access would bias the answer, use the `agent-delegate` clean-room invocation with its isolated working directory and configuration boundary; asking a model not to look does not enforce the boundary. A lead may auto-consult only after local analysis exposes one concrete high-impact uncertainty. Architecture, migration, or risk alone is not a trigger. One call is the default; use an Arc discussion with explicit positions or an explicit user request for a panel.
- **Delegated workhorse:** bounded production work, including fully pre-resolved slices and named acceptance probes, routes through the stable `implement` profile to **Luna max**. Terra high remains a measured roster tier but is no longer the default profile route. Luna high remains benchmarked but is not routed: max gains 23 pass@1 points while remaining cheaper than Terra high. Escalate to **Sol medium** when technical judgment remains and **Sol high** for broad, judgment-bearing, high-stakes, or long-running work. Sol low is no longer ambient because the current workhorse route dominates it on score and benchmark cash.
- **Executor backends:** the codex CLI is the default route to GPT models and the write-mode default (real OS sandbox). The pi CLI (`pi -p`) is the verified provider-plural alternate: its `openai-codex` route shares the Codex pool, while its live `deepseek` route uses independent API billing. Pi has no OS sandbox (read-only ≈ `--tools read,grep,find,ls`, which excludes bash) and emits only the final message. Select it for clean-room provider plurality, a lead without Codex access, or experimental DeepSeek generation; use Codex for GPT writes unless its CLI is the blocker. The opencode CLI is a third quota pool independent of both standing subscriptions, and no profile routes to it. Its v2 provider declares no model variants, so effort is unreachable there by any syntax, and a route naming an effort the backend silently drops is a route that lies about what ran. Pi honours effort and reaches every model on that pool except gpt-5.6-luna, which its bundled catalog omits, so it carries that capacity short of one route. The v2 CLI also has no unattended-approval mode, which ends a non-interactive run at exit 0 with no verdict, and the pool depends on an optional subscription no manifest can observe. Backend contracts and the probe checklist for onboarding new harnesses: `agent-routing delegation` and `agent-routing mechanism`.
- **Delegation effort is priced by residual risk after the gate**, not by how ambiguous the handoff feels. **Luna max** is the stable default for source-verified bounded work, from fully pre-resolved slices through ordinary implementation judgment. Escalate to Sol **medium** or **high** when the brief leaves deeper architecture, API, or semantic choice, or when no discriminating command exists; **Sol xhigh is the hard ceiling**. Sol **ultra** and **max** are prohibited. Migrations, schema and breaking changes, destructive operations, and security keep the Sol-high floor however well specified they are.
- **Acceptance probes are what make the executor floor safe.** Gates catch compile, regression, and lint failures; diff review catches overbuild. Neither sees a plausible implementation of the *wrong semantics*, which is the one failure mode that stays green. Every implementation brief routed below the Sol-high floor names runnable probes, and the executor records each at the final head with `arc verify --command`. Loudness is something the lead constructs, not something a tier buys. A brief whose material risk has no such command is not ready to delegate. Readiness consults declared gates only, so probe evidence is recorded and reviewable but never gating; the reviewer still checks it.
- **Verify a brief's premises before delegating, not after.** Open every path and symbol the brief names and check each claim against source. On the rescue chain, three of six first attempts blocked on unverified brief claims and all four review-stopping findings were faithful implementations of *incomplete briefs* rather than execution errors; no executor tier would have prevented them. If the floor does fail — a workhorse-authored semantic defect passing its named probe and first review, or two members of the fixed next-six workhorse cohort needing extra rounds for executor-caused defects — make probes declarable so they gate, not merely buy a higher tier. Record the exact model and effort and classify every review round as brief-caused, executor-caused, or integration-staleness. Changing the workhorse does not reset the cohort.
- **Quota-window strategy:** the Claude window remains the scarcer pool. Keep Opus on judgment and push specified labor to Codex. OpenAI's published schedule prices every model at 25 credits per API dollar, so benchmark cash ratios transfer directly to task-level credits; official Plus estimates are Sol 10–100, Terra 25–200, and Luna 250–2,000 local messages per five hours. Start bounded implementation on Luna max, and spend Sol where technical judgment or token-efficient persistence earns its rate. Codex fast mode consumes 2.5× credits; Claude fast mode burns its window substantially faster. Both stay deliberate, never ambient. A third pool exists when the OpenCode Go subscription is active: it is metered in usage dollars rather than credits or observed share, which makes the benchmark cash column convert directly into per-window capacity and makes consumption locally measurable — the only pool of the three where that is true. Pi is how a profile reaches it; nothing falls back to it, and no route resolves there by default.
- **Slice according to effort:** Sol high reliably executes an entire multi-slice arc as a single `/goal` run. Luna max gets bounded slices with observable stop conditions and named acceptance probes. Prefer one high-effort goal run or a few coarse Arc slices over a long hand-authored series unless review gates genuinely matter; do not hand a broad ambiguous arc to a cheaper executor merely because its credit rate is low.
- **Workflow calls:** low/medium efforts that the current roster marks fixed-shape remain extraction, classification, aggregation, and bounded summaries; experimental efforts require explicit opt-in. The stable `implement` and `review` profiles provide the current workhorse and first review gate, while backend-specific defaults come from `profiles.toml`. Reviewing may cost more than implementation when a read-only pass buys thoroughness against a diff nobody waits on; that is a reason to resolve the current route deliberately, not to freeze a model name here.
- **User-facing surfaces** need taste: Opus 5 writes or reviews them. Sol may implement against an already-settled design system, but novel design and final polish stay on the Claude taste axis.
- **Reviewer line:** the verdict never claims independence from the model that authored the diff, and review effort is priced by stakes. A lead reviewing delegated work it did not author is valid review coverage; independent review is an escalation for repository policy, explicit user requirements, or a high-consequence approval. When no escalation is required, record deferred coverage as Arc debt. Concrete reviewer routes come from the current roster and resolver; this doctrine does not freeze a tier list. Debt never overrides an actual `changes-requested` verdict. **the resolver's current stable review route is the first review gate for behavior-affecting work; its verdict discharges review on its own** — the current route's field evidence includes ten changes integrated in one session under adversarial briefs: 31 recorded verdicts split 15 approved to 14 changes-requested, 73 recorded findings, and a class of defect no gate catches (a stale observation inherited across a relink, a gate declaration notarized for a command nothing ran, an asserted integration accepting any commit). The false-approval mode was probed deliberately — a silent one-character regression in a file the commit message did not mention, green suite, a test that appeared to cover the affected flag — and it named the plant against the repository's own documentation plus three unplanted defects. It also terminates: asked to approve unless it could name a concrete failing input, it approved. Escalation is by the current named review variant when the verdict is on the critical path or a wrong approval is expensive — irreversible migrations, security boundaries, outside blast radius. Four operating rules travel with the seat, because its faults are repeatable and cheap: **re-run a finding's failing input before recording it** (the mechanism claim is usually right, the consequence sometimes overstated); resolve a self-contradiction across rounds on the merits rather than by round order; read a strictness finding as a claim about where the guard belongs, not an instruction; and scope the brief to `<target>..HEAD` after a rebase, since it reviews exactly the range it is handed. Two dispatch facts: parse for the verdict shape you asked for and treat a missing verdict as an incomplete run rather than a verdict, because exit status does not distinguish them; and a delegated reviewer under `codex exec -s workspace-write` cannot write a ledger inside the Git common dir, so arm it beforehand or plan to record its verdict verbatim as the lead. For lead-authored work, routine/docs-only changes need no external review; behavior-affecting work uses the current resolved review route when an independent pass is required. A lead reviews delegated work it did not author. High-stakes work adds the current high-stakes reviewer route, and if no independent route is available it waits or records debt according to policy rather than inventing independence. **Review is where the money goes, so buy passes deliberately.** Measured over one nine-run session: implementation on Luna max was 43% more tokens and 8% of the cost, while review on Sol high was 92% of it — one Sol high pass costs about nine Luna max implementation slices. Counting runs or tokens hides this entirely; spend is rate times volume. Two consequences. First, **routing Luna to implement routes review off the cheap tier by construction**, because the reviewer is never the author — the Luna-authored exception fires most often precisely because Luna is also the workhorse, and it is worth 12-15x, where tuning effort inside Sol is worth about 1.9x. Second, **batch review by default**: one pass over N related changes, not N passes. Batching is also the more precise shape for defects that span changes, which a per-change reviewer has no reason to look for; per-change review is an opt-in that buys depth on one intricate change, or a verdict before a dependent change is written, and its price is named where it is chosen. Resolve the `review` profile for the backend in use; any variant selection is current routing data rather than a reviewer-tier rule in this doctrine. A lead cannot review its own authored diff as independent, but it can review delegated work it did not author. A killed reviewer loses everything, since it writes no report and leaves no partial work. The arcs behind this seat are in `eras/2026-08-18-luna-reviewer-off-probation.md`; the cost shape is in `eras/2026-08-26-luna-implements-sol-reviews-cost-share.md`.
- **Prohibited modes:** never select Opus 5 `xhigh`, Opus 5 `max`, Sol `ultra`, or Sol `max`, including when explicitly requested. Treat all four as banned routing targets, not escalation tiers. The routing ceilings are **Opus 5 medium** and **Sol xhigh**; Opus 5 high is available but not recommended and requires an explicit user request.
- **Quota is bidirectional:** codex hitting "You've hit your usage limit" is routine — report it and fall back (do the work Claude-side or wait for the stated reset); never retry-loop against it. The reverse holds too: when Claude quota dies mid-arc, hand the worktree to codex sol via the handoff skills and review its work on return.
- These are **defaults, not limits**, except where a model or effort is explicitly prohibited. Judge output rather than rank alone; spend Luna max on bounded implementation and review, Sol on technical judgment and persistence, and Opus 5 on planning, orchestration, taste, and synthesis.
- Machine-readable form: `agent-routing models` for the roster, `agent-routing profiles` and `agent-routing resolve <profile> --backend <backend> --json` for caller-selected routes, and `agent-routing delegation` for mechanism rules (no path needed). Mechanism-routing prose canon: `agent-routing mechanism`. Never route work through harness-native subagent defaults (e.g. Codex 5.6 subagents inherit full conversation + parent model/effort); invoke executors through a resolved profile with a curated brief.
