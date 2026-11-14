# Delegation routing

`agent-routing` selects and validates model, effort, provider and backend for a
caller-selected task profile. The execution mechanism belongs to the application
or harness running the lead. The shared delegation fragment in `agent-harnesses`
defines the personal default; an application's orchestration instructions define
how to use its tools.

## Route and execution mechanism

A route identifies the executor and its policy eligibility. It does not require
a CLI process or make `agent-delegate` the owner of every delegated task. Native
subagents, application-owned child threads and CLI runs can execute a route when
they can represent its required settings and authority.

Resolve the profile before dispatch and pass the selected settings explicitly.
An inherited value is usable only when it is established to match the route.
Report a setting the mechanism cannot express before dispatching; never silently
change the model, effort, provider or execution authority. A backend identifies
the harness and provider path whose capabilities routing validates; a T3 thread
or native subagent is an execution mechanism, not an invented routing backend.

Read `agent-routing` for profile resolution, directed selection, prohibited tiers,
quota admission and reviewer eligibility. `agent-routing delegation` prints the
backend and pool facts, and this document the launch contracts; each execution tool's guide owns its launch,
observation, control and recovery commands.

## Brief and context

Give each child a self-contained task, exact targets, scope ceiling, permitted
writes, completion condition and required verification. Check the paths, symbols
and premises against source before dispatch. Missing targets or prerequisites
require a report rather than an invented substitute.

Use fresh context for bounded work. A conversation fork is appropriate when the
task requires the parent's history; choose it deliberately and verify its model
and effort rather than treating inheritance as route selection. Native execution
does not imply either full-history inheritance or fresh context: inspect the
chosen mechanism's contract.

## Roles and attribution

Lead, implementer and reviewer are roles, independent of model family. Assign
those roles and integration authority explicitly. An executor implements the
assigned task; it delegates only when the task grants that role. The lead owns
dependency order, review and integration. Give concurrent writers separate
branches or worktrees and honor declared blockers.

Preserve the executor's actual authority. Read-only work inspects and reports;
write, commit and Arc-store actions require the corresponding access. The lead
performs required actions the executor cannot perform. A permission label is not
proof of OS isolation; use the execution tool's documented enforcement boundary.

Record the assignment and actual executor in Arc, whatever mechanism launches
it. Application thread IDs, native harness session IDs and delegated-run handles
are distinct identities. An unresolved executor stays unresolved. A successful
runtime result is not a review verdict or integration approval.

A lead may review delegated work it did not author. Independent review follows
repository policy, operator requirements and the consequence of a wrong approval;
it is not automatic for every delegation. Routing assesses reviewer eligibility;
Arc records the verdict and any debt. Debt never overrides changes-requested,
failed gates, blockers or holds.

## Acceptance evidence

Name runnable acceptance probes that distinguish the intended behavior from
plausible wrong behavior where the selected implementation route requires them.
The executor runs them at the final head within its authority and records them
with Arc when its store is writable. Otherwise it reports the command and result
for the lead to run or record. Resolve a material verification gap before treating
the result as accepted.

Ad hoc probe evidence does not make a declared gate pass. Review the probe's
premise and the resulting behavior; a green build alone does not establish the
intended semantics. Profile-specific scope and verification requirements are
the seats' `when` and `why` in `agent-routing profiles`.

## Launching and watching

- An executor launch has exactly one prompt source. `codex exec` appends piped
  stdin to its prompt and blocks until EOF, so a prompt passed as an argument
  gets `< /dev/null`, a prompt on stdin gets one dedicated heredoc, and the
  launch never shares a compound command with another stdin producer.
- Arm two watchdogs on every non-interactive launch: first output within about
  a minute (a near-empty log is a failed launch: kill and relaunch) and log
  growth afterwards (a frozen log is a wedge: inspect the interim output). A live
  process is not a working one.
- An Arc executor leaves a start comment with its session id right after
  reading its spec, so the ledger shows life between begin and first snapshot.
- Generated executor prompts stop before review, merge and integration.
- One writer per branch or worktree.
- Proxy shells relay the exact command and result and never perform or redesign
  the delegated task; their model and effort are the policy's `proxy` rows.
  Labels are `cx-` for codex-backed spawns and `pi-` for pi-backed ones.
