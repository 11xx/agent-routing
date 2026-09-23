# Delegation routing

Use this document when writing or interpreting an arc plan. The model/effort
ladder selects an executor; this matrix determines how work reaches that
executor. Always identify the actor that will read the prompt before choosing a
mechanism.

This file is the canonical mechanism-routing reference: harness instruction
sets (global CLAUDE.md, the /arc skill, executor prompt templates) should
reference it rather than restate it. Model and effort selection stays with the
model/effort ladder; this document owns how the selected executor is invoked
and what context it receives.

Machine-readable form: `agent-routing delegation`; the model/effort ladder is
`agent-routing models`, caller-selected task profiles resolve through
`agent-routing resolve <profile> --backend <backend> --json`, and one-off
explicit tuples validate through the `agent-routing validate` command.
`agent-routing lint` compares the pass@1 and cost
cells the doctrine table restates against the manifest, checks model coverage,
and validates route structure, so numeric drift is detected rather than
remembered. It does not read prose, so a rule stated wrongly in sentences is
caught by review or not at all.

## Routing matrix

| Actor | Task | Mechanism | Rules |
| --- | --- | --- | --- |
| Claude | Plan an arc chain | Write the arc JSON export and a detailed journal spec | Make dependencies and ownership explicit. Generated executor prompts stop before review, merge, or integration. |
| Claude | Delegate implementation to Codex | Use `agent-delegate` with an Arc change and bounded brief; Claude may invoke `codex exec` only through the delegation mechanism | Put executor commands only in instructions Claude itself will run. Record the Arc subject, executor attribution, gates, and debt/follow-up; do not ask the executor to delegate again. |
| Claude | Review and merge | Review `base..head`, record the verdict, then use `arc integrate` when every gate passes | Do not skip review or merge automatically from an implementation prompt. |
| Codex | Execute a local arc | Import the bundle, read the journal spec, and work locally in the assigned worktree | Implement, verify, commit, run `arc snapshot`, and stop for review. Do not run `codex exec`, delegate, merge, or integrate. |
| Codex | Orchestrate sub-Codex work (rare and explicit) | Run `codex exec` with a self-contained plan and wait for its result | Do this only when the prompt explicitly assigns Codex the orchestrator role. Preserve Claude's review and merge boundary. |
| `/arc` skill | Coordinate the workflow | Use the `arc` CLI ledger, worktrees, blockers, snapshots, gates, reviews, and integration checks | Assign one writer per branch/worktree. Give Codex local-only executor prompts. The lead owns dependency order and integration. |

## Roles and boundaries

| Role | CLI binding | Boundary |
| --- | --- | --- |
| Implementer | `ARC_ROLE=implementer` | May record progress, snapshots, verification, discussion, claims, stages, and metadata; may not review, resolve findings, set or release holds, close, or integrate. |
| Reviewer | `ARC_ROLE=reviewer` | May review and resolve findings; may not close or integrate. |
| Lead | `ARC_ROLE=lead` | Full access, including closure and integration. Unset or empty remains equivalent for backward compatibility. |

Delegation prompts set `ARC_ROLE` explicitly: `implementer` for executor
sessions and `reviewer` for review-only sessions. Do not rely on the unset
backward-compatible behavior for delegated work.

## Reviewer line

The verdict never claims independence from the model that authored the diff,
and review effort is priced by stakes, not applied uniformly. A lead reviewing
delegated work it did not author is valid review coverage; do not dispatch a
third model merely because implementation was delegated. Independent review is
an escalation for repository policy, explicit user requirements, or a
high-consequence approval. When that escalation is not required, record routine
deferred coverage as Arc debt, including what was read and what remains owed.
Debt never overrides an actual `changes-requested` verdict.

Concrete reviewer routes are current roster data, not a permanent sentence in
this document. Resolve the `review` profile for the backend in use and inspect
its current stability and effort before dispatch. Sol low never reviews under
the current roster; future roster changes belong in `agent-routing models` and
profiles, not here. Machine form: `agent-routing models` (`[policy].review`).

