# ai-agent-routing

Which model to pick, at which effort, reached by which mechanism — as data,
with one accessor, for every harness and tool on this machine.

```sh
agent-routing models                  # the model/effort matrix
agent-routing delegation              # the mechanism matrix
agent-routing mechanism               # DELEGATION.md, the mechanism prose canon
agent-routing check opus-5 xhigh      # exits 1: prohibited
agent-routing doctrine                # authored prose used by every harness
agent-routing lint                    # check doctrine/manifest agreement
```

## Why it is its own repository

Routing policy is opinionated, personal, and churns on model-era boundaries.
It was living inside a skills repository, which meant skills appeared to change
every time a benchmark landed, and a second copy of the mechanism prose lived
inside `arc` — a tool meant to be usable by any model in any harness, which
cannot ship a document naming one person's two vendors.

Separating it lets `arc` and `tapes` own no routing opinion at all. Neither
picks models: `arc` records whatever `--model` string it is handed, and `tapes`
reports whatever a transcript contains. They are not consumers of this data and
should not become ones.

## What is authoritative

`routing/models.toml` and `routing/delegation.toml` are the machine-readable
source of truth. `doctrine/model-routing.md` and `DELEGATION.md` are the
authored prose sources for decisions the manifests cannot usefully express.

Queryable judgment lives inside the manifest as `role`, `character`,
`weaknesses`, and the `[policy]` block. The authored doctrine carries the
reader-oriented ordering and context that the manifest cannot express. They
are two representations of one policy; `agent-routing lint` makes their shared
model coverage and numbers a mechanical check rather than a remembered
synchronisation step.

| path | status |
| :-- | :-- |
| `routing/*.toml` | machine-readable source of truth — edit here |
| `doctrine/model-routing.md` | authored routing doctrine composed into every harness instruction file |
| `DELEGATION.md` | authored mechanism prose — how work reaches an executor |
| `eras/` | history; why a roster changed, kept when the roster moves on |

## The propagation path

```
doctrine/model-routing.md
    └─ agent-routing doctrine ─→ external fragment in ai-agent-instructions
                                    └─ bin/build writes ~/.claude/CLAUDE.md,
                                       ~/.codex/AGENTS.md,
                                       ~/.config/opencode/AGENTS.md,
                                       ~/.pi/agent/
```

The doctrine and manifest intentionally are not generated from each other: the
manifest keeps one queryable row per effort, while the doctrine compresses and
orders rows for a reader. `agent-routing lint` checks model coverage and every
number represented in both, so disagreement is detected before the instruction
build runs.

## What this repository will not do

**It will not pick a model for you.** `check` answers whether a tier is
prohibited, because that is a recorded fact. There is deliberately no
`agent-routing pick <task>`: selection is judgment, it is the head model's job,
and a CLI that encodes it becomes a stale oracle that is obeyed anyway.

**It will not verify identity or enforce anything.** Nothing here gates. A
harness that ignores this data is not stopped by it; the data only makes the
decision legible and the prohibitions unambiguous.

## Adding or revising a model

1. Edit `routing/models.toml`. Record `pass_at_1` from a real measurement and
   leave a field out rather than guessing it — an absent number is honest, an
   invented one is load-bearing.
2. Note what changed and why in `eras/` when a roster seat moves.
3. Run `agent-routing lint`, then `bin/build` from ai-agent-instructions.

Prohibitions carry a `use` string starting with `prohibited`; `check` keys on
that prefix, so the explanation and the enforcement stay in one place.
