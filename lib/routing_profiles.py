"""Validation and deterministic resolution for named delegation routes."""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re

import stores

STABILITIES = {"stable", "probationary", "experimental"}

#: Every key a route table may carry. A manifest is data an author edits by
#: hand, so a misspelling has to be a refusal: an unrecognised key is silently
#: ignored by every reader, which makes the route it was meant to change look
#: as though the edit never happened.
PROFILE_KEYS = frozenset(
    {
        "id",
        "purpose",
        "provider",
        "model",
        "backend_model",
        "effort",
        "stability",
        "backends",
        "variant",
        "escalation_sources",
        "fallback",
    }
)
VARIANT_KEYS = frozenset(
    {
        "id",
        "provider",
        "model",
        "backend_model",
        "effort",
        "stability",
        "backends",
        "default_for_backend",
        "role_exception",
    }
)
UNROUTABLE_MODEL_STATUSES = {"deprecated", "inactive", "restricted", "retired", "superseded"}
MODEL_STATUSES = UNROUTABLE_MODEL_STATUSES | {"experimental"}
EFFORT_STATUSES = {"explicit-only", "experimental", "probationary"}
#: The order a rank must respect within one model and pool. Manifest order is
#: not this order: older rows list their efforts from the top down.
EFFORT_ORDER = ("low", "medium", "high", "xhigh", "max", "ultra")

REFUSAL_SCHEMA = "agent-routing-refusal/1"


class RouteRefusal(ValueError):
    """A resolution the policy declines, carrying why as data.

    A caller that cannot classify a refusal works around it, and the
    work-around for an opaque failure is a hand-written invocation — which is
    the thing a resolver exists to prevent. The prose stays for a person; the
    payload is for the tool that has to decide what to do next.
    """

    def __init__(self, kind: str, message: str, **fields: object) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.fields = {key: value for key, value in fields.items() if value is not None}

    def payload(self) -> dict[str, object]:
        return {"schema": REFUSAL_SCHEMA, "kind": self.kind, "message": self.message, **self.fields}


def data(root: pathlib.Path) -> stores.Data:
    """The stores at `root`; a refusal naming every problem when they cannot be projected."""
    try:
        loaded = stores.load(root)
    except stores.StoreError as error:
        raise RouteRefusal("manifest-invalid", str(error)) from None
    if loaded.problems:
        raise RouteRefusal("manifest-invalid", "; ".join(loaded.problems))
    return loaded


def route_version(root: pathlib.Path) -> str:
    """SHA-256 over the catalog and policy stores' paths and bytes, cut to twelve hex digits."""
    return data(root).version


def validation_problems(root: pathlib.Path) -> list[str]:
    """Every problem the stores carry, structural and economic alike."""
    return structural_problems(root) + pool_problems(root)


def pool_problems(root: pathlib.Path) -> list[str]:
    """Routes that spend a pool's allowance on a model it does not serve.

    Kept apart from structural validity because it is a property of one route
    rather than of the data: a violation in some other profile must not
    block resolving an unrelated one, and it is the only class of problem a
    caller may deliberately override.
    """
    return loaded_pool_problems(data(root))


def loaded_pool_problems(loaded: stores.Data) -> list[str]:
    """Pool checks on an in-memory candidate, without reading working files."""
    profiles = loaded.profiles
    by_pool = {pool["provider"]: pool for pool in loaded.pools}
    problems: list[str] = []
    for profile in profiles:
        for route in [profile, *profile.get("variant", [])]:
            label = profile["id"] if route is profile else f"{profile['id']}:{route.get('id')}"
            refusal = pool_refusal(by_pool, label, route.get("provider"), route.get("model"))
            if refusal:
                problems.append(refusal.message)
    return problems


def pools(root: pathlib.Path) -> dict[str, dict]:
    return {pool["provider"]: pool for pool in data(root).pools}


def backends(root: pathlib.Path) -> dict[str, dict]:
    return {backend["id"]: backend for backend in data(root).backends}


def _effort_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(effort, str) and effort in EFFORT_ORDER for effort in value)
        and len(value) == len(set(value))
    )


def backend_effort_problems(backend_records: list[dict], models: list[dict]) -> list[str]:
    model_ids = {model["id"] for model in models}
    problems = []
    for backend in backend_records:
        label = f"backend {backend['id']!r}"
        if not _effort_list(backend.get("supported_efforts")):
            problems.append(f"{label}: supported_efforts must be a list of distinct known efforts")
        overrides = backend.get("model_efforts", {})
        if not isinstance(overrides, dict):
            problems.append(f"{label}: model_efforts must be a table of canonical model effort lists")
            continue
        for model_id, efforts in overrides.items():
            if model_id not in model_ids:
                problems.append(f"{label}: model_efforts names unknown canonical model {model_id!r}")
            if not _effort_list(efforts):
                problems.append(f"{label}: model_efforts for {model_id!r} must be a list of distinct known efforts")
    return problems


def backend_effort_refusal(backend: dict, profile: str, model: str, effort: str) -> RouteRefusal | None:
    """A model-specific declaration replaces the backend's common effort set."""
    supported = backend.get("model_efforts", {}).get(model, backend.get("supported_efforts", []))
    if effort in supported:
        return None
    return RouteRefusal(
        "unsupported-effort",
        f"{profile}: unsupported effort {effort!r} for model {model!r} on backend {backend['id']!r}; "
        f"supported efforts: {', '.join(supported) or 'none'}",
        profile=profile,
        backend=backend["id"],
        model=model,
        effort=effort,
        missing_fact=f"backend effort support for {model!r} at {effort!r} on {backend['id']!r}",
    )


def model_effort_facts(root: pathlib.Path, requested_model: str, effort: str | None = None) -> dict:
    """Return the roster facts used by both ``check`` and selection validation.

    Backend-facing aliases and the roster's own ``aliases`` map to canonical
    IDs before prohibition evaluation.
    Keeping the lookup and the prohibition predicate here gives direct
    validation the same fence without making it a subprocess copy of
    ``bin/routing-check``.
    """
    models = data(root).models
    profiles = data(root).profiles
    aliases = {
        route["backend_model"]: route["model"]
        for profile in profiles
        for route in [profile, *profile.get("variant", [])]
        if route.get("backend_model") and route.get("model")
    }
    model_id = aliases.get(requested_model, requested_model)
    model = next(
        (entry for entry in models if model_id in (entry["id"], *entry.get("aliases", []))),
        None,
    )
    model_id = model["id"] if model else model_id
    known_efforts = [entry["effort"] for entry in model.get("effort", [])] if model else []
    tier = next((entry for entry in model.get("effort", []) if entry.get("effort") == effort), None) if model else None
    return {
        "requested_model": requested_model,
        "model_id": model_id,
        "model": model,
        "known_efforts": known_efforts,
        "tier": tier,
        "prohibited_efforts": prohibited_efforts(model, effort) if model else [],
    }


def prohibited_efforts(model: dict | None, effort: str | None = None) -> list[str]:
    """Return prohibited effort names using the canonical ``check`` predicate."""
    if not model:
        return []
    return [
        entry["effort"]
        for entry in model.get("effort", [])
        if entry.get("prohibited") is True
        and (effort is None or entry["effort"] == effort)
    ]


def pool_refusal(by_pool, label, provider, model_id):
    pool = by_pool.get(provider)
    if not pool or model_id in pool.get("serves", []):
        return None
    plan = pool.get("plan", provider)
    alternative = pool.get("pays_for", "another subscription")
    return RouteRefusal(
        "pool",
        f"{label}: {plan} does not serve {model_id!r}; it is paid for by {alternative}",
        profile=label,
        provider=provider,
        model=model_id,
        plan=plan,
        alternative=alternative,
        override="--allow-cross-pool",
    )


def _seating_routes(profiles: list[dict], by_pool: dict[str, dict]):
    """Every ``(profile, route)`` that seats a tier, whatever profile it belongs to.

    Only a stable route seats a tier: an experimental or probationary route is
    a trial, not a seat a rank can order. A route whose pool does not serve its
    model is a pool violation, which ``pool_problems`` reports and a caller may
    override, so it seats nothing there.
    """
    for profile in profiles:
        for route in [profile, *profile.get("variant", [])]:
            if route.get("stability") != "stable" or not route.get("model") or not route.get("effort"):
                continue
            pool = by_pool.get(route.get("provider"))
            if pool is not None and route["model"] not in pool.get("serves", []):
                continue
            yield profile, route


def _seated_tiers(profiles: list[dict], by_pool: dict[str, dict]) -> dict[tuple[str, str], set[str]]:
    """Each ``(model, effort)`` a stable route seats, with the pools that seat it.

    A pool is named by its provider.
    """
    seated: dict[tuple[str, str], set[str]] = {}
    for _, route in _seating_routes(profiles, by_pool):
        seated.setdefault((route["model"], route["effort"]), set()).add(route.get("provider"))
    return seated