| Authoring relation | Routine / docs-only | Behavior-affecting | High-stakes* |
| --- | --- | --- | --- |
| Lead authored | lead judgment; no external review by default | current resolved review route when policy/user/consequence requires it | current high-stakes independent route or an explicit debt/wait decision |
| Delegated implementation | lead reads and records coverage | lead review is valid; current independent route is an escalation | current high-stakes independent route, unless policy records another allowed path |
| Untrusted generator output | lead verifies every claim against source | never a verdict or implementer of record | not routed as a reviewer |

*High-stakes: data migrations, schema or breaking changes, destructive
operations, security-sensitive surfaces.

The active lead model owns planning, synthesis, and the final answer; its
identity and effort come from the live harness and routing data, not this
sentence. When a preferred review pool is exhausted, resolve the current
available route or wait/record debt according to policy. Never invent an actor
or a frozen model name to manufacture independence.

Futures and new evidence are data updates rather than frozen policy: Gemini
3.8 Flash, GLM 5.3, Grok 4.6, and Kimi K3 remain unprobed rows; Fable 5.1 is
available on the Claude subscription but unmeasured; Astra is available to the
operator but unprobed, with low/medium/high hypotheses recorded in the roster.
Concrete selection belongs to the current resolver and the user's request, not
this prose.

## Golden rule

Never tell an executor to delegate to itself.

Before generating a prompt, classify its recipient:

- **Codex executing:** local implementation only; no `codex exec`.
- **Claude delegating to Codex:** use `agent-delegate` against an Arc change
  or bounded range; Claude may run the resolved executor command. Arc owns the
  brief, provenance, rounds, debt, review choice, and integration record.
- **Claude executing:** use the `/arc` workflow and the `arc` CLI directly.
- **Codex orchestrating:** use `codex exec` only when that rare role is named
  explicitly, never by implication.

## Actor rules

### Claude

Do:

- State whether a prompt is for Claude or for Codex before including commands.
- For a Codex executor, say that execution is local to the current harness and
  assigned worktree.
- Provide the bundle location, journal spec, done condition, verification gates,
  and the exact ready-for-review signal.
- Review the final `base..head` diff and retain control of `arc integrate`.

Do not:

- Put `codex exec` in a prompt that Codex will import and execute.
- Assume Codex will create another delegation layer.
- Tell an implementer to merge to the target branch.
- Treat a generated implementation prompt as approval to skip review.

A Codex executor prompt should use this shape:

```markdown
You're in a Codex harness. This is LOCAL execution only.

1. Set `ARC_ROLE=implementer`.
2. Import the arc bundle and read the journal spec.
3. Claim the change and record typed progress stages in the assigned worktree.
4. Implement in the assigned worktree.
5. Run the specified build and test gates.
6. Commit the scoped changes and run `arc snapshot <change>`.
7. Signal: "Arc improvements ready for review."

DO NOT run `codex exec`, delegate to another harness, merge, or integrate.
```

### Codex

Do:

- Treat an imported implementation plan as local work unless it explicitly
  names Codex as an orchestrator.
- Import the bundle, inspect the repository and spec, claim the change, record
  typed stages, implement in the assigned worktree, verify, commit, and
  snapshot.
- Stop before review and integration and report the commits and gate results.
- Flag a prompt as misrouted if it tells a local Codex executor to run
  `codex exec`.

Do not:

- Spawn another Codex from a normal executor prompt.
- Write to another agent's branch or worktree.
- Merge into the target branch or run `arc integrate` when Claude owns review.
- Work around an unclear actor assignment; ask the orchestrator to correct it.

### `/arc` skill

Do:

- Select the workflow profile and record the actor, executor, reviewer,
  integration owner, dependencies, and holds.
- Use the `arc` ledger as the source of truth for snapshots, gates, findings,
  verdicts, blockers, and integration readiness.
- Give every concurrent writer a separate branch and worktree.
- Emit local-only instructions when Codex is the implementer.

Do not:

- Confuse a workflow role with a model-routing decision.
- Put delegation commands in the executor's own prompt.
- Let an implementation agent silently become the reviewer or integration
  owner.
- Merge while a hold, blocker, stale approval, failed gate, or open blocking
  finding remains.

## Native subagents and context routing

