# Haiku 5.5 max on two bounded audit repairs (2026-10-08)

Two operator-directed Claude Code runs used `claude-haiku-5-5#max` to repair
independently identified muzaiten defects. Both retained native initialization
records identify the served model, and the route records requested max through
the first-party experimental implementation path. No standing route changed.

| Measure | Taste seed-store bounds | NOTICE scope parser |
| :-- | --: | --: |
| Dispatch-to-terminal wall time | 34m56s | 9m08s |
| Claude-reported API duration | 12m24s | 8m21s |
| Turns | 87 | 39 |
| Output tokens, including thinking | 170,718 | 120,607 |
| Thinking tokens | 127,725 | 99,771 |
| Cache-read input tokens | 12,552,855 | 3,793,392 |
| Cache-creation input tokens | 277,307 | 179,850 |
| Reported `total_cost_usd` | $1.21554023 | $0.47387646 |
| Requested and applied memory limit | 6 GiB | 3 GiB |

The dollar values are Claude Code's API-list-price equivalents, not measured
subscription spend. Reported API duration covers the client's model calls;
it does not isolate token-generation time. Supervisor artifact discovery was
delayed and is not a valid first-content latency measure in these samples.

The taste repair reproduced a 31-seed store that successful imports made too
large for its own reader, then unified read/write bounds while retaining the
indented storage format. The delivered signed commit `9270654`, retained as
`92706542` with the same source tree and corrected attribution, passed a full
build and 83/83 suites, including real CLI boundary and legacy-store probes.
It also rejects compact input exceeding the normalized exchange-size bound;
that additional behavior is part of the pending batch review. A baseline build
exceeded its foreground timeout and had to resume, and an overlong temporary
directory triggered an existing Unix-socket path limit before the final suite
passed. The wall time includes that build and probe work.

The notice repair admitted safe underscores in the filename grammar. Its
signed commit `0459fc9`, retained as `0459fc99` with the same source tree and
corrected attribution, added actual-inventory and mixed-attribution probes,
with baseline failure and candidate success. Four focused Python tooling
suites passed; the lead independently reran the 20-test notice suite. The
lane deliberately ran no compiler, leaving its full build/test gate to the
serialized batch. It identified a separate location-aware table-scope issue
and left that contract unchanged. No rare-Han data or source-rights decision
was made.

Both runs delivered reviewable patches and preserved failed attempts. Their
requested GPT-6.1 Sol xhigh and Opus xhigh batch review has not yet completed,
and neither patch is integrated in this observation. Passing tests and a
clean signed delivery do not establish independent acceptance.

These are different task shapes, not an xhigh/max pair or a matched comparison
against Luna or DeepSeek. The notice task still spent about 83% of its output
tokens on thinking at max. That is useful effort-cost evidence for a bounded
parser repair, not proof that a lower effort would produce the same patch.
The [playlist trial](2026-10-08-haiku-5-5-muzaiten-field-test.md) remains the
matched effort comparison. No capability, quota-efficiency or routing seat
is inferred from these two samples.

Evidence: the agent-routing journal filing
`20261008T060728Z-haiku-audit-repair-model-notes-todo.md` names the private
checksummed trial bundles, route and native records, metrics, full reports,
probes, failed controls and source artifacts. Later acceptance and additional
xhigh deliveries require separate observations.