def _tier_rank(models: list[dict], model_id: str, effort: str, pool: str) -> int | None:
    model = next((entry for entry in models if entry.get("id") == model_id), None)
    tier = next((entry for entry in (model or {}).get("effort", []) if entry.get("effort") == effort), None)
    rank = (tier or {}).get("seat_rank", {})
    value = rank.get(pool) if isinstance(rank, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def rank_problems(models: list[dict], profiles: list[dict], by_pool: dict[str, dict]) -> list[str]:
    """Ranks are operator policy that orders seated tiers within one pool.

    A pool is the provider a route draws on, declared as a policy ``pool``
    or not: an undeclared provider is unconstrained, and a tier it seats is
    ranked under its name like any other. Every seated tier carries a rank for
    each pool that seats it and no other tier carries one; a rank never falls as effort rises within one model and
    pool, and never inverts two measured pass@1 scores in the same pool.
    """
    seated = _seated_tiers(profiles, by_pool)
    problems: list[str] = []
    ranked: dict[str, list[tuple[int, str, str, float | None]]] = {}
    for model in models:
        model_id = model.get("id")
        efforts_seen: set[str] = set()
        by_pool: dict[str, list[tuple[int, int, str]]] = {}
        for tier in model.get("effort", []):
            effort = tier.get("effort")
            label = f"model {model_id!r} effort {effort!r}"
            if effort in efforts_seen:
                problems.append(f"{label}: declared more than once")
            efforts_seen.add(effort)
            pools_seating = seated.get((model_id, effort), set())
            rank = tier.get("seat_rank")
            if rank is None:
                for pool in sorted(pools_seating):
                    problems.append(f"{label}: seated on pool {pool!r} without a seat_rank")
                continue
            if not isinstance(rank, dict):
                problems.append(f"{label}: seat_rank must map pools to positive integers")
                continue
            if not pools_seating:
                problems.append(f"{label}: seat_rank on a tier no stable route seats")
            for pool, value in sorted(rank.items()):
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    problems.append(f"{label}: seat_rank for pool {pool!r} must be a positive integer, not {value!r}")
                    continue
                if pool not in pools_seating:
                    problems.append(f"{label}: seat_rank for pool {pool!r}, which does not seat this tier")
                if effort in EFFORT_ORDER:
                    by_pool.setdefault(pool, []).append((EFFORT_ORDER.index(effort), value, effort))
                ranked.setdefault(pool, []).append((value, model_id, effort, tier.get("pass_at_1")))
            for pool in sorted(pools_seating - set(rank)):
                problems.append(f"{label}: seated on pool {pool!r} without a seat_rank")
        for pool, entries in by_pool.items():
            entries.sort()
            for (_, lower_rank, lower), (_, higher_rank, higher) in zip(entries, entries[1:]):
                if higher_rank < lower_rank:
                    problems.append(
                        f"model {model_id!r} pool {pool!r}: seat_rank falls from {lower} ({lower_rank}) to {higher} ({higher_rank})"
                    )
    for pool, entries in ranked.items():
        scored = [entry for entry in entries if isinstance(entry[3], (int, float)) and not isinstance(entry[3], bool)]
        for rank_a, model_a, effort_a, score_a in scored:
            for rank_b, model_b, effort_b, score_b in scored:
                if score_a > score_b and rank_a < rank_b:
                    problems.append(
                        f"pool {pool!r}: {model_a} {effort_a} scores {score_a} above {model_b} {effort_b} "
                        f"({score_b}) but holds the lower rank"
                    )
    return problems


def escalation_source_problems(profiles: list[dict]) -> list[str]:
    known = {profile.get("id") for profile in profiles}
    problems: list[str] = []
    for profile in profiles:
        sources = profile.get("escalation_sources", [])
        if not isinstance(sources, list) or not all(isinstance(source, str) for source in sources):
            problems.append(f"{profile.get('id')}: escalation_sources must be a list of profile ids")
            continue
        for source in sources:
            if source not in known:
                problems.append(f"{profile.get('id')}: escalation source {source!r} is not a profile")
            elif source == profile.get("id"):
                problems.append(f"{profile.get('id')}: escalation source {source!r} names the profile itself, which is always implied")
    return problems


def _nonblank_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _family_value(value: object) -> bool:
    """A family name as the roster must spell it: nonblank and unpadded.

    Every family comparison reads ``_family``, so a padded spelling that slips
    past lint still compares equal to its trimmed form rather than escaping the
    independence fence.
    """
    return _nonblank_string(value) and value == value.strip()


def _family(model: dict) -> str:
    return model["family"].strip()


def family_relation(root: pathlib.Path) -> dict[str, list[str]]:
    """Each lineage a catalog ``[[family]]`` row names, with every lineage of its family.

    The one family relation review independence reads: ``assess`` calls a
    reviewer and an author the same family, and ``resolve review`` excludes a
    seat for an author, exactly when the author's lineage is among the
    reviewer's family values. A lineage no row names is a family of its own.
    """
    return {value: row["values"] for row in data(root).families for value in row["values"]}


def family_exception_problems(models: list[dict], profiles: list[dict], relation: dict[str, list[str]],
                              rows: list[dict]) -> list[str]:
    """Why the policy's ``[[family_exception]]`` rows do not each declare one usable exception.

    A row names a catalog ``reviewer`` and a nonempty list of catalog
    ``authors`` of its family other than itself. A reviewer appears in one
    row and holds no seat on the ``review`` profile, so ``resolve review`` and
    ``assess`` never disagree about a seat.
    """
    by_id = {model["id"]: model for model in models if isinstance(model.get("id"), str)}
    review = next((profile for profile in profiles if profile.get("id") == "review"), {})
    review_models = {route.get("model") for route in [review, *review.get("variant", [])]} if review else set()
    seen: set[str] = set()
    problems: list[str] = []
    for row in rows:
        reviewer, authors = row.get("reviewer"), row.get("authors", [])
        where = f"{stores.POLICY} {stores.label('family_exception', row)}"
        if reviewer not in by_id:
            problems.append(f"{where}: reviewer is not a catalog model")
            continue
        if reviewer in seen:
            problems.append(f"{where}: reviewer is already named by another row")
        seen.add(reviewer)
        if reviewer in review_models:
            problems.append(f"{where}: reviewer holds a seat on the review profile")
        if not authors:
            problems.append(f"{where}: authors must name at least one catalog model")
        reviewer_values = _family_values(relation, by_id[reviewer])
        for author in authors:
            if author not in by_id:
                problems.append(f"{where}: {author!r} is not a catalog model")
            elif author == reviewer:
                problems.append(f"{where}: a reviewer cannot except its own model")
            elif _family(by_id[author]) not in reviewer_values:
                problems.append(f"{where}: {author!r} is not of the reviewer's family")
    return problems


def family_exceptions(root: pathlib.Path) -> dict[str, list[str]]:
    """Each excepted reviewer model with the same-family author models it may clear.

    The one reading of ``[[family_exception]]``: ``assess`` raises no
    ``same-family`` for exactly these pairs and lists the authors under
    ``family_exception``.
    """
    return {row["reviewer"]: list(row["authors"]) for row in data(root).policy.get("family_exception", [])}


def _family_values(relation: dict[str, list[str]], model: dict) -> list[str]:
    """Every lineage of ``model``'s family: its row's carried lineages, else its own alone."""
    return relation.get(_family(model), [_family(model)])


def clearance_floor(root: pathlib.Path) -> int:
    """The capability rank a read must reach to clear review debt."""
    review = data(root).policy.get("review", {})
    if type(review.get("clearance")) is not int or review["clearance"] < 1:
        raise RouteRefusal("manifest-invalid", "[review].clearance must be a positive integer capability rank")
    return review["clearance"]


def structural_problems(root: pathlib.Path) -> list[str]:
    """Every structural problem of the stores at `root`, computed once per loaded revision."""
    try:
        loaded = stores.load(root)
    except stores.StoreError as error:
        return [str(error)]
    if loaded.problems:
        return list(loaded.problems)
    if loaded.structural is None:
        loaded.structural = tuple(_structural_problems(root, loaded))
    return list(loaded.structural)


def _structural_problems(root: pathlib.Path, loaded: stores.Data) -> list[str]:
    problems = []
    profiles = loaded.profiles
    models = loaded.models
    by_model = {model["id"]: model for model in models}
    by_backend = {backend["id"]: backend for backend in loaded.backends}
    admission = loaded.policy["admission"]
    where = f"{stores.POLICY} [admission]"
    if admission["max_age_seconds"] <= 0:
        problems.append(f"{where}: max_age_seconds must be a positive integer")
    if not 0 <= admission["claude_minimum_remaining"] < 100:
        problems.append(f"{where}: claude_minimum_remaining must be a percentage below 100")
    known_families = {_family(model) for model in models}
    if not admission["codex_author_families"] or any(
            family not in known_families for family in admission["codex_author_families"]):
        problems.append(f"{where}: codex_author_families must name catalog lineages")
    for key in ("codex_review_backend", "other_review_backend"):
        if admission[key] not in by_backend:
            problems.append(f"{where}: {key} is not a catalog backend")
    delegation = {"pool": loaded.pools}
    usage_keys = [pool.get("usage_key") for pool in delegation.get("pool", []) if "usage_key" in pool]
    if (any(not isinstance(key, str) or key not in {"codex", "claude"} for key in usage_keys)
            or len(usage_keys) != len(set(key for key in usage_keys if isinstance(key, str)))):
        problems.append("pools: usage_key must name a distinct normalized account")
    for pool in delegation.get("pool", []):
        if "usage_key" not in pool:
            continue
        windows = pool.get("windows")
        if (not isinstance(windows, list) or not windows or len(windows) != len(set(map(str, windows)))
                or any(window not in ("five_hour", "seven_day") for window in windows)):
            problems.append(f"pools: {pool.get('provider')} must declare the windows its plan has "
                            "(five_hour, seven_day)")
    problems.extend(backend_effort_problems(loaded.backends, models))
    by_pool = {pool["provider"]: pool for pool in delegation.get("pool", [])}
    for provider, pool in by_pool.items():
        scarcer_than = pool.get("scarcer_than", [])
        if not isinstance(scarcer_than, list) or not all(
            isinstance(other, str) and other in by_pool and other != provider
            for other in scarcer_than
        ):
            problems.append(f"pool {provider!r}: scarcer_than must name other declared providers")
        elif any(provider in by_pool[other].get("scarcer_than", []) for other in scarcer_than):
            problems.append(f"pool {provider!r}: contradictory scarcity ordering")
    model_ids: set[str] = set()
    for model in models:
        if model.get("id") in model_ids:
            problems.append(f"duplicate model {model.get('id')!r}")
        model_ids.add(model.get("id"))
        if not _nonblank_string(model.get("family")):
            problems.append(f"model {model['id']!r}: family must be a nonblank string")
        elif not _family_value(model["family"]):
            problems.append(f"model {model['id']!r}: family {model['family']!r} has surrounding whitespace")
        status = model.get("status")
        if status is not None and status not in MODEL_STATUSES:
            problems.append(f"model {model['id']!r}: unknown status {status!r}")
        for tier in model.get("effort", []):
            tier_status = tier.get("status")
            if tier_status is not None and tier_status not in EFFORT_STATUSES:
                problems.append(f"model {model['id']!r} effort {tier.get('effort')!r}: unknown status {tier_status!r}")
    profile_ids: set[str] = set()
    for profile in profiles:
        profile_id = profile.get("id", "<missing>")
        if profile_id in profile_ids:
            problems.append(f"duplicate profile {profile_id!r}")
        profile_ids.add(profile_id)
        variants = profile.get("variant", [])
        variant_ids: set[str] = set()
        backend_defaults: dict[str, str] = {}
        declared_routes = ([profile] if profile.get("backends") else []) + variants
        if not declared_routes:
            problems.append(f"{stores.POLICY} [[profile]] id={profile_id}: no seats declared")
        elif not profile.get("backends") and not any(route.get("default_for_backend") for route in variants):
            problems.append(f"{stores.POLICY} [[profile]] id={profile_id}: no resolvable default seat")
        for route in declared_routes:
            variant_id = route.get("id", "<missing>")
            label = profile_id if route is profile else f"{profile_id}:{variant_id}"
            allowed = PROFILE_KEYS if route is profile else VARIANT_KEYS
            for key in sorted(set(route) - allowed):
                problems.append(f"{label}: unknown key {key!r}")
            if route is not profile:
                if variant_id in variant_ids:
                    problems.append(f"duplicate variant {label!r}")
                variant_ids.add(variant_id)
                default_for_backend = route.get("default_for_backend", False)
                if not isinstance(default_for_backend, bool):
                    problems.append(
                        f"{label}: default_for_backend must be true or false"
                    )
                elif default_for_backend:
                    for backend_id in route.get("backends", []):
                        # A default is reachable only where the primary route
                        # does not serve the backend itself. One that names a
                        # backend the primary already serves can never be
                        # selected, so it is refused rather than left to look
                        # effective.
                        if backend_id in profile.get("backends", []):
                            problems.append(
                                f"{label}: backend {backend_id!r} is served by {profile_id} itself, "
                                "so this default is unreachable"
                            )
                            continue
                        previous = backend_defaults.get(backend_id)
                        if previous:
                            problems.append(
                                f"{label}: backend {backend_id!r} already defaults to {previous}"
                            )
                        else:
                            backend_defaults[backend_id] = label
            stability = route.get("stability")
            if stability not in STABILITIES:
                problems.append(f"{label}: unknown stability {stability!r}")
            model_id = route.get("model")
            has_role_exception = "role_exception" in route
            role_exception = route.get("role_exception")
            valid_role_exception = (
                has_role_exception
                and route is not profile
                and isinstance(role_exception, str)
                and bool(role_exception.strip())
            )
            if has_role_exception and (
                not isinstance(role_exception, str) or not role_exception.strip()
            ):
                problems.append(f"{label}: role_exception must be a nonblank reason")
            model = by_model.get(model_id)
            if not model:
                problems.append(f"{label}: unknown model {model_id!r}")
            else:
                status = model.get("status")
                if status in UNROUTABLE_MODEL_STATUSES:
                    problems.append(f"{label}: model {model_id!r} is {status}")
                effort = route.get("effort")
                tier = next((entry for entry in model.get("effort", []) if entry.get("effort") == effort), None)
                if not tier:
                    problems.append(f"{label}: model {model_id!r} has no effort {effort!r}")
                elif tier.get("prohibited") is True:
                    problems.append(f"{label}: {model_id} {effort} is prohibited: {tier.get('reason')}")
                elif tier.get("status") == "explicit-only":
                    problems.append(f"{label}: {model_id} {effort} requires an explicit model request and cannot back a profile")
                model_status = model.get("status")
                tier_status = tier.get("status") if tier else None
                if model_status == "experimental" and stability != "experimental":
                    problems.append(f"{label}: experimental model {model_id!r} requires experimental stability")
                if tier_status == "probationary" and stability not in {"probationary", "experimental"}:
                    problems.append(f"{label}: probationary tier {model_id} {effort} cannot be marked {stability}")
                if tier_status == "experimental" and stability != "experimental":
                    problems.append(f"{label}: experimental tier {model_id} {effort} cannot be marked {stability}")
                if not valid_role_exception:
                    role_refusal = _model_role_refusal(profile_id, model_id, model)
                    if role_refusal:
                        problems.append(f"{label}: {role_refusal.message}")
            provider = route.get("provider")
            backends = route.get("backends", [])
            if not backends:
                problems.append(f"{label}: no backends declared")
            for backend_id in backends:
                backend = by_backend.get(backend_id)
                if not backend:
                    problems.append(f"{label}: unknown backend {backend_id!r}")
                    continue
                if backend.get("status") != "verified":
                    problems.append(f"{label}: backend {backend_id!r} is not verified")
                if provider not in backend.get("providers", []):
                    problems.append(f"{label}: provider {provider!r} is unsupported by backend {backend_id!r}")
                if (_effort_list(backend.get("supported_efforts"))
                        and isinstance(backend.get("model_efforts", {}), dict)
                        and all(_effort_list(value) for value in backend.get("model_efforts", {}).values())):
                    refusal = backend_effort_refusal(backend, label, model_id, route.get("effort"))
                    if refusal:
                        problems.append(refusal.message)
    problems.extend(rank_problems(models, profiles, {pool.get("provider"): pool for pool in delegation.get("pool", [])}))
    problems.extend(escalation_source_problems(profiles))
    from review_ladder import project_data, table_problems

    problems.extend(table_problems(project_data(loaded)))
    relation = {value: row["values"] for row in loaded.families for value in row["values"]}
    problems.extend(family_exception_problems(models, profiles, relation,
                                              loaded.policy.get("family_exception", [])))
    if loaded.policy["review"]["clearance"] < 1:
        problems.append(f"{stores.POLICY} [review]: clearance must be a positive integer capability rank")
    for profile in profiles:
        rules = profile.get("fallback", [])
        if not isinstance(rules, list):
            problems.append(f"{profile['id']}: fallback must be a list")
            continue
        for rule in rules:
            if not isinstance(rule, dict) or set(rule) - {"from_provider", "backend", "variant"}:
                problems.append(f"{profile['id']}: invalid fallback route keys")
                continue
            if (not isinstance(rule.get("from_provider"), str)
                    or rule["from_provider"] not in {pool.get("provider") for pool in delegation.get("pool", [])}):
                problems.append(f"{profile['id']}: unknown fallback source pool")
            target = (_baseline_route(profile, rule.get("backend")) if rule.get("variant") is None else
                      next((route for route in profile.get("variant", []) if route["id"] == rule["variant"]
                            and rule.get("backend") in route.get("backends", [])), None))
            if target is None or target.get("stability") != "stable":
                problems.append(f"{profile['id']}: fallback must name a stable route on its backend")
    return problems


def _profile_records(root: pathlib.Path):
    profiles = data(root).profiles
    for profile in profiles:
        yield profile, profile
        yield from ((profile, variant) for variant in profile.get("variant", []))


def _profile_backend_routes(root: pathlib.Path, backend: str) -> list[str]:
    return sorted(
        profile["id"] if route is profile else f"{profile['id']}:{route['id']}"
        for profile, route in _profile_records(root)
        if backend in route.get("backends", [])
    )


def _profile_for_selection(root: pathlib.Path, profile_id: str, backend: str) -> dict:
    if ":" in profile_id:
        raise RouteRefusal(
            "invalid-selection",
            f"operator-directed selection requires base profile {profile_id!r}, not a profile variant",
            profile=profile_id,
            backend=backend,
            missing_fact="base execution profile",
        )
    profiles = data(root).profiles
    profile = next((entry for entry in profiles if entry.get("id") == profile_id), None)
    if not profile:
        raise RouteRefusal(
            "unknown-profile",
            f"unknown profile {profile_id!r}",
            profile=profile_id,
            backend=backend,
        )
    profile_backends = sorted(
        {backend_id for route in [profile, *profile.get("variant", [])] for backend_id in route.get("backends", [])}
    )
    if backend not in profile_backends:
        backend_routes = _profile_backend_routes(root, backend)
        raise RouteRefusal(
            "unsupported-backend",
            f"profile {profile_id!r} does not support backend {backend!r}; "
            f"supported routes: {', '.join(backend_routes) or 'none'}",
            profile=profile_id,
            backend=backend,
            profile_backends=profile_backends,
            backend_routes=backend_routes,
        )
    return profile


def _backend_model_identity(root: pathlib.Path, backend: str, provider: str, model_id: str) -> str | None:
    """The model string `backend` is invoked with through `provider`, from the catalog's reach rows."""
    return stores.reach_name(data(root).catalog, model_id, backend, provider)


def _model_role_refusal(profile_id: str, model_id: str, model: dict) -> RouteRefusal | None:
    """An unroutable model, or a policy fence keeping the model off this profile."""
    status = model.get("status")
    if status in UNROUTABLE_MODEL_STATUSES:
        successor = model.get("successor")
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} is {status}" + (f"; its successor is {successor!r}" if successor else ""),
            profile=profile_id,
            model=model_id,
            model_status=status,
            successor=successor,
        )
    fence = model.get("fences", {}).get(profile_id)
    if fence:
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} cannot serve profile {profile_id!r}: {fence}",
            profile=profile_id,
            model=model_id,
            fence=fence,
        )
    return None