Harness-native subagent features are not a substitute for this matrix. As of
2026-07, Codex (GPT-5.6) subagents by default inherit the whole conversation
plus the parent's model family and reasoning level. Both defaults conflict
with the routing policy:

- Effort inheritance is the wrong direction. A high-effort orchestrator
  spawning same-effort context gatherers is the most expensive possible
  configuration; the ladder routes fixed-shape calls to Luna low, bounded
  implementation to Luna max, planning and review to Astra, and
  judgment-bearing execution to Sol high.
- Whole-conversation inheritance is unscoped context transfer. It pays for
  the entire session history in every child and buries the task signal.
  Delegated work gets a curated, self-contained brief: the spec, the done
  condition, the gates, and nothing else. That is what arc bundles and
  journal specs are for.

So: do not route work through native subagent defaults. Invoke executors
explicitly (`codex exec` with a chosen model and effort, an arc bundle plus
spec, or an orchestration script) where model, effort, and context are all
stated. Revisit if a harness ships per-subagent model/effort/context
controls and they prove reliable.

Explicit model selection does not remove prompting safeguards. Every
implementation prompt routed below the Sol-high floor must name exact targets,
set a scope ceiling, prohibit unrequested tests and refactors, and state abort
conditions. Every Sol write-mode prompt keeps the same fence at all efforts.
If a named target or prerequisite is absent, the executor stops and reports it;
it must not substitute another target or improvise a workaround.

## Acceptance probes

Effort is priced by residual risk after the gate, which only works if the
risk is observable. Declared gates catch compile, regression, and lint
failures, and reading the diff catches overbuild — but neither sees a
plausible implementation of the *wrong semantics*, and that failure stays
green. Buying a more expensive executor does not reliably catch it either,
because the executor was faithful to what it was told.

So the brief names acceptance probes: runnable commands whose outcome
distinguishes the intended behavior from the plausible substitute. The
executor runs each at its final head and records it with

    arc verify --command '<the probe>'

which puts the evidence in the ledger beside the gate results, bound to the
revision a reviewer is looking at. Naming such a command requires knowing the
required behavior — which is the lead's job regardless — not predicting the
executor's mistake, which nobody can do at any tier. A brief whose material
risk has no such command is not ready to delegate: resolve the risk, or
escalate the tier.

Two limits, stated rather than glossed:

- **Probes are recorded, not enforcing.** Integration readiness consults
  declared gates only, so ad hoc probe evidence never gates and never turns a
  gate green. The convention holds because a reviewer checks for it. A
  reviewer who assumes the tool is checking will stop checking.
- **A probe is only as good as the premise behind it.** Verify every path,
  symbol, and claim a brief makes against the source *before* delegating. On
  the rescue chain, three of six first attempts blocked on unverified brief
  claims, and all four review-stopping findings were faithful implementations
  of incomplete briefs rather than execution errors; brief quality, not
  executor tier, was the binding constraint. Those findings were major ones
  riding `changes-requested` verdicts — their structured `blocking` field was
  false, so what stopped the work was the verdict, not the finding.

If the floor fails anyway — a workhorse-authored semantic defect passing its
named probe and first review, or two changes in the fixed *next six* workhorse
cohort needing extra verdict rounds for executor-caused defects — make probes
declarable so they gate, not to buy a higher tier. An absent or
non-discriminating probe is a gap in the machinery, and escalation only
answers it if declarable probes exist and the defect recurs regardless. The
cohort is fixed at adoption rather than rolling; changing the workhorse model
does not reset it. Evaluating it needs the data recorded: which model and effort
implemented each change, and whether each review
round was brief-caused, executor-caused, or integration-staleness. Only
executor-caused rounds count against the floor.

The strongest known pattern is programmatic orchestration: generate a
dedicated one-off script that spawns each agent with an explicit prompt,
model, effort, and input set, and encodes the control flow (fan-out,
gates, joins) as code rather than conversation. Claude Code's workflow
scripts work this way. An arc chain is the ledger-backed equivalent:
deterministic dependency order, curated per-executor specs, machine-checked
gates. Prefer either over implicit inheritance.

## Executor backends (harness adapters)

