# ai-agent-routing

Which model to pick, at which effort, reached by which mechanism — as data,
with one accessor, for every harness and tool on this machine.

```sh
agent-routing models                  # the model/effort matrix
agent-routing delegation              # the mechanism matrix
agent-routing mechanism               # DELEGATION.md, the mechanism prose canon
agent-routing check opus-5 xhigh      # exits 1: prohibited
agent-routing gen                     # regenerate the prose view from the data
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

`routing/models.toml` and `routing/delegation.toml` are the source of truth.
Everything else in this repository is either generated from them or is prose
they cannot express.

Judgment lives *inside* the manifest, as `role`, `character`, `weaknesses` and
the `[policy]` block — fields on the record they describe. This is deliberate.
A separate prose document restating the same decisions is a second source of
truth with a manual synchronisation rule, and that rule is always eventually
broken. Edit the field; the prose view follows.

| path | status |
| :-- | :-- |
| `routing/*.toml` | source of truth — edit here |
| `DELEGATION.md` | source of truth for mechanism prose — how work reaches an executor |
| `generated/model-routing.org` | generated; a named noweb block that `README.org` in ai-agent-instructions pulls in |
| `eras/` | history; why a roster changed, kept when the roster moves on |

## The propagation path

```
routing/models.toml
    └─ agent-routing gen ─→ generated/model-routing.org   (#+name: model-routing)
                                └─ noweb-referenced by ai-agent-instructions/README.org
                                        └─ tangled to ~/.claude/CLAUDE.md,
                                           ~/.codex/AGENTS.md,
                                           ~/.config/opencode/AGENTS.md,
                                           ~/.pi/agent/
```

The generated file is a named `markdown` src block carrying `:tangle no`, which
is the convention the instruction repository already uses for library blocks:
per-harness targets set `:noweb yes` and pull blocks in by name. It is a noweb
reference rather than `#+INCLUDE` because `org-babel-tangle` never expands
`#+INCLUDE` — that is an export-time feature, and a tangle would silently emit
the literal keyword instead of the content.

`agent-routing gen --check` fails when the generated view is stale, so the
staleness is detectable rather than discovered later in a harness that has been
reading a wrong number for a week.

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
3. `agent-routing gen`, then retangle from ai-agent-instructions.

Prohibitions carry a `use` string starting with `prohibited`; `check` keys on
that prefix, so the explanation and the enforcement stay in one place.
