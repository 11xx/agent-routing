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
quota admission and reviewer eligibility. `agent-routing delegation` exposes the
mechanism and backend facts; each execution tool's guide owns its launch,
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
intended semantics. Profile-specific scope and verification requirements remain
in `agent-routing delegation` and the model policy.

## Backend capabilities

The backend entries in `agent-routing delegation` retain provider support,
effort mappings, isolation boundaries and quota-pool facts. Model and profile
selection comes from `agent-routing models`, `agent-routing profiles` and the
resolver. Read the chosen execution tool's current guide for stdin, session
resumption, cancellation, output retention, liveness and resource supervision.
Do not infer a native application's behavior from a CLI launch contract.
