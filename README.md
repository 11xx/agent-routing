# ai-agent-routing

Which model to pick, at which effort, reached by which mechanism — as data,
with one accessor, for every harness and tool on this machine.

```sh
agent-routing                         # the routing guide: start here
agent-routing models                  # the model/effort matrix
agent-routing profiles                # named task-shape routes
agent-routing resolve implement --backend codex --json
agent-routing delegation              # the mechanism matrix
agent-routing mechanism               # DELEGATION.md, the mechanism prose canon
agent-routing check opus-5 xhigh      # exits 1: prohibited
agent-routing doctrine                # authored prose used by every harness
agent-routing lint                    # check doctrine/manifest agreement
agent-routing lint-consumers          # reject roster pins in active consumers
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

`routing/models.toml`, `routing/profiles.toml`, and
`routing/delegation.toml` are the machine-readable source of truth.
`doctrine/model-routing.md` and `DELEGATION.md` are the
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
| `doctrine/guide.md` | the routing guide, printed by the bare invocation |
| `doctrine/model-routing.md` | authored routing doctrine, read on demand via `agent-routing doctrine` |
| `DELEGATION.md` | authored mechanism prose — how work reaches an executor |
| `eras/` | history; why a roster changed, kept when the roster moves on |

## The propagation path

A harness instruction file carries a short pointer to this CLI rather than a copy
of the roster, so the policy is read when a routing decision is actually in front
of an agent instead of occupying every context window.

```
routing/*.toml             ─→ agent-routing resolve   one caller-selected route
doctrine/guide.md          ─→ agent-routing           the guide, bare invocation
doctrine/model-routing.md  ─→ agent-routing doctrine  the policy in full
```

`ai-agent-instructions` composes that pointer into `~/.claude/CLAUDE.md`,
`~/.codex/AGENTS.md`, `~/.config/opencode/AGENTS.md`, and
`~/.pi/agent/AGENTS.md`. Nothing downstream embeds the roster, which is what
`agent-routing lint-consumers` exists to enforce.

The doctrine and manifest intentionally are not generated from each other: the
manifest keeps one queryable row per effort, while the doctrine compresses and
orders rows for a reader. `agent-routing lint` checks model coverage and every
number represented in both, so disagreement is detected before the instruction
build runs.

`agent-routing lint-consumers` scans the active delegation surfaces in the two
direct consumer repositories. It rejects concrete model IDs and static agent
model frontmatter while leaving tests and historical manifests out of scope.
The proxy-shell agent aliases are the one deliberate exception: their
version-agnostic Claude alias is required by Claude's static agent frontmatter,
and the central delegation manifest records that shell-only policy.

## Named route profiles

Callers classify work by task shape and pass that choice to the resolver. The
resolver is a pure local table read: it does not inspect the task, access the
network, cache results on disk, or choose a profile. A successful response has
exactly the concrete route and a hash of the three routing manifests for durable
logs:

```sh
agent-routing resolve extract --backend pi --json
agent-routing resolve generate --backend pi --allow-experimental --json
```

Profiles stay on one axis: extraction, exploration, candidate generation,
bounded implementation,
broad execution, planning, review, design, or an interactive harness default.
Backend sandboxing, tool fences, output capture, and
liveness remain adapter behavior in `DELEGATION.md` and the backend skills.
Probationary and experimental variants fail closed unless the caller explicitly
passes `--allow-experimental`.

## What this repository will not do

**It will not classify work for you.** `resolve` maps a caller-selected profile
to the current route, and `check` answers whether a tier is prohibited. There
is deliberately no `agent-routing pick <task>`: classification is judgment,
it is the head model's job, and a CLI that guesses becomes a stale oracle.

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
