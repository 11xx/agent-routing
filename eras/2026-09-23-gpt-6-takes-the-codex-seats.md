# Model era: GPT-6 takes the Codex-side seats (2026-09-23 → )

The GPT-6 family replaced GPT-5.6 in every Codex-side seat, and DeepSeek V4.1
Flash became pi's default route for every GPT profile. Both moves were made by
operator direction. No GPT-6 row exists on this matrix, so this record states
what the seats rest on.

## Seats

| Profile | Codex route | Pi route |
| :--- | :--- | :--- |
| extract | gpt-6-luna low | deepseek-flash max (Go pool) |
| explore | gpt-6-luna max | deepseek-flash max (Go pool) |
| implement | gpt-6-luna max | deepseek-flash max (Go pool) |
| plan | gpt-6-astra medium; `astra-xhigh` variant | deepseek-flash max (Go pool) |
| execute | gpt-6-sol high | deepseek-flash max (Go pool) |
| review | gpt-6-astra medium; `fast` gpt-6-sol high; `high-stakes` gpt-6-astra xhigh | deepseek-flash max (Go pool) |
| interactive | — | deepseek-flash max (Go pool) |
| generate | — | deepseek-flash max (Go pool), stable |
| computer-use (experimental) | gpt-6-luna low / medium / high | the same, through pi's `openai-codex` provider |

The Claude variants and `design` did not move. `generate` left DeepSeek's own billing for the subsidised Go pool.

## What the seats rest on

- **Luna.** Vendor DeepSWE 66.6% (effort unstated), within noise of 5.6 Luna
  max's board row, at under half the price, and the operator's judgment that
  it is better and cheaper in use. Its tiers sit exactly where 5.6 Luna's
  measured seats were, because its own effort curve is unmeasured; whether it
  shares 5.6 Luna's low-effort cliff is the first thing real sessions settle.
- **Sol.** Vendor figures near Fable 5 xhigh on DeepSWE at about 80% less
  cost. High holds the seat 5.6 Sol high earned.
- **Astra.** Operator evidence that low and medium cover Sol-max-class work and
  that medium and high read alike, so medium holds plan and review and xhigh is
  the try-harder tier. The 2026-09-20 field arc measured context and quota
  behaviour, not capability; its context-carry weakness stands on the row.
  Review moved off Luna because the operator judged Luna too light for the
  reviewer of record.
- **DeepSeek V4.1 Flash on pi.** Three field arcs on the build in service
  (2026-09-18, 09-19, 09-22) and the operator's direction. No arc has tested
  its approvals, and every identifier it emits is still checked against
  source. V4 Pro is deprecated in favour of it.

## What changed around the seats

- GPT-5.6 Luna, Sol, and Terra are superseded; their measured rows remain as
  the evidence the successors were seated on.
- The GOAT (`commandcode`) pool is no longer used, so its variants and pool
  entry are gone and GLM 5.3 Flash is unrouted. The pi extension that reaches
  GOAT lives in the harness repository and is separate cleanup.
- Pi reaches all three GPT-6 models through `openai-codex` once its login is
  current, with a per-model `contextWindow` override matching the codex CLI's
  1.05M `model_context_window`. The profiles still send pi to DeepSeek by
  operator direction.

## What would move a seat

A Datacurve row for any GPT-6 model, a field arc showing GPT-6 Luna failing a
bounded slice that 5.6 Luna max landed, or an Astra approval that a later
review overturns.
