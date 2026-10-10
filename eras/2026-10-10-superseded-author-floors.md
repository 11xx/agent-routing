# Model era: author floors for superseded implementers (2026-10-10 → )

A superseded model can remain the author of a shipped diff. Its unseated
efforts carry `author_floor` when shipped implementation history establishes
authorship, with a floor at least as high as its successor at the same effort.
Retirement grants no reviewer eligibility and does not relax family exclusions,
backend support, stable-route requirements, or selection prohibitions.

## Shipped-history inventory

The 2026-10-10 inventory examined `Implemented-by:` lines in commit bodies
reachable from local `master` and `main` branches, using `HEAD` for repositories
with neither branch. It covered 114 repositories: 109 with commit history and
five with no commits. Retained topic branches were excluded from shipped
evidence. None of the six superseded rows declares a manifest alias.

| Superseded model | Shipped implementation evidence | Author floors |
| :--- | :--- | :--- |
| gpt-6-sol | agent-delegate, agent-env, agent-harnesses, agent-routing, Arc, Muzaiten, Tapes | low/medium 1; high/xhigh 2; max 4 |
| gpt-5.6-luna | Tapes | low/medium/high/xhigh/max 1 |
| opus-5 | No matching implementer line | None |
| gpt-5.6-sol | No matching implementer line | None |
| gpt-5.6-terra | No matching implementer line | None |
| opus-4.8 | No matching implementer line; no declared efforts | None |

Examples include GPT-6 Sol's `e4a6302` in agent-delegate and `fdc3d0d` in
Tapes, and GPT-5.6 Luna's `214a084` in Tapes. The scan identifies historical
authorship, not the number of open review debts. Absence means no matching
implementer evidence in that inventory, not a claim about unrecorded work.

## Conservative floors

GPT-6 Sol uses GPT-6.1 Sol's floors at every effort. The successor's Artificial
Analysis curve is above its predecessor at every tier, as recorded in
`2026-09-29-gpt-6-1-sol-takes-the-sol-seats.md`. Requiring its review level is
conservative against that evidence.

GPT-5.6 Luna uses GPT-6 Luna's floor 1 at every effort. The successor's seats
rest on the predecessor's measured tiers and operator evidence of better
capability, recorded in `2026-09-23-gpt-6-takes-the-codex-seats.md`; no evidence
places the predecessor above the successor.

`resolve review --backend claude --author 'gpt-6-sol#xhigh'` selects Opus 5.5
xhigh with eligible independence and author tier 2. Sol max requires tier 4,
beyond every offered reviewer; omitting its effort also uses that highest
floor and recommends debt. GPT-5.6 Luna's efforts require tier 1. Models
without shipped authorship need no floor, and lint does not infer that history
or demand a floor merely because a row is superseded.