The matrix above routes *roles*; this section routes *invocations*. A
backend is a CLI a lead can drive programmatically to run a selected model.
Each backend has an adapter contract — the facts a lead must know before
composing a command. A backend is routable only after every contract row
has been probed and recorded here; until then it is "unprobed" and must not
be selected.

Adapter contract (probe checklist for onboarding any new harness):

1. **Non-interactive entrypoint** — the `claude -p` / `codex exec`
   equivalent, and how the prompt is passed (argument, stdin, file).
2. **Model and effort selection** — explicit flags; never rely on the
   harness default or fuzzy matching in delegation commands.
3. **Working directory** — a `-C`-style flag, or `cd` before invoking.
4. **Final-message capture** — where the answer lands (stdout, `-o` file)
   and how noisy the channel is.
5. **Isolation** — OS sandbox, tool allowlist, or nothing; what write mode
   actually fences.
6. **Clean-room switches** — how to suppress ambient config, sessions,
   extensions, and context files so the curated brief is the whole input.
7. **Resume** — continuing a prior run for follow-ups.
8. **Quota identity** — which subscription pool the backend draws from and
   the exact usage-limit error signature. Two backends on one pool are not
   fallbacks for each other's limits.

### Verified backends (2026-08-01)

| Contract | codex CLI (`codex exec`) | pi (`pi -p`), v0.83.0 | Claude CLI (`claude -p`) | opencode (`opencode run`), v1.18.10 |
| --- | --- | --- | --- | --- |
| Entrypoint | `codex exec "<prompt>"` | `pi -p "<prompt>"`; `@file` args inline files (specs) | `claude -p "<prompt>"` | `opencode run "<prompt>"` |
| Model | `-m gpt-6-{luna,sol,astra}` | GPT: `--provider openai-codex --model gpt-6-{luna,sol,astra}`; DeepSeek: `--provider opencode-go --model deepseek-v4.1-flash` on the Go pool, `--provider deepseek --model deepseek-flash` (V4.1) on DeepSeek's own billing; MiMo trial: `--provider opencode-go --model mimo-v2.6-flash` / `mimo-v2.6-pro` | `--model claude-opus-5` | `-m opencode-go/<model>` |
| Effort | `-c model_reasoning_effort="low\|medium\|high\|xhigh"` | `--thinking off\|minimal\|low\|medium\|high\|xhigh\|max` (or `:level` model suffix) | `--effort low\|medium\|high` | `--variant high\|max` |
| Working dir | `-C <dir>` | none — `cd` first | none — `cd` first; `--add-dir=<path>` adds explicit read roots | `--dir <dir>` |
| Capture | `-o <file>`; stdout is the full transcript (noisy) | stdout is exactly the final message | stdout for one-shot calls; `--output-format stream-json` for supervised runs | stdout is the final message under a `> build · <model>` header; `--format json` gives a JSONL event stream with per-step token counts |
| Isolation | OS sandbox, which `agent-delegate` opens to `-s danger-full-access` by default; `-s read-only` / `-s workspace-write` (+ `writable_roots`) narrows a run | **none**; read-only ≈ `--tools read,grep,find,ls` (no bash, so no git/shell inspection); write mode is unsandboxed user access | permission mode plus tool allowlist; `plan` is the read-only consultation mode | **none**; permission config, and `--auto` approves everything not explicitly denied |
| Clean-room | curated prompt; reads repo AGENTS.md | `--no-session --no-extensions --no-skills --no-context-files` | `--safe-mode --disable-slash-commands --no-session-persistence` with a curated stdin prompt | `--pure` drops external plugins only; AGENTS.md and `~/.config/opencode/skills` still load |
| Resume | `codex exec resume --last` | `--session <id>` / `-c` / `--fork` | `--resume <session-id>` | `-c` / `-s <id>` / `--fork` |
| Quota | ChatGPT/Codex subscription; "You've hit your usage limit … try again at HH:MM" | Provider-dependent: `openai-codex` uses the **same** ChatGPT/Codex pool; `deepseek` uses separate API billing and quota; `opencode-go` draws the Go subscription, metered in usage dollars | Claude subscription through the first-party client | Conditional OpenCode Go subscription — a third pool metered in usage dollars ($12/5h, $30/week, $60/month), locally readable via `opencode stats`. Limit signature unprobed |

