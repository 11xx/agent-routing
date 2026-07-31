# Model era: Terra/Luna price and credit reset (2026-07-30 → )

OpenAI cut GPT-5.6 Terra's standard API token prices by 20% and Luna's by 80%
without changing the measured capability or output-token rows. At the same
time, the Codex documentation began publishing the corresponding subscription
credit rates and approximate five-hour message ranges. That closed the open
question of whether the Codex pool was token-counted or model-weighted.

## Price and subscription evidence

Prices are per million short-context tokens. Credits are per million tokens in
ChatGPT Work and Codex.

| Model | API input / output | Subscription input / output credits | Plus local messages / 5h |
| :--- | :--- | :--- | :--- |
| Sol | $5 / $30 (unchanged) | 125 / 750 | 10–100 |
| Terra | $2 / $12 (was $2.50 / $15) | 50 / 300 | 25–200 |
| Luna | $0.20 / $1.20 (was $1 / $6) | 5 / 30 | 250–2,000 |

Context, reasoning, tools, retrieval, and caching make the published message
ranges approximate rather than exact transforms of the credit schedule. Every
token class for all three models costs 25 credits per API dollar, so task-level
subscription-credit ratios equal the benchmark cash ratios. Codex fast mode
consumes 2.5 times the standard credits.

Applying the uniform token-price cuts to the existing DeepSWE token mix moves
Terra high from $1.13 to about $0.90 per task and Luna high from $0.78 to about
$0.16. The benchmark capability and token counts are unchanged.

## Routing consequence

- **Terra high** is the default workhorse for bounded production work, including
  fully pre-resolved slices and tasks retaining ordinary judgment. It beats Sol
  low by nine points and costs 84% as much in both API cash and task-level
  subscription credits.
- **Luna high** is a probationary pre-resolved executor. It nearly matches Sol
  low's pass@1 for about 15% of its cash and credit cost, but the price change
  supplies no new capability evidence. Controlled field trials with exact
  probes and lead review precede any ambient promotion.
- **Sol medium/high** retain technical judgment, reviewer, and long-horizon
  roles. Sol low is no longer an ambient route; its remaining advantage is
  output-token efficiency, which needs a concrete compatibility or latency
  reason to matter.
- Luna low/medium remain fixed-shape workflow tiers. Price does not repair the
  measured effort cliff. Luna xhigh/max are economical experimental
  planned-execution tiers, but their unmeasured field reliability, long outputs,
  and step counts keep them out of default, lead, and reviewer roles.

## DeepSeek V4 status on 2026-07-31

DeepSeek separately released the re-post-trained V4 Flash 0731 API in public
beta. It is adapted for the Responses API and Codex and is live through the Pi
backend on this machine. DeepSeek reports 54.4 on DeepSWE at max effort, but the
run used its own unreleased Harness minimal mode, so the number is not treated
as directly comparable to the neutral roster.

The callable V4 Pro endpoint remains the April preview. DeepSeek says the final
Pro release will follow soon; it did not ship alongside Flash 0731. Flash enters
as an experimental bounded executor with exact probes and lead review. Pro keeps
only its measured defect-generation niche until the final endpoint is released
and tested.

## Primary sources

- OpenAI API pricing: https://developers.openai.com/api/docs/pricing
- OpenAI Codex pricing and credits: https://learn.chatgpt.com/docs/pricing
- DeepSeek release log: https://api-docs.deepseek.com/updates/
- DeepSeek models and pricing: https://api-docs.deepseek.com/quick_start/pricing/
