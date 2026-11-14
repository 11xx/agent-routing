# Model routing

Standing principles. They hold whatever the roster is; the seats, bans and
ranks that apply them follow, rendered from the stores.

## Choosing

- Model choice is the operator's deliberate judgment, recorded as seats. It is never spread across models to balance quota.
- The caller chooses the profile by the shape of the work; `resolve` maps that choice to a seat and never reads the prompt.
- Seats are defaults, not limits, except a prohibited tier, which stays prohibited even when asked for by name.
- Only models reached through a verified local backend are routed; a probationary model is labeled experimental and needs an explicit opt-in.
- Compare candidates as model-and-effort tiers, capability and cost together. Effort moves a model across the roster.
- A top tier is never selected from benchmark rank alone: tops stop paying, and every family has one.
- Never generalize one tier's behavior from another; a model's effort curve is measured, not assumed.
- Taste is the larger models' edge on work no benchmark scores, and it varies by domain. It breaks ties between close tiers and decides before cost for design, visual and copy work.
- Novel user-facing design and final polish stay on the taste axis; implementation against a settled design system need not.
- A vendor's own harness, or an aggregator board, is its own scale. Its figures are recorded with evaluator and date and never merged with another scale.

## Escalating

- Escalating above the caller's own seat, or into a scarcer pool, is offered to the user, naming the route, what it buys and the pool it spends. A standing user authorization replaces the ask for the work it covers.
- Routing upward within what the caller's seat costs is ordinary, and so is escalating to the caller's own tier; prefer an equivalent tier from another lab.
- A declined offer leaves the work at the caller's tier, except under a floor, where it waits.
- Consult another model automatically only after local analysis exposes one concrete, high-impact uncertainty; architecture, migration or risk alone is not a trigger. One consultation is the default, and a panel needs an Arc discussion with explicit positions or an explicit user request.
- The head model's own effort is not an escalation path: a slice its working tier cannot land is decomposed, given better context, or given a sideways second opinion.
- Founding slices of a clean repository set the conventions later models copy, so they go to the head model at its routing ceiling; the conventions then land in AGENTS.md and the format and lint gates.

## Delegating

- Delegation runs a resolved route with a curated brief. Whatever the mechanism, establish the model, effort and context the child runs with rather than accepting the mechanism's defaults.
- Delegation effort is priced by residual risk after the gate, not by how ambiguous the handoff feels. Migrations, schema and breaking changes, destructive operations and security keep the judgment-bearing tier however well specified.
- Task distance is a routing axis: a misreading compounds with arc length, so cheap tiers are safe over short distances and specification effort belongs where the arc is long.
- Wall-clock is a routing axis: a slow tier holds its harness slot, so work that gates others is budgeted by its tail, not its median.
- Do not hand a broad ambiguous arc to a cheaper executor because its rate is low; give it bounded slices with observable stop conditions.
- Verify a brief's premises against source before delegating. A brief that asserts something untrue about the code is the lead's defect, not the executor's.
- Acceptance probes make a workhorse floor safe: a brief routed below the judgment-bearing tier names runnable probes for its material risks, or it is not ready.
- If a workhorse-authored semantic defect passes its named probe and first review, or two of a fixed six-change workhorse cohort need extra verdict rounds for executor-caused defects, make acceptance probes declarable so they gate; escalate the tier only if the defect recurs once they do. Changing the workhorse model does not reset the cohort.
- Each delegated change records the exact model and effort that implemented it, and each review round is classified brief-caused, executor-caused or integration-staleness; only executor-caused rounds count against a workhorse floor.
- A user instruction outranks a model's picture of its environment: check the environment claim before deviating from the instruction.
- Drive a long delegation directly with a backgrounded call, never through a proxy agent free to invent its own wait.
- Defect generation and adjudication are separable: a model below the reviewer floor may generate candidates under an adversarial brief, and each stays a candidate until a reviewer-tier model or the lead confirms it against source.

## Reviewing

- The reviewer is never the author, and independence is never manufactured. A lead that did not write delegated work may review it and record that verdict.
- Independent review is an escalation for repository policy, an explicit user requirement, or a costly wrong approval. Otherwise the lead inspects, runs the gates and records the deferred coverage as Arc debt, which never overrides changes-requested.
- A reviewer from another lab is the stronger check where independence matters; route eligibility is never a verdict or an identity check.
- A change jointly authored across two labs is reviewed by the stronger of the two labs' review seats; its verdict discharges the debt without claiming independence from its own lab's commits.
- Re-run a finding's failing input before recording it, resolve a contradiction across rounds on the merits, and read a strictness finding as a claim about where the guard belongs.
- Scope a review brief to the range it should read, and treat a missing verdict as an incomplete run, not a verdict.
- Spend is rate times volume, never run count. Batch review by default: one pass over related changes also finds the defects that span them.
- A probationary reviewer leaves probation on an independent score and an approval another reviewer confirmed.

## Quota

- Usage-limit errors are routine: report, fall back to the other subscription or wait for the reset, and never retry-loop.
- Keep the scarcer pool's head model on judgment and push specified labor to the less scarce pool. Fast modes stay deliberate, never ambient.
- Each provider's quota is measured in its own terms, observed window share or published credits; never extrapolate one provider's accounting onto another. Observed figures are uncached; a warm cache stretches a window.

## Field evidence

- Every frontier release earns its own field record. A successor inherits its predecessor's weaknesses as precautions, never its record.
- A field note records the model, effort, harness and checkpoint it observed, and its cause keeps a brief's fault from being recorded as the model's.
- A roster copied into a consumer goes stale; point the consumer at a verb instead.

## Glossary

- **Intelligence:** how complex a problem the model completes correctly, unsupervised.
- **Taste:** cleanliness of UI and UX, architectural code quality, API design, copy.
