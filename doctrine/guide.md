agent-routing — which model runs a task, and on which subscription.

This repository is the single owner of the roster, the named delegation
profiles, and the mechanism rules: the manifests hold the queryable view, and
the authored documents hold what a table cannot say. This CLI is how every
harness, skill, and script reads them without knowing where they live, so policy
is read when a decision is actually in front of you rather than carried in every
context window on the chance that one appears.

RESOLVE A ROUTE
  agent-routing resolve <profile> --backend <backend> --json

  The caller chooses the profile. resolve never reads a prompt and never
  classifies work; it maps that recorded choice to the current provider, model,
  effort, and stability, with a route version fingerprinting all three manifests
  so an answer can be tied to the exact data that produced it. Probationary and
  experimental routes need --allow-experimental — a whole profile as much as a
  variant — so a route that is not ready cannot be reached by accident.

VALIDATE AN OPERATOR-DIRECTED SELECTION
  agent-routing validate --profile <profile> --backend <backend>
    --model <model> --effort <effort> --provider <provider>
    --reason <text> [--allow-experimental] [--allow-cross-pool] --json

  validate keeps the named profile as the execution shape and checks an
  explicit model tuple without resolving that profile or selecting a variant.
  Direct selections are unrostered and experimental, so they require
  --allow-experimental even when the model also appears on a named route.
  The result identifies itself as operator-directed and carries the canonical
  and backend model identities plus the route-version witness. Unknown pool
  membership and missing backend/model support are refusals, not opt-ins.

CHOOSE A PROFILE BY THE SHAPE OF THE WORK
  extract      one fixed-input, fixed-output classification, extraction,
               aggregation, or bounded summary
  explore      read-only reconnaissance and source mapping, without a verdict
  plan         read-only technical planning: feasibility, failure modes, order
  implement    bounded production work whose targets and probes are already named
  execute      broad or multi-slice work where technical judgment and long-horizon
               persistence remain material
  review       read-only correctness and regression review of a bounded,
               behavior-affecting change
  design       read-only judgment on UX, copy, API ergonomics, or simplicity
  generate     candidate generation whose output is raw material rather than a
               deliverable, and never the last model to touch shipped work
  interactive  the default Pi parent session, before a child route is selected

  `agent-routing profiles` prints which backends each profile accepts.

WHAT BINDS BEFORE ANY QUERY
  Two co-equal leads sit on separate quota pools. The head model and the
  technical peer score alike at their working tiers and draw different
  subscriptions, so they are independent capacity rather than alternatives:
  route by which window has headroom, and by axis.

  Prohibited tiers stay prohibited when asked for by name, because every family
  stops paying before its top tier. Escalating a delegated route is ordinary —
  a workhorse tier upward, or across to the technical peer where judgment
  remains — but the head model's own effort is not an escalation path: a slice
  its working tier cannot land gets decomposed, given better context, or a
  sideways second opinion.

  An escalation that costs more than the caller's own seat, or draws on a
  scarcer pool, is offered to the user with its price and never dispatched on
  the caller's own initiative. A clean repository is where that question most
  often arises: its founding slices set the conventions every later model
  copies, so they belong on the best-taste tier the roster offers.

    agent-routing check <model> [effort]   exit non-zero if that pair is banned

  The reviewer is never the author. An approval from the identity that
  authored the patchset is not independent, and independence is never
  manufactured by inventing a second actor. That fence governs the claim, not
  whether a lead may inspect delegated work: a lead that did not write the
  implementation reviews it and records that verdict, carrying the executor's
  attribution where the ledger supports it.

  Independent review is an escalation, not a reflex. Repository policy, an
  explicit user requirement, or a wrong approval costly enough to warrant
  another judgment earns it; otherwise the lead inspects the delegated result,
  runs the declared gates, and integrates with an explicit debt record naming
  the coverage and the deeper pass still owed. Debt is a routine record of
  deferred coverage, not a reason to stop, and it never overrides an actual
  changes-requested verdict.

  Delegation goes through a resolved route carrying a curated brief, never a
  harness's native subagent defaults: those inherit the parent's model,
  effort, and entire conversation, which is why they are never the route.

READ THE POLICY IN FULL
  agent-routing doctrine     the authored policy, with the evidence and the
                             reasoning behind each rule
  agent-routing mechanism    the mechanism-routing prose canon
  agent-routing models       the model and effort matrix
  agent-routing profiles     the named delegation profiles
  agent-routing delegation   the delegation mechanism matrix
  agent-routing eras         model-era history

KEEP CONSUMERS HONEST
  agent-routing lint             compare the doctrine table's pass@1 and cost
                                 cells against the manifest, check model
                                 coverage, and validate route structure
  agent-routing lint-consumers   reject concrete roster pins in consumers

  A roster copied into a consumer is a roster that goes stale, and one transition
  once left four embedded copies wrong at the same time. Point a consumer at a
  verb instead of quoting a model.

WHERE THINGS ARE
  agent-routing root    the repository holding this data
  agent-routing dir     the manifest directory
  agent-routing all     every manifest, concatenated
