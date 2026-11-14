"""The three data stores under data/: catalog, policy and field notes.

`catalog.toml` holds facts about models, `policy.toml` what `resolve`
answers, and `notes.jsonl` dated field notes that no routing decision reads.
Each TOML store is a flat list of row tables plus a few tables of scalars.
`emit` writes one canonical form: a fixed key order per table, rows in the
order given, and every row naming a model or profile directly after it, so a
hand edit and a verb edit produce the same diff. `problems` checks the whole
data set and names the offending row. `load` projects the stores into the
route and tier records the resolver works on.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import pathlib
import re
import tomllib

DATA = "data"
CATALOG = f"{DATA}/catalog.toml"
POLICY = f"{DATA}/policy.toml"
NOTES = f"{DATA}/notes.jsonl"
CATALOG_SCHEMA = "agent-routing-catalog/1"
POLICY_SCHEMA = "agent-routing-policy/1"

EFFORTS = ("default", "low", "medium", "high", "xhigh", "max", "ultra")
MODEL_STATUSES = ("experimental", "superseded", "retired", "deprecated", "inactive", "restricted")
TIER_STABILITIES = ("explicit-only", "probationary", "experimental")
SEAT_STABILITIES = ("stable", "probationary", "experimental")
BACKEND_STATUSES = ("verified", "unprobed")
NOTE_KINDS = ("strength", "weakness", "observation", "measurement")
NOTE_CAUSES = ("brief", "executor", "integration", "unknown")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# A key's type: str, int, num, bool, date, time, strs (a list of strings).
CATALOG_TABLES = {
    "family": (("id", "str", True), ("lineages", "strs", False), ("cache_write_ratio", "num", False),
               ("cache_write_1h_ratio", "num", False), ("credits_per_dollar", "num", False)),
    "backend": (("id", "str", True), ("status", "str", True), ("providers", "strs", True),
                ("efforts", "strs", True)),
    "model": (("id", "str", True), ("family", "str", True), ("aliases", "strs", False), ("status", "str", False),
              ("successor", "str", False), ("build", "str", False), ("build_date", "date", False)),
    "tier": (("model", "str", True), ("effort", "str", True), ("rank", "int", True), ("floor", "int", True),
             ("stability", "str", False), ("prohibited", "bool", False), ("reason", "str", False)),
    "price": (("model", "str", True), ("read", "date", True), ("from", "date", False), ("input", "num", False),
              ("cache_miss_input", "num", False), ("cached_input", "num", False), ("cache_hit_input", "num", False),
              ("cache_write", "num", False), ("cache_write_1h", "num", False), ("output", "num", False)),
    "surcharge": (("model", "str", True), ("threshold_input_tokens", "int", True), ("threshold_inclusive", "bool", True),
                  ("input_multiplier", "num", True), ("cache_multiplier", "num", True),
                  ("output_multiplier", "num", True)),
    "price_window": (("model", "str", True), ("from", "time", True), ("until", "time", True),
                     ("multiplier", "num", True), ("days", "strs", False)),
    "credit": (("model", "str", True), ("input", "num", False), ("cached_input", "num", False),
               ("output", "num", False)),
    "reach": (("model", "str", True), ("backend", "str", True), ("provider", "str", True),
              ("backend_model", "str", True), ("agent_alias", "str", False)),
    "effort_support": (("model", "str", True), ("backend", "str", True), ("efforts", "strs", True)),
}
CATALOG_LAYOUT = (("family", "backend"), "model", ("tier", "price", "surcharge", "price_window", "credit", "reach",
                                                    "effort_support"))

POLICY_SETTINGS = {
    "review": (("clearance", "int", True),),
    "admission": (("max_age_seconds", "int", True), ("codex_author_families", "strs", True),
                  ("codex_review_backend", "str", True), ("other_review_backend", "str", True),
                  ("claude_minimum_remaining", "int", True)),
}
POLICY_TABLES = {
    "pool": (("provider", "str", True), ("plan", "str", True), ("serves", "strs", True), ("pays_for", "str", True),
             ("usage_key", "str", False), ("windows", "strs", False), ("scarcer_than", "strs", False),
             ("why", "str", True)),
    "family_exception": (("reviewer", "str", True), ("authors", "strs", True), ("why", "str", True),
                         ("since", "date", True)),
    "fence": (("model", "str", True), ("profile", "str", True), ("why", "str", True), ("since", "date", True)),
    "profile": (("id", "str", True), ("purpose", "str", True), ("escalation_sources", "strs", False)),
    "seat": (("profile", "str", True), ("variant", "str", False), ("backend", "str", True), ("provider", "str", True),
             ("model", "str", True), ("effort", "str", True), ("stability", "str", True), ("default", "bool", False),
             ("role_exception", "str", False), ("when", "str", True), ("why", "str", True), ("since", "date", True)),
    "fallback": (("profile", "str", True), ("from_provider", "str", True), ("backend", "str", True),
                 ("variant", "str", False)),
    "seat_rank": (("model", "str", True), ("effort", "str", True), ("pool", "str", True), ("rank", "int", True)),
    "repository": (("id", "str", True), ("name", "str", True)),
    "accessor": (("id", "str", True), ("command", "strs", True), ("expected_sources", "strs", True)),
    "consumer": (("id", "str", True), ("repository", "str", True), ("path", "str", True), ("checks", "strs", True),
                 ("generated", "str", False)),
    "proxy": (("consumer", "str", True), ("path", "str", True), ("model", "str", True), ("effort", "str", True)),
    "pin": (("consumer", "str", True), ("path", "str", True), ("model", "str", True), ("effort", "str", True),
            ("profile", "str", True), ("variant", "str", False), ("backend", "str", True),
            ("generated", "bool", False), ("allow_experimental", "bool", False)),
}
POLICY_LAYOUT = (("pool", "family_exception", "fence"), "profile", ("seat", "fallback"),
                 ("seat_rank", "repository", "accessor", "consumer", "proxy", "pin"))
NOTE_KEYS = (("id", "str", True), ("date", "date", True), ("model", "str", True), ("effort", "str", False),
             ("kind", "str", True), ("areas", "strs", True), ("claim", "str", True), ("cause", "str", True),
             ("evidence", "str", True), ("metrics", "metrics", False))

HEADERS = {
    CATALOG: "# Facts about models: families, backends, models, tiers, prices and reachability.\n"
             "# Written in canonical form; `agent-routing format` rewrites a hand edit into it.\n",
    POLICY: "# What `resolve` answers: pools, profiles, seats, fallbacks, ranks and consumer pins.\n"
            "# Written in canonical form; `agent-routing format` rewrites a hand edit into it.\n",
}


class StoreError(ValueError):
    """A store that cannot be read as its schema says."""


# --- canonical emission -------------------------------------------------------


# TOML basic strings escape the quote, the backslash and every control character but tab.
_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r"}


def _scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StoreError(f"cannot write the non-finite number {value!r}")
        return repr(value)
    if isinstance(value, str):
        return '"' + "".join(_ESCAPES.get(char) or (f"\\u{ord(char):04x}" if ord(char) < 0x20 or ord(char) == 0x7F
                                                     else char) for char in value) + '"'
    if isinstance(value, list):
        return "[" + ", ".join(_scalar(item) for item in value) + "]"
    raise StoreError(f"cannot write {type(value).__name__} value {value!r} in a store")


def _row(name: str, spec, row: dict, *, array: bool = True) -> str:
    known = [key for key, _, _ in spec]
    extra = [key for key in row if key not in known]
    if extra:
        raise StoreError(f"[{name}] has unknown key {extra[0]!r}")
    lines = [f"[[{name}]]" if array else f"[{name}]"]
    lines += [f"{key} = {_scalar(row[key])}" for key in known if key in row]
    return "\n".join(lines) + "\n"


def _grouped(document: dict, tables: dict, layout) -> list[str]:
    """Blocks in layout order: leading tables, then each owner row followed by the rows naming it, then the rest."""
    leading, owner, members, trailing = layout[0], layout[1], layout[2], layout[3] if len(layout) > 3 else ()
    blocks = []
    for name in leading:
        blocks += [_row(name, tables[name], row) for row in document.get(name, [])]
    owner_key = "id"
    member_key = "model" if owner == "model" else "profile"
    owners = [row.get(owner_key) for row in document.get(owner, [])]
    for row in document.get(owner, []):
        blocks.append(_row(owner, tables[owner], row))
        for name in members:
            blocks += [_row(name, tables[name], member) for member in document.get(name, [])
                       if member.get(member_key) == row.get(owner_key)]
    for name in members:
        orphans = [member for member in document.get(name, []) if member.get(member_key) not in owners]
        blocks += [_row(name, tables[name], member) for member in orphans]
    for name in trailing:
        blocks += [_row(name, tables[name], row) for row in document.get(name, [])]
    return blocks


def emit_catalog(document: dict) -> str:
    _refuse_unknown_tables(document, set(CATALOG_TABLES) | {"schema"}, CATALOG)
    blocks = [f"schema = {_scalar(document.get('schema', CATALOG_SCHEMA))}\n",
              *_grouped(document, CATALOG_TABLES, CATALOG_LAYOUT)]
    return HEADERS[CATALOG] + "\n" + "\n".join(blocks)


def emit_policy(document: dict) -> str:
    _refuse_unknown_tables(document, set(POLICY_TABLES) | set(POLICY_SETTINGS) | {"schema"}, POLICY)
    blocks = [f"schema = {_scalar(document.get('schema', POLICY_SCHEMA))}\n"]
    blocks += [_row(name, spec, document[name], array=False) for name, spec in POLICY_SETTINGS.items()
               if name in document]
    blocks += _grouped(document, POLICY_TABLES, POLICY_LAYOUT)
    return HEADERS[POLICY] + "\n" + "\n".join(blocks)


def emit_note(note: dict) -> str:
    known = [key for key, _, _ in NOTE_KEYS]
    extra = [key for key in note if key not in known]
    if extra:
        raise StoreError(f"note {note.get('id')!r} has unknown key {extra[0]!r}")
    ordered = {key: note[key] for key in known if key in note}
    if "metrics" in ordered:
        ordered["metrics"] = dict(sorted(ordered["metrics"].items()))
    return json.dumps(ordered, ensure_ascii=False, separators=(", ", ": ")) + "\n"


def emit_notes(notes: list[dict]) -> str:
    return "".join(emit_note(note) for note in notes)


def _refuse_unknown_tables(document: dict, allowed: set, store: str) -> None:
    extra = sorted(set(document) - allowed)
    if extra:
        raise StoreError(f"{store}: unknown table {extra[0]!r}")


# --- reading ------------------------------------------------------------------


def parse_toml(text: str, store: str) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise StoreError(f"{store}: {error}") from error


def parse_notes(text: str) -> list[dict]:
    notes = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise StoreError(f"{NOTES}:{number}: blank line")
        try:
            note = json.loads(line)
        except ValueError as error:
            raise StoreError(f"{NOTES}:{number}: {error}") from error
        if not isinstance(note, dict):
            raise StoreError(f"{NOTES}:{number}: a note is a JSON object")
        notes.append(note)
    return notes


def texts_at(root: pathlib.Path) -> dict[str, str]:
    return {name: (root / name).read_text() for name in (CATALOG, POLICY)}


def route_version(texts: dict[str, str]) -> str:
    """The first twelve hex digits of SHA-256 over each routing store's path and bytes."""
    digest = hashlib.sha256()
    for name in (CATALOG, POLICY):
        digest.update(name.encode() + b"\0" + texts[name].encode() + b"\0")
    return digest.hexdigest()[:12]


