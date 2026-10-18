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
| Claude | Delegate implementation to Codex | Use `agent-delegate` with an Arc change and bounded brief; Claude may invoke `codex exec` only through the delegation mechanism | Name the Codex sandbox and its commit/snapshot boundary in the prompt. Put executor commands only in instructions Claude itself will run. Record the Arc subject, executor attribution, gates, and debt/follow-up; do not ask the executor to delegate again. |
| Claude | Review and merge | Review `base..head`, record the verdict, then use `arc integrate` when every gate passes | Do not skip review or merge automatically from an implementation prompt. |
| Codex | Execute a local arc | Read the journal spec and work in the assigned worktree; import the bundle only when the sandbox and Arc store permit writes, otherwise the lead imports it and provides the spec | Under `read-only`, inspect and report. Under `workspace-write`, implement and verify, then leave the diff for the lead to commit and snapshot. Under full access, implement, verify, and commit; snapshot when the Arc store is writable, otherwise the lead snapshots. Never run `codex exec`, delegate, merge, or integrate. |
| Codex | Orchestrate sub-Codex work (rare and explicit) | Run `codex exec` with a self-contained plan and wait for its result | Do this only when the prompt explicitly assigns Codex the orchestrator role. Preserve Claude's review and merge boundary. |
| `/arc` skill | Coordinate the workflow | Use the `arc` CLI ledger, worktrees, blockers, snapshots, gates, reviews, and integration checks | Assign one writer per branch/worktree. Give Codex local-only prompts with sandbox-specific commit and snapshot instructions. The lead owns dependency order and integration. |

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
this document. Resolve the `review` profile for the backend in use with
`--author '<model>#<effort>'` naming the diff author, and inspect its current
stability, effort, and `review.independence` before independent-review dispatch.
A result without the author reports `unverified`; it is not evidence of
independence. The resolver refuses when no stable route outside the author's
family meets its review floor and recommends Arc debt. `ARC_MODEL` identifies
the caller and is not an author fallback. Operator-directed selections require
their own independence check. Sol low never reviews under
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
available on the Claude subscription but unmeasured; Sonnet 5.5 is a trial row
on the same subscription, reached only by operator direction; Astra is available to the
operator but unprobed, with low/medium/high hypotheses recorded in the roster.
Concrete selection belongs to the current resolver and the user's request, not
this prose.

## Golden rule

Never tell an executor to delegate to itself.

Before generating a prompt, classify its recipient:

- **Codex executing:** local work only, with actions bounded by the sandbox:
  `read-only` means inspect and report, `workspace-write` means leave the
  verified diff for the lead to commit and snapshot, and full access permits
  the authorized commit and snapshot workflow when the Arc store is writable.
  Arc imports, claims, stages, verification records, and snapshots write the
  Arc store. If the sandbox or store prevents one of those writes, the lead
  performs it. No `codex exec`.
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
- For a Codex executor, name the sandbox and assigned worktree: `read-only`
  means inspect and report, `workspace-write` leaves the verified diff for the
  lead to commit and snapshot, and full access retains the authorized commit
  and snapshot workflow.
- Provide the bundle location, journal spec, done condition, verification gates,
  and the exact ready-for-review signal.
- Review the final `base..head` diff and retain control of `arc integrate`.

Do not:

- Put `codex exec` in a prompt that Codex will import and execute.
- Assume Codex will create another delegation layer.
- Tell an implementer to merge to the target branch.
- Treat a generated implementation prompt as approval to skip review.

A Codex executor prompt should name the sandbox and use this shape:

```markdown
You're in a Codex harness. This is LOCAL execution only.

1. Set `ARC_ROLE=implementer`.
2. Import the Arc bundle and read the journal spec only when the sandbox and
   Arc store permit writes. Under `read-only`, or when the store is not
   writable, the lead imports the bundle and provides the spec for inspection.
3. Claim the change and record typed progress stages only when the sandbox and
   Arc store permit writes; otherwise the lead records progress.
4. Implement in the assigned worktree when the sandbox permits writes.
5. Run the specified build and test gates when the sandbox permits execution;
   under `read-only`, inspect and report without running gates.
6. Under `workspace-write`, leave the verified diff for the lead to commit and
   snapshot. Under full access, commit the scoped changes when authorized and
   run `arc snapshot <change>` only when the Arc store is writable. Under
   `read-only`, inspect and report without writing. If the store prevents an
   import, evidence record, or snapshot, the lead performs that write.
7. Under full access, signal readiness for review after the required gates and
   snapshot. Under `workspace-write`, report the verified diff for the lead to
   commit and snapshot; under `read-only`, report inspection findings.

DO NOT run `codex exec`, delegate to another harness, merge, or integrate.
```