def _selection_pool_refusal(
    root: pathlib.Path,
    profile_id: str,
    backend: str,
    provider: str,
    model_id: str,
    allow_cross_pool: bool,
) -> RouteRefusal | None:
    by_pool = pools(root)
    pool = by_pool.get(provider)
    missing_fact = f"pool membership for provider {provider!r} and model {model_id!r}"
    if pool is None or "serves" not in pool:
        raise RouteRefusal(
            "unknown-pool-membership",
            f"no pool fact declares whether provider {provider!r} serves {model_id!r}; refusing to infer membership",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            missing_fact=missing_fact,
        )
    refusal = pool_refusal(by_pool, profile_id, provider, model_id)
    if refusal and not allow_cross_pool:
        raise refusal
    return refusal


def _baseline_route(profile: dict, backend: str) -> dict | None:
    """The route ``resolve`` would pick for ``backend`` without a variant."""
    if backend in profile.get("backends", []):
        return profile
    return next(
        (
            variant
            for variant in profile.get("variant", [])
            if variant.get("default_for_backend") is True and backend in variant.get("backends", [])
        ),
        None,
    )


def _classify_selection(
    root: pathlib.Path,
    profile: dict,
    backend: str,
    model_id: str,
    effort: str,
    provider: str,
) -> dict[str, object]:
    """Place a directed tuple relative to the profile's own route.

    ``direction`` compares policy ranks within the selection's pool: ``same``
    for the baseline itself, ``upgrade``, ``lateral`` or ``downgrade`` when
    both ends are ranked there, and ``unranked`` otherwise. A tuple is
    eligible when this profile, or a profile it names in
    ``escalation_sources``, seats it on a stable route. The selection is
    stable only against a stable baseline, and then when it is eligible and
    does not rank below the baseline, or when it is a stable variant of this
    profile on the requested backend and provider. A stable upgrade is an
    operator escalation; everything else stays operator-directed.
    """
    models = data(root).models
    profiles = data(root).profiles
    by_id = {entry.get("id"): entry for entry in profiles}
    selected = (model_id, effort, provider)

    baseline_route = _baseline_route(profile, backend)
    baseline = None
    direction = "unranked"
    if baseline_route is not None:
        baseline_tuple = (baseline_route["model"], baseline_route["effort"], baseline_route["provider"])
        baseline = f"{baseline_route['model']}#{baseline_route['effort']}"
        if selected == baseline_tuple:
            direction = "same"
        else:
            selected_rank = _tier_rank(models, model_id, effort, provider)
            baseline_rank = (
                _tier_rank(models, baseline_route["model"], baseline_route["effort"], provider)
                if baseline_route["provider"] == provider
                else None
            )
            if selected_rank is not None and baseline_rank is not None:
                direction = (
                    "upgrade"
                    if selected_rank > baseline_rank
                    else "lateral"
                    if selected_rank == baseline_rank
                    else "downgrade"
                )

    def seats(entry: dict) -> bool:
        return any(
            route.get("stability") == "stable"
            and (route.get("model"), route.get("effort"), route.get("provider")) == selected
            for route in [entry, *entry.get("variant", [])]
        )

    sources = [profile, *(by_id[source] for source in profile.get("escalation_sources", []) if source in by_id)]
    eligible = any(seats(entry) for entry in sources)
    named_variant = any(
        variant.get("stability") == "stable"
        and backend in variant.get("backends", [])
        and (variant.get("model"), variant.get("effort"), variant.get("provider")) == selected
        for variant in profile.get("variant", [])
    )
    stable = (
        baseline_route is not None
        and baseline_route.get("stability") == "stable"
        and ((eligible and direction in {"same", "upgrade", "lateral"}) or named_variant)
    )
    return {
        "baseline": baseline,
        "direction": direction,
        "stability": "stable" if stable else "experimental",
        "selection_kind": "operator-escalation" if stable and direction == "upgrade" else "operator-directed",
    }


