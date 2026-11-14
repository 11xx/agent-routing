agent-routing — which model runs a task, and on which subscription.

This repository is the single owner of the roster, the named delegation
profiles and the mechanism rules. Three stores under data/ hold the facts, and
doctrine/principles.md and DELEGATION.md hold what a table cannot say. This
CLI is how every harness, skill and script reads them without knowing where
they live, so policy is read when a decision is in front of you rather than
carried in every context window on the chance that one appears.

THE STORES
  data/catalog.toml   facts about models: families and their lineages,
                      backends, models with status and successor, tiers with
                      rank, floor, stability and bans, API prices, surcharges,
                      time-of-day windows, Codex credits, reachability per
                      backend and provider, and per-backend effort support
  data/policy.toml    what the resolver, validate, assess, frontier and
                      admit-review decide from: review clearance, admission
                      thresholds, pools, family exceptions, fences, profiles,
                      seats, fallbacks, pool-local seat ranks, review seats by
                      purpose and the consumer inventory; and the guards,
                      standing instructions for
                      using a tier (a model, optionally an effort and a
                      profile) that leads follow. No verb that selects,
                      validates or refuses a route reads a guard.
  data/notes.jsonl    dated field notes, one JSON object a line: a model, an
                      optional effort, a kind (strength, weakness, observation,
                      measurement), area tags, a one-sentence claim, a cause
                      (brief, executor, integration, unknown), an evidence
                      reference and optional metrics. Append-only. No verb
                      that selects, validates or refuses a route reads them.

  Note ids are n followed by at least four decimal digits, increasing across
  notes and events. Every event has id, date, event and note (an earlier id):
    again       evidence; adds an occurrence with a date and reference
    retract     reason; marks a note inactive
    supersede   reason and replacement (an earlier corrected note id)
    undo        reason; cancels an earlier record without deleting it
  A correction appends the corrected note and then its supersede event.
  A compensation can cancel an undo record, restoring its effect. Earlier
  lines retain every byte. Notes are reference evidence; events change no
  route answer or route_version.

  Rows are flat and prose is short: a seat names the backends it serves, its
  `when` is one sentence saying what it is for, its `why` the reason it holds,
  its `since` the date it took effect. A guard's `rule` and `why` are one
  sentence each, and its `because` names the notes it rests on. A ban carries
  a one-sentence reason.

  A review seat is the operator's choice of reader for one review purpose
  (clearance, findings or exhaustive), one author lab, and one backend: its
  `author_family` is a catalog [[family]] id, a lineage no family row groups,
  or `any`, and its model and effort name a stable route of the review
  profile on that backend. Lint refuses a review seat that can never serve
  its purpose: a clearance seat below the [review] clearance floor or in the
  lab of the authors it is for, a clearance or findings seat below every
  floor of those authors, and an exhaustive seat below the highest-ranked
  stable review route its backend's pools serve. It also names a lab whose
  models hold a seat outside review when no clearance seat outside that lab
  can serve it.

  `lint` checks each store's raw shape (tables, key types, required and
  unknown keys) before anything reads it; every verb refuses a problem in
  what it decides from as manifest-invalid, naming the store and row. Guards
  and notes are outside that path both ways: no deciding verb reads them, and
  a fault in one never makes resolve, validate, assess, frontier,
  admit-review, check, routes, seats or ladder refuse. `lint`, `format`,
  `doctrine` and the change gate validate them.

  Each store is written in one canonical form: fixed key order, each model's
  rows (tiers, prices, reach) after the model and each profile's seats and
  fallbacks after the profile, in their recorded order. Parsing and writing a
  store reproduces it byte for byte.

    agent-routing lint               validate the whole data set; each problem
                                     names its store and row
    agent-routing format [--check]   rewrite the stores in canonical form, or
                                     name the ones that are not

  The route version is the first twelve hex digits of SHA-256 over, for the
  catalog and then the policy, the path, a NUL byte, the file's bytes and a
  NUL byte. Notes do not move it.