### Codex

Do:

- Treat an imported implementation plan as local work unless it explicitly
  names Codex as an orchestrator.
- Under `read-only`, inspect the repository and spec, then report without
  writing. Under `workspace-write`, implement and verify in the assigned
  worktree, then leave the diff for the lead to commit and snapshot. Under full
  access, follow the authorized claim, implementation, verification, and
  commit workflow; snapshot only when the Arc store is writable. The lead
  performs any Arc-state write the executor cannot make.
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
- Emit local-only instructions that name the sandbox and its commit/snapshot
  boundary when Codex is the implementer.

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
  implementation to Luna max, planning to Astra, and review and
  judgment-bearing execution to Sol xhigh.
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
implementation prompt routed below the Sol-xhigh floor must name exact targets,
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
executor runs each at its final head when the sandbox permits execution. It
records the result with `arc verify --command` only when both the sandbox and
Arc store permit that write; otherwise it reports the command and result for
the lead to record. A read-only executor inspects and reports without running
gates or probes.

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
| Model | `-m gpt-6-{luna,astra}` or `-m gpt-6.1-sol` | GPT: `--provider openai-codex --model gpt-6-{luna,astra}` or `gpt-6.1-sol`; DeepSeek: `--provider opencode-go --model deepseek-v4.1-flash` on the Go pool, `--provider deepseek --model deepseek-flash` (V4.1) on DeepSeek's own billing; MiMo trial: `--provider opencode-go --model mimo-v2.6-flash` / `mimo-v2.6-pro` | `--model claude-opus-5-5`; explicit Haiku trial: `--model claude-haiku-5-5` | `-m opencode-go/<model>` |
| Effort | `-c model_reasoning_effort="low\|medium\|high\|xhigh\|max"` | `--thinking off\|minimal\|low\|medium\|high\|xhigh\|max` (or `:level` model suffix) | `--effort low\|medium\|high\|xhigh\|max` | `--variant high\|max` |
| Working dir | `-C <dir>` | none — `cd` first | none — `cd` first; `--add-dir=<path>` adds explicit read roots | `--dir <dir>` |
| Capture | `-o <file>`; stdout is the full transcript (noisy) | stdout is exactly the final message | stdout for one-shot calls; `--output-format stream-json` for supervised runs | stdout is the final message under a `> build · <model>` header; `--format json` gives a JSONL event stream with per-step token counts |
| Isolation | OS sandbox; `agent-delegate` defaults to `danger-full-access` unless the caller supplies a sandbox. `read-only` inspects only. Under `workspace-write`, Git metadata and linked-worktree index/HEAD remain read-only, so the lead commits and snapshots; full access permits authorized executor commits and snapshots. | **none**; every run has unsandboxed user access, and `agent-delegate` states read-only as an appended system-prompt instruction, never a tool allowlist | **none**; every delegated run uses `bypassPermissions`, and read-only is an appended instruction, never plan mode or a tool allowlist | **none**; permission config, and `--auto` approves everything not explicitly denied |
| Clean-room | curated prompt; reads repo AGENTS.md | `--no-session --no-extensions --no-skills --no-context-files` | `--safe-mode --disable-slash-commands --no-session-persistence` with a curated stdin prompt | `--pure` drops external plugins only; AGENTS.md and `~/.config/opencode/skills` still load |
| Resume | `codex exec resume --last` | `--session <id>` / `-c` / `--fork` | `--resume <session-id>` | `-c` / `-s <id>` / `--fork` |
| Quota | ChatGPT/Codex subscription; "You've hit your usage limit … try again at HH:MM" | Provider-dependent: `openai-codex` uses the **same** ChatGPT/Codex pool; `deepseek` uses separate API billing and quota; `opencode-go` draws the Go subscription, metered in usage dollars | Claude subscription through the first-party client | Conditional OpenCode Go subscription — a third pool metered in usage dollars ($12/5h, $30/week, $60/month), locally readable via `opencode stats`. Limit signature unprobed |

