# The Codex plan seat moves to GPT-6.1 Sol at xhigh (2026-10-29)

The operator moved `plan`'s Codex seat from `gpt-6-astra#medium` to
`gpt-6.1-sol#xhigh`: Astra is the older generation, and Sol plans at least as
well. The earlier choice of Astra rested on its low write rate at higher
efforts (apply_patch on 16.3% of tool calls at low, 0.8% at high), from which
medium was taken as the economical seat. Sol already holds the execute and
review Codex seats at xhigh.

`plan:astra-xhigh` stays selectable by name. It is also the stable route that
seats Astra's xhigh tier for review ranking.
