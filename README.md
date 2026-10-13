# agent-routing

Which model to pick, at which effort, reached by which mechanism — as data,
with one accessor, for every harness and tool on this machine.

```sh
agent-routing                         # the routing guide: start here
agent-routing models                  # the model/effort matrix
agent-routing profiles                # named task-shape routes
agent-routing seats --json            # derived bindings and the declared head default
agent-routing resolve implement --backend codex --json
agent-routing validate --profile plan --backend codex --model gpt-6-astra \
  --effort medium --provider openai-codex --reason "operator directed" \
  --allow-experimental --json
agent-routing delegation              # the mechanism matrix
agent-routing mechanism               # DELEGATION.md, the mechanism prose canon
agent-routing check opus-5 xhigh      # exits 1: prohibited
agent-routing doctrine                # authored prose used by every harness
agent-routing lint                    # pass@1/cost cells, coverage, routes
agent-routing lint-consumers          # reject roster pins in active consumers
```

For a tuple the operator named exactly, `validate --operator-named` permits
explicit-only and experimental selection while preserving bans and backend and
pool support. Refusals list stable seated efforts for the requested tuple's
profile and supported routes for its backend. `agent-routing seats --json`
shows the bindings before a selection; `check` tests prohibition alone.

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
model coverage, their pass@1 and cost cells, and route structure a mechanical
check rather than a remembered synchronisation step.

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
routing/*.toml             ─→ agent-routing validate  one explicit tuple
doctrine/guide.md          ─→ agent-routing           the guide, bare invocation
doctrine/model-routing.md  ─→ agent-routing doctrine  the policy in full
```

`agent-harnesses` composes that pointer into `~/.claude/CLAUDE.md`,
`~/.codex/AGENTS.md`, `~/.config/opencode/AGENTS.md`, and
`~/.pi/agent/AGENTS.md`. Its `agent-harness delegation-sources` accessor
declares the instruction and agent surfaces to `agent-routing lint-consumers`;
nothing downstream embeds the roster, which is what that guard exists to
enforce.

The doctrine and manifest intentionally are not generated from each other: the
manifest keeps one queryable row per effort, while the doctrine compresses and
orders rows for a reader. `agent-routing lint` checks model coverage, route
structure, and the pass@1 and cost cells the doctrine table restates, so a
number that drifts is caught before anything reads it.

It does not read the doctrine's prose, nor the table's other columns. A rule
stated wrongly in sentences is caught by review or not at all, which is why an
authored change here carries a reviewer rather than only a green gate.

`agent-routing lint-consumers` scans the active delegation surfaces in the two
direct consumer repositories. It rejects concrete model IDs and static agent
model frontmatter while leaving tests and historical manifests out of scope.
The proxy-shell agent aliases are the one deliberate exception: their
version-agnostic Claude alias is required by Claude's static agent frontmatter,
and the central delegation manifest records that shell-only policy.

Consumer siblings are found beside the canonical checkout through Git’s common
directory, including when the lint runs from a linked worktree.
`AGENT_CODE_ROOT` overrides that location for an isolated consumer tree.

The `[[accessor]]` entry in `routing/consumers.toml` owns a floor,
`expected_sources`: the source ids its accessor must report. The lint exits
nonzero, naming the missing ids, when the accessor reports fewer, and when an
accessor declares no floor, so a harness-side regression cannot shrink what is
checked. Sources beyond the floor are checked as well.

## Named route profiles

Callers classify work by task shape and pass that choice to the resolver. The
resolver is a pure local table read: it does not inspect the task, access the
network, cache results on disk, or choose a profile. A successful response carries
the concrete route and a hash of the three routing manifests for durable logs.
Review responses also carry author eligibility constraints:

```sh
agent-routing resolve extract --backend pi --json
agent-routing resolve generate --backend pi --allow-experimental --json
```

On the Claude backend `explore` and `extract` default to Haiku 5.5 at high, the
cheap subscription seat for read-only reconnaissance and fixed-shape
extraction; `explore --variant opus` selects Opus 5.5 xhigh. Haiku is reached
only through the `claude` backend, never through an API-billed pool.

Profiles stay on one axis: extraction, exploration, candidate generation,
bounded implementation,
broad execution, planning, review, design, or an interactive harness default.
Backend sandboxing, tool fences, output capture, and
liveness remain adapter behavior in `DELEGATION.md` and the backend skills.
Probationary and experimental routes fail closed unless the caller explicitly
passes `--allow-experimental`, a whole profile as much as a variant.

The `computer-use` profile is an explicit experimental desktop-worker route,
separate from coding implementation. It supports Codex and Pi, defaulting to Sol
low; `--variant medium` and `--variant high` select explicit comparison tiers
on either backend. `--variant xhigh` is supported on Codex alone. All require `--allow-experimental`; no failure automatically
escalates the model.

Claude can run Opus 5.5 for this profile through an explicit `--variant opus`
or an operator-directed model selection. There is no Claude default for
`computer-use`; either path requires `--allow-experimental`.

Desktop access and the retained run/resume lifecycle are owned by agent-delegate.
The route does not restrict CU capabilities or claim a measured cost/quality win.

### Author-aware independent review

Supply the diff author's model and effort when resolving independent review:

```sh
agent-routing resolve review --backend claude --author 'gpt-6.1-sol#xhigh' --json
```

`--author` is valid only for `review`. Roster aliases and backend model IDs are
canonicalized; `ARC_MODEL` is not read, because the caller may differ from the
diff author. A model without `#effort` uses its highest declared review floor.
If any of that model's efforts lacks a floor, supply the recorded effort or
expect a refusal. Model families and excluded author families must be nonblank strings without
surrounding whitespace; malformed families invalidate the manifest, and every
family comparison reads the trimmed value. Unknown author models, efforts, or review floors recommend
debt rather than inferring eligibility.

Each review route declares `excluded_author_families` in `profiles.toml`.
Variants inherit the base profile's exclusions unless they declare their own;
every route must exclude its reviewer's family. This fences the Claude and GPT
pools by model lineage, including a model reached through another provider.
`review_tier` in `models.toml` sets a seated tier's reviewer tier and author
floor. An unseated tier may carry `author_floor`, which sets only the author
requirement and grants no reviewer eligibility. Superseded models with shipped
implementation history carry floors at least as high as their successors at
each declared effort; retirement does not remove a diff's review requirement.
Superseded rows without shipped authorship need no floor. Lint requires `review_tier`
on every seated tier and refuses either field on the other kind of tier.
Both fields use the same cross-family scale:
1 is bounded work, 2 a working technical peer, 3 the high-stakes tier, and 4
an explicit top effort beyond the offered review seats. These are conservative
policy floors, independent of benchmark scores and pool-local escalation ranks.
An unclassified model or effort has no assumed position on this scale.

An author-aware result requires a stable route outside the excluded families
with `reviewer_tier >= author_tier`. The backend default keeps precedence when
eligible; otherwise the resolver checks the remaining routes in manifest order
on that same backend. An explicit `--variant` confines eligibility to that
variant. It never switches backends. Experimental opt-in cannot waive
independence or the author floor.

Successful review JSON adds `review` with `author`, `independence`,
`excluded_author_families`, and `reviewer_tier`; author-aware results also carry
`author_tier` and report `independence: "eligible"`. This is route eligibility,
not a review verdict or proof that a different actor performed the review.
For a diff with multiple authors, check every author; one coordinate does not
certify the others.

Without `--author`, the same concrete route remains available and `review`
reports `author: null` and `independence: "unverified"`, alongside its family
exclusions and reviewer tier. Callers must inspect this field before claiming
independence. Existing consumers that parse only the concrete route fields
continue to run, but do not establish author eligibility.

If no eligible route exists, resolution exits 1 with empty stdout. The final
stderr line is an `agent-routing-refusal/1` payload with
`kind: "review-independence"`, a `reason`, and `recommendation: "record-debt"`.
Record Arc review debt or wait for eligible capacity according to repository
policy; debt never overrides a changes-requested verdict. Non-review routes
keep their concrete output contract.

## Seat bindings

`seats` projects the profile and variant bindings, including labeled trials,
with their backend, provider, model, effort, stability and route version.
The head-default query is the `plan` profile on Claude. An absent binding
reports a null default and its resolver refusal. The actual head is unobserved. Ambient model variables do not establish a session.
Evidence references are null where the manifests declare none. There is no
separate seats manifest; model bars and review eligibility keep their existing
sources.

## Review frontier

```sh
agent-routing frontier --author 'opus-5.5#xhigh' --reads 'gpt-6.1-sol#xhigh' --json
```

`frontier` answers the strongest review seat eligible for an author, as
`agent-routing-frontier/1`: the `route_version`, the author with its floor, a
`status`, and `frontier`, the highest `review_tier` with every seat at that
tier as a model, effort, backend and pool. A caller that stores the reads a
change received compares them against it at read time, so no tier is ever
stored.

A seat is a stable review route on any backend whose pool serves its model:
a route whose effective `excluded_author_families` is set, the kind
`resolve review` can sell. A seat on another profile never raises the
frontier. Eligibility is `assess`'s verbatim: the frontier adds no independence
rule. Seats are ordered by `review_tier`, the cross-family scale `assess`
compares, never by the pool-local `rank`. Quota is not an input, so an
exhausted pool still marks the frontier and a clearance cannot flip on a pool
running dry. An author whose floor is unestablished answers `floor-unknown`
with no frontier; one whose floor no seat reaches answers `no-eligible-seat`.

Each `--reads` coordinate returns its `assess` result under the same route
version and a `standing` of `below`, `at` or `above` the frontier's tier, or
`unranked` when the read's tier is unseated or no frontier exists. Standing
compares tiers only; the read's own independence is its assessment's.

## Operator-directed selection

An explicit one-off model choice keeps the execution shape separate from model
resolution. Call `validate` with the base profile, backend, model, effort,
provider, and a nonblank reason:

```sh
agent-routing validate \
  --profile plan --backend codex --model gpt-6-astra --effort medium \
  --provider openai-codex --reason "operator directed" \
  --allow-experimental --json
```

The command does not resolve the profile or select a variant. Its JSON result
records the base execution profile, canonical and backend model identities,
the applied opt-ins, the `route_version` witness, and where the tuple sits
relative to the route the profile would have chosen. A prohibited tier,
unsupported model/backend or effort fact, unknown pool membership, or model-role
restriction refuses before any of that. A known cross-pool selection
additionally requires `--allow-cross-pool`; that opt-in does not waive missing
backend, model, or effort support.

Each backend in `delegation.toml` declares `supported_efforts`, the common
levels it can send without dropping or clamping them. `model_efforts` maps
canonical model IDs to lists that replace that common set for a particular
catalog mapping. An empty set supports no effort. Structural lint checks
these declarations and every profile/backend pairing; both `resolve` and
`validate` enforce them, regardless of experimental or cross-pool opt-ins.
Pi's declared Sol support ends at high; its DeepSeek mapping supports max.
A custom Pi model declaration must be verified and recorded in the capability
data before it can authorize a higher tier. OpenCode's delegated v2 provider
supports no effort variants. Catalog presence alone does not establish support.

`baseline` is the tuple `resolve` would return for the profile and backend,
as `<canonical model>#<effort>`, or null when no route answers that backend.
`direction` compares policy ranks inside the selection's pool: `same` for the
baseline itself, `upgrade`, `lateral` or `downgrade` when both ends are
ranked there, and `unranked` otherwise. Ranks live on seated tiers in
`models.toml` as `rank = { "<pool>" = <n> }`; they are operator policy, not
measured capability, and compare only within one pool. A tuple is eligible
when the profile, or a profile it names in `escalation_sources`, seats it on
a stable route.

A selection is `stable` only against a stable baseline, and then when it is
eligible and does not rank below the baseline, or when it is a stable variant
of the profile on the requested backend and provider. A stable upgrade
reports `selection_kind = "operator-escalation"`; every other selection is
`operator-directed`, and anything left experimental requires
`--allow-experimental`. `rostered` stays false for both, because the route
did not choose the tuple.

`resolve` is the route-selected surface; its review eligibility metadata does
not certify an operator-directed `validate` selection's independence.
Both commands emit machine-readable refusal payloads with the
`agent-routing-refusal/1` schema on stderr.

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
3. Run `agent-routing lint`. The harness instruction files name the verb
   rather than embedding the roster, so a roster edit needs no rebuild there.
   Changing the `interactive` profile is the exception: Pi's settings name that
   route, so `~/code/agent-harnesses/bin/agent-harness build` has to
   materialize it.

Prohibitions carry a `use` string starting with `prohibited`; `check` keys on
that prefix, so the explanation and the enforcement stay in one place.
