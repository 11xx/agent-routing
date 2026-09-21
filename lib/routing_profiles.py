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
    {"id", "purpose", "provider", "model", "backend_model", "effort", "stability", "backends", "variant"}
)
VARIANT_KEYS = frozenset(
    {"id", "provider", "model", "backend_model", "effort", "stability", "backends", "default_for_backend"}
)
UNROUTABLE_MODEL_STATUSES = {"deprecated", "inactive", "restricted", "retired", "superseded"}
MODEL_STATUSES = UNROUTABLE_MODEL_STATUSES | {"experimental"}
EFFORT_STATUSES = {"explicit-only", "experimental", "probationary"}

REFUSAL_SCHEMA = "agent-routing-refusal/1"


class RouteRefusal(ValueError):
    """A resolution the policy declines, carrying why as data.

    A caller that cannot classify a refusal works around it, and the
    work-around for an opaque failure is a hand-written invocation — which is
    the thing a resolver exists to prevent. The prose stays for a person; the
    payload is for the tool that has to decide what to do next.
    """

    def __init__(self, kind: str, message: str, **fields: str | list[str]) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.fields = {key: value for key, value in fields.items() if value is not None}

    def payload(self) -> dict[str, str | list[str]]:
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


def model_effort_facts(root: pathlib.Path, requested_model: str, effort: str | None = None) -> dict:
    """Return the roster facts used by both ``check`` and selection validation.

    Backend-facing aliases map to canonical IDs before prohibition evaluation.
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
    model = next((entry for entry in models if entry["id"] == model_id), None)
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


def structural_problems(root: pathlib.Path) -> list[str]:
    profiles_path = root / "routing" / "profiles.toml"
    profiles = load_toml(profiles_path).get("profile", [])
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    delegation = load_toml(root / "routing" / "delegation.toml")
    by_model = {model["id"]: model for model in models}
    by_backend = {backend["id"]: backend for backend in delegation.get("backend", [])}
    problems: list[str] = []
    for model in models:
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
    return candidates


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
    selected from it, and direct selections are always unrostered/experimental
    even when the same model appears on an automatic route.
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

    stability = "experimental"
    if not allow_experimental:
        raise RouteRefusal(
            "stability",
            f"operator-directed selection of {model_id!r} is unrostered/experimental; pass --allow-experimental to opt in",
            profile=profile_id,
            backend=backend,
            provider=provider,
            model=model_id,
            effort=effort,
            stability=stability,
            selection_kind="operator-directed",
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
        "selection_kind": "operator-directed",
        "stability": stability,
        "allow_experimental": allow_experimental,
        "allow_cross_pool": allow_cross_pool,
    }
    if pool_refusal_result:
        selection["cross_pool"] = pool_refusal_result.fields["plan"]
    return selection


def resolve(
    root: pathlib.Path,
    profile_id: str,
    backend: str,
    *,
    variant_id: str | None = None,
    allow_experimental: bool = False,
    allow_cross_pool: bool = False,
) -> dict[str, str]:
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
    return route


def dumps(route: dict[str, str]) -> str:
    return json.dumps(route, sort_keys=True, separators=(",", ":"))