Backend selection between the two GPT routes:

- **codex CLI is the default for GPT work**, and mandatory-by-default for
  write mode: its OS sandbox is a real fence; pi's write mode has none.
  Route write-mode work through pi only when the codex CLI itself is the
  blocker (broken install, incompatible flag, harness without codex
  access), and then only inside a dedicated worktree with explicit
  scope fencing in the prompt.
- **pi's niche is provider plurality and lead portability**: one adapter
  reaches every provider the user has logged in. Today `openai-codex` reaches
  GPT-5.6 on the shared Codex subscription, `deepseek` reaches V4.1 Flash
  and V4 Pro on independent API billing, and `opencode-go` reaches the
  probationary MiMo rows on the Go subscription through an operator-directed
  selection. Any harness that can run a shell can
  drive it. A non-Claude, non-Codex lead delegating to GPT goes through Pi.
- **DeepSeek Flash is routed as a generator, and its seat is probation.** The
  live build is V4.1 Flash, reached as `--provider deepseek --model
  deepseek-flash`; the versioned id it replaces is deprecated. Both the
  vendor's 54.4 DeepSWE result and the independent testing that measured
  confident fabrication describe that predecessor, not the build in service,
  and V4.1 has no field arc here. Route it through the `generate` profile for
  raw material a lead adjudicates, under a brief that fences what it may
  produce, and keep it off the last edit of shipped work until a field arc on
  V4.1 says otherwise. V4 Pro 0813 is generally available
  and measures 63% on the Datacurve board; it keeps the briefed
  defect-generation niche until a field arc.
- **MiMo V2.6 Flash and Pro are probation, and Flash is the row benchmarked
  going forward.** Both rows are unmeasured — no score, no field arc, no
  approval anyone has confirmed — and no profile resolves to either. Reach
  them as `--provider opencode-go --model mimo-v2.6-flash` (or
  `mimo-v2.6-pro`) through a validated operator-directed selection:
  `agent-routing validate --profile <shape> --backend pi --model
  mimo-v2.6-flash --effort high --provider opencode-go --reason <text>
  --allow-experimental`, which records the execution shape, pool, and reason
  against the route version. Pro is read as a little stronger at about three
  times Flash's input; that read is an estimate, so Flash stays the benchmark
  subject and a trial's result — not the price and not the read — is what
  would move either row. Both take a fully specified brief with exact targets,
  a scope ceiling, named acceptance probes, and lead review, and neither is
  the last model to touch shipped work.
- pi "read-only" (`--tools read,grep,find,ls`) is tool-level, not
  OS-level, and excludes bash entirely: file reading and search work,
  `git log`/build commands do not. Investigations needing shell stay on
  `codex exec -s read-only`.
- Liveness, watchdog, and one-prompt-source stdin rules below apply to
  every backend. pi's stdin behavior under `-p` is unprobed: apply the
  same `< /dev/null` discipline defensively.
- **opencode reaches a third quota pool, on the condition that it is paid
  for.** Its `opencode-go` provider draws on neither the Claude window nor
  the Codex credit schedule, which makes it capacity the other two backends
  cannot substitute for. That is also its whole reason to exist here: on
  capability it offers nothing the roster lacks. Availability is a payment
  state no manifest can observe, so every route through it is experimental,
  opt-in, and fails closed; confirm the credential before routing and treat
  its absence as a stop rather than a fallback.
- **Reach Luna-on-Go through opencode, not pi.** pi's bundled `opencode-go`
  catalog carries 16 of the 17 Go models and omits exactly `gpt-5.6-luna`,
  with no refresh path — `pi update models` fails outright. For the other 16
  either backend works.
- **Some Go models are hosted in China** and run only while the workspace's
  data-residency opt-in is on. With it on, as it was on 2026-09-22, they route
  normally; switched off, they refuse with "only available hosted in China and
  requires explicit opt in", as `deepseek-v4-flash` did on 2026-08-01. The
  setting is the operator's, and delegating to one sends repository context
  there; the roster records it and does not gate on it.
