"""Validation and deterministic resolution for named delegation routes."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import tomllib

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
        "excluded_author_families",
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
        "excluded_author_families",
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


def load_toml(path: pathlib.Path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


def route_version(root: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for relative in ("routing/models.toml", "routing/profiles.toml", "routing/delegation.toml"):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def validation_problems(root: pathlib.Path) -> list[str]:
    """Every problem the manifests carry, structural and economic alike."""
    return structural_problems(root) + pool_problems(root)


def pool_problems(root: pathlib.Path) -> list[str]:
    """Routes that spend a pool's allowance on a model it does not serve.

    Kept apart from structural validity because it is a property of one route
    rather than of the manifest: a violation in some other profile must not
    block resolving an unrelated one, and it is the only class of problem a
    caller may deliberately override.
    """
    profiles = load_toml(root / "routing" / "profiles.toml").get("profile", [])
    by_pool = pools(root)
    problems: list[str] = []
    for profile in profiles:
        for route in [profile, *profile.get("variant", [])]:
            label = profile["id"] if route is profile else f"{profile['id']}:{route.get('id')}"
            refusal = pool_refusal(by_pool, label, route.get("provider"), route.get("model"))
            if refusal:
                problems.append(refusal.message)
    return problems


def pools(root: pathlib.Path) -> dict[str, dict]:
    delegation = load_toml(root / "routing" / "delegation.toml")
    return {pool["provider"]: pool for pool in delegation.get("pool", [])}


def backends(root: pathlib.Path) -> dict[str, dict]:
    delegation = load_toml(root / "routing" / "delegation.toml")
    return {backend["id"]: backend for backend in delegation.get("backend", [])}


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
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    profiles = load_toml(root / "routing" / "profiles.toml").get("profile", [])
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
        if str(entry.get("use", "")).startswith("prohibited")
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
    """Every route that seats a tier, whatever profile it belongs to.

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
            yield route


def _seated_tiers(profiles: list[dict], by_pool: dict[str, dict]) -> dict[tuple[str, str], set[str]]:
    """Each ``(model, effort)`` a stable route seats, with the pools that seat it.

    A pool is named by its provider.
    """
    seated: dict[tuple[str, str], set[str]] = {}
    for route in _seating_routes(profiles, by_pool):
        seated.setdefault((route["model"], route["effort"]), set()).add(route.get("provider"))
    return seated