def _route_seat_when(root: pathlib.Path, resolved_profile: str) -> str | None:
    """The `when` of the seat a resolved `profile[:variant]` names."""
    profile_id, _, variant = resolved_profile.partition(":")
    return next((seat["when"] for seat in data(root).policy.get("seat", [])
                 if seat["profile"] == profile_id and seat.get("variant") == (variant or None)), None)


def _selection_seat_when(root: pathlib.Path, profile: dict, backend: str, provider: str, model: str,
                         effort: str) -> str | None:
    """The `when` of the seat a directed selection is: the named profile's, then an escalation source's."""
    seats = data(root).policy.get("seat", [])
    for profile_id in [profile["id"], *profile.get("escalation_sources", [])]:
        for seat in seats:
            if (seat["profile"], seat["provider"], seat["model"], seat["effort"]) == (profile_id, provider, model,
                                                                                       effort) \
                    and backend in seat["backends"]:
                return seat["when"]
    return None


def caller_confirmation(root: pathlib.Path, route: dict, canonical_model: str,
                        caller: str | None, caller_provider: str | None = None, *,
                        benefit: str | None = None) -> dict | None:
    """Compare an observed caller seat with known pool-local ranks and scarcity."""
    if caller is None:
        if caller_provider is not None:
            raise RouteRefusal("invalid-caller", "--caller-provider requires --caller")
        return None
    coordinate = _assessed_coordinate(root, caller, "caller", effort_required=True)
    by_pool = pools(root)
    providers = [provider for provider, pool in by_pool.items()
                 if coordinate["model"] in pool.get("serves", [])]
    if caller_provider is None:
        if len(providers) != 1:
            raise RouteRefusal("invalid-caller", "name the observed caller pool with --caller-provider",
                               caller=caller, providers=providers)
        caller_provider = providers[0]
    if caller_provider not in providers:
        raise RouteRefusal("invalid-caller", "caller provider does not serve the observed model",
                           caller=caller, provider=caller_provider, providers=providers)
    provider = route["provider"]
    caller_rank = coordinate["tier"].get("seat_rank", {}).get(caller_provider)
    selected = model_effort_facts(root, canonical_model, route["effort"])["tier"]
    selected_rank = selected.get("seat_rank", {}).get(provider)
    comparison = "unranked"
    if provider == caller_provider and caller_rank is not None and selected_rank is not None:
        comparison = "above" if selected_rank > caller_rank else "below" if selected_rank < caller_rank else "same"
    pool_comparison = "unranked"
    if provider == caller_provider:
        pool_comparison = "same"
    elif caller_provider in by_pool.get(provider, {}).get("scarcer_than", []):
        pool_comparison = "scarcer"
    elif provider in by_pool[caller_provider].get("scarcer_than", []):
        pool_comparison = "less-scarce"
    reasons = []
    if comparison == "above":
        reasons.append("above-caller-seat")
    if pool_comparison == "scarcer":
        reasons.append("scarcer-pool")
    offer = True if reasons else False if comparison != "unranked" else None
    return {
        "schema": "agent-routing-confirmation/1",
        "advisory": True,
        "offer_to_user": offer,
        "reasons": reasons,
        "rank_comparison": comparison,
        "pool_comparison": pool_comparison,
        "caller": {"model": coordinate["model"], "effort": coordinate["effort"],
                   "provider": caller_provider, "rank": caller_rank},
        "selection": {"model": route["model"], "effort": route["effort"],
                      "provider": provider, "rank": selected_rank,
                      "pool": by_pool.get(provider, {}).get("plan")},
        "benefit": benefit,
    }