_CACHE: dict = {}


def load(root: pathlib.Path) -> "Data":
    """The routing stores at `root`, parsed again whenever either file's bytes change."""
    root = pathlib.Path(root)
    texts = texts_at(root)
    key = str(root.resolve())
    cached = _CACHE.get(key)
    if cached is None or cached[0] != texts:
        cached = (texts, Data.from_texts(texts))
        _CACHE[key] = cached
    return cached[1]


def load_notes(root: pathlib.Path) -> list[dict]:
    path = pathlib.Path(root) / NOTES
    return parse_notes(path.read_text()) if path.exists() else []


class Data:
    """The catalog and policy, raw and projected into route and tier records."""

    def __init__(self, catalog: dict, policy: dict, version: str):
        self.catalog = catalog
        self.policy = policy
        self.version = version
        self.structural: tuple[str, ...] | None = None
        self.models = project_models(catalog, policy)
        self.profiles = project_profiles(catalog, policy)
        self.backends = project_backends(catalog)
        self.pools = [dict(row) for row in policy.get("pool", [])]
        self.families = project_families(catalog)

    @classmethod
    def from_texts(cls, texts: dict[str, str]) -> "Data":
        return cls(parse_toml(texts[CATALOG], CATALOG), parse_toml(texts[POLICY], POLICY), route_version(texts))

    def by_model(self) -> dict[str, dict]:
        return {model["id"]: model for model in self.models}