EDIT POLICY OR CATALOG
  All edit commands take --dry-run and --json. Catalog and policy edits
  require --why TEXT (one or two sentences); a seat's or guard's stored why
  is one sentence, at most 240 characters. Repeat --because NOTE_ID to cite
  motivating notes in the commit body; guards also retain them in because.

  set-seat PROFILE --backend BACKEND [--backend BACKEND...] [--variant NAME]
    --model MODEL --effort EFFORT [--provider PROVIDER]
    [--stability stable|probationary|experimental] --when SENTENCE --why TEXT
      Create or update the seat identified by profile and optional variant.
      Backends replace the row's backend list. Provider can be omitted only
      when every backend has exactly one common reach provider. An existing
      stability is retained unless supplied; new seats default to stable.
  remove-seat PROFILE [--variant NAME] --why TEXT
      Remove that seat. A default backend must retain a resolvable default.
  default-seat PROFILE --variant NAME [--backend BACKEND...] --why TEXT
      Make that variant the unnamed request's default on all its backends.
      Multi-backend rows default together. An overlapping primary is retained
      as primary-BACKEND (backends joined with hyphens when there are several),
      leaving its other backends on the primary. A partly overlapping variant
      default needs a hand split first; the command names it and refuses.
  prohibit MODEL EFFORT --reason SENTENCE --why TEXT
  allow MODEL EFFORT --why TEXT
      Set or lift the tier's prohibition. A seated prohibition is refused;
      choose another seat before prohibiting the tier.
  rank MODEL EFFORT --rank N --floor N --why TEXT
      Set capability rank and author floor. This moves Arc assurance at once;
      clearance changes when Arc next imports the ladder.
  set-fallback PROFILE --from-provider PROVIDER --backend BACKEND
    [--variant NAME] --why TEXT
  remove-fallback PROFILE --from-provider PROVIDER --backend BACKEND --why TEXT
      Upsert or remove the fallback keyed by profile, exhausted provider and
      destination backend. The destination must be a stable seat.
  set-review-seat PURPOSE --author-family FAMILY|any --backend BACKEND
    --model MODEL --effort EFFORT --when SENTENCE --why TEXT
  remove-review-seat PURPOSE --author-family FAMILY|any --backend BACKEND --why TEXT
      Upsert or remove the review seat keyed by purpose (clearance, findings
      or exhaustive), author lab and backend. Its model and effort name a
      stable review route on that backend that can serve the purpose. An edit
      leaving a lab whose models hold seats without a clearance seat outside
      it is refused, naming the lab.
  set-guard MODEL [--effort EFFORT] [--profile PROFILE] --rule SENTENCE --why TEXT
  retire-guard MODEL [--effort EFFORT] [--profile PROFILE] --why TEXT
      Upsert or retire one guard at this exact scope. Multiple guards at the
      same scope are ambiguous; edit them by hand. Neither rule nor because
      influences any deciding verb.
  add-model MODEL --family FAMILY --reach JSON [--reach JSON...]
    --tier JSON [--tier JSON...] --why TEXT
      Add a minimal catalog model. Each reach object has backend, provider,
      backend_model and optional agent_alias; each tier object has effort,
      rank, floor and optional stability. The model key is supplied by the
      command. Large roster changes, including pool membership, use hand edits.
  supersede-model MODEL --successor MODEL --why TEXT
      Mark an unseated model superseded; its notes remain reference evidence.

  Each edit builds candidate text in memory and validates the whole data set,
  including route, pool, price and rank relations, notes and guards. A refusal
  names the store and row and leaves the files untouched. Writers hold a
  checkout lock; readers take its shared lock so catalog and policy are read
  together. Files are flushed to a temporary sibling and renamed. A failed
  Git commit restores the earlier working bytes. Signing follows Git config.
  The commit contains only changed data paths, the reason, motivating note
  ids and Routing-edit: VERB. When arc env establishes an acting harness and
  model, Implemented-by records them. Nothing is pushed.

  agent-routing commit --why TEXT [--because NOTE_ID...] [--dry-run] [--json]
    Validate and canonicalize hand edits, then commit only data paths. Other
    edits refuse dirty data paths, staged or unstaged, with instructions to
    commit them or discard them. Unrelated staged work stays staged.
  agent-routing log [--limit N] [--json]
    Show the stores' Git history, including hand commits, newest first. Each
    line carries a short hash, date, verb, row and the reason's first sentence.
  agent-routing undo --why TEXT [--dry-run] [--json]
    Revert the latest Routing-edit commit as a new verb commit. Disjoint later
    edits are retained; overlapping edits refuse. Catalog and policy regain
    the previous bytes. Notes regain their previous presentation through
    appended undo events, preserving every earlier byte. Undoing an undo
    restores the effect of the original edit.

  Every edit names the store, table and row, then prints only changed fields
  as field: old → new. Added rows list their fields; removed rows are named
  as removed. The footer carries old and new route_version, commit id, and
  affected generated consumers with refresh commands. Notes
  leave route_version unchanged. --json emits one agent-routing-edit/1 object
  with verb, dry_run, changes, old_route_version, new_route_version,
  stale_consumers and commit (null for dry runs); changes name store, table,
  before and after. Errors use agent-routing-edit-error/1 with verb and error.
  Generation is reported from seat and reach inputs, not by reading deployed
  consumers. Emit stages agents/ and consumers-pins.toml under its output
  directory; consumer deployment owns installation and enrollment of pins.