def validate_selection(
    root: pathlib.Path,
    profile_id: str,
    backend: str,
    model: str,
    effort: str,
    provider: str,
    reason: str,
    *,
    allow_experimental: bool = False,
    allow_cross_pool: bool = False,
    operator_named: bool = False,
    caller: str | None = None,
    caller_provider: str | None = None,
) -> dict[str, object]:
    """Validate an operator-directed tuple without resolving its profile.

    ``profile_id`` describes the execution shape only. No route or variant is
    selected from it, and a direct selection is never rostered. Every refusal
    runs first; then the tuple is classified against the route the profile
    would have chosen (see ``_classify_selection``), and only a selection that
    classification leaves experimental needs ``allow_experimental``.
    """
    allow_experimental = allow_experimental or operator_named
    fields = {
        "profile": profile_id,
        "backend": backend,
        "model": model,
        "effort": effort,
        "provider": provider,
        "reason": reason,
    }
    for name, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise RouteRefusal(
                "invalid-selection",
                f"operator-directed selection requires a nonblank {name}",
                field=name,
                missing_fact=name,
            )
    reason = reason.strip()

    problems = structural_problems(root)
    if problems:
        raise RouteRefusal(
            "manifest-invalid",
            "routing profiles are invalid: " + "; ".join(problems),
            profile=profile_id,
            backend=backend,
        )

    backend_facts = backends(root)
    backend_fact = backend_facts.get(backend)
    if backend_fact is None:
        raise RouteRefusal(
            "unknown-backend",
            f"unknown backend {backend!r}; the catalog has no backend fact for it",
            profile=profile_id,
            backend=backend,
            missing_fact=f"backend declaration for {backend!r}",
        )
    if backend_fact.get("status") != "verified":
        raise RouteRefusal(
            "backend-unverified",
            f"backend {backend!r} is not verified for direct selection",
            profile=profile_id,
            backend=backend,
            provider=provider,
            missing_fact=f"verified backend fact for {backend!r}",
        )
    if provider not in backend_fact.get("providers", []):
        raise RouteRefusal(
            "unsupported-provider",
            f"provider {provider!r} is unsupported by backend {backend!r}",
            profile=profile_id,
            backend=backend,
            provider=provider,
            missing_fact=f"provider/backend support for {provider!r}/{backend!r}",
        )
    profile = _profile_for_selection(root, profile_id, backend)

    facts = model_effort_facts(root, model, effort)
    model_id = facts["model_id"]
    model_fact = facts["model"]
    if model_fact is None:
        raise RouteRefusal(
            "unknown-model",
            f"unknown model {model_id!r}; the catalog has no model fact for it; "
            "accepted routing ids: " + ", ".join(
                entry["id"] for entry in data(root).models
            ),
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            missing_fact=f"model declaration for {model_id!r}",
        )
    known_efforts = facts["known_efforts"]
    if effort not in known_efforts:
        raise RouteRefusal(
            "unknown-effort",
            f"unknown effort for {model_id}: {effort}",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            effort=effort,
            known_efforts=sorted(known_efforts),
            missing_fact=f"effort fact for {model_id!r} at {effort!r}",
        )
    if facts["prohibited_efforts"]:
        raise RouteRefusal(
            "prohibited",
            f"prohibited: {model_id} at {effort}",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            effort=effort,
            selection_kind="operator-directed",
        )
    role_refusal = _model_role_refusal(profile_id, model_id, model_fact)
    if role_refusal:
        role_refusal.fields.update({"backend": backend, "provider": provider})
        raise role_refusal

    # Establish the pool fact before consulting generic backend model syntax.
    # This prevents an unrostered provider from looking supported merely
    # because its adapter accepts a placeholder model string.
    pool_refusal_result = _selection_pool_refusal(
        root,
        profile_id,
        backend,
        provider,
        model_id,
        allow_cross_pool,
    )
    backend_model = _backend_model_identity(root, backend, provider, model_id)
    if backend_model is None:
        raise RouteRefusal(
            "unsupported-model",
            f"backend {backend!r} has no declared support for model {model_id!r}",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            missing_fact=f"backend model support for {model_id!r} on {backend!r}",
        )

    effort_refusal = backend_effort_refusal(backend_fact, profile_id, model_id, effort)
    if effort_refusal:
        raise effort_refusal

    classification = _classify_selection(root, profile, backend, model_id, effort, provider)
    stability = classification["stability"]
    selection_kind = classification["selection_kind"]
    if stability != "stable" and not allow_experimental:
        seated_efforts = [
            tier_effort for tier_effort in EFFORT_ORDER
            if tier_effort in known_efforts
            and not prohibited_efforts(model_fact, tier_effort)
            and backend_effort_refusal(backend_fact, profile_id, model_id, tier_effort) is None
            and _classify_selection(root, profile, backend, model_id, tier_effort, provider)["stability"] == "stable"
        ]
        raise RouteRefusal(
            "stability",
            f"operator-directed selection of {model_id!r} at {effort!r} is not a seated escalation of "
            f"{profile_id!r} on {backend!r}; seated efforts for {model_id!r} on "
            f"{profile_id!r}/{backend!r}/{provider!r}: {', '.join(seated_efforts) or 'none'}; "
            "pass --allow-experimental to opt in, or --operator-named when the operator named this exact tuple",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            effort=effort,
            stability=stability,
            selection_kind=selection_kind,
            direction=classification["direction"],
            override="--allow-experimental",
            seated_efforts=seated_efforts,
        )

    version = route_version(root)
    selection = {
        "backend": backend,
        "backend_model": backend_model,
        "base_profile": profile["id"],
        "canonical_model": model_id,
        "effort": effort,
        "model": model_id,
        "profile": profile["id"],
        "provider": provider,
        "reason": reason,
        "route_version": version,
        "rostered": False,
        "selection_kind": selection_kind,
        "stability": stability,
        "direction": classification["direction"],
        "baseline": classification["baseline"],
        "allow_experimental": allow_experimental,
        "allow_cross_pool": allow_cross_pool,
        "operator_named": operator_named,
    }
    if pool_refusal_result:
        selection["cross_pool"] = pool_refusal_result.fields["plan"]
    confirmation = caller_confirmation(
        root, selection, model_id, caller, caller_provider,
        benefit=_selection_seat_when(root, profile, backend, provider, model_id, effort))
    if confirmation is not None:
        selection["confirmation"] = confirmation
    return selection


def _floors(model: dict, effort_tier: dict | None) -> list[int | None]:
    """Each declared author floor, including every effort when none is named."""
    tiers = [effort_tier] if effort_tier is not None else model.get("effort", [])
    return [tier.get("floor") for tier in tiers]


def _review_author(
    root: pathlib.Path,
    author: str,
    profile: str,
    backend: str,
    *,
    allow_unknown_floor: bool = False,
) -> dict:
    model_id, separator, effort = author.partition("#")
    facts = model_effort_facts(root, model_id, effort if separator else None)
    model = facts["model"]
    reason = None
    floors: list[int | None] = []
    if not model:
        reason = "unknown-author"
    elif not _nonblank_string(model.get("family")):
        reason = "unknown-author-family"
    elif separator and facts["tier"] is None:
        reason = "unknown-author-effort"
    else:
        floors = _floors(model, facts["tier"] if separator else None)
        if not floors or None in floors:
            reason = "unknown-author-tier"
    if reason and not (allow_unknown_floor and reason == "unknown-author-tier"):
        raise RouteRefusal(
            "review-independence",
            f"cannot establish the family and review tier of author {author!r}; record Arc review debt",
            profile=profile,
            backend=backend,
            author=author,
            reason=reason,
            recommendation="record-debt",
        )
    return {
        "coordinate": facts["model_id"] + (f"#{effort}" if separator else ""),
        "family": _family(model),
        "tier": None if reason else max(floors),
    }


ASSESSMENT_SCHEMAS = {1: "agent-routing-assessment/1", 2: "agent-routing-assessment/2"}
ASSESSMENT_SCHEMA = ASSESSMENT_SCHEMAS[2]
REVIEW_PURPOSES = ("findings", "clearance")
INELIGIBLE_REVIEW_DEBT_KIND = "ineligible-review"


def model_identities(root: pathlib.Path, model_id: str) -> list[str]:
    """Every model string routing accepts for the roster model ``model_id``.

    The roster id, its ``aliases``, and the ``model`` and ``backend_model`` of
    each route that denotes it. A string is listed only when
    ``model_effort_facts`` resolves it back to the same model.
    """
    model = next((entry for entry in data(root).models
                  if entry["id"] == model_id), None)
    candidates = {model_id, *(model or {}).get("aliases", [])}
    for _, route in _profile_records(root):
        if route.get("model") in candidates:
            candidates.update(value for value in (route["model"], route.get("backend_model")) if value)
    return sorted(
        candidate for candidate in candidates
        if model_effort_facts(root, candidate)["model_id"] == model_id
    )