# --- projection ---------------------------------------------------------------


def _rows(document: dict, table: str, **match) -> list[dict]:
    return [row for row in document.get(table, []) if all(row.get(key) == value for key, value in match.items())]


PRICE_KEYS = ("input", "cache_miss_input", "cached_input", "cache_hit_input", "cache_write", "cache_write_1h", "output")


def project_models(catalog: dict, policy: dict) -> list[dict]:
    """Each model with its tiers, prices and terms in the shape the resolver and exports read."""
    ranks: dict[tuple[str, str], dict[str, int]] = {}
    for row in policy.get("seat_rank", []):
        ranks.setdefault((row.get("model"), row.get("effort")), {})[row.get("pool")] = row.get("rank")
    models = []
    for row in catalog.get("model", []):
        model = {key: row[key] for key in ("id", "family", "aliases", "status", "successor", "build", "build_date")
                 if key in row}
        model["superseded"] = row.get("status") in {"superseded", "retired"}
        fences = {fence.get("profile"): fence.get("why") for fence in _rows(policy, "fence", model=row.get("id"))}
        if fences:
            model["fences"] = fences
        tiers = []
        for tier in _rows(catalog, "tier", model=row.get("id")):
            entry = {key: tier[key] for key in ("effort", "rank", "floor", "prohibited", "reason") if key in tier}
            if "stability" in tier:
                entry["status"] = tier["stability"]
            rank = ranks.get((row.get("id"), tier.get("effort")))
            if rank:
                entry["seat_rank"] = rank
            tiers.append(entry)
        model["effort"] = tiers
        prices = _rows(catalog, "price", model=row.get("id"))
        base = [price for price in prices if "from" not in price]
        if base:
            model["api_price_per_million"] = {key: base[0][key] for key in PRICE_KEYS if key in base[0]}
            model["api_price_read"] = base[0].get("read")
            changes = [price for price in prices if "from" in price]
            if changes:
                model["api_price_changes"] = [{"from": price["from"],
                                               "per_million": {key: price[key] for key in PRICE_KEYS if key in price}}
                                              for price in changes]
        surcharge = _rows(catalog, "surcharge", model=row.get("id"))
        if surcharge:
            model["long_context_surcharge"] = {key: value for key, value in surcharge[0].items() if key != "model"}
        windows = _rows(catalog, "price_window", model=row.get("id"))
        if windows:
            model["time_of_day_prices"] = [{key: value for key, value in window.items() if key != "model"}
                                           for window in windows]
        credit = _rows(catalog, "credit", model=row.get("id"))
        if credit:
            model["subscription_credits_per_million"] = {key: value for key, value in credit[0].items()
                                                         if key != "model"}
        models.append(model)
    return models