FILE AND READ FIELD EVIDENCE
  agent-routing note --model MODEL [--effort EFFORT]
    --kind strength|weakness|observation|measurement --area AREA [--area AREA...]
    --claim SENTENCE --cause brief|executor|integration|unknown --evidence REF
    [--metrics JSON] [--date YYYY-MM-DD] [--dry-run] [--json]
      Append one canonical note with the next id. Metrics are a nonempty
      object of finite numbers and strings. The date defaults to today.
  agent-routing again NOTE_ID --evidence REF [--date YYYY-MM-DD]
      Append one recurrence. No reason is required.
  agent-routing retract NOTE_ID --reason TEXT [--date YYYY-MM-DD]
      Append a retraction for a mistaken live note.
  agent-routing supersede NOTE_ID --claim SENTENCE --evidence REF --reason TEXT
    [--model MODEL] [--effort EFFORT] [--kind KIND] [--area AREA...]
    [--cause CAUSE] [--metrics JSON] [--date YYYY-MM-DD]
      Append a corrected note, inheriting unspecified fields, then a
      supersession referencing it. The earlier note becomes inactive.
  Recurrence and disposition commands also take --dry-run and --json.
  No note command needs --why. Earlier lines are never rewritten; the
  notes-grow-only change invariant checks every intervening revision.

  agent-routing notes [MODEL] [--kind KIND] [--area AREA]
    [--liveness live|inactive|all] [--json]
      Filter notes, live by default, ordered by occurrence count, latest
      occurrence date, then id. Dates and evidence accompany each occurrence.
  agent-routing card MODEL [--json]
      Print seats, prohibited tiers and scoped guards, then live evidence in
      recurrence and recency order. Sections are Seats, Prohibited, Guards,
      Weaknesses, Strengths, Observations and measurements, then inherited
      evidence. Empty sections say none. A predecessor naming this model as
      its catalog successor contributes evidence under "Inherited from
      PREDECESSOR, unverified for this model".

READABLE TEXT VIEWS
  Text uses the terminal width, or 80 columns for redirected output. Seat
  columns align across the model's own rows. Variants read profile:variant;
  experimental and probationary labels lead the seat's when sentence.
  Guards lead with their effort and profile scope, with why, since and
  because beneath the rule. Claims wrap with a hanging indent; evidence
  has its own indented line. A note shows ×N and a date range only when its
  first and last dates differ. notes leads each entry with model and effort,
  and inactive entries say retracted or superseded with their reason.
  Text uses no colour. JSON output retains the complete structured result.

  The invented fixture, at 80 columns:

    agent-routing card nw-atlas-2

nw-atlas-2 · northwind
Seats
  implement:atlas       claude  medium  default  Specified implementation from a
                                                 Northwind session.
  implement:atlas-high  claude  high             Implementation that needs the
                                                 head model's standing tier.
  implement:bounded     claude  medium           experimental · Explicit
                                                 comparison with a fixed
                                                 deadline.
  review:atlas          claude  xhigh   default  Review from a Northwind
                                                 session.