def _assessed_coordinate(root: pathlib.Path, coordinate: str, role: str, *, effort_required: bool) -> dict:
    """Resolve a ``model[#effort]`` coordinate against the roster or refuse."""
    model_id, separator, effort = coordinate.partition("#")
    facts = model_effort_facts(root, model_id, effort if separator else None)
    model = facts["model"]
    problem = None
    if not model:
        problem = f"unknown {role} model {model_id!r}"
    elif not _nonblank_string(model.get("family")):
        problem = f"{role} model {facts['model_id']!r} has no family"
    elif effort_required and not separator:
        problem = f"{role} {coordinate!r} needs an effort: <model>#<effort>"
    elif separator and facts["tier"] is None:
        problem = f"{role} model {facts['model_id']!r} has no effort {effort!r}"
    if problem:
        raise RouteRefusal(
            "unknown-coordinate",
            problem,
            role=role,
            coordinate=coordinate,
        )
    return {
        "model": facts["model_id"],
        "effort": effort if separator else None,
        "family": _family(model),
        "family_values": _family_values(family_relation(root), model),
        "excepted_authors": family_exceptions(root).get(facts["model_id"], []),
        "identities": model_identities(root, facts["model_id"]),
        "tier": facts["tier"] if separator else None,
        "floors": _floors(model, facts["tier"] if separator else None),
        "rank": min(tier["rank"] for tier in ([facts["tier"]] if separator else model["effort"])),
        "seated": (facts["model_id"], effort) in _seated_tiers(
            data(root).profiles, pools(root)),
    }


def _author_rows(written: list[dict]) -> tuple[list[dict], int | None, bool]:
    """Each author with its floor, the highest known floor, and whether every floor is known."""
    rows = []
    for author in written:
        known = bool(author["floors"]) and None not in author["floors"]
        rows.append({
            "model": author["model"],
            "effort": author["effort"],
            "family": author["family"],
            "identities": author["identities"],
            "floor": max(author["floors"]) if known else None,
        })
    known_floors = [row["floor"] for row in rows if row["floor"] is not None]
    return rows, max(known_floors) if known_floors else None, len(known_floors) == len(rows)


def _assessment(
    reader: dict,
    written: list[dict],
    version: str,
    clearance: int | None,
    *,
    schema: int = 2,
    purpose: str = "clearance",
) -> dict[str, object]:
    """The assessment of a resolved reviewer against resolved authors.

    The one place eligibility is decided: ``assess_review`` and ``frontier_review``
    both read it, so no second independence rule can disagree with it.

    ``independence`` is eligible exactly when no qualifier but
    ``below-clearance`` or the informational ``reviewer-unseated`` holds.
    An author the reviewer's ``[[family_exception]]`` row names raises no
    ``same-family``; the assessment lists such authors under
    ``family_exception`` instead, outside the qualifiers, so a consumer that
    reads only the closed qualifier set sees a clearing read as clearing.
    Clearance ignores seating and requires family independence and both floors.
    ``findings`` asks only that the reviewer's tier reach each author's floor,
    rejecting its own model at a lower effort. Schema 1 carries the
    independence answer alone.
    """
    review_tier = reader["rank"]
    author_rows, floor, floors_known = _author_rows(written)

    qualifiers = []
    if any(author["model"] == reader["model"] for author in written):
        qualifiers.append("same-model")
    kin = [author for author in written if author["family"] in reader["family_values"]]
    excepted = sorted({author["model"] for author in kin if author["model"] in reader["excepted_authors"]})
    if any(author["model"] not in reader["excepted_authors"] for author in kin):
        qualifiers.append("same-family")
    if review_tier is not None and floor is not None and review_tier < floor:
        qualifiers.append("below-floor")
    if schema > 1 and review_tier is not None and review_tier < clearance:
        qualifiers.append("below-clearance")
    if not floors_known:
        qualifiers.append("floor-unknown")
    if not reader["seated"]:
        qualifiers.append("reviewer-unseated")
    independent = not [qualifier for qualifier in qualifiers if qualifier not in {"below-clearance", "reviewer-unseated"}]
    clears = not [q for q in qualifiers if q != "reviewer-unseated"]

    assessment = {
        "schema": ASSESSMENT_SCHEMAS[schema],
        "route_version": version,
        "reviewer": {
            "model": reader["model"],
            "effort": reader["effort"],
            "family": reader["family"],
            "identities": reader["identities"],
            "review_tier": review_tier,
        },
        "authors": author_rows,
        "floor": floor,
        "independence": "eligible" if independent else "ineligible",
        "qualifiers": qualifiers,
        "debt_kind": None if clears else INELIGIBLE_REVIEW_DEBT_KIND,
    }
    if excepted:
        assessment["family_exception"] = excepted
    if schema > 1:
        findings = review_tier is not None and floors_known and all(
            review_tier >= row["floor"] and not (
                row["model"] == reader["model"] and reader["effort"] is not None
                and row["effort"] is not None
                and reader["effort"] != row["effort"]
                and EFFORT_ORDER.index(reader["effort"]) < EFFORT_ORDER.index(row["effort"])
            )
            for row in author_rows
        )
        assessment.update(purpose=purpose, clearance=clearance,
                          findings="eligible" if findings else "ineligible", clears=clears)
    return assessment


def _purpose(purpose: str | None) -> str:
    if purpose is None:
        return "clearance"
    if purpose not in REVIEW_PURPOSES:
        raise RouteRefusal("invalid-purpose", f"purpose must be one of {', '.join(REVIEW_PURPOSES)}, not {purpose!r}")
    return purpose


def assess_review(
    root: pathlib.Path,
    reviewer: str,
    authors: list[str],
    *,
    purpose: str | None = None,
    schema: int = 2,
    as_of: str | None = None,
    accepted: str | None = None,
) -> dict[str, object]:
    """Assess one reviewer against the authors of the diff it read.

    Pure policy over the roster: any reviewer can be assessed, seated by a
    profile or not. The qualifiers are a closed set; the read clears exactly
    when no blocking qualifier holds. Both answers are given whatever the purpose; the purpose
    records which question the caller asked. Schema 1 answers independence
    alone, so it refuses a findings purpose.
    """
    if schema not in ASSESSMENT_SCHEMAS:
        raise RouteRefusal("invalid-schema", f"no assessment schema {schema!r}")
    if schema == 1 and purpose == "findings":
        raise RouteRefusal(
            "invalid-purpose",
            "--purpose findings needs schema 2: agent-routing-assessment/1 answers clearance only",
        )
    purpose = _purpose(purpose)
    if as_of is not None:
        return _assessment_at(root, reviewer, authors, as_of, purpose=purpose, schema=schema, accepted=accepted)
    if accepted is not None:
        raise RouteRefusal("invalid-accepted", "--accepted needs --as-of for a dated assessment")
    clearance = clearance_floor(root)
    if not authors:
        raise RouteRefusal("unknown-coordinate", "no author given", role="author")
    reader = _assessed_coordinate(root, reviewer, "reviewer", effort_required=False)
    written = [_assessed_coordinate(root, author, "author", effort_required=False) for author in authors]
    return _assessment(reader, written, route_version(root), clearance, schema=schema, purpose=purpose)


def _assessment_at(root: pathlib.Path, reviewer: str, authors: list[str], as_of: str, *,
                   purpose: str, schema: int, accepted: str | None = None) -> dict:
    from review_ladder import (EVIDENCE, evidence_at, is_stores, legacy_manifests, read_at, recorded, table_at,
                               table_problems)

    try:
        revision, texts = read_at(root, as_of, accepted)
        evidence = evidence_at(root, revision)
        models = table_at(root, texts)
        problems = table_problems(models)
        if problems:
            raise ValueError(f"version v-{revision}: {'; '.join(problems)}")
    except ValueError as error:
        raise RouteRefusal("historical-ladder", str(error)) from error
    if is_stores(texts):
        revision_data = recorded(texts)
        profiles, pool_rows, review = revision_data.profiles, revision_data.pools, revision_data.policy.get("review")
    else:
        manifest, profile_document, delegation = legacy_manifests(texts)
        profiles, pool_rows = profile_document.get("profile", []), delegation.get("pool", [])
        review = manifest.get("review", {"clearance": 2})
    seated = _seated_tiers(profiles, {row["provider"]: row for row in pool_rows})

    def coordinate(value: str, role: str) -> dict:
        name, separator, effort = value.partition("#")
        model = next((row for row in models if name in row["identities"]), None)
        tiers = [row for row in model["efforts"] if not separator or row["effort"] == effort] if model else []
        if not model or not tiers:
            raise RouteRefusal("unknown-coordinate", f"unknown {role} coordinate {value!r} at {as_of}",
                               role=role, coordinate=value)
        return {"model": model["model"], "effort": effort if separator else None,
                "family": model["family"], "family_values": [model["family"]], "excepted_authors": [],
                "identities": model["identities"], "rank": min(row["rank"] for row in tiers),
                "floors": [row["floor"] for row in tiers],
                "seated": (model["model"], effort) in seated}

    if not authors:
        raise RouteRefusal("unknown-coordinate", "no author given", role="author")
    if not isinstance(review, dict) or type(review.get("clearance")) is not int or review["clearance"] < 1:
        raise RouteRefusal("manifest-invalid", "[review].clearance must be a positive integer capability rank")
    digest = hashlib.sha256()
    for name, text in texts.items():
        digest.update(name.encode() + b"\0" + text.encode() + b"\0")
    digest.update(EVIDENCE.encode() + b"\0")
    digest.update(b"absent\0" if evidence is None else b"present\0" + evidence.encode())
    digest.update(dumps({"model": models}).encode())
    return _assessment(coordinate(reviewer, "reviewer"), [coordinate(author, "author") for author in authors],
                       digest.hexdigest()[:12], review["clearance"], schema=schema, purpose=purpose)


