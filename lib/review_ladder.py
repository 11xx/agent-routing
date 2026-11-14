"""Dated capability tables, independent of routing seats and prices."""

from __future__ import annotations

import datetime as dt
import pathlib
import re
import subprocess
import tomllib
import types

import stores

SCHEMA = "arc-review-ladder/1"
NUMERIC_START = "dc54196"
# The accepted commit whose ladder module projects every revision still kept
# in the legacy routing files: its reconstruction of legacy tiers, its lab
# names and its era-file sources are history, read from Git rather than
# restated here.
RECONSTRUCTION = "6f219e5bf2fd4a1a80b1de5041a536aa4eeb5353"
GAP_START = "2026-08-01T00:00:00Z"
# The ladder's design record, cited by every pre-numeric record; it lives in Git history.
EVIDENCE = "eras/2026-11-04-capability-ladder.md"
TABLE_PATHS = (stores.CATALOG, stores.POLICY, "routing/models.toml", "routing/profiles.toml")


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


def snapshot(root: pathlib.Path, revision: str) -> dict[str, str]:
    """The routing data at `revision`: the stores where they exist, else the legacy routing files."""
    present = git(root, "ls-tree", "--name-only", revision, "--", stores.CATALOG).strip()
    names = (stores.CATALOG, stores.POLICY) if present else (
        "routing/models.toml", "routing/profiles.toml", "routing/delegation.toml")
    return {name: git(root, "show", f"{revision}:{name}") for name in names}


def is_stores(texts: dict[str, str]) -> bool:
    return stores.CATALOG in texts


def legacy_manifests(texts: dict[str, str]) -> tuple[dict, dict, dict]:
    return tuple(tomllib.loads(texts[f"routing/{name}.toml"]) for name in ("models", "profiles", "delegation"))


_HISTORICAL: dict = {}


def historical(root: pathlib.Path) -> types.ModuleType:
    """The ladder module as accepted at RECONSTRUCTION, which reads the legacy routing files."""
    key = str(pathlib.Path(root).resolve())
    if key not in _HISTORICAL:
        module = types.ModuleType("review_ladder_at_reconstruction")
        source = git(root, "show", f"{RECONSTRUCTION}:lib/review_ladder.py")
        exec(compile(source, f"{RECONSTRUCTION}:lib/review_ladder.py", "exec"), module.__dict__)
        _HISTORICAL[key] = module
    return _HISTORICAL[key]


def project_data(data: "stores.Data") -> list[dict]:
    """The capability table of the stores: each model's lab, identities, retirement and tiers."""
    labs = {value: row["lab"] for row in data.families for value in row["values"]}
    models = []
    for model in data.models:
        identities = {model["id"], *model.get("aliases", [])}
        for profile in data.profiles:
            for route in [profile, *profile.get("variant", [])]:
                if route.get("model") == model["id"] and route.get("backend_model"):
                    identities.add(route["backend_model"])
        models.append({"model": model["id"], "identities": sorted(identities),
                       "family": labs.get(model["family"], model["family"]), "superseded": model["superseded"],
                       "efforts": sorted(({"effort": tier["effort"], "rank": tier["rank"], "floor": tier["floor"]}
                                          for tier in model["effort"]), key=lambda row: row["effort"])})
    return sorted(models, key=lambda row: row["model"])


def table_at(root: pathlib.Path, texts: dict[str, str]) -> list[dict]:
    """The capability table a revision's data declares."""
    if is_stores(texts):
        return project_data(stores.Data.from_texts(texts))
    module = historical(root)
    manifest, profiles, _ = legacy_manifests(texts)
    return module.project(manifest, profiles, historical=module.legacy(manifest))


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
                  f"{start}^..{revision}", "--", *TABLE_PATHS).splitlines()
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
    return rev, snapshot(root, rev)


def evidence_at(root: pathlib.Path, revision: str) -> str | None:
    """The dated era file, or its explicit absence, without a worktree fallback."""
    if not git(root, "ls-tree", "--name-only", revision, "--", EVIDENCE).strip():
        return None
    return git(root, "show", f"{revision}:{EVIDENCE}")


def version_at(root: pathlib.Path, revision: str, date: str) -> dict:
    try:
        texts = snapshot(root, revision)
        if not is_stores(texts):
            module = historical(root)
            manifest, _, _ = legacy_manifests(texts)
            if module.legacy(manifest) and not any(
                "review_tier" in tier or "author_floor" in tier
                for model in manifest.get("model", []) for tier in model.get("effort", [])
            ):
                raise ValueError("ladder-gap: the accepted revision predates the numeric capability record")
        table = table_at(root, texts)
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"version v-{revision}: {error}") from error
    version = {"id": f"v-{revision}", "effective_from": date, "source": source(root, revision, texts),
               "gap": False, "model": table}
    validate({"schema": SCHEMA, "version": [version]})
    return version


def current_version(root: pathlib.Path, accepted: str) -> dict:
    """The first accepted commit of the current table, including shallow snapshots."""
    entries = git(root, "log", "--first-parent", "--format=%H %cI", accepted, "--", *TABLE_PATHS).splitlines()
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


def source(root: pathlib.Path, rev: str, texts: dict[str, str]) -> str:
    if is_stores(texts):
        return f"agent-routing {stores.CATALOG} at {rev}"
    return historical(root).source(root, rev)


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