- opencode has no OS sandbox and `--auto` approves everything not explicitly
  denied, so write mode carries pi's exposure without pi's tool allowlist.
  Its dollar-denominated window also makes context discipline a cost
  question: `--pure` drops external plugins only, and AGENTS.md plus
  `~/.config/opencode/skills` still load on every launch — a bare probe
  prompt wrote 16.3k cache tokens before doing any work.
- Claude is the first-party backend for `design` and taste-axis review. It is
  not a substitute for Pi's native provider route; its subscription entitlement
  belongs to the Claude client.

## Launcher hygiene and liveness

Rules from the 2026-07-17 claim-stage-protocol stall postmortem (a `codex exec` blocked
forever reading a stdin pipe another heredoc had opened; no channel showed
the difference between hung and working for seven minutes).

Launching a non-interactive executor:

- Give `codex exec` exactly one prompt source. Prompt as an argument means
  stdin MUST be closed: append `< /dev/null`. Prompt via stdin means a
  single heredoc feeding codex and nothing else. Never let an executor
  launch share a compound command with any other stdin consumer or
  producer (heredocs, pipes) — journal appends and launches are separate
  commands.
- Redirect output to a log file per executor; the log is the liveness
  probe.

Arm two watchdog tiers at launch, always:

- **First-output (seconds):** the executor banner appears within seconds
  of a healthy start. Log still near-empty after 60 s = launch failure;
  kill and relaunch, do not wait.
- **Progress (minutes):** a log that stops growing for longer than the
  task plausibly needs is a wedge, not deep thought. Check interim output
  before assuming work is happening; a hung process and a working one are
  otherwise indistinguishable.

Executors claim immediately and record typed progress with their native
identity:

```sh
ARC_HARNESS=codex ARC_SESSION="${CODEX_THREAD_ID:?}" arc claim <change>
ARC_HARNESS=codex ARC_SESSION="${CODEX_THREAD_ID:?}" arc stage <change> started
# after reading the executor spec
ARC_HARNESS=codex ARC_SESSION="${CODEX_THREAD_ID:?}" arc stage <change> spec-read
```

Continue with `implementing`, `verifying`, or `blocked-on --note <reason>` as
work changes state. Repeating a stage is a heartbeat; changing it is progress.
Leads consume raw events with `arc events --follow --change <change>`, inspect
the time-derived claim object in `arc status`, or wait with
`arc watch <change> --until stalled|snapshot|ready|integrated|closed`. A stale
claim is still live and owned; an expired one is not. Claims remain advisory:
an identified lead may release a live foreign claim, and `arc integrate` warns
about but does not block on one.

## Correct and incorrect delegation

### Correct: Claude invokes Codex

Claude prepares an Arc change or journal brief and runs the resolved
`agent-delegate`/`codex exec` mechanism itself. The nested prompt tells Codex
what to implement locally, where to record its result, and which gate proves it.

### Incorrect: Codex is told to invoke itself

```markdown
You are the Codex executor. Run `codex exec` to implement this plan.
```

This creates an unnecessary nested harness, can exceed the parent harness's
timeout, and may leave work half-finished. Replace it with local worktree
instructions.

### Correct: Codex completes an arc implementation

Codex imports the bundle, reads the journal spec, claims the change, records
typed stages, edits and tests in its worktree, makes scoped commits, runs
`arc snapshot`, and signals that the arc is ready for review. Claude later
reviews and integrates.

### Incorrect: the implementation prompt merges

```markdown
After tests pass, run `arc integrate --cleanup` and merge to master.
```

The executor does not own that decision. It must stop after the snapshot so
Claude can review the exact patchset.

### Correct: `/arc` coordinates a chain

An **arc** is the goal-level unit: a tagged series of one or more ledger
changes carried to integration. A **chain** is arc's orchestration of that
series: the blocked-by graph in which ready sibling changes run in parallel
while dependent changes wait mechanically for their prerequisites. The lead
opens each change with its declared blockers, assigns local-only executor
prompts, and starts downstream implementation only when the ledger reports
it ready. Claude reviews and integrates each approved patchset. (Members
are "changes", never "arcs"; parallel scheduling groups are not "waves".)

### Incorrect: `/arc` shares a checkout

Two implementers are assigned to the same branch or worktree, or a downstream
executor is told to bypass a blocker. Give each writer isolated ownership and
honor the ledger state instead.