Prohibited
  max: Fixture ban: the top tier buys nothing over xhigh.
Guards
  · high, implement: Name exact targets and stop when a target is absent before
    beginning any implementation.
    why: The fixture's failed brief left its target ambiguous.
    since 2030-01-06   because n0003
Weaknesses
  n0003  ×2  2030-01-06 → 2030-01-09   An ambiguous target can send
                                       implementation past the intended files
                                       unless the brief names a stop condition.
    evidence: 2030-01-06 fixture:case-3
    evidence: 2030-01-09 fixture:repeat
Strengths
  n0005  ×1  2030-01-07   A bounded change with named probes lands cleanly.
    evidence: fixture:case-5
Observations and measurements
  n0010  ×1  2030-01-09   The corrected fixture score is one quarter.
    evidence: fixture:case-10
    metrics: pass_at_1: 0.25
Inherited from nw-atlas-1, unverified for this model
  n0006  ×1  2030-01-03   The predecessor needed explicit target boundaries.
    evidence: fixture:case-6

  A preview names its seat and shows only the fields it changes:

agent-routing set-seat implement --variant flat --backend pi \
  --model orbit-flash --effort low --when "Fixed-scope implementation from pi." \
  --why "Use the cheaper measured tier." --dry-run

set-seat (dry run)
data/policy.toml seat implement:flat (backends: pi)
  effort: max → low
  when: Specified implementation from pi. → Fixed-scope implementation from pi.
  why: The flat pool's workhorse. → Use the cheaper measured tier.
  since: 2030-01-03 → 2030-01-09
route_version: b31715eb8626 -> 298e8fdfce1f
stale consumers: none

RESOLVE A ROUTE
  agent-routing resolve <profile> --backend <backend> --json

  The caller chooses the profile. resolve never reads a prompt and never
  classifies work; it maps that recorded choice to the current provider, model,
  effort and stability, with the route version tying the answer to the exact
  data that produced it. The answer names the backend's own model string from
  the catalog's reach row. Probationary and experimental routes need
  --allow-experimental — a whole profile as much as a variant — so a route that
  is not ready cannot be reached by accident.

  For review, add --author '<model>#<effort>' using the diff author's
  recorded coordinate, and --purpose for what the read is for. The answer is
  the policy's review seat for that purpose, the author's lab and the
  backend: the lab's own [[review_seat]] row, else its `any` row. resolve
  checks that seat against the purpose's requirement and refuses, naming
  it, when the seat does not meet it:
    clearance   the default; the independent read of a change, the one that
                may clear review debt: a stable seat outside the author's lab,
                at or above both the author's capability floor and the
                policy's [review] clearance
    findings    candidate defects for someone else to adjudicate: a seat at or
                above the author's tier, its own lab included, except the
                same model at a lower effort
    exhaustive  a whole-surface read chosen for capability: a seat among the
                backend's highest-ranked stable review routes, the author's
                own lab and model included; it never clears, and --author is
                optional
  A route's excluded families are its reviewer's family: the lineages the
  catalog's [[family]] row groups with the reviewer's own, the same relation
  assess reads for same-family. --variant names the route instead of the
  policy's seat and is checked the same way. Capability grants no routing
  seat. A missing seat, or one the author's facts do not satisfy, is a
  refusal, never a weaker reviewer: for clearance and findings
  "review-independence" recommending Arc review debt, for exhaustive
  "review-purpose" with reason "no-review-seat" or "below-top-rank". Unknown
  author floors also recommend debt, except for exhaustive, which needs no
  floor. Omitting #effort uses the highest declared author floor; missing
  floors are not inferred.

  Without --author or --purpose, review JSON carries the backend's default
  review route with independence: "unverified", the excluded author
  families, and the reviewer tier inside `review`; --purpose clearance or
  findings then refuses, since there is nothing to judge. With an author it
  carries the author floor, the purpose, and the seat's three answers:
  independence ("eligible" when outside the excluded families and at the
  author's tier), findings ("eligible" or "ineligible") and clears (true or
  false), with the assessment qualifiers. A findings route may say
  independence "ineligible" and clears false; only clears true discharges
  debt. An exhaustive answer always says clears false and adds
  purpose_qualifiers: ["not-chosen-for-independence"]. Eligibility is not a
  verdict. ARC_MODEL is never used as the author, since the caller may not
  have written the diff. --author and --purpose are only valid for review.

  When no route serves the purpose, --accept-ineligible (which needs --author
  and refuses exhaustive, which clears nothing) returns the strongest stable
  seat instead of refusing, ties broken by the profile's order of
  preference. Its `review` block carries the seat's answers and qualifiers,
  recommendation: "record-debt" and debt_kind: "ineligible-review". Where a
  route serves the purpose the answer is the same with or without the flag.

  Which review answers are rows and which are ranks: resolve review with
  --author or --purpose, and admit-review through it, answer the policy's
  review seats, bounded by ranks, floors and labs. The rest is computed from
  ranks and labs: assess judges any pair; frontier is the strongest eligible
  review route for an author; ladder exports the capability table; and the
  strongest seat --accept-ineligible returns is chosen by rank.

