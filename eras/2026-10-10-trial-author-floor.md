# Model era: author floors for unseated trials (2026-10-10 → )

A diff's author requirement and a model's reviewer eligibility are separate
policy decisions. A stable profile route seats a tier; that tier carries
`review_tier` for both its reviewer level and the minimum level for review of
its diffs. An unseated tier may carry `author_floor` for the latter requirement
alone. Neither field is a benchmark score or a pool-local escalation rank.

## Sonnet 5.5 author requirements

Sonnet 5.5's floors match Opus 5.5 at each effort:

| Effort | Author floor | Launch-day Sonnet / Opus index |
| :--- | :--- | :--- |
| max | 4 | 56 / 58 |
| xhigh | 2 | 52 / 56 |
| high | 2 | 47 / 54 |
| medium | 1 | 41 / 51 |
| low | 1 | 36 / 42 |

The Artificial Analysis Intelligence Index v4.3.2 observations, recorded in
`2026-09-28-sonnet-5-5-enters-on-trial.md`, place Sonnet at or below Opus at
every effort. Requiring the same review level is conservative against that
evidence. It does not establish Sonnet's capability as a reviewer. Sonnet has
no profile seat and remains an operator-directed trial.

## Routing and refusal

Review author lookup uses `review_tier` when present and `author_floor`
otherwise. Without an effort, it requires every effort to have a declared
floor and uses the highest. Unknown floors recommend Arc review debt.

Sonnet xhigh has author floor 2 and can receive independent review from the
stable Codex route, GPT-6.1 Sol xhigh. Sonnet max has floor 4; every offered
review route is below 4, so its diffs require recorded review debt. Family
exclusions, stable-route eligibility, backend support, and pool policy still
bind. An author floor does not add a route or make a trial a reviewer candidate.

Lint requires positive integer floors, `review_tier` on every seated tier,
and `author_floor` only on unseated tiers. Author requirements are independent
of pool-local ranks and profile seats.