- Acceptance probes are recorded and reviewable, never gating: readiness
  consults declared gates only, so the reviewer enforces the convention.

## Backends

`agent-routing delegation` prints each backend's providers, efforts and
reachable models, and the pools that bound them. The launch contracts:

| | codex | pi | claude | opencode (v1) |
| :--- | :--- | :--- | :--- | :--- |
| entrypoint | `codex exec "<prompt>"` | `pi -p "<prompt>"`; `@file` inlines a spec | `claude -p "<prompt>"` | `opencode run "<prompt>"` |
| model | `-m <backend model>` | `--provider <provider> --model <backend model>` | `--model <backend model>` | `-m opencode-go/<model>` |
| effort | `-c model_reasoning_effort="<effort>"` | `--thinking <level>` or a `:level` suffix | `--effort <effort>` | `--variant low\|high\|max` |
| workdir | `-C <dir>` | none; `cd` first | none; `cd` first | `--dir <dir>` |
| capture | `-o <file>`; stdout is the noisy transcript | stdout is the final message | `--output-format stream-json --verbose`; keep the final result | stdout under a `> build · <model>` header; `--format json` streams per-step token counts |
| isolation | OS sandbox; `-s read-only` or `-s workspace-write` narrows a run | none | none; delegated runs use `bypassPermissions` | none; `--auto` approves everything not denied |
| clean room | — | `--no-session --no-extensions --no-skills --no-context-files` | — | `--pure` drops plugins only; AGENTS.md and skills still load |
| resume | `codex exec resume --last` | `--session <id>`, `-c` or `--fork` | `--resume <id>`, plus `--fork-session` | `-c`, `-s <id>` or `--fork` |

- **codex.** Under `workspace-write` every writable root's `.git`, and a linked
  worktree's git dir, stay read-only, also for a root added with `--add-dir`.
  Adding the common dir keeps objects, refs and the default Arc store writable,
  but the worktree index and HEAD stay read-only, so the executor leaves its
  diff for the lead to commit and snapshot. Under `read-only` it inspects and
  reports; under full access it commits and snapshots when the Arc store is
  writable.
- **pi.** `--provider` is never optional: a model name authenticated on two
  providers aborts the run. `xhigh` and `max` reach the provider only when pi's
  model definition maps them; an unmapped model drops both and clamps a
  requested `max` to `high` without saying so. Read-only is an appended
  instruction, never a tool allowlist. The provider decides the pool: pi's
  `openai-codex` provider shares the Codex subscription and is no quota
  fallback, and `opencode-go` draws the Go subscription.
- **claude.** Read-only is an appended instruction, never plan mode or a tool
  allowlist. A route runs at the effort its seat binds.
- **opencode.** The row describes the v1 CLI. `--variant` is honored but
  unvalidated: a misspelled value silently falls back to the default effort, so
  confirm the tier from `reasoning` in the `--format json` token counts. The v2
  CLI (`opencode2`) declares no model variants, has no `--dir` and no unattended
  approval mode, so a permission prompt ends a run at exit 0 with no verdict.
  Exit status is honest. The default context prefix is heavy (a bare prompt
  wrote 16.3k cache tokens), so fence context on a dollar-metered window. Confirm
  `opencode auth list` shows OpenCode Go before routing; an absent credential is
  a stop, not a fallback.

## Pools

- The Go pool is an optional subscription metered in usage dollars ($12 per five
  hours, $30 weekly, $60 monthly), off both standing windows. A lapsed
  subscription or a disabled data-residency opt-in fails the pi runs it carries;
  the work moves to codex or claude, which serve the same profiles, and nothing
  falls back onto the pool from another window.
- Several Go models are hosted in China and run only while the workspace's
  data-residency opt-in is on. The setting is the operator's; delegating to one
  sends repository context there, and routing records the fact without gating
  on it.
- The same model on a different pool keeps its capability record but not its
  quota accounting.
- Model and profile selection comes from `agent-routing models`,
  `agent-routing profiles` and the resolver. Read the chosen execution tool's
  current guide for session resumption, cancellation, output retention, liveness
  and resource supervision; a native application's behavior is not inferred
  from a CLI launch contract.