LIST ROUTES FOR A PICKER
  agent-routing routes --json [--backend <backend>] [--profile <profile>]

  Emit one agent-routing-routes/1 object with route_version, routes and
  prohibited. Each route carries profile, variant, backend, provider, model,
  effort, stability and the default flag reported by seats. It equals the plain
  resolve answer for those coordinates, without opt-ins, authors or quota
  observations. Unnamed requests use variant: null; backend-default variants
  are also listed by name. Routes needing experimental or cross-pool opt-in are
  omitted.

  The filters restrict routes only, together or individually; unmatched values
  yield an empty list. prohibited always lists every banned model and effort
  with its recorded reason. Routes sort by profile, variant (unnamed first) and
  backend; prohibitions sort by model and effort. --json is required.

QUOTA ADMISSION BEFORE DISPATCH
  agent-routing resolve <profile> --backend <backend> --usage-file usage.json --json
  agent-routing admit-review --author <model>[#effort] --usage-file usage.json
    --base <revision> --head <revision> --json

  The caller supplies normalized account-window JSON from `agent-status usage`.
  Routing reads that file alone and never probes an account. A policy pool's
  `usage_key` names the account; the policy's [admission] table holds snapshot
  freshness and the review threshold, and its [[fallback]] rows the ordered
  fallbacks of each profile. Each pool declares the windows its plan has
  (`windows`). Every declared window must be reported fresh and valid, and
  every reported window must have room, declared or not. Unavailable, stale,
  expired or inconsistent observations do not establish availability.

  Without --usage-file, resolve remains a data-only query. With it, an
  exhausted pool follows the profile's fallback for that provider and records
  the original route as `rerouted_from` with reason `pool-exhausted`. Both
  pools exhausted, an unmeasured alternative, a profile without a fallback, or
  a pinned --variant yields one bounded refusal. Only fallback routes declared
  for that profile are authorized; no retry occurs. Check admission at the
  fan-out boundary before creating executor sessions. A snapshot describes
  observed headroom; it does not reserve capacity.

  admit-review emits agent-routing-review-admission/1. Authors whose lineage
  [admission] codex_author_families lists are reviewed on its
  codex_review_backend, others on its other_review_backend. A review on the
  claude window needs more than claude_minimum_remaining percent of its
  five-hour window. At or below it, with unmeasured quota, or with no eligible
  reviewer it returns status `review-debt`, route null, recommendation
  `record-debt` and debt_kind `independent-review`. A route outcome names the
  model, effort, read-only execution, non-persistence and the supplied
  base-to-head range. Pass resolved revisions. The adapter enforces those
  execution requirements; routing neither dispatches a reviewer nor records a
  verdict. On review-debt, record `arc debt <change> --kind independent-review
  --reason <reason>`. Eligibility and headroom are admission facts, never an
  approval. Quota does not change `frontier`, which describes the strongest
  rostered coverage.

ASSESS A REVIEW
  agent-routing assess --reviewer <model>[#<effort>]
    --author <model>[#<effort>] [--author ...]
    [--purpose findings|clearance|exhaustive] [--as-of <RFC3339> [--accepted <ref>]]
    [--schema 1|2] [--json]

  Every catalog tier has a capability rank and author floor: 1 bounded work,
  2 a working technical peer, 3 the top review band. Capability is independent
  of seats, model size, price and retirement. Rank measures the reviewer; floor
  is the least rank for authored work and can be lower. Lint requires both
  values and a rank in another family that meets every floor. No exclusive top
  is valid. The policy's pool-local seat_rank orders selections, not
  capability.

  assess judges any known pair, including retired models and unseated tiers:
    findings  eligible when rank reaches every author's floor, except the
              same model at an effort lower than its author's
    clears    true when findings are eligible, the reviewer is independent
              of every author's family, and rank reaches [review] clearance
  Equal-rank same-family reads can find but never clear, except for the
  model pairs a policy [[family_exception]] row names. An effort-less reviewer
  uses its minimum rank; an effort-less author its maximum floor. --purpose
  records the question asked and leads the text; both answers are always
  given.

  An exhaustive read is chosen for capability, not independence, so
  --purpose exhaustive never clears and adds purpose_qualifiers:
  ["not-chosen-for-independence"], outside the closed qualifier set, in
  both schemas. A reader of the closed set must see why the read does not
  clear, so the answer is given only when a closed qualifier already makes
  the read ineligible (same-model, same-family, below-floor or
  floor-unknown). A reviewer independent of every author is refused as
  "exhaustive-independent". --as-of reads the accepted branch's first-parent history at the
  instant; --accepted <ref> selects that history explicitly. The default is
  the repository's default branch, never the checkout's HEAD. Remote
  origin/HEAD identifies the local default branch when available; a sole local
  master or main is the fallback. Ambiguous or unavailable defaults require
  --accepted. Without --as-of, assess uses the current stores and refuses
  --accepted.

  A dated answer reads the stores at the pinned revision; a revision before the
  stores existed is read through the ladder's recorded reconstruction of the
  routing files it held. A revision whose policy wrote a route as one seat row
  per backend reads as the one route those rows share, and a revision whose
  stores have problems is refused rather than read as an empty table. route_version binds the pinned data, the ladder's
  design record at that revision (or its absence), and the projected
  capability table. Dates before the numeric record refuse with ladder-gap;
  invalid or timezone-less instants are refused. Dated reads validate the
  complete accepted capability history as ladder --history does.
  Non-increasing version dates refuse with effective_from must increase and
  name the offending version. Each exported version takes effect at its
  effective_from instant. Dated reads select commits before the next
  capability version; an earlier-dated neutral descendant cannot make that
  next table take effect sooner.

  --json emits agent-routing-assessment/2 with the route version, purpose,
  clearance, reviewer, authors, floor, independence, qualifiers, findings,
  clears and debt_kind. The reviewer's review_tier field carries its capability
  rank; authors carry floor. Each coordinate includes its known identities. The
  shape is independent of --as-of. --schema 1 emits the independence answer
  without purpose, clearance, findings, clears or below-clearance; it refuses
  --purpose findings. Without --json the answer is one line, ending with any
  purpose qualifier.

  Qualifiers are a closed set:
    same-model         the reviewer is an author's model, at any effort
    same-family        a shared family under the catalog's [[family]] rows
    below-floor        rank is below the highest author's floor
    below-clearance    rank is below [review] clearance
    floor-unknown      an author's floor is unestablished
    reviewer-unseated  no stable route seats the reviewer's tier; a routing
                       note that does not refuse findings or clearance
  Independence ignores below-clearance and reviewer-unseated. Clearance
  ignores only reviewer-unseated. A pair a [[family_exception]] row names
  raises no same-family; the assessment lists those authors under
  family_exception, outside the qualifiers. Unknown models or efforts are
  refused.

EXPORT THE CAPABILITY LADDER
  agent-routing ladder --json [--history] [--accepted <ref>]

  Emit arc-review-ladder/1, the same structure Arc imports as JSON or TOML.
  Both modes read the accepted ref, resolved once to a commit, with the same
  default-branch selection as assess --as-of. They ignore the checkout's
  branch and working files. Plain output contains the current accepted
  capability table alone; --history reconstructs each distinct table from the
  start of the numeric record onward, reading the stores where a revision has
  them and the routing files it held otherwise. Commits changing only prices,
  seats or notes do not create versions.

  A version's effective_from is the committer time of the accepted ref's
  first-parent commit whose table differs from its parent's. Land table
  changes as a no-ff merge, or as a single commit directly on the accepted
  branch. A no-ff merge records acceptance time and excludes topic-internal
  tables. Fast-forwarding a series of topic commits does not record when those
  tables were accepted and must not be used for capability changes.

  Each version has a stable id and a source naming its accepted commit. Before
  the numeric record begins there is one gap=true version without a model
  table; no rank is invented for that span. The producer validates every
  version before emitting any bytes: positive integers, reachable cross-family
  floors, unique ids and identities, nonempty efforts, and strictly increasing
  RFC 3339 instants. Failure names the version. Unavailable numeric-era history
  is refused by --history; current-only export can use a shallow accepted
  snapshot.

FIND THE REVIEW FRONTIER
  agent-routing frontier --author <model>[#<effort>]
    [--reads <model>#<effort>...] [--json]

  frontier answers, from ranks rather than review seat rows, the strongest
  review route eligible for an author, so a caller can tell whether a
  recorded read is still the best routing can buy. A seat is a stable review
  route on any backend whose pool serves its model, a
  route of the review profile, the kind resolve review can sell; a seat on
  another profile never raises the frontier. It is eligible exactly when assess
  calls it independent, so frontier carries no independence rule of its own.
  Seats are ordered by review_tier, the cross-family scale assess compares,
  never by a pool-local rank. Quota and pool availability are not inputs: an
  exhausted pool still marks the frontier, and the answer moves only when the
  stores do. --json emits agent-routing-frontier/1: the route version, the
  author with its floor, a status, the frontier, and the reads.
    status "frontier"          frontier carries the highest eligible
                               review_tier and every seat at that tier, each
                               a model, effort, backend and pool
    status "floor-unknown"     an author floor is unestablished, so there is
                               no frontier; a floor is never guessed
    status "no-eligible-seat"  the floor is known and no seat reaches it
  Each --reads coordinate carries its agent-routing-assessment/1 under the
  answered route version, and a standing against the frontier's tier: "below",
  "at" or "above", or "unranked" when there is no frontier. Standing compares
  tiers only; the read's own independence is in its assessment. Without --json
  it prints one line for the author and one per read.

VALIDATE AN OPERATOR-DIRECTED SELECTION
  agent-routing validate --profile <profile> --backend <backend>
    --model <model> --effort <effort> --provider <provider>
    --reason <text> [--allow-experimental | --operator-named] [--allow-cross-pool] --json

  When the operator names the exact tuple, --operator-named permits both
  explicit-only and experimental selection. It records that assertion and
  preserves prohibitions, model status, fences, backend effort support and
  pool checks. A model with a status (superseded, retired and the like) is
  refused with its successor; a policy [[fence]] keeps a model off a profile
  with its reason. Unseated selection refusals list the stable seated efforts
  for the requested model, profile, backend and provider. `agent-routing seats
  --json` lists the bindings before selection; `check` answers only
  prohibition, not seating. Backend model spellings are the catalog's reach
  rows and aliases. An unsupported profile refusal lists the backend's
  supported routes.

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
  policy cannot compare. A less scarce pool establishes no cross-pool tier cost
  comparison, so that move remains unknown. Cross-pool ranks remain unranked.
  The block names the caller, the selection, the pool and, as `benefit`, the
  `when` of the seat being selected: for resolve the seat it answered with,
  for validate the named profile's seat, or else an escalation source's, on
  that backend, provider, model and effort. A selection that is no seat has a
  null benefit. A standing user authorization replaces the offer; the block is
  not a dispatch gate.

CHOOSE A PROFILE BY THE SHAPE OF THE WORK
  `agent-routing profiles` prints every profile with its purpose line, and
  each seat with the backends it serves and its `when`. Choose by the shape of
  the work, never by the model you expect.

WHAT BINDS BEFORE ANY QUERY
  The standing principles are doctrine/principles.md, printed first by
  `agent-routing doctrine`. Three of them bind every query:

  Prohibited tiers stay prohibited when asked for by name.

    agent-routing check <model> [effort]   exit non-zero if that pair is banned

  An escalation that costs more than the caller's own seat, or draws on a
  scarcer pool, is offered to the user, naming the route, what it buys and the
  pool it spends.

  The reviewer is never the author, and independence is never manufactured.
  Independent review is an escalation, not a reflex; otherwise the lead
  inspects, runs the gates and records the deferred coverage as Arc debt.

READ THE POLICY
  agent-routing doctrine     the principles, then every profile's seats with
                             their when, why and since and the guards on
                             them, the guards on unseated tiers, the bans,
                             fences, pools and the catalog, rendered from the
                             stores
  agent-routing mechanism    the delegation mechanism canon (DELEGATION.md)
  agent-routing models       the catalog
  agent-routing profiles     the policy
  agent-routing delegation   the backend, reachability, effort-support and
                             pool rows
  agent-routing all          the catalog, the policy and the field notes

KEEP CONSUMERS HONEST
  agent-routing lint-consumers   reject concrete roster pins in the sibling
                                 repositories the policy's consumer inventory
                                 names; fails when an accessor reports fewer
                                 sources than the floor the policy declares

  A roster copied into a consumer goes stale. Point a consumer at a verb
  instead of quoting a model. This lint reads other repositories, so it runs
  on demand rather than in this repository's change gate.

EXPORT LIST PRICES FOR TAPES
  agent-routing prices [--format tapes] [--output <file>]

  Print each catalog price row, or write it as a tapes-price-table/2 file for
  tapes to price sessions with. tapes never reads this repository: install the
  written file where tapes looks for a table, ~/.config/tapes/prices.toml, or
  point TAPES_PRICES or --prices at it. Each model is exported under its
  catalog id with the ids harnesses record as aliases (the model's aliases and
  its reach rows' backend models), dated by the row's read date, and priced
  only in the categories the row prices: input and cache-miss input as
  uncached_input, cached and cache-hit input as cache_read, cache_write as
  cache_write_5m, cache_write_1h, and output. A [[surcharge]] row becomes a
  long-context term: once a request's whole prompt (uncached input, cache reads
  and cache writes) is over the threshold, or reaches it where
  threshold_inclusive says so, the whole request pays the input, cache and
  output multipliers, cache writes at the cache multiplier. The term names API
  per-token billing only: a subscription pays no surcharge. [[price_window]]
  rows become UTC time-of-day windows that price every category the row prices
  at their multiplier, on the days of the week a window's days names (mon..sun)
  or every day. Public holidays are not expressed. A price row with a `from`
  date is one more price for the same model, in effect from that date until
  the next. Prices are API list prices; a pool that bills below list does not
  change them.

EMIT STATIC CLAUDE AGENTS
  agent-routing emit claude-agents [--profile <shape>] [--variant <variant>]
    [--allow-experimental] [--output-dir <dir>] [--check]

  Emit resolved definitions and their pin table as one JSON bundle. Stable
  routes are the default; trials need explicit opt-in, and bans remain
  binding. Each agent's model is the reach row's agent alias, and its pins
  belong to the policy consumer generated from claude-agents. --output-dir
  stages agents/ and consumers-pins.toml; --check reads them and fails on
  drift. A generated pin makes consumer lint compare the full file. Harness
  deployment owns installation and session loading. Runtime settings are not
  generated by routing.

WHERE THINGS ARE
  agent-routing root    the repository holding this data
  agent-routing dir     the data directory

`agent-routing seats --json` projects every declared profile and variant by
backend, provider, model, effort, stability and default status. Trials retain
their stability label. The head-default query is the `plan` route on Claude; a
missing binding is reported with its refusal. The actual head is unobserved,
independent of `ARC_MODEL`.
