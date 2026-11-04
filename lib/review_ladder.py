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
    if model == "gpt-6.1-sol":
        return 3 if effort in {"high", "xhigh", "max"} else 1
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


def author_floor(model: str, effort: str) -> int:
    """The least reviewer rank for authored work, independent of reviewer strength."""
    if model == "gpt-6.1-sol" and effort in {"high", "xhigh", "max"}:
        return 2
    return capability(model, effort)


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
                for field in ("review_tier", "author_floor"):
                    if field in tier and (type(tier[field]) is not int or tier[field] < 1):
                        raise ValueError(f"{model_id}#{effort}: legacy {field} rank/floor must be a positive integer")
                # Legacy 4 expressed an unreachable seat, not measured capability.
                recorded_rank = tier.get("review_tier")
                recorded_floor = tier.get("author_floor", recorded_rank)
                rank = recorded_rank if recorded_rank is not None and recorded_rank < 4 else capability(model_id, effort)
                floor = recorded_floor if recorded_floor is not None and recorded_floor < 4 else author_floor(model_id, effort)
                if model_id == "gpt-6.1-sol":
                    rank, floor = capability(model_id, effort), author_floor(model_id, effort)
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


def validate(ladder: dict) -> None:
    if ladder.get("schema") != SCHEMA or not ladder.get("version"):
        raise ValueError(f"expected {SCHEMA} with at least one version")
    seen = set()
    previous = None
    for version in ladder["version"]:
        label = version.get("id")
        try:
            if not isinstance(label, str) or not label.strip() or label in seen:
                raise ValueError("version id must be nonempty and unique")
            seen.add(label)
            timestamp = instant(version.get("effective_from"))
            if previous is not None and timestamp <= previous:
                raise ValueError("effective_from must increase")
            previous = timestamp
            if not isinstance(version.get("source"), str) or not version["source"].strip():
                raise ValueError("source is empty")
            if type(version.get("gap")) is not bool:
                raise ValueError("gap must be boolean")
            if version["gap"]:
                if "model" in version:
                    raise ValueError("gap carries a model table")
            else:
                if not version.get("model"):
                    raise ValueError("model table is empty")
                problems = table_problems(version["model"])
                if problems:
                    raise ValueError("; ".join(problems))
        except ValueError as error:
            raise ValueError(f"version {label!r}: {error}") from error


def accepted_revision(root: pathlib.Path, accepted: str | None = None) -> str:
    """Pin the accepted ref without using the checkout's HEAD as a default."""
    if accepted is None:
        remote = git(root, "for-each-ref", "--format=%(symref)", "refs/remotes/origin/HEAD").strip()
        if remote:
            local = "refs/heads/" + remote.removeprefix("refs/remotes/origin/")
            accepted = local if git(root, "for-each-ref", "--format=%(refname)", local).strip() else remote
        else:
            candidates = git(root, "for-each-ref", "--format=%(refname)",
                             "refs/heads/master", "refs/heads/main").splitlines()
            if len(candidates) != 1:
                raise ValueError("cannot establish the default accepted branch; pass --accepted <ref>")
            accepted = candidates[0]
    return git(root, "rev-parse", "--verify", "--end-of-options", f"{accepted}^{{commit}}").strip()


def commits(root: pathlib.Path, accepted: str | None = None) -> list[tuple[str, str]]:
    revision = accepted_revision(root, accepted)
    start = git(root, "rev-parse", NUMERIC_START).strip()
    entries = git(root, "log", "--first-parent", "--reverse", "--format=%H %cI",
                  f"{start}^..{revision}", "--", "routing/models.toml", "routing/profiles.toml").splitlines()
    if not entries or entries[0].split()[0] != start:
        raise ValueError(f"numeric capability history from {NUMERIC_START} is unavailable on the accepted ref")
    return [(rev, utc(date)) for rev, date in (line.split() for line in entries)]


