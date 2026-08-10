agent-routing — which model runs a task, and on which subscription.

The manifests in this repository are the single owner of the roster, the named
delegation profiles, and the mechanism rules. This CLI is how every harness,
skill, and script reads them without knowing where they live, so routing policy
is read when a decision is actually in front of you rather than carried in every
context window on the chance that one appears.

RESOLVE A ROUTE
  agent-routing resolve <profile> --backend <backend> --json

  The caller chooses the profile. resolve never reads a prompt and never
  classifies work; it maps that recorded choice to the current provider, model,
  effort, and stability, with a route version naming the manifest the answer came
  from. Probationary and experimental variants need --allow-experimental, so a
  route that is not ready cannot be reached by accident.

CHOOSE A PROFILE BY THE SHAPE OF THE WORK
  extract      one fixed-input, fixed-output classification, extraction,
               aggregation, or bounded summary
  explore      read-only reconnaissance and source mapping, without a verdict
  plan         read-only technical planning: feasibility, failure modes, order
  implement    bounded production work whose targets and probes are already named
  execute      broad or multi-slice work where technical judgment and long-horizon
               persistence remain material
  review       read-only correctness and regression review of a bounded change
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

    agent-routing check <model> [effort]   exit non-zero if that pair is banned

  The reviewer is never the author. Delegation goes through a resolved route
  carrying a curated brief, never a harness's native subagent defaults, which
  inherit the parent's model, effort, and entire conversation.

READ THE POLICY IN FULL
  agent-routing doctrine     the authored policy, with the evidence and the
                             reasoning behind each rule
  agent-routing mechanism    the mechanism-routing prose canon
  agent-routing models       the model and effort matrix
  agent-routing profiles     the named delegation profiles
  agent-routing delegation   the delegation mechanism matrix
  agent-routing eras         model-era history

KEEP CONSUMERS HONEST
  agent-routing lint             report where doctrine and manifest disagree
  agent-routing lint-consumers   reject concrete roster pins in consumers

  A roster copied into a consumer is a roster that goes stale, and one transition
  once left four embedded copies wrong at the same time. Point a consumer at a
  verb instead of quoting a model.

WHERE THINGS ARE
  agent-routing root    the repository holding this data
  agent-routing dir     the manifest directory
  agent-routing all     every manifest, concatenated
