"""Validation and deterministic resolution for named delegation routes."""

from __future__ import annotations

import hashlib
import json
import pathlib
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

    def __init__(self, kind: str, message: str, **fields: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.fields = {key: value for key, value in fields.items() if value is not None}

    def payload(self) -> dict[str, str]:
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
        raise RouteRefusal(
            "unsupported-backend",
            f"profile {resolved_profile!r} does not support backend {backend!r}",
            profile=resolved_profile,
            backend=backend,
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
