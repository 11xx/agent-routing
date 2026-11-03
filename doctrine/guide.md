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

QUOTA ADMISSION BEFORE DISPATCH
  agent-routing resolve execute --backend codex --usage-file usage.json --json
  agent-routing admit-review --author <model>[#effort] --usage-file usage.json
    --base <revision> --head <revision> --json

  The caller supplies normalized account-window JSON from `agent-status usage`.
  Routing reads that file alone and never probes an account. Pool `usage_key`
  bindings in delegation.toml identify the account; profiles.toml owns snapshot
  freshness, the review threshold and each ordered fallback list. Each pool
  declares the windows its plan has (`windows`: Codex Pro has only the weekly
  one, Claude Max both). Every declared window must be reported fresh and
  valid, and every reported window must have room, declared or not.
  Unavailable, stale, expired or inconsistent observations do not establish
  availability.

  Without --usage-file, resolve remains a manifest-only query. With it, an
  exhausted execute pool follows the standing Codex-to-Opus or Claude-to-Sol
  route and records the original route as `rerouted_from` with reason
  `pool-exhausted`. Both pools exhausted, an unmeasured alternative, a profile
  without a fallback, or a pinned --variant yields one bounded refusal. Only
  fallback routes declared for that profile are authorized; no retry occurs.
  Check admission at the fan-out boundary before creating executor sessions.
  A snapshot describes observed headroom; it does not reserve capacity.

  admit-review emits agent-routing-review-admission/1. Codex-family authors
  select the current independent first-party Claude review seat only above
  50 percent remaining in the five-hour window. At 50 percent or below,
  unmeasured quota, or no eligible reviewer it returns status `review-debt`,
  route null, recommendation `record-debt`, and debt_kind `independent-review`.
  Claude-authored work keeps the independent Codex reviewer, subject to that
  pool's measured availability. A route outcome names the model, effort,
  read-only execution, non-persistence and the supplied base-to-head range.
  Pass resolved revisions. The adapter enforces those execution requirements;
  routing neither dispatches a reviewer nor records a verdict. On review-debt,
  record `arc debt <change> --kind independent-review --reason <reason>`.
  Eligibility and headroom are admission facts, never an approval. Quota does
  not change `frontier`, which describes the strongest rostered coverage.

ASSESS A REVIEW
  agent-routing assess --reviewer <model>#<effort>
    --author <model>[#<effort>] [--author ...]
    [--purpose findings|clearance] [--schema 1|2] [--json]

  assess judges any reviewer against the authors of the diff it read: a seated
  route, an operator-directed selection, or a model no profile seats. It
  answers two questions about the read:
    findings  "eligible" when the reviewer's review_tier reaches every
              author's floor, and strictly exceeds the floor of each author
              of its own family; the findings can be trusted, but the read
              does not by that alone clear review debt
    clears    true when the reviewer is family-independent of every author
              and its review_tier is at or above both the highest author
              floor and the clearance floor, models.toml [review] clearance;
              only a clearing read discharges review debt
  --purpose names the question asked, clearance by default. Both answers are
  always given; the purpose is recorded and leads the text line.

  --json emits agent-routing-assessment/2: the route version, the purpose, the
  clearance floor, the reviewer with its review_tier (null when its tier is
  unseated), each author with its floor, the highest known floor, findings,
  clears, independence, the qualifiers, and debt_kind "ineligible-review" when
  the read does not clear. independence is "eligible" exactly when no
  qualifier other than below-clearance holds. The reviewer and each author
  carry identities: the sorted roster id, aliases, and routed backend_model
  and model strings that routing resolves to that model, so a caller holding a
  harness-reported name can match it without routing data. --schema 1 emits
  agent-routing-assessment/1, the independence answer alone, without
  below-clearance, purpose, clearance, findings or clears; it refuses
  --purpose findings. Without --json it prints one line.

  A read clears exactly when no qualifier holds. The qualifiers are a closed
  set:
    same-model         the reviewer is an author's model, at any effort
    same-family        the reviewer shares a family with an author; always
                       present with same-model
    below-floor        the reviewer's review_tier is under the highest author
                       floor
    below-clearance    the reviewer's review_tier is under the clearance floor
    floor-unknown      an author's floor is unestablished
    reviewer-unseated  the reviewer's tier has no review_tier
  Floors follow the resolve rules: review_tier, else author_floor; an author
  without #effort uses the highest declared floor; a missing floor is never
  inferred. Models resolve through the roster's ids and aliases, and an unknown
  model or effort is refused, never guessed.

FIND THE REVIEW FRONTIER
  agent-routing frontier --author <model>[#<effort>]
    [--reads <model>#<effort>...] [--json]

  frontier answers the strongest review seat eligible for an author, so a
  caller can tell whether a recorded read is still the best routing can buy.
  A seat is a stable review route on any backend whose pool serves its
  model, one that carries excluded_author_families, the kind resolve review
  can sell; a seat on another profile never raises the frontier. It is
  eligible exactly when assess calls it independent, so frontier carries no
  independence rule of its own. Seats are ordered by review_tier, the
  cross-family scale assess compares, never by a pool-local rank. Quota and
  pool availability are not inputs: an exhausted pool still marks the
  frontier, and the answer moves only when the manifests do. --json emits
  agent-routing-frontier/1: the route version, the author with its floor, a
  status, the frontier, and the reads.
    status "frontier"          frontier carries the highest eligible
                               review_tier and every seat at that tier, each
                               a model, effort, backend and pool
    status "floor-unknown"     an author floor is unestablished, so there is
                               no frontier; a floor is never guessed
    status "no-eligible-seat"  the floor is known and no seat reaches it
  Each --reads coordinate carries its agent-routing-assessment/1 under the
  answered route version, and a standing against the frontier's tier: "below", "at" or
  "above", or "unranked" when the read's tier is unseated or there is no
  frontier. Standing compares tiers only; the read's own independence is in
  its assessment. Without --json it prints one line for the author and one per
  read.

VALIDATE AN OPERATOR-DIRECTED SELECTION
  agent-routing validate --profile <profile> --backend <backend>
    --model <model> --effort <effort> --provider <provider>
    --reason <text> [--allow-experimental] [--allow-cross-pool] --json

  When the operator names the exact tuple, --operator-named permits both
  explicit-only and experimental selection. It records that assertion and
  preserves prohibitions, role fences, backend effort support and pool checks.
  Unseated selection refusals list the stable seated efforts for the requested
  model, profile, backend and provider. `agent-routing seats --json` lists the
  bindings before selection; `check` answers only prohibition, not seating.
  Backend model spellings are roster aliases. An unsupported profile refusal
  lists the backend's supported routes; Claude's `explore` and `extract` are
  read-only shapes.

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

COMPARE WITH THE CALLER'S OBSERVED SEAT
  resolve and validate accept --caller <model>#<effort> and an optional
  --caller-provider <provider>. Name the provider when a model belongs to
  several pools. The caller is an observation, never inferred from ARC_MODEL.

  The optional `confirmation` block is agent-routing-confirmation/1 and
  advisory: `offer_to_user` is true for a higher rank in the same pool or a
  declared scarcer pool, false for a known ordinary move, and null when the
  policy cannot compare. A less scarce pool establishes no cross-pool tier
  cost comparison, so that move remains unknown. Cross-pool ranks remain
  unranked. The block names
  the caller, selection, pool and tier's stated benefit. A standing user
  authorization replaces the offer; the block is not a dispatch gate.

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
                                 coverage, and validate route structure and
                                 API prices: known category keys, a read
                                 date on every price, and a long-context
                                 surcharge with its threshold, its boundary
                                 and its multipliers, time-of-day windows
                                 that do not overlap in any hour of the
                                 week, and dated price
                                 changes in order after the read date
  agent-routing lint-consumers   reject concrete roster pins in consumers; fails
                                 when an accessor reports fewer sources than
                                 the floor routing/consumers.toml declares

  A roster copied into a consumer is a roster that goes stale, and one transition
  once left four embedded copies wrong at the same time. Point a consumer at a
  verb instead of quoting a model.

EXPORT LIST PRICES FOR TAPES
  agent-routing prices [--format tapes] [--output <file>]

  Print each roster row's api_price_per_million, or write it as a
  tapes-price-table/2 file for tapes to price sessions with. tapes never reads
  this repository: install the written file where tapes looks for a table,
  ~/.config/tapes/prices.toml, or point TAPES_PRICES or --prices at it. Each
  model is exported under its roster id with the ids harnesses record as
  aliases (the row's aliases and the backend_model routes bind to it), dated
  by its api_price_read, and priced only in the categories the row prices:
  input and cache-miss input as uncached_input, cached and cache-hit input as
  cache_read, cache_write as cache_write_5m, cache_write_1h, and output. A row
  with a long_context_surcharge carries it as a long-context term: once a
  request's whole prompt (uncached input, cache reads and cache writes) is
  over the threshold, or reaches it where threshold_inclusive says so, the
  whole request pays the input, cache and output multipliers, cache writes
  at the cache multiplier. The term names API per-token billing only: a
  Claude Code or Codex subscription pays no surcharge. A row's
  time_of_day_prices become UTC time-of-day windows that price every category
  the row prices at its multiplier, on the days of the week a window's days
  names (mon..sun) or every day, as DeepSeek's off-peak hours, its weekday
  peak hours on weekends included, are priced at half. Public holidays are
  not expressed. A row's api_price_changes export one model per price under
  the same ids, each in effect from its date until the next, as Gemini 3.8
  Flash doubles on 2027-01-01. Prices are API list prices; a pool that bills
  below list does not change them.

EMIT STATIC CLAUDE AGENTS
  agent-routing emit claude-agents [--profile <shape>] [--variant <variant>]
    [--allow-experimental] [--output-dir <dir>] [--check]

  Emit resolved definitions and their pin table as one JSON bundle. Stable
  routes are the default; trials need explicit opt-in, and bans remain binding.
  --output-dir stages agents/ and consumers-pins.toml; --check reads them and
  fails on drift. A generated pin makes consumer lint compare the full file.
  Harness deployment owns installation and session loading. Runtime settings
  are not generated by routing.

WHERE THINGS ARE
  agent-routing root    the repository holding this data
  agent-routing dir     the manifest directory
  agent-routing all     every manifest, concatenated

`agent-routing seats --json` projects every declared profile and variant by
backend, provider, model, effort, stability and default status. Trials retain
their stability label. The head-default query is the `plan` route on Claude; a missing binding is
reported with its refusal. The actual head is unobserved, independent of `ARC_MODEL`. A missing evidence
reference is null. Bars and author/reviewer eligibility remain model-row facts.
