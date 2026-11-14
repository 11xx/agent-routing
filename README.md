# agent-routing

Which model to pick, at which effort, reached by which mechanism — as data,
with one accessor, for every harness and tool on this machine.

```sh
agent-routing                         # the routing guide: start here
agent-routing profiles                # the policy: profiles, seats, pools
agent-routing models                  # the catalog: models, tiers, prices, reach
agent-routing resolve implement --backend codex --json
agent-routing check <model> <effort>  # exits 1 on a prohibited tier
agent-routing doctrine                # principles plus the policy, rendered
agent-routing lint                    # validate the whole data set
agent-routing prices --format tapes --output ~/.config/tapes/prices.toml
```

The guide (`doctrine/guide.md`, the bare invocation) is the contract for every
verb.

## Why it is its own repository

Routing policy is opinionated, personal, and churns whenever a model ships.
Keeping it here lets `arc` and `tapes` hold no routing opinion of their own.
`arc` records whatever `--model` string it is handed, clears review debt
against the capability ladders it imports from `agent-routing ladder`, and asks
the live `frontier` answer for review assurance. A rank edit here therefore
moves Arc's assurance at once, and moves what Arc clears only when Arc next
imports the ladder. `tapes` reports whatever a transcript contains.
`agent-routing prices --format tapes` writes API list prices in tapes' own
`tapes-price-table/2` format, which the operator installs where tapes looks for
a price table; tapes reads only that file.

## What is authoritative

| path | holds |
| :-- | :-- |
| `data/catalog.toml` | facts about models: families, backends, tiers, prices, reachability |
| `data/policy.toml` | what routing decides from: profiles, seats, review seats by purpose, pools, fallbacks, fences, admission; and the guards leads follow |
| `data/notes.jsonl` | dated field notes; no routing decision reads them |
| `doctrine/principles.md` | the standing principles |
| `doctrine/guide.md` | the routing guide and verb contracts |
| `DELEGATION.md` | how work reaches an executor: roles, briefs, launch contracts |

The catalog and policy hold short, flat rows. A seat names the backends it
serves and says in one sentence `when` it applies, `why` it holds and `since`
when. A guard is a standing instruction for using a tier: one-sentence `rule`
and `why`, with the notes it rests on. Leads follow guards; no verb that
selects, validates or refuses a route reads them, and a fault in a guard or a
note is lint's to name, never a refused route. Notes and their recurrence,
retraction, supersession and undo events share increasing ids. Each event
appends a dated record; earlier evidence retains its bytes. Anything longer is a
principle, a note, or nothing. `agent-routing doctrine` renders the principles
and the stores together, so the readable policy cannot drift from the data.

## The propagation path

A harness instruction file carries a short pointer to this CLI rather than a
copy of the roster, so the policy is read when a routing decision is in front
of an agent. `agent-harnesses` composes that pointer into each harness's
instruction file, and its `agent-harness delegation-sources` accessor declares
the instruction and agent surfaces to `agent-routing lint-consumers`, which
rejects concrete model ids and static model frontmatter in the consumer
repositories the policy's `[[consumer]]` and `[[accessor]]` rows name. Sibling
repositories are found beside the canonical checkout through Git's common
directory; `AGENT_CODE_ROOT` overrides that location. The lint reads other
repositories, so it runs on demand.

`agent-routing emit claude-agents` renders static Claude agent definitions and
their `[[pin]]` table from resolved routes; a consumer enrolls them and the
consumer lint holds them to the rendering.

## What this repository will not do

**It will not classify work for you.** `resolve` maps a caller-selected profile
to the current route; there is no `agent-routing pick <task>`.

**It will not enforce anything.** A harness that ignores this data is not
stopped by it; the data makes the decision legible and the prohibitions
unambiguous.

## Changing the data

Use an edit verb for a single policy or catalog change. Every edit validates
all three stores before writing, locks the checkout, publishes canonical
files by rename, and makes one signed-as-configured Git commit containing
only data paths. `--why` records the reason; repeat `--because NOTE_ID` to
cite field evidence. `--dry-run` validates and previews without writing, and
`--json` emits one result object for callers.

The invented fixture shows the fields a preview changes:

```sh
agent-routing set-seat implement --variant flat --backend pi \
  --model orbit-flash --effort low --when "Fixed-scope implementation from pi." \
  --why "Use the cheaper measured tier." --dry-run
```

```text
set-seat (dry run)
data/policy.toml seat implement:flat (backends: pi)
  effort: max → low
  when: Specified implementation from pi. → Fixed-scope implementation from pi.
  why: The flat pool's workhorse. → Use the cheaper measured tier.
  since: 2030-01-03 → 2030-01-09
route_version: b31715eb8626 -> 298e8fdfce1f
stale consumers: none
```

A card puts seats and guard instructions before field evidence:

```sh
agent-routing card nw-swift-2
```

```text
nw-swift-2 · northwind
Seats
  extract:swift  claude  high  default  Fixed-shape calls from a Northwind
                                        session.
Prohibited
  none
Guards
  · max: Run max only as a capped trial, never as an escalation.
    why: The tier is explicit-only and unmeasured.
    since 2030-01-05
Weaknesses
  none
Strengths
  none
Observations and measurements
  none
Inherited, unverified for this model
  none
```

`set-seat`, `remove-seat` and `default-seat` edit seats; `prohibit`, `allow`
and `rank` edit tiers; `set-fallback` and `remove-fallback` edit recovery
routes; `set-review-seat` and `remove-review-seat` edit the reader for a review
purpose; `set-guard` and `retire-guard` edit standing instructions;
`add-model` and `supersede-model` cover small catalog changes. The guide
lists their arguments. Notes use `note`, `again`, `retract` and `supersede`;
`notes` filters the live evidence and `card` shows a model's policy and
recurrence-ordered evidence, marking predecessor evidence inherited and
unverified.

For a large roster edit, change the files by hand and run
`agent-routing commit --why "REASON"`. It validates and canonicalizes before
committing; a regular edit refuses pre-existing staged or unstaged data
changes. Earlier note bytes cannot be rewritten, even by the commit verb.
`log` shows the data history. `undo` reverses the latest verb edit in a new
commit, preserving disjoint later edits and refusing conflicts. Policy undo
restores the previous bytes; note undo appends a compensating event.

An edit names each row and prints only changed fields as `old → new`,
followed by route versions and affected consumers with refresh commands. Claude definitions
refresh with `agent-routing emit claude-agents`; interactive harness settings
refresh with `agent-harness build`. Generated output and its pin table must
be installed by the consumer's deployment workflow; the edit performs no
deployment and pushes nothing.

Rolling provider ids keep a checkpoint-specific `build` on the catalog row;
field notes name the build, provider, harness and effort they observed.

## Checking a change

`bin/check-change` is the gate. It checks the committed head of a clean
checkout against the change's base (`--base REV`, else the merge base with the
target branch `arc show --json` names):

1. **Compile.** Every Python source under `lib/`, `bin/` and `tests/` compiles,
   and every shell script in `bin/` passes `bash -n`.
2. **Invariants.** `checks/invariants.toml`, read from the base plus entries
   the candidate adds under new names, within 3 seconds: `lint-routing`
   validates the live data, `roster-ids` refuses any catalog id in code,
   templates or tests, and `notes-grow-only` rejects any revision that rewrites
   earlier field evidence.
3. **Tests.** Every module under `tests/`, once, each in its own process and
   all at the same time. A failure, an error or a skip fails it.
4. **Witnesses.** The tests the change's commits name, at most three, each run
   alone within 5 seconds.

A commit touching `lib/`, `bin/`, `templates/`, `tests/` or `checks/` names its
witness in its final trailer block, or says why it has none:

```text
Witness: tests/test_check_change.py::CheckChangeTest.test_a_fourth_witness_is_refused
Witness: none (renames a helper; no behaviour changes)
```

The run fits the `BUDGET` in `bin/check-change`, 5 seconds; an overrun fails
and names its phase. Checks run with a private home, temporary and XDG
directories, and every run writes a JSON receipt under
`$XDG_CACHE_HOME/agent-routing/checks/`.

The tests read an invented data set in `tests/fixtures/data` — labs, models,
backends and pools that do not exist — so they test the tool and never the
roster, and a data edit never breaks one. `python3 -m unittest discover -s
tests` runs them by hand.
