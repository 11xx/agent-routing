# Model era: GPT-6.1 Sol takes the Sol seats (2026-09-29 → )

GPT-6.1 Sol replaced GPT-6 Sol in every seat it held, at the same tier, by
operator direction on its release day, and took the review seat from Astra
medium the same day. Astra keeps plan and the high-stakes variants, Luna keeps
its seats, and pi's profile defaults stay on DeepSeek. No GPT-6 row exists on
this matrix, so this record states what the moves rest on.

## Seats

| Profile | Route |
| :--- | :--- |
| execute | gpt-6.1-sol high (codex) |
| review | gpt-6.1-sol high (codex); `astra` variant gpt-6-astra medium; `high-stakes` gpt-6-astra xhigh |
| computer-use (experimental) | gpt-6.1-sol low; `medium`, `high`, `xhigh` comparison variants (codex, pi) |

Its max tier is explicit-only. `gpt-6-sol` is superseded and refused at every tier.

## What the move rests on

Artificial Analysis's launch-day Intelligence Index, index / cost per task. None
of it is a DeepSWE row, so none of it is in the pass@1 column.

| Effort | GPT-6.1 Sol | GPT-6 Sol | GPT-6 Astra |
| :--- | :--- | :--- | :--- |
| low | 42.1 / $0.13 | 33.9 / $0.13 | 45.8 / $0.82 |
| medium | 47.8 / $0.21 | 39.8 / $0.25 | 49.6 / $1.54 |
| high | 50.2 / $0.32 | 42.8 / $0.38 | 50.9 / $1.73 |
| xhigh | 51.0 / $0.39 | 44.1 / $0.52 | 52.4 / $2.31 |
| max | 51.8 / $0.72 | 47.5 / $1.05 | 52.7 / $3.26 |

The successor scores higher at every tier and costs no more at any tier. List
prices are unchanged at $2 / $10 per million, and the Codex credit rates match
GPT-6 Sol's apart from cached input, which halves. So the seats move at the tiers
they already held. Nothing about the seat itself was re-decided.

| Observation | Source |
| :--- | :--- |
| $2 input, $0.10 cached input, $2.50 cache write, $10 output per million; 2x input and cache, 1.5x output above 272k input tokens; 1.05M context, 128k maximum output | OpenAI model page |
| 50 / 2.5 / 250 Codex credits per million; Plus 15-160 local messages per five hours against GPT-6 Sol's 15-150 | Codex pricing page |
| Efforts low through max plus ultra; default low; 272k context, 872k maximum | Codex CLI 0.159.0 model cache |
| DeepSWE 1.1 75.2% at high, against Astra 74.8% and GPT-6 Sol 68.8% | vendor, as reported by launch coverage |
| OSWorld 2.0 71.4% at max, against Astra 73.5% | vendor, as reported by launch coverage |
| Works around explicit restrictions in 23.5% of cases, against GPT-6 Sol 64.4% and Astra 17.4% | vendor, as reported by launch coverage |
| GPT-6.1 Astra withheld over deception and acting without permission in internal testing | launch coverage |

The vendor's own post refused automated reads, so its figures are recorded as the
coverage reports them.

## Why max is explicit-only

The curve flattens above high. Xhigh buys 0.8 index points for 23% more per task,
and max buys another 0.8 for 84% more than xhigh and twice its wall-clock; the
field report's DeepSWE fork scored both below low and high. That keeps max out
of every automatic path and off the escalation ladder. It is not banned, by
operator direction: a prohibition has no override, and GPT-6 Sol max's ban was
a judgment about that model. A direct request runs it as a bounded trial read
against xhigh, on codex, since pi clamps it to high.

## Review moves off Astra

The launch-day index put 6.1 Sol high level with Astra medium at a fifth of the
cost per task. A field report from early access then supplied what an index
point cannot: review on real codebases. Theo Browne ("OpenAI fights back",
t3.gg, 2026-09-29, https://www.youtube.com/watch?v=vu8X3YroB-w) reports:

- a deep audit of his orchestrator level with Astra's, slightly above it on one
  scoring, at about half the price;
- first place at 87.4 in a blind ten-model codebase-improvement comparison,
  against Astra's 83.8;
- a real regression on a pull request, caught with code reading and computer
  use, that Opus 5.5 and Fable 5.1 had both missed;
- a blind Opus 5.5 judgment that it would pick this model over Astra for
  finding what is wrong, and rank it about level with Opus.

Review is where Codex spend concentrates, and 6.1 Sol's credits are a fifth of
Astra's at every token class (a tenth for cached input). So review moved to Sol
high on operator direction, and `fast` folded into the default. Astra medium
stays reachable as the `astra` variant for a second Codex-side judgment, and
Astra xhigh keeps `high-stakes`.

The same report sets the limits of the seat:

- **Long unattended building is below frontier.** It follows its process rules
  even when they stop all progress, and does not ask for help. A multi-day
  compiler port burned tokens without progress, and Opus 5.5 then made that
  progress in a day.
- **First drafts are harder to merge** than Opus 5.5's and carried real bugs.
- **Its judgment running machines** made more slips than Astra's.
- **Front-end work has no taste**, and fills the UI with slop copy.
- **Computer use is slightly below Astra**, and close enough to use it there.

Its author also runs the site the Artificial Analysis curve above was read
from, so the report and the curve are one source, not two.

## What did not move

- **Astra keeps plan and the high-stakes variants.** Nothing in the field
  report tests planning, and it has Astra making the fewest judgment slips of
  the models it compared, which is the axis a plan and a costly approval turn
  on.
- **The Sol line's fences stay.** 5.6 Sol's overbuild and over-determination
  weaknesses were fenced on GPT-6 Sol without a field arc to lift them. The
  restriction figure improved from 64.4% to 23.5%, which is still well short of
  lifting a fence. The field report adds a third, stalling without asking, so a
  long execute arc names a no-progress stop condition in its brief.
- **Pi's catalog lags.** Pi 0.99.0 does not list the model, so it is sent as a
  custom id with no thinking-level mapping. There, a requested xhigh or max
  clamps to high without saying so, and the computer-use xhigh comparison is a
  codex-only reading until the catalog carries the model.

## What would move a seat

A Datacurve row for GPT-6.1 Sol, a field arc where it fails a judgment-bearing
arc GPT-6 Sol landed, or a Sol approval that an Astra or Opus review on the
same diff overturns.
