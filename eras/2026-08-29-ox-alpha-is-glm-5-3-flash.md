# 2026-08-29 — Ox Alpha is GLM 5.3 Flash, and leaves probation

The stealth route `ox-alpha`, probationary since 2026-08-23, was disclosed as
Z.AI's GLM 5.3 Flash. The two rows are one model, merged under
`glm-5.3-flash` with `ox-alpha` kept as an alias so the earlier record stays
readable. The undisclosed-provenance weakness retires with the identity: the
vendor is named, and the model is reachable through pi as
`z-ai/glm-5.3-flash` on the `commandcode` and `openrouter` providers, with the
provider always explicit because a bare model name is ambiguous across both
and aborts the run.

The probation bar was an independent pass@1 and one confirmed approval. What
retired it instead was a full implementation arc, field-measured on 2026-08-29:
a fork lifecycle command built in an unfamiliar Rust codebase, then thirteen
independent review findings repaired across five rounds, ending green with
every repair verified by probe. It disputed the reviewer where the reviewer
was wrong, said unprompted that its own fix was the weaker of two options, and
caught its own acceptance probe passing both before and after a change.

It enters as a cheap-lane implementer and adversarial reviewer beside Luna max,
which it matches in taste and capability while Luna follows a brief more
literally. Route by shape and by price: GLM when the slice's shape is still in
question or when cost decides, Luna when the slice is tightly specified with a
named gate. The pairing is the point — each reviews the other, on independent
providers and independent quota, so an implement-and-review loop needs no
expensive tier and the author never reviews its own diff.

Vendor-reported 63.4% on DeepSWE v1.1 stays out of the pass@1 column under the
standing rule for vendor benchmarks. List pricing is $0.15 per million input,
$0.03 cached, and $0.50 output, halved by a promotion running to 2026-09-09;
the row records list price so it does not expire. Per-task cost on this
benchmark is unmeasured, and the prices place it well under Luna max's $0.61.

Three caveats stand: no independent pass@1 here, no measured approval — every
round measured had it repairing findings rather than issuing verdicts — and an
operational hazard that will bite a caller who routes here without reading.
Three of seven long-brief dispatches never started, holding a socket without
ever reaching the model, one for two hours and three minutes. A healthy run
writes its session file in about nine seconds, so nothing routes here on a
critical path without a first-artifact watchdog.

The delegation consumers moved in the same pass. The three delegation skills
were replaced by the `agent-delegate` CLI, so `consumers.toml` now declares
that repository's proxy agents and sources instead of the retired skill trees.