Effort capability is declared per backend in `delegation.toml` as
`supported_efforts`, with canonical `model_efforts` overrides replacing the
common set. Routing lint, resolution, and operator-directed validation refuse
unsupported efforts even with opt-ins. Pi's declared Sol catalog supports low,
medium, and high; xhigh and max require a verified custom model mapping recorded
in the capability data. DeepSeek's Pi mapping supports low, high and max. The delegated
OpenCode v2 provider supports no effort variants.

Backend selection between the two GPT routes:

- **codex CLI is the default for GPT work**, and mandatory-by-default for
  write mode: its OS sandbox is a real fence; pi's write mode has none.
  Route write-mode work through pi only when the codex CLI itself is the
  blocker (broken install, incompatible flag, harness without codex
  access), and then only inside a dedicated worktree with explicit
  scope fencing in the prompt.
- **pi's niche is provider plurality and lead portability**: one adapter
  reaches every provider the user has logged in. Today `openai-codex` reaches
  GPT-6 on the shared Codex subscription, `opencode-go` reaches V4.1 Flash —
  pi's default for every GPT profile and for `generate` — and the
  probationary MiMo rows on the Go subscription, and `deepseek` reaches V4.1
  Flash on independent API billing that no profile uses. Any harness that can run a shell can
  drive it. A non-Claude, non-Codex lead delegating to GPT goes through Pi.
- **DeepSeek V4.1 Flash 1017 is pi's default route, at max.** It is reached
  on the Go pool as `--provider opencode-go --model deepseek-v4.1-flash`,
  through each GPT profile's `deepseek-go` variant and through `generate`.
  Low and high are explicit alternatives. Five field arcs belong to September
  V4.1 Flash; the vendor's 54.4 DeepSWE result and fabrication observations
  belong to V4 Flash 0731. Neither measures 1017. Record each new observation's
  checkpoint, provider, harness and effort, and qualify provider-reported
  identity separately from the expected checkpoint behind a rolling alias.
  Brief it fully and check every identifier against source. V4 Pro is
  deprecated in favour of it.
- **MiMo V2.6 Flash and Pro are probation, and the preference between them
  is open.** Both rows are unmeasured — no score, no field arc, no
  approval anyone has confirmed — and no profile resolves to either. Reach
  them as `--provider opencode-go --model mimo-v2.6-flash` (or
  `mimo-v2.6-pro`) through a validated operator-directed selection:
  `agent-routing validate --profile <shape> --backend pi --model
  mimo-v2.6-flash --effort high --provider opencode-go --reason <text>
  --allow-experimental`, which records the execution shape, pool, and reason
  against the route version. Pro is read as a little stronger at about three
  times Flash's input; that read is an estimate, so a trial's result — not the
  price and not the read — is what would move either row. Both take a fully specified brief with exact targets,
  a scope ceiling, named acceptance probes, and lead review, and neither is
  the last model to touch shipped work.
- Delegated runs are not fenced (operator decision
  `delegated-runs-are-not-fenced`, agent-delegate journal). On Claude and pi,
  read-only is an instruction `agent-delegate` appends to the system prompt:
  change no repository or configuration file. Journal entries, the run's
  scratch directory, its report and build and test output are always
  writable, and the run keeps bash, so `git log` and gates work. No backend
  receives a tool allowlist or Claude's plan mode.
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
- Pi 0.99.1's bundled `opencode-go` catalog lists both `gpt-5.6-luna` and
  `gpt-6-luna`. Catalog presence describes client model metadata; profile
  seats and pool eligibility remain defined by the routing manifests.
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
- Before dispatch, `resolve --usage-file` checks caller-supplied normalized
  windows and follows only the profile's declared fallback. Record its
  `rerouted_from` identity and `pool-exhausted` reason with the run, including
  a changed backend; never retry the exhausted route. At a batch boundary,
  resolve admission before starting the executor sessions. A pinned tuple
  has no implicit fallback.
- `admit-review --author <coordinate> --usage-file <snapshot> --base <revision>
  --head <revision> --json` returns a quota-admitted independent route or typed
  `review-debt`. A route must execute with its explicit model and effort,
  read-only access and session persistence disabled over the named range.
  The Claude adapter's read-only mode is an instruction rather than a tool
  allowlist. A debt result dispatches nothing and requires an Arc
  `independent-review` obligation; it supplies no approval. Preserve an actual
  reviewer's verdict verbatim and bind it to the reviewed head before Arc
  integration. No quota result is review evidence.