def _tier_rank(models: list[dict], model_id: str, effort: str, pool: str) -> int | None:
    model = next((entry for entry in models if entry.get("id") == model_id), None)
    tier = next((entry for entry in (model or {}).get("effort", []) if entry.get("effort") == effort), None)
    rank = (tier or {}).get("rank", {})
    value = rank.get(pool) if isinstance(rank, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def rank_problems(models: list[dict], profiles: list[dict], by_pool: dict[str, dict]) -> list[str]:
    """Ranks are operator policy that orders seated tiers within one pool.

    A pool is the provider a route draws on, declared in ``delegation.toml``
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
            rank = tier.get("rank")
            if rank is None:
                for pool in sorted(pools_seating):
                    problems.append(f"{label}: seated on pool {pool!r} without a rank")
                continue
            if not isinstance(rank, dict):
                problems.append(f"{label}: rank must map pools to positive integers")
                continue
            if not pools_seating:
                problems.append(f"{label}: rank on a tier no stable route seats")
            for pool, value in sorted(rank.items()):
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    problems.append(f"{label}: rank for pool {pool!r} must be a positive integer, not {value!r}")
                    continue
                if pool not in pools_seating:
                    problems.append(f"{label}: rank for pool {pool!r}, which does not seat this tier")
                if effort in EFFORT_ORDER:
                    by_pool.setdefault(pool, []).append((EFFORT_ORDER.index(effort), value, effort))
                ranked.setdefault(pool, []).append((value, model_id, effort, tier.get("pass_at_1")))
            for pool in sorted(pools_seating - set(rank)):
                problems.append(f"{label}: seated on pool {pool!r} without a rank")
        for pool, entries in by_pool.items():
            entries.sort()
            for (_, lower_rank, lower), (_, higher_rank, higher) in zip(entries, entries[1:]):
                if higher_rank < lower_rank:
                    problems.append(
                        f"model {model_id!r} pool {pool!r}: rank falls from {lower} ({lower_rank}) to {higher} ({higher_rank})"
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


def review_policy_problems(models: list[dict], profiles: list[dict], by_pool: dict[str, dict]) -> list[str]:
    by_model = {model["id"]: model for model in models}
    families = {_family(model) for model in models if _nonblank_string(model.get("family"))}
    seated = _seated_tiers(profiles, by_pool)
    problems: list[str] = []
    for model in models:
        for tier in model.get("effort", []):
            label = f"model {model['id']!r} effort {tier['effort']!r}"
            for field in ("review_tier", "author_floor"):
                if field in tier and (type(tier[field]) is not int or tier[field] < 1):
                    problems.append(f"{label}: {field} must be a positive integer")
            if (model["id"], tier["effort"]) in seated:
                if "review_tier" not in tier:
                    problems.append(f"{label}: seated tier has no review_tier")
                if "author_floor" in tier:
                    problems.append(f"{label}: author_floor on a seated tier")
            elif "review_tier" in tier:
                problems.append(f"{label}: review_tier on a tier no stable route seats")
    for profile in profiles:
        for route in [profile, *profile.get("variant", [])]:
            label = profile["id"] if route is profile else f"{profile['id']}:{route['id']}"
            if profile["id"] != "review":
                if "excluded_author_families" in route:
                    problems.append(f"{label}: excluded_author_families is only valid for review")
                continue
            excluded = route.get("excluded_author_families", profile.get("excluded_author_families"))
            if not isinstance(excluded, list) or not excluded or not all(_nonblank_string(family) for family in excluded):
                problems.append(f"{label}: excluded_author_families must be a nonempty list of model families")
                continue
            excluded = [family.strip() for family in excluded]
            for family in route.get("excluded_author_families", profile.get("excluded_author_families")):
                if family != family.strip():
                    problems.append(f"{label}: excluded author family {family!r} has surrounding whitespace")
            for family in excluded:
                if family not in families:
                    problems.append(f"{label}: unknown excluded author family {family!r}")
            model = by_model.get(route.get("model"))
            if model is None:
                continue
            if not _nonblank_string(model.get("family")) or _family(model) not in excluded:
                problems.append(f"{label}: excluded_author_families must exclude the reviewer's family")
            tier = next((tier for tier in model.get("effort", []) if tier.get("effort") == route.get("effort")), {})
            if "review_tier" not in tier:
                problems.append(f"{label}: reviewer model/effort has no review_tier")
    return problems


def structural_problems(root: pathlib.Path) -> list[str]:
    profiles_path = root / "routing" / "profiles.toml"
    profiles = load_toml(profiles_path).get("profile", [])
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    delegation = load_toml(root / "routing" / "delegation.toml")
    by_model = {model["id"]: model for model in models}
    by_backend = {backend["id"]: backend for backend in delegation.get("backend", [])}
    problems: list[str] = []
    problems.extend(backend_effort_problems(delegation.get("backend", []), models))
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
        for route in [profile, *variants]:
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
                elif str(tier.get("use", "")).lower().startswith("prohibited"):
                    problems.append(f"{label}: {model_id} {effort} is prohibited: {tier['use']}")
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
    problems.extend(review_policy_problems(models, profiles, {pool.get("provider"): pool for pool in delegation.get("pool", [])}))
    return problems


def _profile_records(root: pathlib.Path):
    profiles = load_toml(root / "routing" / "profiles.toml").get("profile", [])
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
    profiles = load_toml(root / "routing" / "profiles.toml").get("profile", [])
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
        raise RouteRefusal(
            "unsupported-backend",
            f"profile {profile_id!r} does not support backend {backend!r}",
            profile=profile_id,
            backend=backend,
            profile_backends=profile_backends,
            backend_routes=_profile_backend_routes(root, backend),
        )
    return profile


def _model_forms(model_id: str, model: dict, requested_model: str) -> list[str]:
    forms: list[str] = []
    values = [model_id, requested_model, *model.get("aliases", [])]
    for value in values:
        for form in (value, value.replace(".", "-"), value.split("/")[-1]):
            if form and form not in forms:
                forms.append(form)
    return forms


def _routed_backend_model(
    root: pathlib.Path,
    model_id: str,
    requested_model: str,
    provider: str,
    backend: str,
) -> str | None:
    model = model_effort_facts(root, requested_model)["model"]
    forms = _model_forms(model_id, model, requested_model) if model else [model_id, requested_model]
    for profile, route in _profile_records(root):
        if route.get("provider") != provider or backend not in route.get("backends", []):
            continue
        if route.get("model") == model_id or route.get("backend_model") in forms:
            return route.get("backend_model", route.get("model"))
    return None


def _flag_model_candidates(flag: str) -> list[str]:
    candidates: list[str] = []
    for match in re.finditer(r"[A-Za-z0-9][A-Za-z0-9_./:-]*\{[^{}]+\}[A-Za-z0-9_./:-]*", flag):
        token = match.group(0)
        prefix, choices, suffix = re.fullmatch(r"(.*)\{([^{}]+)\}(.*)", token).groups()
        candidates.extend(prefix + choice + suffix for choice in choices.split(","))
    candidates.extend(re.findall(r"[A-Za-z0-9][A-Za-z0-9_./:-]+", flag))
    # A flag string is prose as well as syntax: an id that closes a sentence
    # carries the stop with it, and it is the id a caller must be handed.
    return [candidate.rstrip(".:") for candidate in candidates]


def _backend_model_identity(
    root: pathlib.Path,
    backend: str,
    provider: str,
    model_id: str,
    requested_model: str,
    model: dict,
) -> str | None:
    backend_fact = backends(root)[backend]
    forms = _model_forms(model_id, model, requested_model)
    routed = _routed_backend_model(root, model_id, requested_model, provider, backend)
    if routed:
        return routed

    flag = str(backend_fact.get("model_flag", ""))
    candidates = _flag_model_candidates(flag)
    for candidate in candidates:
        if any(form in candidate for form in forms):
            return candidate

    generic = re.search(r"([A-Za-z0-9_./:-]*)<model>([A-Za-z0-9_./:-]*)", flag)
    if generic and model_id in pools(root).get(provider, {}).get("serves", []):
        return f"{generic.group(1)}{model_id}{generic.group(2)}"
    return None


def _model_role_refusal(profile_id: str, model_id: str, model: dict) -> RouteRefusal | None:
    status = model.get("status")
    role = str(model.get("role", ""))
    lowered = role.lower()
    if status in UNROUTABLE_MODEL_STATUSES:
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} is {status}: {role}",
            profile=profile_id,
            model=model_id,
            model_status=status,
            role=role,
        )
    if "never select" in lowered or "never for anything that ships" in lowered:
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} is not selectable for this execution shape: {role}",
            profile=profile_id,
            model=model_id,
            role=role,
        )
    if profile_id == "plan" and "not a lead" in lowered:
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} cannot serve the lead profile {profile_id!r}",
            profile=profile_id,
            model=model_id,
            role=role,
        )
    if profile_id == "interactive" and "interactive default" in lowered and "not a lead" in lowered:
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} cannot serve the interactive profile",
            profile=profile_id,
            model=model_id,
            role=role,
        )
    if profile_id != "generate" and "generator" in lowered:
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} is generator-only and cannot serve profile {profile_id!r}",
            profile=profile_id,
            model=model_id,
            role=role,
        )
    if profile_id == "review" and (
        "never an adjudicator" in lowered or "never the reviewer of record" in lowered
    ):
        return RouteRefusal(
            "model-role",
            f"model {model_id!r} cannot be the reviewer of record for profile {profile_id!r}",
            profile=profile_id,
            model=model_id,
            role=role,
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
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    profiles = load_toml(root / "routing" / "profiles.toml").get("profile", [])
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
) -> dict[str, object]:
    """Validate an operator-directed tuple without resolving its profile.

    ``profile_id`` describes the execution shape only. No route or variant is
    selected from it, and a direct selection is never rostered. Every refusal
    runs first; then the tuple is classified against the route the profile
    would have chosen (see ``_classify_selection``), and only a selection that
    classification leaves experimental needs ``allow_experimental``.
    """
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
            f"unknown backend {backend!r}; delegation.toml has no backend fact for it",
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
            f"unknown model {model_id!r}; models.toml has no model fact for it",
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
    backend_model = _backend_model_identity(root, backend, provider, model_id, model, model_fact)
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
        raise RouteRefusal(
            "stability",
            f"operator-directed selection of {model_id!r} at {effort!r} is not a seated escalation of "
            f"{profile_id!r} on {backend!r}; pass --allow-experimental to opt in",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            effort=effort,
            stability=stability,
            selection_kind=selection_kind,
            direction=classification["direction"],
            override="--allow-experimental",
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
    }
    if pool_refusal_result:
        selection["cross_pool"] = pool_refusal_result.fields["plan"]
    return selection


def _floors(model: dict, effort_tier: dict | None) -> list[int | None]:
    """One floor per effort an author coordinate may stand for.

    A tier carries its floor as ``review_tier`` when seated or ``author_floor``
    when not. A coordinate without an effort stands for every declared tier;
    a tier with neither field contributes ``None`` and is never inferred.
    """
    tiers = [effort_tier] if effort_tier is not None else model.get("effort", [])
    return [tier.get("review_tier", tier.get("author_floor")) for tier in tiers]


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


ASSESSMENT_SCHEMA = "agent-routing-assessment/1"
INELIGIBLE_REVIEW_DEBT_KIND = "ineligible-review"


def model_identities(root: pathlib.Path, model_id: str) -> list[str]:
    """Every model string routing accepts for the roster model ``model_id``.

    The roster id, its ``aliases``, and the ``model`` and ``backend_model`` of
    each route that denotes it. A string is listed only when
    ``model_effort_facts`` resolves it back to the same model.
    """
    model = next((entry for entry in load_toml(root / "routing" / "models.toml").get("model", [])
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
        "identities": model_identities(root, facts["model_id"]),
        "tier": facts["tier"] if separator else None,
        "floors": _floors(model, facts["tier"] if separator else None),
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


def _assessment(reader: dict, written: list[dict], version: str) -> dict[str, object]:
    """The assessment of a resolved reviewer against resolved authors.

    The one place eligibility is decided: ``assess_review`` and ``frontier_review``
    both read it, so no second independence rule can disagree with it.
    """
    review_tier = (reader["tier"] or {}).get("review_tier")
    author_rows, floor, floors_known = _author_rows(written)

    qualifiers = []
    if any(author["model"] == reader["model"] for author in written):
        qualifiers.append("same-model")
    if any(author["family"] == reader["family"] for author in written):
        qualifiers.append("same-family")
    if review_tier is not None and floor is not None and review_tier < floor:
        qualifiers.append("below-floor")
    if not floors_known:
        qualifiers.append("floor-unknown")
    if review_tier is None:
        qualifiers.append("reviewer-unseated")

    return {
        "schema": ASSESSMENT_SCHEMA,
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
        "independence": "ineligible" if qualifiers else "eligible",
        "qualifiers": qualifiers,
        "debt_kind": INELIGIBLE_REVIEW_DEBT_KIND if qualifiers else None,
    }


def assess_review(root: pathlib.Path, reviewer: str, authors: list[str]) -> dict[str, object]:
    """Assess one reviewer against the authors of the diff it read.

    Pure policy over the roster: any reviewer can be assessed, seated by a
    profile or not. The qualifiers are a closed set and the read is eligible
    exactly when none holds.
    """
    if not authors:
        raise RouteRefusal("unknown-coordinate", "no author given", role="author")
    reader = _assessed_coordinate(root, reviewer, "reviewer", effort_required=True)
    written = [_assessed_coordinate(root, author, "author", effort_required=False) for author in authors]
    return _assessment(reader, written, route_version(root))


FRONTIER_SCHEMA = "agent-routing-frontier/1"


def frontier_review(root: pathlib.Path, author: str, reads: list[str] | tuple[str, ...] = ()) -> dict[str, object]:
    """The strongest eligible review seat for one author, and where reads stand against it.

    A seat is a stable route on any profile and backend (``_seating_routes``);
    it is eligible exactly when ``assess`` calls it so, and seats are ordered
    by ``review_tier``, the cross-family scale ``assess`` compares, never by a
    pool-local rank. Quota and pool availability are not inputs: the answer
    moves only when the manifests do. An author whose floor is unestablished
    has no frontier, since every seat would be ``floor-unknown``.

    Each read is assessed under the same route version; its ``standing`` is
    ``below``, ``at`` or ``above`` the frontier's tier, or ``unranked`` when the
    read has no tier or there is no frontier.
    """
    version = route_version(root)
    written = _assessed_coordinate(root, author, "author", effort_required=False)
    rows, floor, floors_known = _author_rows([written])
    profiles = load_toml(root / "routing" / "profiles.toml").get("profile", [])

    seated: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for route in _seating_routes(profiles, pools(root)):
        seated.setdefault((route["model"], route["effort"]), set()).update(
            (backend, route["provider"]) for backend in route.get("backends", [])
        )
    eligible = []
    for (model, effort), places in seated.items():
        reader = _assessed_coordinate(root, f"{model}#{effort}", "reviewer", effort_required=True)
        assessment = _assessment(reader, [written], version)
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
        assessment = assess_review(root, read, [author])
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


def _review_constraints(root: pathlib.Path, profile: dict, selected: dict) -> dict:
    tier = model_effort_facts(root, selected["model"], selected["effort"])["tier"]
    return {
        "excluded_author_families": [
            family.strip()
            for family in selected.get("excluded_author_families", profile["excluded_author_families"])
        ],
        "reviewer_tier": tier["review_tier"],
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
    accept_ineligible: bool = False,
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

    profiles_path = root / "routing" / "profiles.toml"
    profiles = load_toml(profiles_path).get("profile", [])
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
            f"profile {resolved_profile!r} does not support backend {backend!r}",
            profile=resolved_profile,
            backend=backend,
            profile_backends=profile_backends,
            backend_routes=backend_routes,
        )
    review = None
    if profile_id == "review":
        constraints = _review_constraints(root, profile, selected)
        review = {"author": None, "independence": "unverified", **constraints}
        if author is not None:
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
                constraints = _review_constraints(root, profile, candidate)
                if pool_refusal(pools(root), profile_id, candidate["provider"], candidate["model"]) and not allow_cross_pool:
                    continue
                seats.append(candidate)
                if author_facts["family"] in constraints["excluded_author_families"]:
                    continue
                if author_facts["tier"] is None or constraints["reviewer_tier"] < author_facts["tier"]:
                    continue
                eligible = candidate
                break
            assessment = None
            if eligible is None and accept_ineligible and seats:
                # The strongest seat by review tier; max keeps the first of
                # equals, which is the profile's own order of preference.
                eligible = max(seats, key=lambda seat: _review_constraints(root, profile, seat)["reviewer_tier"])
                constraints = _review_constraints(root, profile, eligible)
                assessment = assess_review(
                    root,
                    f"{eligible['model']}#{eligible['effort']}",
                    [author_facts["coordinate"]],
                )
            if eligible is None:
                raise RouteRefusal(
                    "review-independence",
                    f"no independent stable review route at or above author {author!r} on backend {backend!r}; "
                    "record Arc review debt",
                    profile=resolved_profile,
                    backend=backend,
                    author=author_facts["coordinate"],
                    author_family=author_facts["family"],
                    author_tier=author_facts["tier"],
                    recommendation="record-debt",
                    reason="no-eligible-route",
                )
            selected = eligible
            resolved_profile = profile_id if selected is profile else f"{profile_id}:{selected['id']}"
            review = {
                "author": author_facts["coordinate"],
                "author_tier": author_facts["tier"],
                "independence": "eligible",
                **constraints,
            }
            if assessment is not None:
                review.update(
                    independence=assessment["independence"],
                    qualifiers=assessment["qualifiers"],
                    recommendation="record-debt",
                    debt_kind=assessment["debt_kind"],
                )
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
    return route


def dumps(route: dict[str, object]) -> str:
    return json.dumps(route, sort_keys=True, separators=(",", ":"))