def reach_row(catalog: dict, model: str, backend: str, provider: str) -> dict | None:
    """How `backend` reaches `model` through `provider`, if the catalog says it can."""
    return next(iter(_rows(catalog, "reach", model=model, backend=backend, provider=provider)), None)


def reach_name(catalog: dict, model: str, backend: str, provider: str) -> str | None:
    row = reach_row(catalog, model, backend, provider)
    return row["backend_model"] if row else None


def project_profiles(catalog: dict, policy: dict) -> list[dict]:
    """Each profile with its primary route and named variants, one route per seat group.

    The seats of one route, its rows for each backend, share every field but
    the backend and its reasons; `problems` refuses a route whose rows differ.
    """
    profiles = []
    for row in policy.get("profile", []):
        profile = {key: row[key] for key in ("id", "purpose", "escalation_sources") if key in row}
        routes: dict[str | None, dict] = {}
        for seat in _rows(policy, "seat", profile=row.get("id")):
            variant = seat.get("variant")
            route = routes.get(variant)
            if route is None:
                route = {"provider": seat.get("provider"), "model": seat.get("model"), "effort": seat.get("effort"),
                         "stability": seat.get("stability"), "backends": []}
                if variant is not None:
                    route["id"] = variant
                    if "default" in seat:
                        route["default_for_backend"] = seat["default"]
                if "role_exception" in seat:
                    route["role_exception"] = seat["role_exception"]
                name = reach_name(catalog, seat.get("model"), seat.get("backend"), seat.get("provider"))
                if name is not None and name != seat.get("model"):
                    route["backend_model"] = name
                routes[variant] = route
            route["backends"].append(seat.get("backend"))
        primary = routes.pop(None, {"backends": []})
        profile.update({key: value for key, value in primary.items()})
        profile["variant"] = list(routes.values())
        fallbacks = [{key: value for key, value in rule.items() if key != "profile"}
                     for rule in _rows(policy, "fallback", profile=row.get("id"))]
        if fallbacks:
            profile["fallback"] = fallbacks
        profiles.append(profile)
    return profiles