- **Sonnet 5.5 is a trial, not a seat.** It is unmeasured and no profile
  resolves to it. Reach it as `claude -p --model claude-sonnet-5-5 --effort
  <tier>` through a validated operator-directed selection:
  `agent-routing validate --profile <shape> --backend claude --model
  sonnet-5.5 --effort <tier> --provider anthropic --reason <text>
  --allow-experimental`. Low, xhigh, and max are explicit-only, and max is a
  bounded trial under a token or time cap, never an escalation; medium and
  high are the trial tiers, and the first comparison is high against Opus 5.5
  medium on the same real work. Record the model, requested
  and effective effort, harness, and evaluator with every result. At its top
  tier the agent fanned out into subagents, timeouts, and out-of-scope
  edits, so read a run's diff against its brief's scope ceiling.

- **Haiku 5.5 high is the stable explore and extract seat on the claude
  backend.** It is the fixed id `claude-haiku-5-5`, the cheap Claude
  subscription seat for read-only reconnaissance (scouts) and fixed-shape
  extraction: `resolve explore --backend claude` and `resolve extract
  --backend claude` return it, and `--variant opus` selects Opus 5.5 xhigh for
  reconnaissance instead. It is never routed through an API-billed pool: a pi
  or OpenCode provider that bills the Claude API pays five times the
  short-prompt price above 100k prompt tokens and draws a paid pool where the
  subscription already covers the model, so only the Anthropic pool serves it
  and no other backend declares it. It holds no implementation, execution,
  planning or review seat. Medium is probationary; low, xhigh and max are
  explicit-only. Select any of them for another shape through `agent-routing
  validate --profile <shape> --backend claude --model haiku-5.5 --effort
  <tier> --provider anthropic --reason <text> --allow-experimental`, then pass
  the returned model and effort to the first-party client. A scout's report is
  a lead, not an established fact: verify each load-bearing fact against
  source, and give a fact the plan depends on to two overlapping lanes so one
  misread is caught ([field record](eras/2026-10-09-claude-roster-refresh.md)).
  Earlier trials are in `eras/2026-10-08-haiku-5-5-muzaiten-field-test.md` and
  the [read-only triage swarm](eras/2026-10-08-haiku-5-5-triage-swarm.md); Luna
  and DeepSeek worked different tasks, so neither compares their seats.
  The Anthropic pool serves Opus 5.5,
  Fable 5.1, Sonnet 5.5, and Haiku 5.5; Opus 5, Fable 5, Sonnet 5, and
  Haiku 4.5 are outside its served set.

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

Codex executors use the claim and stage sequence only when their sandbox and
Arc store permit those writes. A read-only executor inspects and reports
without claims or stages; a workspace-write executor leaves the commit and
snapshot to the lead; full access retains the authorized claim and commit
workflow, with a snapshot only when the Arc store is writable. When the store
prevents an import, evidence record, or snapshot, the lead performs it.
Executors record typed progress with their native identity:

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
`agent-delegate`/`codex exec` mechanism itself. The nested prompt names Codex's
sandbox, local worktree, commit/snapshot boundary, result location, and gate.

### Incorrect: Codex is told to invoke itself

```markdown
You are the Codex executor. Run `codex exec` to implement this plan.
```

This creates an unnecessary nested harness, can exceed the parent harness's
timeout, and may leave work half-finished. Replace it with local worktree
instructions.

### Correct: Codex completes an arc implementation

Codex reads the journal spec and works in the assigned worktree. A read-only
executor reports without writes; a workspace-write executor edits and verifies
then leaves the diff for the lead to commit and snapshot; a full-access
executor follows its authorized claim and commit workflow, then snapshots when
the Arc store is writable. The lead imports, records evidence, or snapshots
whenever the executor's sandbox or store does not permit those writes. Claude
later reviews and integrates.

### Incorrect: the implementation prompt merges

```markdown
After tests pass, run `arc integrate --cleanup` and merge to master.
```

The executor does not own that decision. A full-access executor stops after
its authorized snapshot when the Arc store is writable. A workspace-write
executor leaves the diff for the lead to commit and snapshot; a read-only
executor reports its inspection without writing. If the sandbox or Arc store
prevents an import, evidence record, or snapshot, the lead performs that write
before reviewing the exact patchset.

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
