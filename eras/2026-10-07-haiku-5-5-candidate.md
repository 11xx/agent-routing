# Claude Haiku 5.5: a candidate beneath the standing workhorses

Claude Haiku 5.5 is available under the fixed model id `claude-haiku-5-5` with
five effort levels. It enters the roster as a Claude-side candidate selected
through an operator-directed, experimental validation. No profile or fallback
uses it. GPT-6 Luna keeps bounded Codex implementation, and DeepSeek V4.1 Flash
keeps the OpenCode Go and steered-generation seats until a comparison on real
work establishes a different allocation.

## What is known

[Anthropic's model overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview)
records a 1M-token context, 128k maximum output, adaptive thinking, and medium
as the Claude Code and API default effort. The
[pricing table](https://platform.claude.com/docs/en/about-claude/pricing) has
two regimes for a whole prompt:

| Prompt size | Input / MTok | Cache read / MTok | 5m cache write / MTok | Output / MTok |
| :--- | ---: | ---: | ---: | ---: |
| Up to 100k input tokens | $0.10 | $0.01 | $0.125 | $0.50 |
| Over 100k input tokens | $0.50 | $0.05 | $0.625 | $2.50 |

The [migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide)
says its newer tokenizer counts approximately 30% more tokens than Haiku 4.5
for the same text. That comparison says nothing about its token count relative
to Luna or DeepSeek. API list prices do not establish subscription quota weight.

[Anthropic's release table](https://www.anthropic.com/claude-haiku-5-5)
compares Haiku 5.5 with GPT-6 Luna:

| Vendor-run measure | Haiku 5.5 | GPT-6 Luna |
| :--- | ---: | ---: |
| GDPval-AA v2.1 Elo | 1620 | 1437 |
| Terminal-Bench 4.0 | 39.2% | 16.4% |
| FrontierCode 1.1 Main | 46.4% | 42.4% |
| OSWorld 2.1 offline subset | 72.4% | 48.9% |

The table does not identify an effort for each score. It belongs to Anthropic's
evaluation and does not fill this roster's DeepSWE pass@1 or per-task cost
cells. Anthropic positions Haiku for short, high-volume work and acknowledges
that Sonnet 5.5 and Opus 5.5 remain better for complex agentic coding.

The user-supplied [Slopalytics comparison](https://slopalytics.com/?models=gpt-6-astra,gpt-6-1-sol,claude-opus-5-5,claude-fable-5-1,claude-haiku-5-5,gemini-4-argon,gpt-6-luna,deepseek-v4-1-flash,glm-5-3-flash)
labels its data as Artificial Analysis. Its static snapshot says it was fetched
2026-10-07T19:25:38Z. These are Intelligence Index points and costs per index
task on that proxy, not this repository's task distribution:

| Proxy variant | Index | Cost per index task | Output speed | Time per task |
| :--- | ---: | ---: | :--- | :--- |
| Haiku 5.5 xhigh | 41.25 | $0.124 | unavailable | unavailable |
| Haiku 5.5 max with fallback | 43.40 | $0.213 | unavailable | unavailable |
| GPT-6 Luna max | 38.12 | $0.068 | 127.9 tokens/s | 389.6s |
| DeepSeek V4.1 Flash max | 39.46 | $0.265 | 216.1 tokens/s | 289.2s |
| GLM 5.3 Flash max | 41.81 | $0.253 | 51.2 tokens/s | 1035.4s |

Haiku low, medium, and high have index points but no cost values in the
snapshot; all Haiku speed and time values are absent. The meaning and effect of
its `with fallback` variant label are not established by the proxy. Its xhigh
point is above Luna and DeepSeek on this index, with a higher per-task cost than
Luna and lower than DeepSeek. Nothing here proves Haiku is faster in this
workflow, cheaper on a real task, or safe as the last model to touch a patch.

## Trial boundary

Medium and high are probationary. Low is explicit-only because
[Anthropic's prompting guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5)
warns that low can skip searches and checks in long agent prompts. Xhigh is
explicit-only because it sometimes finishes with no visible answer after
putting the answer in thinking. Max is explicit-only because no field result
calibrates its additional cost or failure style. Every selection needs
`--allow-experimental` and a reason; no standing route points here.

The comparison that could earn a seat uses the same bounded briefs and
acceptance probes for Haiku medium/high/xhigh, Luna max, and DeepSeek V4.1 Flash
max. Record accepted artifacts, defects that survived the executor's checks,
repair rounds, wall time, output tokens, context size, quota or subscription
weight, and refusals. Run short and over-100k-context shapes separately because
the API price tier changes. DeepSeek's open-weight/local-data role remains
separate from hosted model quality. A route moves only after the field record
shows where Haiku helps, not because one launch chart favors it.