FRONTIER_SCHEMA = "agent-routing-frontier/1"


def frontier_review(root: pathlib.Path, author: str, reads: list[str] | tuple[str, ...] = ()) -> dict[str, object]:
    """The strongest eligible review seat for one author, and where reads stand against it.

    A seat is a stable, pool-valid route of the ``review`` profile on any
    backend, the kind ``resolve review`` can sell. A seat on another profile is
    not a review a caller can buy. It is eligible exactly when ``assess`` calls it independent, and seats are ordered
    by ``review_tier``, the cross-family scale ``assess`` compares, never by a
    pool-local rank. Quota and pool availability are not inputs: the answer
    moves only when the manifests do. An author whose floor is unestablished
    has no frontier, since every seat would be ``floor-unknown``.

    Each read carries its ``agent-routing-assessment/1`` under the same route version; its ``standing`` is
    ``below``, ``at`` or ``above`` the frontier's tier, or ``unranked`` when the
    read has no tier or there is no frontier.
    """
    version = route_version(root)
    written = _assessed_coordinate(root, author, "author", effort_required=False)
    rows, floor, floors_known = _author_rows([written])
    profiles = data(root).profiles

    seated: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for profile, route in _seating_routes(profiles, pools(root)):
        if profile["id"] != "review":
            continue
        seated.setdefault((route["model"], route["effort"]), set()).update(
            (backend, route["provider"]) for backend in route.get("backends", [])
        )
    eligible = []
    for (model, effort), places in seated.items():
        reader = _assessed_coordinate(root, f"{model}#{effort}", "reviewer", effort_required=True)
        assessment = _assessment(reader, [written], version, None, schema=1)
        if assessment["independence"] == "eligible":
            eligible.append((assessment["reviewer"]["review_tier"], model, effort, places))

    status, frontier = "floor-unknown", None
    if floors_known:
        status = "no-eligible-seat"
        if eligible:
            tier = max(entry[0] for entry in eligible)
            status, frontier = "frontier", {
                "review_tier": tier,
                "seats": sorted(
                    ({"model": model, "effort": effort, "backend": backend, "pool": pool}
                     for entry_tier, model, effort, places in eligible if entry_tier == tier
                     for backend, pool in places),
                    key=lambda seat: (seat["model"], seat["effort"], seat["backend"], seat["pool"]),
                ),
            }

    answered = []
    for read in reads:
        assessment = assess_review(root, read, [author], schema=1)
        tier = assessment["reviewer"]["review_tier"]
        if tier is None or frontier is None:
            standing = "unranked"
        else:
            standing = "below" if tier < frontier["review_tier"] else "at" if tier == frontier["review_tier"] else "above"
        answered.append({"standing": standing, "assessment": assessment})

    return {
        "schema": FRONTIER_SCHEMA,
        "route_version": version,
        "author": {**rows[0], "floor": floor},
        "status": status,
        "frontier": frontier,
        "reads": answered,
    }


def _review_constraints(root: pathlib.Path, selected: dict) -> dict:
    """A review route's family exclusions and tier: its reviewer's family values, by the family relation."""
    facts = model_effort_facts(root, selected["model"], selected["effort"])
    return {
        "excluded_author_families": _family_values(family_relation(root), facts["model"]),
        "reviewer_tier": facts["tier"]["rank"],
    }


def _lower_same_model(reviewer: str, author: str) -> bool:
    model, _, effort = reviewer.partition("#")
    author_model, separator, author_effort = author.partition("#")
    return (model == author_model and bool(separator) and effort != author_effort
            and EFFORT_ORDER.index(effort) < EFFORT_ORDER.index(author_effort))


def _seat_answers(author: dict, constraints: dict, clearance: int, reviewer: str) -> dict[str, bool]:
    """A review seat's answers for one author, by the route's family exclusions.

    Independent: outside the author's excluded families and at or above the
    author's tier. Clears: independent and at or above the clearance floor.
    Findings: at or above the author's tier, except the same model at a
    lower effort.
    """
    tier, floor = constraints["reviewer_tier"], author["tier"]
    excluded = author["family"] in constraints["excluded_author_families"]
    reaches = floor is not None and tier >= floor
    independent = reaches and not excluded
    return {
        "independent": independent,
        "findings": reaches and not _lower_same_model(reviewer, author["coordinate"]),
        "clears": independent and tier >= clearance,
        "excluded": excluded,
    }


def resolve(
    root: pathlib.Path,
    profile_id: str,
    backend: str,
    *,
    variant_id: str | None = None,
    allow_experimental: bool = False,
    allow_cross_pool: bool = False,
    author: str | None = None,
    purpose: str | None = None,
    accept_ineligible: bool = False,
    caller: str | None = None,
    caller_provider: str | None = None,
    usage: dict | None = None,
    now: int | None = None,
) -> dict[str, object]:
    # Structural validity is a property of the manifest and gates every
    # resolution. A pool violation is a property of one route, so it is judged
    # against the route actually selected rather than blocking an unrelated
    # one somewhere else in the file.
    problems = structural_problems(root)
    if problems:
        raise RouteRefusal(
            "manifest-invalid",
            "routing profiles are invalid: " + "; ".join(problems),
            profile=profile_id,
            backend=backend,
        )

    profiles = data(root).profiles
    profile = next((entry for entry in profiles if entry["id"] == profile_id), None)
    if not profile:
        raise RouteRefusal(
            "unknown-profile",
            f"unknown profile {profile_id!r}",
            profile=profile_id,
            backend=backend,
        )
    if author is not None and profile_id != "review":
        raise RouteRefusal(
            "invalid-author",
            "--author is only valid when resolving review",
            profile=profile_id,
            backend=backend,
        )
    if purpose is not None and (profile_id != "review" or author is None):
        raise RouteRefusal(
            "invalid-purpose",
            "--purpose needs review and the diff --author to judge against",
            profile=profile_id,
            backend=backend,
        )
    if purpose is not None and purpose not in REVIEW_PURPOSES:
        raise RouteRefusal(
            "invalid-purpose",
            f"purpose must be one of {', '.join(REVIEW_PURPOSES)}, not {purpose!r}",
            profile=profile_id,
            backend=backend,
        )
    if accept_ineligible and author is None:
        raise RouteRefusal(
            "invalid-author",
            "--accept-ineligible needs the diff --author to assess against",
            profile=profile_id,
            backend=backend,
        )
    selected = profile
    resolved_profile = profile_id
    if variant_id:
        selected = next((entry for entry in profile.get("variant", []) if entry["id"] == variant_id), None)
        if not selected:
            raise RouteRefusal(
                "unknown-variant",
                f"profile {profile_id!r} has no variant {variant_id!r}",
                profile=profile_id,
                variant=variant_id,
                backend=backend,
            )
        resolved_profile = f"{profile_id}:{variant_id}"
    elif backend not in profile.get("backends", []):
        # The primary route wins wherever it serves the backend; a backend
        # default answers only for a backend the primary excludes. The lint
        # refuses a default that names a backend the primary already serves,
        # so this precedence cannot silently shadow one.
        backend_default = next(
            (
                entry
                for entry in profile.get("variant", [])
                if entry.get("default_for_backend") is True
                and backend in entry.get("backends", [])
            ),
            None,
        )
        if backend_default is not None:
            selected = backend_default
            resolved_profile = f"{profile_id}:{selected['id']}"
    if backend not in selected.get("backends", []):
        requested_routes = [selected] if variant_id else [profile, *profile.get("variant", [])]
        profile_backends = sorted(
            {backend_id for route in requested_routes for backend_id in route.get("backends", [])}
        )
        backend_routes = sorted(
            profile_entry["id"]
            if route is profile_entry
            else f"{profile_entry['id']}:{route['id']}"
            for profile_entry in profiles
            for route in [profile_entry, *profile_entry.get("variant", [])]
            if backend in route.get("backends", [])
        )
        raise RouteRefusal(
            "unsupported-backend",
            f"profile {resolved_profile!r} does not support backend {backend!r}; "
            f"supported routes: {', '.join(backend_routes) or 'none'}",
            profile=resolved_profile,
            backend=backend,
            profile_backends=profile_backends,
            backend_routes=backend_routes,
        )
    review = None
    if profile_id == "review":
        constraints = _review_constraints(root, selected)
        review = {"author": None, "independence": "unverified", **constraints}
        if author is not None:
            purpose = _purpose(purpose)
            clearance = clearance_floor(root)
            author_facts = _review_author(
                root, author, resolved_profile, backend, allow_unknown_floor=accept_ineligible
            )
            candidates = [selected] if variant_id else [selected, *(
                route for route in [profile, *profile.get("variant", [])] if route is not selected
            )]
            eligible = None
            seats = []
            for candidate in candidates:
                if backend not in candidate.get("backends", []) or candidate["stability"] != "stable":
                    continue
                constraints = _review_constraints(root, candidate)
                if pool_refusal(pools(root), profile_id, candidate["provider"], candidate["model"]) and not allow_cross_pool:
                    continue
                seats.append(candidate)
                answers = _seat_answers(author_facts, constraints, clearance, f"{candidate["model"]}#{candidate["effort"]}")
                # An excluded-family seat is never a fallback: a findings read
                # from the author's own family comes only from the route the
                # caller resolved, so a cost-gated variant is reached by name.
                if answers["clears"] if purpose == "clearance" else (
                        answers["findings"] and (candidate is selected or not answers["excluded"])):
                    eligible = candidate
                    break
            accepted = False
            if eligible is None and accept_ineligible and seats:
                # The strongest seat by review tier; max keeps the first of
                # equals, which is the profile's own order of preference.
                eligible = max(seats, key=lambda seat: _review_constraints(root, seat)["reviewer_tier"])
                constraints = _review_constraints(root, eligible)
                accepted = True
            if eligible is None:
                raise RouteRefusal(
                    "review-independence",
                    (f"no independent stable review route at or above author {author!r} "
                     f"and at or above clearance floor {clearance}"
                     if purpose == "clearance" else
                     f"no stable review route for findings at or above author {author!r}")
                    + f" on backend {backend!r}; record Arc review debt",
                    profile=resolved_profile,
                    backend=backend,
                    author=author_facts["coordinate"],
                    author_family=author_facts["family"],
                    author_tier=author_facts["tier"],
                    purpose=purpose,
                    clearance=clearance,
                    recommendation="record-debt",
                    reason="no-eligible-route",
                )
            selected = eligible
            resolved_profile = profile_id if selected is profile else f"{profile_id}:{selected['id']}"
            assessment = assess_review(
                root, f"{selected['model']}#{selected['effort']}", [author_facts["coordinate"]], purpose=purpose
            )
            answers = _seat_answers(author_facts, constraints, clearance, f"{selected["model"]}#{selected["effort"]}")
            review = {
                "author": author_facts["coordinate"],
                "author_tier": author_facts["tier"],
                "purpose": purpose,
                "independence": "eligible" if answers["independent"] else "ineligible",
                "findings": "eligible" if answers["findings"] else "ineligible",
                "clears": answers["clears"],
                "qualifiers": assessment["qualifiers"],
                **constraints,
            }
            if accepted:
                review.update(recommendation="record-debt", debt_kind=INELIGIBLE_REVIEW_DEBT_KIND)
    stability = selected["stability"]
    if stability != "stable" and not allow_experimental:
        raise RouteRefusal(
            "stability",
            f"profile {resolved_profile!r} is {stability}; pass --allow-experimental to opt in",
            profile=resolved_profile,
            backend=backend,
            stability=stability,
            override="--allow-experimental",
        )
    effort_refusal = backend_effort_refusal(
        backends(root)[backend], resolved_profile, selected["model"], selected["effort"]
    )
    if effort_refusal:
        raise effort_refusal
    provider = selected["provider"]
    model = selected.get("backend_model", selected["model"])
    refusal = pool_refusal(pools(root), resolved_profile, provider, selected["model"])
    if refusal and not allow_cross_pool:
        raise refusal
    route = {
        "provider": provider,
        "model": model,
        "effort": selected["effort"],
        "stability": stability,
        "profile": resolved_profile,
        "backend": backend,
        "route_version": route_version(root),
    }
    if refusal:
        # A deliberate crossing is recorded, not merely permitted: whoever
        # reads a spent allowance later is looking for exactly this.
        route["cross_pool"] = refusal.fields["plan"]
    if "role_exception" in selected:
        route["role_exception"] = selected["role_exception"]
    if review is not None:
        route["review"] = review
    confirmation = caller_confirmation(root, route, selected["model"], caller, caller_provider,
                                       benefit=_route_seat_when(root, resolved_profile))
    if confirmation is not None:
        route["confirmation"] = confirmation
    if usage is not None:
        from quota_routing import admit_route

        route = admit_route(root, profile, route, usage, now=now,
                            pinned=variant_id is not None, author=author, purpose=purpose,
                            accept_ineligible=accept_ineligible, caller=caller,
                            caller_provider=caller_provider)
    return route