def project_backends(catalog: dict) -> list[dict]:
    backends = []
    for row in catalog.get("backend", []):
        backend = {"id": row.get("id"), "status": row.get("status"), "providers": row.get("providers", []),
                   "supported_efforts": row.get("efforts", [])}
        overrides = {support["model"]: support["efforts"]
                     for support in _rows(catalog, "effort_support", backend=row.get("id"))}
        if overrides:
            backend["model_efforts"] = overrides
        backends.append(backend)
    return backends


def project_families(catalog: dict) -> list[dict]:
    """The family rows grouping lineages, each with its lab id and the lineage values models carry."""
    carried = {model.get("family") for model in catalog.get("model", [])}
    rows = []
    for row in catalog.get("family", []):
        values = [value for value in dict.fromkeys([row.get("id"), *row.get("lineages", [])]) if value in carried]
        rows.append({"lab": row.get("id"), "values": values})
    return rows


# --- validation ---------------------------------------------------------------

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")


def _typed(kind: str, value) -> bool:
    if kind == "str":
        return isinstance(value, str) and bool(value.strip()) and value == value.strip()
    if kind == "int":
        return type(value) is int
    if kind == "num":
        return type(value) in (int, float) and math.isfinite(value)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "strs":
        return isinstance(value, list) and all(_typed("str", item) for item in value) and len(set(value)) == len(value)
    if kind == "date":
        if not isinstance(value, str) or not _DATE.fullmatch(value):
            return False
        try:
            return datetime.date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if kind == "time":
        return isinstance(value, str) and bool(_TIME.fullmatch(value))
    if kind == "metrics":
        return isinstance(value, dict) and bool(value) and all(
            isinstance(key, str) and (type(item) in (int, float, str) and item == item) for key, item in value.items())
    raise AssertionError(kind)


def label(table: str, row: dict) -> str:
    """How a problem names a row: its table and identifying keys."""
    keys = {"family": ("id",), "backend": ("id",), "model": ("id",), "tier": ("model", "effort"),
            "price": ("model", "from"), "surcharge": ("model",), "price_window": ("model", "from"),
            "credit": ("model",), "reach": ("model", "backend", "provider"), "effort_support": ("model", "backend"),
            "pool": ("provider",), "family_exception": ("reviewer",), "fence": ("model", "profile"),
            "profile": ("id",), "seat": ("profile", "variant", "backend"), "fallback": ("profile", "backend"),
            "seat_rank": ("model", "effort", "pool"), "repository": ("id",), "accessor": ("id",),
            "consumer": ("id",), "proxy": ("consumer", "path"), "pin": ("consumer", "path")}.get(table, ())
    parts = [f"{key}={row[key]}" for key in keys if isinstance(row, dict) and key in row]
    return f"[[{table}]] " + " ".join(parts) if parts else f"[[{table}]]"


