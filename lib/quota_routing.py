"""Admission from caller-supplied account windows, without account access."""

from __future__ import annotations

import math
import pathlib
import time

from routing_profiles import RouteRefusal, _review_author, load_toml, pools, resolve, route_version, structural_problems


def admission_policy(root):
    policy = load_toml(root / "routing/profiles.toml").get("admission")
    if policy is None:
        raise RouteRefusal("manifest-invalid", "quota admission requires an admission policy")
    return policy


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


WINDOWS = ("five_hour", "seven_day")


def pool_window(root: pathlib.Path, provider: str, usage: dict, now: int) -> dict:
    """A pool's headroom from the windows its plan has.

    A window the pool declares must be reported, valid and current, or the
    pool is unmeasured. A window the plan does not have is not expected, but
    one that is reported anyway still counts, so an exhausted window always
    blocks.
    """
    pool = pools(root).get(provider, {})
    key = pool.get("usage_key")
    declared = pool.get("windows", ())
    observation = usage.get(key) if isinstance(usage, dict) and key else None
    unknown = {"state": "unknown", "provider": provider}
    if not isinstance(observation, dict) or observation.get("state") != "fresh":
        return unknown
    updated = observation.get("updated_at")
    policy = admission_policy(root)
    if not _number(updated) or not 0 <= now - updated <= policy["max_age_seconds"]:
        return unknown
    windows = {}
    for name in WINDOWS:
        window = observation.get(name)
        if window is None and name not in declared:
            continue
        if not isinstance(window, dict):
            return unknown
        used, remaining, reset = (window.get(field) for field in
                                  ("used_percentage", "remaining_percentage", "resets_at"))
        if (not all(_number(value) for value in (used, remaining, reset))
                or not 0 <= remaining <= 100 or not 0 <= used <= 100
                or used + remaining != 100 or reset <= now):
            return unknown
        windows[name] = {"remaining_percentage": remaining, "resets_at": reset}
    return {"state": "exhausted" if any(window["remaining_percentage"] == 0
                                         for window in windows.values()) else "available",
            "provider": provider, "observed_at": updated, "windows": windows}


def admit_route(root, profile, route, usage, *, now=None, pinned=False,
                author=None, purpose=None, accept_ineligible=False, caller=None, caller_provider=None):
    now = int(time.time()) if now is None else now
    quota = pool_window(root, route["provider"], usage, now)
    if quota["state"] == "available":
        return {**route, "quota": quota}
    if quota["state"] == "unknown":
        raise RouteRefusal("quota-unknown", "pool availability is unmeasured or stale; refresh the usage snapshot before dispatch",
                           profile=route["profile"], backend=route["backend"], provider=route["provider"], quota=quota)
    skipped = [{**route, "reason": "pool-exhausted", "quota": quota}]
    if not pinned:
        for rule in profile.get("fallback", []):
            if rule["from_provider"] != route["provider"]:
                continue
            candidate = resolve(root, profile["id"], rule["backend"], variant_id=rule.get("variant"),
                                author=author, purpose=purpose, accept_ineligible=accept_ineligible,
                                caller=caller, caller_provider=caller_provider)
            alternative_quota = pool_window(root, candidate["provider"], usage, now)
            if alternative_quota["state"] == "available":
                return {**candidate, "rerouted_from": skipped[0], "quota": alternative_quota}
            skipped.append({**candidate, "reason": "pool-" + alternative_quota["state"], "quota": alternative_quota})
    raise RouteRefusal("pool-exhausted", "pool exhausted; no authorized measured fallback has room; wait for reset",
                       profile=route["profile"], backend=route["backend"], provider=route["provider"],
                       skipped_routes=skipped, pinned=pinned)


def admit_review(root: pathlib.Path, author: str, usage: dict, base: str, head: str, *, now=None) -> dict:
    """Select independent coverage or return an obligation, never a verdict."""
    if not all(isinstance(value, str) and value.strip() for value in (base, head)):
        raise RouteRefusal("invalid-range", "review admission requires an explicit nonblank base and head")
    problems = structural_problems(root)
    if problems:
        raise RouteRefusal("manifest-invalid", "; ".join(problems))
    now = int(time.time()) if now is None else now
    answer = {"schema": "agent-routing-review-admission/1", "route_version": route_version(root),
              "author": author, "range": {"base": base, "head": head}, "route": None}

    def debt(reason, quota=None):
        return {**answer, "status": "review-debt", "reason": reason,
                "recommendation": "record-debt", "debt_kind": "independent-review", "quota": quota}

    try:
        written = _review_author(root, author, "review", "claude")
    except RouteRefusal as refusal:
        return debt(refusal.fields.get("reason", refusal.kind))
    policy = admission_policy(root)["review"]
    codex_author = written["family"] in policy["codex_author_families"]
    backend = policy["codex_review_backend"] if codex_author else policy["other_review_backend"]
    try:
        route = resolve(root, "review", backend, author=author)
    except RouteRefusal as refusal:
        return debt(refusal.fields.get("reason", refusal.kind))
    quota = pool_window(root, route["provider"], usage, now)
    if quota["state"] != "available":
        return debt("pool-" + quota["state"], quota)
    if codex_author and quota["windows"]["five_hour"]["remaining_percentage"] <= policy["claude_minimum_remaining"]:
        return debt("claude-window-at-or-below-threshold", quota)
    return {**answer, "status": "route", "route": route, "quota": quota,
            "execution": {"access": "read-only", "persist_session": False,
                          "range": f"{base}..{head}", "model": route["model"], "effort": route["effort"]}}
