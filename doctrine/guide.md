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

  For independent review, add --author '<model>#<effort>' using the diff
  author's recorded coordinate. Review routes exclude their own model family
  and require a stable reviewer at or above the author's review_tier, or
  author_floor for an unseated tier. An author_floor grants no reviewer seat. An
  ineligible default may select an eligible variant on the same backend;
  --variant confines the choice. No eligible route means a refusal recommending
  Arc review debt, not a weaker or same-family reviewer. Unknown author floors
  also recommend debt. Omitting #effort uses the highest declared author floor;
  missing floors are not inferred.

  Without --author, review JSON carries independence: "unverified", the
  excluded author families, and the reviewer tier inside `review`. With an
  eligible author it carries independence: "eligible" and the author floor.
  Eligibility is not a verdict. ARC_MODEL is never used as the author, since
  the caller may not have written the diff. --author is only valid for review.

  When no eligible route exists, --accept-ineligible (which needs --author)
  returns the strongest stable seat instead of refusing, ties broken by the
  profile's order of preference. Its `review` block carries independence:
  "ineligible", the assessment qualifiers, recommendation: "record-debt" and
  debt_kind: "ineligible-review". It never appears as independent. Where an
  eligible route exists the answer is the same with or without the flag.

ASSESS A REVIEW
  agent-routing assess --reviewer <model>#<effort>
    --author <model>[#<effort>] [--author ...] [--json]

  assess judges any reviewer against the authors of the diff it read: a seated
  route, an operator-directed selection, or a model no profile seats. --json
  emits agent-routing-assessment/1: the route version, the reviewer with its
  review_tier (null when its tier is unseated), each author with its floor, the
  highest known floor, independence "eligible" or "ineligible", the qualifiers,
  and debt_kind "ineligible-review" when ineligible. The reviewer and each
  author carry identities: the sorted roster id, aliases, and routed
  backend_model and model strings that routing resolves to that model, so a
  caller holding a harness-reported name can match it without routing data.
  Without --json it prints one line. A read is eligible exactly when no qualifier holds. The qualifiers
  are a closed set:
    same-model         the reviewer is an author's model, at any effort
    same-family        the reviewer shares a family with an author; always
                       present with same-model
    below-floor        the reviewer's review_tier is under the highest author
                       floor
    floor-unknown      an author's floor is unestablished
    reviewer-unseated  the reviewer's tier has no review_tier
  Floors follow the resolve rules: review_tier, else author_floor; an author
  without #effort uses the highest declared floor; a missing floor is never
  inferred. Models resolve through the roster's ids and aliases, and an unknown
  model or effort is refused, never guessed.

VALIDATE AN OPERATOR-DIRECTED SELECTION
  agent-routing validate --profile <profile> --backend <backend>
    --model <model> --effort <effort> --provider <provider>
    --reason <text> [--allow-experimental] [--allow-cross-pool] --json

  validate keeps the named profile as the execution shape and checks an
  explicit model tuple without resolving that profile or selecting a variant.
  The result carries the canonical and backend model identities, the
  route-version witness, the profile's own route as `baseline`, and a
  `direction` from comparing policy ranks within the selection's pool. Only a
  stable baseline admits a stable selection, and then either a tuple the
  profile or its `escalation_sources` seat stably, at or above the baseline,
  or a stable variant of the profile on the requested backend and provider,
  whatever its rank. A stable upgrade reports `operator-escalation`. Every
  other selection is experimental and requires --allow-experimental. Unknown
  pool membership and missing backend/model support are refusals, not
  opt-ins.

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
  stops paying before its top tier. Escalating a delegated route within what
  the caller's own seat costs is ordinary — a workhorse tier upward, or across
  to the technical peer where judgment remains — but the head model's own
  effort is not an escalation path: a slice its working tier cannot land gets
  decomposed, given better context, or a sideways second opinion.

    agent-routing check <model> [effort]   exit non-zero if that pair is banned

  An escalation that costs more than the caller's own seat, or draws on a
  scarcer pool, is offered to the user by default, naming the route, what it
  buys, and the pool it spends. A standing user instruction that
  pre-authorizes escalation replaces the ask for the work it covers. A
  declined offer leaves the work at the caller's tier, except under a floor,
  where it waits. Escalating to the caller's own tier is ordinary; prefer an
  equivalent tier from another lab. Compare candidates as model-and-effort
  tiers, capability and cost together, and let taste break ties. One place the question arises is a clean repository: its
  founding slices set the conventions every later model copies, so they belong
  on the head model at its routing ceiling.

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