def read_at(root: pathlib.Path, as_of: str, accepted: str | None = None) -> tuple[str, dict[str, str]]:
    timestamp = instant(as_of)
    revision = accepted_revision(root, accepted)
    entries = commits(root, revision)
    if timestamp < instant(entries[0][1]):
        raise ValueError(f"ladder-gap: no numeric capability record at {as_of}")
    versions = export(root, history=True, accepted=revision)["version"]
    end = revision
    for version in versions:
        if not version["gap"] and instant(version["effective_from"]) > timestamp:
            end = version["id"].removeprefix("v-") + "^"
            break
    history = git(root, "log", "--first-parent", "--reverse", "--format=%H %cI",
                  f"{entries[0][0]}^..{end}").splitlines()
    eligible = [(rev, date) for rev, date in (line.split() for line in history) if instant(date) <= timestamp]
    if not eligible:
        raise ValueError(f"ladder-gap: no numeric capability record at {as_of}")
    rev, _ = eligible[-1]
    return rev, {name: git(root, "show", f"{rev}:routing/{name}.toml")
                 for name in ("models", "profiles", "delegation")}


def evidence_at(root: pathlib.Path, revision: str) -> str | None:
    """The dated era file, or its explicit absence, without a worktree fallback."""
    if not git(root, "ls-tree", "--name-only", revision, "--", EVIDENCE).strip():
        return None
    return git(root, "show", f"{revision}:{EVIDENCE}")


def version_at(root: pathlib.Path, revision: str, date: str) -> dict:
    try:
        manifest = historical_manifest(root, revision, "models")
        profiles = historical_manifest(root, revision, "profiles")
        if legacy(manifest) and not any(
            "review_tier" in tier or "author_floor" in tier
            for model in manifest.get("model", []) for tier in model.get("effort", [])
        ):
            raise ValueError("ladder-gap: the accepted revision predates the numeric capability record")
        table = project(manifest, profiles, historical=legacy(manifest))
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"version v-{revision}: {error}") from error
    version = {"id": f"v-{revision}", "effective_from": date, "source": source(root, revision),
               "gap": False, "model": table}
    validate({"schema": SCHEMA, "version": [version]})
    return version


def current_version(root: pathlib.Path, accepted: str) -> dict:
    """The first accepted commit of the current table, including shallow snapshots."""
    entries = git(root, "log", "--first-parent", "--format=%H %cI", accepted, "--",
                  "routing/models.toml", "routing/profiles.toml").splitlines()
    current = None
    for entry in entries:
        revision, date = entry.split()
        version = version_at(root, revision, utc(date))
        if current is not None and version["model"] != current["model"]:
            break
        current = version
        if revision.startswith(NUMERIC_START):
            break
    if current is None:
        raise ValueError("the accepted ref has no capability table")
    return current


def source(root: pathlib.Path, rev: str) -> str:
    eras = git(root, "ls-tree", "-r", "--name-only", rev, "--", "eras").splitlines()
    eras = [name for name in eras if any(term in name for term in (
        "fable", "opus", "gpt-6", "haiku", "sonnet", "author-floor", "workhorse", "field-test", "september", "mimo",
    ))]
    return f"agent-routing routing/models.toml at {rev}; reconstruction: {EVIDENCE}; era evidence: " + ", ".join(eras)


def export(root: pathlib.Path, *, history: bool = False, accepted: str | None = None) -> dict:
    revision = accepted_revision(root, accepted)
    if not history:
        ladder = {"schema": SCHEMA, "version": [current_version(root, revision)]}
        validate(ladder)
        return ladder
    versions = [{"id": "gap-2026-08-01", "effective_from": GAP_START, "gap": True,
                 "source": f"No numeric capability record before routing/models.toml at {NUMERIC_START}; {EVIDENCE}"}]
    for rev, date in commits(root, revision):
        version = version_at(root, rev, date)
        if len(versions) == 1 or versions[-1]["model"] != version["model"]:
            versions.append(version)
    ladder = {"schema": SCHEMA, "version": versions}
    validate(ladder)
    return ladder
