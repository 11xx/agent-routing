# Capability ladder

Rank and floor use one cross-family capability scale: 1 for bounded work,
2 for a working technical peer, and 3 for deliberate deep review. A model's
size, price, routing seat, selection prohibition, and retirement do not decide
its capability. Every author floor has a reviewer rank in another family.
Pool ordering is a separate `seat_rank` map.

The following are policy judgments from the recorded evidence, not benchmark
scores. Rank and floor are equal at each tier. A range names every declared
effort in that range; other models' tiers are not inferred from it.

| Model | Rank and floor by effort | Evidence |
| :--- | :--- | :--- |
| opus-5.5 | low/medium 1; high/xhigh 2; max 3 | [launch](2026-09-22-opus-5-5-head-model.md), [Claude curve](2026-10-09-claude-roster-refresh.md), [field tiers](2026-10-24-opus-5-5-efforts-head-high-implement-low.md) |
| opus-5 | low 1; medium/high/xhigh/max 2 | [DeepSWE and plateau](2026-07-25-opus-5-head-model-era.md) |
| fable-5 | low/medium 1; high/xhigh/max 2 | [Sol parity and plateau](2026-07-12-fable-5-subscription-era.md); medium is conservatively in the low band |
| fable-5.1 | low/medium 1; high/xhigh 2; max 3 | [Claude curve](2026-10-09-claude-roster-refresh.md), [author comparison](2026-10-13-fable-author-floors.md) |
| sonnet-5.5 | low/medium 1; high/xhigh 2; max 3 | [effort curve](2026-09-28-sonnet-5-5-enters-on-trial.md), [author comparison](2026-10-10-trial-author-floor.md) |
| haiku-5.5 | low/medium/high/xhigh/max 1 | [candidate curve](2026-10-07-haiku-5-5-candidate.md), [audit repairs](2026-10-08-haiku-5-5-audit-repairs.md) |
| gpt-5.6-sol | low/medium 1; high/xhigh/max/ultra 2 | measured roster: medium 61%, high 69%, xhigh 71%, max 73%; [Fable parity](2026-07-12-fable-5-subscription-era.md); ultra has no established gain over max |
| gpt-6-sol | low/medium 1; high/xhigh/max 2 | [succession](2026-09-23-gpt-6-takes-the-codex-seats.md), [comparison curve](2026-09-29-gpt-6-1-sol-takes-the-sol-seats.md) |
| gpt-6.1-sol | low/medium 1; high/xhigh/max 2 | [review field comparison and flattening curve](2026-09-29-gpt-6-1-sol-takes-the-sol-seats.md); max adds no separate capability band |
| gpt-6-astra | low/medium 2; high/xhigh/max 3 | numeric ladder at dc54196, [availability](2026-09-05-astra-availability-evidence.md), [comparison curve](2026-09-29-gpt-6-1-sol-takes-the-sol-seats.md) |
| gpt-5.6-terra | high/xhigh 1; max 2 | measured roster's 54%, 60%, 70% DeepSWE tiers |
| gpt-6.1-terra | low/medium/high/xhigh/max 2 | operator's peer classification in the roster; selectable medium/high/xhigh remain separate route facts |
| gpt-5.6-luna, gpt-6-luna | low/medium/high/xhigh/max 1 | [field review](2026-08-18-luna-reviewer-off-probation.md), [succession](2026-09-23-gpt-6-takes-the-codex-seats.md) |
| sonnet-5 | low/medium/high/xhigh/max 1 | roster's dominated bounded-work classification; no peer-level review evidence |
| opus-4.8 | high/max 1 | [predecessor comparison](2026-07-25-opus-5-head-model-era.md), 52% and 59% DeepSWE |
| gpt-5.5 | low/medium 1; high/xhigh/max 2 | roster's predecessor relation; conservative Sol-family floor, no promotion over its successor |
| kimi-k3 | max 2 | measured roster 69%, long-horizon field characterization in the roster |
| grok-4.6 | xhigh 1 | measured roster 67%, bounded second-opinion classification |
| muse-spark-1.2, muse-spark-1.3 | xhigh 1 | [field evidence](2026-08-05-muse-spark-and-field-corroboration.md), roster's unconfirmed-approval limit |
| deepseek-flash | low/high/max 1 | [field test](2026-10-08-deepseek-v41-go-muzaiten-field-test.md), [1017 field arc](2026-10-29-deepseek-flash-1017-mahaf-engine-field-arc.md) |
| deepseek-v4-pro | max 1 | [generator-only evidence](2026-08-01-deepseek-generator-only.md) |
| glm-5.3-flash | high/max 1 | [measured build](2026-08-29-ox-alpha-is-glm-5-3-flash.md) |
| gemini-3.8-flash | high 1 | [independent roster measurements](2026-09-03-september-releases-enter-unseated.md) |
| glm-5.3 | max 1 | [independent roster measurements](2026-09-03-september-releases-enter-unseated.md) |
| mimo-v2.6-flash | high 1 | [probation evidence](2026-09-22-mimo-v26-enters-probation.md) |
| mimo-v2.6-pro | medium/high 1 | [sibling classification](2026-09-22-mimo-v26-enters-probation.md); the retained ledger records implementation at medium |
| small-model-class | default 1 | roster's bounded, dominated class; `default` denotes the class rather than an invented reasoning effort |

## Historical reconstruction

The numeric record begins at dc54196, committed 2026-10-07T04:51:04Z.
Earlier reads, from 2026-08-01, fall in a gap. No rank is supplied for that
span. Within the numeric era, each commit's model roster, efforts, identities,
family relation and retirement state are retained. Its `review_tier` or
`author_floor` supplies the numeric band where present. Tiers without either
use the judgments above, explicitly sourced here. Effort-less predecessor rows
use their recorded effort sets. Legacy level 4 was an unreachable seat
requirement: the documented capability judgment supplies its rank and floor,
including Sol max at 2 and the deep Claude and Astra tiers at 3.

These are reconstructed tables, not a claim that unranked tiers already had
numeric capability declarations. A source names both the original commit and
this reconstruction evidence. Consecutive equal capability tables produce one
version, so prices and seating changes alone do not change a version.

Model family names identify labs: Claude is Anthropic; GPT-5.5, GPT-5.6 and
GPT-6 are OpenAI. Historical harness spellings belong in identities. Retired
rows remain available to assessment without becoming selectable routes.