def dumps(route: dict[str, object]) -> str:
    return json.dumps(route, sort_keys=True, separators=(",", ":"))


def seats_view(root: pathlib.Path) -> dict[str, object]:
    """A read-only view of declared bindings, including explicitly labeled trials."""
    problems = validation_problems(root)
    if problems:
        raise RouteRefusal("invalid-manifest", "; ".join(problems))
    version = route_version(root)
    seats = []
    for profile, route in _profile_records(root):
        for backend in route.get("backends", []):
            seats.append({
                "profile": profile["id"],
                "variant": None if route is profile else route["id"],
                "backend": backend,
                "provider": route["provider"],
                "model": route.get("backend_model", route["model"]),
                "roster_model": route["model"],
                "effort": route["effort"],
                "stability": route["stability"],
                "default": _baseline_route(profile, backend) is route,
                "route_version": version,
                "evidence_ref": None,
            })
    try:
        head = resolve(root, "plan", "claude")
        refusal = None
    except RouteRefusal as error:
        head = None
        refusal = error.payload()
    return {
        "schema": "agent-routing-seats/1",
        "route_version": version,
        "seats": seats,
        "head_default": head,
        "head_default_refusal": refusal,
        "actual_head": {"status": "unobserved"},
    }


def routes_view(root: pathlib.Path, *, backend: str | None = None,
                profile_id: str | None = None) -> dict[str, object]:
    """List the coordinates that resolve without opt-ins or quota observations."""
    view = seats_view(root)
    coordinates = {}
    for seat in view["seats"]:
        profile, variant, served_backend = (seat[key] for key in ("profile", "variant", "backend"))
        coordinates[profile, variant, served_backend] = seat["default"]
        unnamed = (profile, None, served_backend)
        coordinates[unnamed] = coordinates.get(unnamed, False) or seat["default"]
    routes = []
    for profile, variant, served_backend in sorted(coordinates, key=lambda key: (key[0], key[1] or "", key[2])):
        if backend is not None and backend != served_backend:
            continue
        if profile_id is not None and profile_id != profile:
            continue
        try:
            route = resolve(root, profile, served_backend, variant_id=variant)
        except RouteRefusal as error:
            if error.kind not in {"stability", "unsupported-backend", "pool"}:
                raise
            continue
        routes.append({
            "profile": profile, "variant": variant, "backend": served_backend,
            **{key: route[key] for key in ("provider", "model", "effort", "stability")},
            "default": coordinates[profile, variant, served_backend],
        })
    prohibited = []
    for model in data(root).models:
        banned = prohibited_efforts(model)
        for tier in model.get("effort", []):
            if tier["effort"] in banned:
                prohibited.append({"model": model["id"], "effort": tier["effort"], "reason": tier["reason"]})
    return {
        "schema": "agent-routing-routes/1",
        "route_version": view["route_version"],
        "routes": routes,
        "prohibited": sorted(prohibited, key=lambda row: (row["model"], row["effort"])),
    }


def relation_problems(loaded: stores.Data) -> list[str]:
    """Rank order along effort, family cache-write ratios and credit rates."""
    problems = []
    family_of = {value: row for row in loaded.catalog.get("family", [])
                 for value in [row.get("id"), *row.get("lineages", [])]}
    for model in loaded.models:
        model_id = model["id"]
        ranks = sorted((EFFORT_ORDER.index(tier["effort"]), tier["effort"], tier["rank"])
                       for tier in model.get("effort", []) if tier.get("effort") in EFFORT_ORDER)
        for (_, lower, lower_rank), (_, higher, higher_rank) in zip(ranks, ranks[1:]):
            if higher_rank < lower_rank:
                problems.append(f"{stores.CATALOG} [[tier]] model={model_id}: rank falls from {lower} "
                                f"({lower_rank}) to {higher} ({higher_rank})")
        family = family_of.get(model["family"], {})
        prices = model.get("api_price_per_million", {})
        for key, ratio_key in (("cache_write", "cache_write_ratio"), ("cache_write_1h", "cache_write_1h_ratio")):
            ratio = family.get(ratio_key)
            if ratio is not None and "input" in prices and not math.isclose(prices.get(key, math.nan),
                                                                             ratio * prices["input"]):
                problems.append(f"{stores.CATALOG} [[price]] model={model_id}: {key} must be {ratio:g} times "
                                f"input ({ratio * prices['input']:g}), not {prices.get(key)}")
        credits = model.get("subscription_credits_per_million", {})
        rate = family.get("credits_per_dollar")
        if credits and rate is None:
            problems.append(f"{stores.CATALOG} [[credit]] model={model_id}: its family declares no credits_per_dollar")
        for key, value in credits.items() if rate is not None else ():
            expected = rate * prices.get(key, math.nan)
            if not math.isclose(value, expected):
                problems.append(f"{stores.CATALOG} [[credit]] model={model_id}: {key} credits must be {rate:g} per "
                                f"API dollar ({expected:g}), not {value:g}")
    return problems


def data_problems(root: pathlib.Path) -> list[str]:
    """Every problem in the data set: shape, canonical form, notes, routes, pools, prices and relations."""
    from price_export import price_problems

    try:
        loaded = stores.load(root)
    except stores.StoreError as error:
        return [str(error)]
    problems = stores.canonical_problems(root) + stores.standing_problems(root, loaded)
    if loaded.problems:
        return problems + list(loaded.problems)
    structural = structural_problems(root)
    if structural:
        return problems + structural
    return (problems + pool_problems(root) + price_problems(loaded.models) + relation_problems(loaded))