def shape_problems(document: dict, tables: dict, store: str, settings: dict | None = None) -> list[str]:
    """Unknown tables and keys, missing required keys and mistyped values, each naming its row."""
    problems = []
    settings = settings or {}
    for name in sorted(set(document) - set(tables) - set(settings) - {"schema"}):
        problems.append(f"{store}: unknown table [{name}]")
    for name, spec in settings.items():
        row = document.get(name)
        if row is None:
            problems.append(f"{store}: [{name}] is missing")
        elif not isinstance(row, dict):
            problems.append(f"{store}: [{name}] must be a table")
        else:
            problems += _key_problems(f"{store} [{name}]", spec, row)
    for name, spec in tables.items():
        rows = document.get(name, [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            problems.append(f"{store}: [[{name}]] must be an array of tables")
            continue
        for row in rows:
            problems += _key_problems(f"{store} {label(name, row)}", spec, row)
    return problems


def _key_problems(where: str, spec, row: dict) -> list[str]:
    problems = []
    known = {key: (kind, required) for key, kind, required in spec}
    for key in row:
        if key not in known:
            problems.append(f"{where}: unknown key {key!r}")
        elif not _typed(known[key][0], row[key]):
            problems.append(f"{where}: {key} must be {_KIND_TEXT[known[key][0]]}, not {row[key]!r}")
    for key, (kind, required) in known.items():
        if required and key not in row:
            problems.append(f"{where}: {key} is required")
    return problems


_KIND_TEXT = {"str": "a nonblank unpadded string", "int": "an integer", "num": "a finite number",
              "bool": "true or false", "strs": "a list of distinct nonblank strings", "date": "a YYYY-MM-DD date",
              "time": "an HH:MM UTC time", "metrics": "a nonempty object of numbers and strings"}


def catalog_problems(catalog: dict) -> list[str]:
    store = CATALOG
    problems = shape_problems(catalog, CATALOG_TABLES, store)
    if catalog.get("schema") != CATALOG_SCHEMA:
        problems.append(f"{store}: schema must be {CATALOG_SCHEMA!r}")
    models = {row.get("id") for row in catalog.get("model", [])}
    backends = {row.get("id"): row for row in catalog.get("backend", [])}
    seen: dict[tuple, str] = {}

    def unique(table: str, row: dict, key: tuple) -> None:
        if key in seen:
            problems.append(f"{store} {label(table, row)}: declared twice")
        seen[key] = table

    for row in catalog.get("model", []):
        unique("model", row, ("model", row.get("id")))
        if row.get("status") is not None and row.get("status") not in MODEL_STATUSES:
            problems.append(f"{store} {label('model', row)}: status must be one of {', '.join(MODEL_STATUSES)}")
        if "successor" in row and row["successor"] not in models:
            problems.append(f"{store} {label('model', row)}: successor {row['successor']!r} is not a catalog model")
    names: dict[str, str] = {}
    for row in catalog.get("model", []):
        for name in [row.get("id"), *row.get("aliases", [])]:
            if name in names and names[name] != row.get("id"):
                problems.append(f"{store} {label('model', row)}: {name!r} already names model {names[name]!r}")
            names.setdefault(name, row.get("id"))
    for row in catalog.get("backend", []):
        unique("backend", row, ("backend", row.get("id")))
        if row.get("status") not in BACKEND_STATUSES:
            problems.append(f"{store} {label('backend', row)}: status must be one of {', '.join(BACKEND_STATUSES)}")
        for effort in row.get("efforts", []) if isinstance(row.get("efforts"), list) else []:
            if effort not in EFFORTS:
                problems.append(f"{store} {label('backend', row)}: unknown effort {effort!r}")
    for table in ("tier", "price", "surcharge", "price_window", "credit", "reach", "effort_support"):
        for row in catalog.get(table, []):
            if row.get("model") not in models:
                problems.append(f"{store} {label(table, row)}: model is not a catalog model")
    for row in catalog.get("tier", []):
        unique("tier", row, ("tier", row.get("model"), row.get("effort")))
        if row.get("effort") not in EFFORTS:
            problems.append(f"{store} {label('tier', row)}: effort must be one of {', '.join(EFFORTS)}")
        for key in ("rank", "floor"):
            if type(row.get(key)) is int and row[key] < 1:
                problems.append(f"{store} {label('tier', row)}: {key} must be a positive integer")
        if row.get("stability") is not None and row.get("stability") not in TIER_STABILITIES:
            problems.append(f"{store} {label('tier', row)}: stability must be one of {', '.join(TIER_STABILITIES)}")
        if row.get("prohibited") is True and "reason" not in row:
            problems.append(f"{store} {label('tier', row)}: a prohibited tier names its reason")
        if "reason" in row and row.get("prohibited") is not True:
            problems.append(f"{store} {label('tier', row)}: reason belongs to a prohibited tier")
        if row.get("prohibited") is False:
            problems.append(f"{store} {label('tier', row)}: omit prohibited rather than writing false")
    for row in catalog.get("price", []):
        unique("price", row, ("price", row.get("model"), row.get("from")))
    for table in ("surcharge", "credit"):
        for row in catalog.get(table, []):
            unique(table, row, (table, row.get("model")))
    for row in catalog.get("price_window", []):
        for day in row.get("days", []) if isinstance(row.get("days"), list) else []:
            if day not in DAYS:
                problems.append(f"{store} {label('price_window', row)}: days are written {', '.join(DAYS)}")
    for row in catalog.get("reach", []):
        unique("reach", row, ("reach", row.get("model"), row.get("backend"), row.get("provider")))
        backend = backends.get(row.get("backend"))
        if backend is None:
            problems.append(f"{store} {label('reach', row)}: backend is not a catalog backend")
        elif row.get("provider") not in backend.get("providers", []):
            problems.append(f"{store} {label('reach', row)}: backend {row['backend']!r} has no provider "
                            f"{row.get('provider')!r}")
    for row in catalog.get("effort_support", []):
        unique("effort_support", row, ("effort_support", row.get("model"), row.get("backend")))
        if row.get("backend") not in backends:
            problems.append(f"{store} {label('effort_support', row)}: backend is not a catalog backend")
        for effort in row.get("efforts", []) if isinstance(row.get("efforts"), list) else []:
            if effort not in EFFORTS:
                problems.append(f"{store} {label('effort_support', row)}: unknown effort {effort!r}")
    lineages: dict[str, str] = {}
    for row in catalog.get("family", []):
        unique("family", row, ("family", row.get("id")))
        for value in dict.fromkeys([row.get("id"), *row.get("lineages", [])]):
            if value in lineages:
                problems.append(f"{store} {label('family', row)}: {value!r} already belongs to family "
                                f"{lineages[value]!r}")
            lineages[value] = row.get("id")
        carried = {model.get("family") for model in catalog.get("model", [])}
        for value in row.get("lineages", []):
            if value not in carried:
                problems.append(f"{store} {label('family', row)}: no catalog model carries lineage {value!r}")
    return problems


def policy_problems(policy: dict, catalog: dict) -> list[str]:
    store = POLICY
    problems = shape_problems(policy, POLICY_TABLES, store, POLICY_SETTINGS)
    if policy.get("schema") != POLICY_SCHEMA:
        problems.append(f"{store}: schema must be {POLICY_SCHEMA!r}")
    models = {row.get("id") for row in catalog.get("model", [])}
    backends = {row.get("id") for row in catalog.get("backend", [])}
    profiles = {row.get("id") for row in policy.get("profile", [])}
    seen: set[tuple] = set()

    def unique(table: str, row: dict, key: tuple) -> None:
        if key in seen:
            problems.append(f"{store} {label(table, row)}: declared twice")
        seen.add(key)

    for row in policy.get("profile", []):
        unique("profile", row, ("profile", row.get("id")))
    for row in policy.get("seat", []):
        unique("seat", row, ("seat", row.get("profile"), row.get("variant"), row.get("backend")))
        where = f"{store} {label('seat', row)}"
        if row.get("profile") not in profiles:
            problems.append(f"{where}: profile is not a policy profile")
        if row.get("model") not in models:
            problems.append(f"{where}: model {row.get('model')!r} is not a catalog model")
        if row.get("backend") not in backends:
            problems.append(f"{where}: backend {row.get('backend')!r} is not a catalog backend")
        if row.get("stability") not in SEAT_STABILITIES:
            problems.append(f"{where}: stability must be one of {', '.join(SEAT_STABILITIES)}")
        if "default" in row and "variant" not in row:
            problems.append(f"{where}: default names a variant that answers an unnamed request")
        if row.get("model") in models and reach_name(catalog, row.get("model"), row.get("backend"),
                                                     row.get("provider")) is None:
            problems.append(f"{where}: no [[reach]] row says how backend {row.get('backend')!r} reaches "
                            f"{row.get('model')!r} through {row.get('provider')!r}")
        for key in ("when", "why"):
            text = row.get(key)
            if isinstance(text, str) and (len(text) > 240 or text.count(". ") > 0):
                problems.append(f"{where}: {key} is one sentence of at most 240 characters")
    groups: dict[tuple, dict] = {}
    for row in policy.get("seat", []):
        key = (row.get("profile"), row.get("variant"))
        first = groups.setdefault(key, row)
        fields = ("provider", "model", "effort", "stability", "default", "role_exception")
        differing = [field for field in fields if row.get(field) != first.get(field)]
        if differing:
            problems.append(f"{store} {label('seat', row)}: {differing[0]} differs from the same route's "
                            f"{first.get('backend')} seat; one route's seats agree on all but backend and reasons")
    for row in policy.get("fallback", []):
        if row.get("profile") not in profiles:
            problems.append(f"{store} {label('fallback', row)}: profile is not a policy profile")
    for row in policy.get("seat_rank", []):
        unique("seat_rank", row, ("seat_rank", row.get("model"), row.get("effort"), row.get("pool")))
    for row in policy.get("fence", []):
        unique("fence", row, ("fence", row.get("model"), row.get("profile")))
        if row.get("model") not in models:
            problems.append(f"{store} {label('fence', row)}: model is not a catalog model")
        if row.get("profile") not in profiles:
            problems.append(f"{store} {label('fence', row)}: profile is not a policy profile")
    for row in policy.get("pool", []):
        unique("pool", row, ("pool", row.get("provider")))
        for model in row.get("serves", []) if isinstance(row.get("serves"), list) else []:
            if model not in models:
                problems.append(f"{store} {label('pool', row)}: serves {model!r}, which is not a catalog model")
    for row in policy.get("pin", []):
        if row.get("profile") not in profiles:
            problems.append(f"{store} {label('pin', row)}: profile is not a policy profile")
    return problems


def note_problems(notes: list[dict], catalog: dict) -> list[str]:
    problems = []
    models = {row.get("id") for row in catalog.get("model", [])}
    ids: set = set()
    previous = None
    for note in notes:
        where = f"{NOTES} note {note.get('id')!r}"
        problems += _key_problems(where, NOTE_KEYS, note)
        if note.get("id") in ids:
            problems.append(f"{where}: id is used twice")
        ids.add(note.get("id"))
        if note.get("model") not in models:
            problems.append(f"{where}: model {note.get('model')!r} is not a catalog model")
        if note.get("kind") not in NOTE_KINDS:
            problems.append(f"{where}: kind must be one of {', '.join(NOTE_KINDS)}")
        if note.get("cause") not in NOTE_CAUSES:
            problems.append(f"{where}: cause must be one of {', '.join(NOTE_CAUSES)}")
        if "effort" in note and note["effort"] not in EFFORTS:
            problems.append(f"{where}: effort must be one of {', '.join(EFFORTS)}")
        if note.get("id") is not None and previous is not None and str(note["id"]) <= previous:
            problems.append(f"{where}: ids increase down the file")
        previous = str(note.get("id"))
    return problems


def canonical_problems(root: pathlib.Path) -> list[str]:
    """Each store whose bytes differ from what the emitter writes for its content."""
    root = pathlib.Path(root)
    problems = []
    for name, emit in ((CATALOG, emit_catalog), (POLICY, emit_policy)):
        text = (root / name).read_text()
        try:
            written = emit(parse_toml(text, name))
        except StoreError as error:
            problems.append(_named(name, error))
            continue
        if written != text:
            problems.append(f"{name}: not in canonical form; `agent-routing format` rewrites it")
    path = root / NOTES
    if path.exists():
        text = path.read_text()
        try:
            if emit_notes(parse_notes(text)) != text:
                problems.append(f"{NOTES}: not in canonical form; `agent-routing format` rewrites it")
        except StoreError as error:
            problems.append(_named(NOTES, error))
    return problems


def _named(store: str, error: StoreError) -> str:
    return str(error) if str(error).startswith(store) else f"{store}: {error}"


def format_stores(root: pathlib.Path) -> list[str]:
    """Rewrite each store in canonical form; the paths that changed."""
    root = pathlib.Path(root)
    changed = []
    for name, emit, parse in ((CATALOG, emit_catalog, lambda text: parse_toml(text, CATALOG)),
                              (POLICY, emit_policy, lambda text: parse_toml(text, POLICY)),
                              (NOTES, emit_notes, parse_notes)):
        path = root / name
        if not path.exists():
            continue
        text = path.read_text()
        written = emit(parse(text))
        if written != text:
            path.write_text(written)
            changed.append(name)
    return changed
