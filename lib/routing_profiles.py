"""Validation and deterministic resolution for named delegation routes."""

from __future__ import annotations

import hashlib
import json
import pathlib
import tomllib

STABILITIES = {"stable", "probationary", "experimental"}
UNROUTABLE_MODEL_STATUSES = {"deprecated", "inactive", "restricted", "retired", "superseded"}


def load_toml(path: pathlib.Path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


def route_version(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def validation_problems(root: pathlib.Path) -> list[str]:
    profiles_path = root / "routing" / "profiles.toml"
    profiles = load_toml(profiles_path).get("profile", [])
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    delegation = load_toml(root / "routing" / "delegation.toml")
    by_model = {model["id"]: model for model in models}
    by_backend = {backend["id"]: backend for backend in delegation.get("backend", [])}

    problems: list[str] = []
    profile_ids: set[str] = set()
    for profile in profiles:
        profile_id = profile.get("id", "<missing>")
        if profile_id in profile_ids:
            problems.append(f"duplicate profile {profile_id!r}")
        profile_ids.add(profile_id)
        variants = profile.get("variant", [])
        variant_ids: set[str] = set()
        for route in [profile, *variants]:
            variant_id = route.get("id", "<missing>")
            label = profile_id if route is profile else f"{profile_id}:{variant_id}"
            if route is not profile:
                if variant_id in variant_ids:
                    problems.append(f"duplicate variant {label!r}")
                variant_ids.add(variant_id)
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
) -> dict[str, str]:
    problems = validation_problems(root)
    if problems:
        raise ValueError("routing profiles are invalid: " + "; ".join(problems))

    profiles_path = root / "routing" / "profiles.toml"
    profiles = load_toml(profiles_path).get("profile", [])
    profile = next((entry for entry in profiles if entry["id"] == profile_id), None)
    if not profile:
        raise ValueError(f"unknown profile {profile_id!r}")
    selected = profile
    resolved_profile = profile_id
    if variant_id:
        selected = next((entry for entry in profile.get("variant", []) if entry["id"] == variant_id), None)
        if not selected:
            raise ValueError(f"profile {profile_id!r} has no variant {variant_id!r}")
        resolved_profile = f"{profile_id}:{variant_id}"
    if backend not in selected.get("backends", []):
        raise ValueError(f"profile {resolved_profile!r} does not support backend {backend!r}")
    stability = selected["stability"]
    if stability != "stable" and not allow_experimental:
        raise ValueError(
            f"profile {resolved_profile!r} is {stability}; pass --allow-experimental to opt in"
        )
    return {
        "provider": selected["provider"],
        "model": selected.get("backend_model", selected["model"]),
        "effort": selected["effort"],
        "stability": stability,
        "profile": resolved_profile,
        "backend": backend,
        "route_version": route_version(profiles_path),
    }


def dumps(route: dict[str, str]) -> str:
    return json.dumps(route, sort_keys=True, separators=(",", ":"))
