"""Dated capability tables, independent of routing seats and prices."""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import subprocess
import tomllib

SCHEMA = "arc-review-ladder/1"
NUMERIC_START = "dc54196"
GAP_START = "2026-08-01T00:00:00Z"
EVIDENCE = "eras/2026-11-04-capability-ladder.md"
RETIRED = {"gpt-5.6-sol", "gpt-6-sol", "opus-5", "fable-5"}
RECORDED_IDENTITIES = {"opus-5": ["claude-opus-5"], "fable-5": ["claude-fable-5"],
                       "glm-5.3-flash": ["z-ai/glm-5.3-flash"]}
EFFORT_ORDER = ("default", "low", "medium", "high", "xhigh", "max", "ultra")


def instant(value: str) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value
    ):
        raise ValueError(f"expected an RFC 3339 instant, got {value!r}")
    try:
        return dt.datetime.fromisoformat(value.upper().replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError as error:
        raise ValueError(f"expected an RFC 3339 instant, got {value!r}") from error


def utc(value: str) -> str:
    return instant(value).isoformat().replace("+00:00", "Z")


def git(root: pathlib.Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"cannot read ladder history: {result.stderr.strip()}")
    return result.stdout


def historical_manifest(root: pathlib.Path, revision: str, name: str) -> dict:
    return tomllib.loads(git(root, "show", f"{revision}:routing/{name}.toml"))


def capability(model: str, effort: str) -> int:
    """The sourced reconstruction judgments for tiers without numeric capability."""
    if model == "gpt-6-astra":
        return 3 if effort in {"high", "xhigh", "max"} else 2
    if model in {"opus-5.5", "fable-5.1", "sonnet-5.5"}:
        return 3 if effort == "max" else 2 if effort in {"high", "xhigh"} else 1
    if model == "opus-5" and effort == "medium":
        return 2
    if model in {"opus-5", "fable-5", "gpt-5.6-sol", "gpt-6-sol", "gpt-6.1-sol", "gpt-5.5"}:
        return 2 if effort in {"high", "xhigh", "max", "ultra"} else 1
    if model == "gpt-6.1-terra":
        return 2
    if model == "gpt-5.6-terra":
        return 2 if effort == "max" else 1
    if model == "kimi-k3":
        return 2
    return 1


def canonical_efforts(model: dict) -> list[dict]:
    """Restore effort-less predecessor rows from their recorded era evidence."""
    tiers = model.get("effort", [])
    if tiers:
        return tiers
    names = {
        "fable-5": ("low", "medium", "high", "xhigh", "max"),
        "opus-4.8": ("high", "max"),
        "sonnet-5": ("low", "medium", "high", "xhigh", "max"),
        "gpt-5.5": ("low", "medium", "high", "xhigh", "max"),
        "kimi-k3": ("max",),
        "small-model-class": ("default",),
    }.get(model["id"])
    if names is None:
        raise ValueError(f"no recorded effort set for {model['id']!r}")
    return [{"effort": effort} for effort in names]


def legacy(manifest: dict) -> bool:
    return not any("floor" in tier or "seat_rank" in tier or type(tier.get("rank")) is int
                   for model in manifest.get("model", []) for tier in model.get("effort", []))


def project(manifest: dict, profiles: dict, *, historical: bool = False) -> list[dict]:
    relation = {value: row["id"] for row in manifest.get("family", [])
                for value in [row["id"], *row.get("aliases", [])]}
    models = []
    for model in manifest.get("model", []):
        model_id = model["id"]
        family = model.get("family")
        family = relation.get(family, family) if isinstance(family, str) else ""
        if family in {"gpt-5.6", "gpt-5.5"}:
            family = "openai"
        if family == "claude":
            family = "anthropic"
        identities = {model_id, *model.get("aliases", []), *RECORDED_IDENTITIES.get(model_id, [])}
        for profile in profiles.get("profile", []):
            for route in [profile, *profile.get("variant", [])]:
                if route.get("model") == model_id and route.get("backend_model"):
                    identities.add(route["backend_model"])
        efforts = []
        for tier in canonical_efforts(model) if historical else model.get("effort", []):
            effort = tier["effort"]
            if historical:
                # Legacy 4 expressed an unreachable seat, not measured capability.
                recorded = tier.get("review_tier", tier.get("author_floor"))
                rank = recorded if type(recorded) is int and recorded < 4 else capability(model_id, effort)
                floor = rank
            else:
                rank, floor = tier.get("rank"), tier.get("floor")
            efforts.append({"effort": effort, "rank": rank, "floor": floor})
        models.append({"model": model_id, "identities": sorted(identities), "family": family,
                       "superseded": model.get("superseded", model.get("status") in {"superseded", "retired"}),
                       "efforts": sorted(efforts, key=lambda row: row["effort"])})
    return sorted(models, key=lambda row: row["model"])


def table_problems(models: list[dict]) -> list[str]:
    problems = []
    identities = set()
    ids = set()
    ranks = []
    for model in models:
        label = model.get("model")
        if not isinstance(label, str) or not label.strip() or label in ids:
            problems.append(f"duplicate or empty model id {label!r}")
        ids.add(label)
        family = model.get("family")
        if not isinstance(family, str) or not family.strip():
            problems.append(f"{label}: family is empty")
        if type(model.get("superseded")) is not bool:
            problems.append(f"{label}: superseded must be boolean")
        names = model.get("identities", [])
        if not names or not all(isinstance(name, str) and name.strip() for name in names):
            problems.append(f"{label}: identities must be nonempty strings")
        for name in names:
            if name in identities:
                problems.append(f"{label}: duplicate identity {name!r}")
            identities.add(name)
        efforts = model.get("efforts", [])
        if not efforts:
            problems.append(f"{label}: efforts is empty")
        seen = set()
        for tier in efforts:
            effort = tier.get("effort")
            if not isinstance(effort, str) or not effort.strip() or effort in seen:
                problems.append(f"{label}: duplicate or empty effort {effort!r}")
            seen.add(effort)
            for field in ("rank", "floor"):
                if type(tier.get(field)) is not int or tier[field] < 1:
                    problems.append(f"{label}#{effort}: {field} must be a positive integer")
            if type(tier.get("rank")) is int:
                ranks.append((family, tier["rank"]))
    for model in models:
        for tier in model.get("efforts", []):
            floor = tier.get("floor")
            if type(floor) is int and not any(f != model["family"] and rank >= floor for f, rank in ranks):
                problems.append(f"{model['model']}#{tier['effort']}: floor {floor} has no other-family rank (exclusive top)")
    return problems


def commits(root: pathlib.Path) -> list[tuple[str, str]]:
    start = git(root, "rev-parse", NUMERIC_START).strip()
    entries = git(root, "log", "--first-parent", "--reverse", "--format=%H %cI",
                  f"{start}^..HEAD", "--", "routing/models.toml").splitlines()
    if not entries or entries[0].split()[0] != start:
        raise ValueError(f"numeric capability history from {NUMERIC_START} is unavailable")
    return [(rev, utc(date)) for rev, date in (line.split() for line in entries)]


def read_at(root: pathlib.Path, as_of: str) -> tuple[str, dict[str, str]]:
    timestamp = instant(as_of)
    entries = commits(root)
    if timestamp < instant(entries[0][1]):
        raise ValueError(f"ladder-gap: no numeric capability record at {as_of}")
    history = git(root, "log", "--first-parent", "--format=%H %cI", f"{entries[0][0]}^..HEAD").splitlines()
    eligible = [(rev, date) for rev, date in (line.split() for line in history) if instant(date) <= timestamp]
    if not eligible:
        raise ValueError(f"ladder-gap: no numeric capability record at {as_of}")
    rev, _ = max(eligible, key=lambda entry: instant(entry[1]))
    return rev, {name: git(root, "show", f"{rev}:routing/{name}.toml")
                 for name in ("models", "profiles", "delegation")}
