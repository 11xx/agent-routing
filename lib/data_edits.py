"""Validated store transactions, row edits and their Git edit log.

The public entry point is apply(root, verb, **options). A dry run has the
same result schema and performs no writes. Consumers can render that result
with render(result) or serialize it as JSON.
"""

import contextlib
import copy
import datetime
import difflib
import hashlib
import os
import pathlib
import re
import shlex
import subprocess
import tempfile

import field_notes
import stores

PATHS = (stores.CATALOG, stores.POLICY, stores.NOTES)
TRAILER = "Routing-edit"


def git(root, *args, input=None, env=None):
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", **(env or {})}
    run = subprocess.run(["git", "-C", str(root), *args], input=input, capture_output=True, env=environment)
    if run.returncode:
        raise stores.StoreError(run.stderr.decode().strip() or f"git {args[0]} failed")
    return run.stdout


class StaleState(stores.StoreError):
    """The stores or their edit history moved since the state an edit was asked to start from."""


def today():
    """The date an edit records when it is given none."""
    return datetime.date.today().isoformat()


def edit_date(given):
    """The date an edit records: the one given, as YYYY-MM-DD, else today."""
    if given is None:
        return today()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", given) and datetime.date.fromisoformat(given):
            return given
    except ValueError:
        pass
    raise stores.StoreError(f"--date must be a calendar date as YYYY-MM-DD, not {given!r}")


def read_texts(root):
    return {name: (root / name).read_bytes().decode("utf-8") for name in PATHS}


def state(root, texts):
    """The stores' bytes and the last commit that changed them, as one digest.

    An edit computed from one state, previewed or confirmed, is the same edit
    only from that state: the bytes decide row edits, and the history decides
    what undo reverts. A caller reads it under the store lock.
    """
    digest = hashlib.sha256()
    for name in PATHS:
        digest.update(name.encode() + b"\0" + texts[name].encode() + b"\0")
    digest.update(git(root, "log", "-1", "--format=%H", "--", *PATHS).strip())
    return digest.hexdigest()[:16]


def observe(root):
    """The route version and the state of the stores, read together under the shared lock."""
    root = pathlib.Path(root).resolve()
    with stores.store_lock(root, exclusive=False):
        texts = read_texts(root)
        return {"route_version": stores.route_version(texts), "state": state(root, texts)}


def candidate_problems(texts):
    """The whole data set, checked in memory by the deciding path's own validators."""
    import routing_profiles as routes
    from price_export import price_problems

    loaded = stores.Data.from_texts(texts)
    notes = stores.parse_notes(texts[stores.NOTES])
    errors = (list(loaded.problems) + stores.note_problems(notes, loaded.catalog)
              + stores.guard_problems(loaded.policy, loaded.catalog, notes))
    if loaded.problems:
        return errors
    errors += routes._structural_problems(None, loaded)
    errors += (routes.loaded_pool_problems(loaded) + price_problems(loaded.models) + routes.relation_problems(loaded)
               + routes.review_coverage_problems(loaded))
    # Profile-shaped diagnostics identify the underlying store row at the write boundary.
    return [error if error.startswith("data/") else f"{stores.POLICY} [[seat/profile]] {error}" for error in errors]


def checked(texts):
    errors = candidate_problems(texts)
    if errors:
        raise stores.StoreError("\n".join(errors))


def default_problems(before, after):
    def bindings(texts):
        return {(row["profile"], backend) for row in stores.Data.from_texts(texts).policy.get("seat", [])
                if "variant" not in row or row.get("default") for backend in row["backends"]}
    profiles = {row["id"] for row in stores.Data.from_texts(after).policy.get("profile", [])}
    return [f"{stores.POLICY} [[seat]] profile={profile} backend={backend}: "
            "edit removes the resolvable default; choose another default first"
            for profile, backend in sorted(bindings(before) - bindings(after)) if profile in profiles]


def why_text(value):
    if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
        raise stores.StoreError("--why is required: one or two sentences on one line")
    value = value.strip()
    if len(re.findall(r"[.!?](?:\s|$)", value)) > 2:
        raise stores.StoreError("--why is one or two sentences")
    return value


def require_one(rows, where, **key):
    found = [row for row in rows if all(row.get(k) == v for k, v in key.items())]
    if len(found) != 1:
        raise stores.StoreError(f"{where} {key}: expected one row, found {len(found)}")
    return found[0]


def selection_classes(root, texts, pools):
    """validate's classification of every directed selection it answers in these pools, in one data set.

    Every profile, by every tier of every model a backend reaches through
    one of the pools, asked of validate itself (as --allow-experimental
    would), answering from these texts parsed once: a selection it refuses,
    for any reason, has no classification here.
    """
    import routing_profiles as routes

    loaded = stores.Data.from_texts(texts)
    by_model = loaded.by_model()
    classes = {}
    with routes.answering_from(loaded):
        for profile in loaded.profiles:
            for reach in loaded.catalog.get("reach", []):
                if reach["provider"] not in pools or reach["model"] not in by_model:
                    continue
                for tier in by_model[reach["model"]].get("effort", []):
                    key = (profile["id"], reach["backend"], reach["model"], tier["effort"], reach["provider"])
                    try:
                        answer = routes.validate_selection(root, *key, "Compare the pool ranks.", allow_experimental=True)
                    except routes.RouteRefusal:
                        continue
                    classes[key] = {name: answer[name] for name in ("direction", "stability", "selection_kind")}
    return classes


def classification_changes(root, before, after, changes):
    """The directed selections in the pools an edit of pool ranks touches that validate answers both before and
    after it, classified differently."""
    pools = {row[side]["pool"] for row in changes if row["table"] == "seat_rank" for side in ("before", "after")
             if row[side]}
    if not pools:
        return None
    old, new = selection_classes(root, before, pools), selection_classes(root, after, pools)
    return [dict(profile=key[0], backend=key[1], model=key[2], effort=key[3], pool=key[4], before=old[key],
                 after=new[key]) for key in old if key in new and old[key] != new[key]]


def seated_tiers(catalog, policy):
    """Each (model, effort, pool) a stable route seats, by the definition validation ranks."""
    import routing_profiles as routes

    by_pool = {row["provider"]: row for row in policy.get("pool", [])}
    seated = routes._seated_tiers(stores.project_profiles(catalog, policy), by_pool)
    return {(model, effort, pool) for (model, effort), pools in seated.items() for pool in pools}


def pool_order(policy, pool):
    """The pool's seat_rank rows, lowest rank first."""
    import routing_profiles as routes

    def effort(row):
        return routes.EFFORT_ORDER.index(row["effort"]) if row["effort"] in routes.EFFORT_ORDER else -1
    return sorted((row for row in policy.get("seat_rank", []) if row["pool"] == pool),
                  key=lambda row: (row["rank"], row["model"], effort(row)))


def pool_placement(policy, previous, model, effort, pool):
    """Where a seat's tier sits in its pool's order: its current rank, or the rank suggested for it and why.

    A seat moved within one pool keeps the place its previous tier held, so
    a directed selection compares with it as it compared with the seat
    before; any other seat starts at the bottom, rank 1, where it outranks
    nothing. Either is then kept inside the model's own order on that pool,
    which never falls as effort rises.
    """
    import routing_profiles as routes

    ranks = {(row["model"], row["effort"], row["pool"]): row["rank"] for row in policy.get("seat_rank", [])}
    if (model, effort, pool) in ranks:
        return dict(current=ranks[model, effort, pool], suggested=ranks[model, effort, pool], basis="its current rank")
    rank, basis = 1, "starts at the bottom of the pool, outranking nothing"
    if previous and previous.get("stability") == "stable" and previous.get("provider") == pool \
            and (previous["model"], previous["effort"], pool) in ranks:
        rank = ranks[previous["model"], previous["effort"], pool]
        basis = f"keeps the place {previous['model']} {previous['effort']} held"
    order = routes.EFFORT_ORDER
    if effort in order:
        lower = [value for (m, e, p), value in ranks.items()
                 if (m, p) == (model, pool) and e in order and order.index(e) < order.index(effort)]
        higher = [value for (m, e, p), value in ranks.items()
                  if (m, p) == (model, pool) and e in order and order.index(e) > order.index(effort)]
        if lower and rank < max(lower):
            rank, basis = max(lower), f"is raised to {model}'s lower efforts there, since rank never falls as effort rises"
        if higher and rank > min(higher):
            rank, basis = min(higher), f"is lowered to {model}'s higher efforts there, since rank never falls as effort rises"
    return dict(current=None, suggested=rank, basis=basis)


def settle_pool_ranks(catalog, policy, verb, opts, seated_before, previous):
    """Rank the tier a seat edit newly seats, and drop each rank the edit leaves on a tier no stable route seats."""
    after = seated_tiers(catalog, policy)
    ranked = {(row["model"], row["effort"], row["pool"]): row for row in policy.get("seat_rank", [])}
    rank = opts.get("pool_rank")
    if verb == "set-seat":
        seat = require_one(policy["seat"], f"{stores.POLICY} [[seat]]", profile=opts["profile"],
                           variant=opts.get("variant"))
        tier = (seat["model"], seat["effort"], seat["provider"])
        where = f"{stores.POLICY} {stores.label('seat', seat)}"
        if tier not in after:
            if rank is not None:
                raise stores.StoreError(f"{where}: --pool-rank orders the tier a stable seat holds within its pool, "
                                        f"and this seat holds none on {tier[2]!r}")
        elif tier in ranked:
            if rank is not None:
                ranked[tier]["rank"] = rank
        elif rank is None:
            order = ", ".join(f"{row['model']} {row['effort']} {row['rank']}" for row in pool_order(policy, tier[2]))
            placement = pool_placement(policy, previous, *tier)
            raise stores.StoreError(
                f"{where}: {tier[0]} {tier[1]} has no pool rank on {tier[2]!r}; pass --pool-rank N to place it in "
                f"that pool's order ({order or 'nothing ranked yet'}); --pool-rank {placement['suggested']} "
                f"{placement['basis']}")
        else:
            policy.setdefault("seat_rank", []).append(dict(model=tier[0], effort=tier[1], pool=tier[2], rank=rank))
    stranded = seated_before - after
    if stranded:
        policy["seat_rank"] = [row for row in policy.get("seat_rank", [])
                               if (row["model"], row["effort"], row["pool"]) not in stranded]


def change_rows(catalog, policy, verb, opts, today):
    """Mutate a private candidate, then keep pool ranks on exactly the tiers stable seats hold."""
    seated = seated_tiers(catalog, policy)
    previous = None
    if verb == "set-seat":
        previous = copy.deepcopy(next((row for row in policy.get("seat", []) if row["profile"] == opts["profile"]
                                       and row.get("variant") == opts.get("variant")), None))
    edit_rows(catalog, policy, verb, opts, today)
    settle_pool_ranks(catalog, policy, verb, opts, seated, previous)


def edit_rows(catalog, policy, verb, opts, today):
    """Mutate a private candidate; row keys are explicit and never inferred from prose."""
    why = opts["why"]
    if verb in {"set-seat", "remove-seat", "default-seat"}:
        rows = policy.setdefault("seat", [])
        key = {"profile": opts["profile"], "variant": opts.get("variant")}
        found = [row for row in rows if all(row.get(k) == v for k, v in key.items())]
        if verb == "set-seat":
            model, effort = opts["model"], opts["effort"]
            backends = opts["backend"]
            provider = opts.get("provider")
            if provider is None:
                common = set.intersection(*[{row["provider"] for row in catalog.get("reach", [])
                                             if row["model"] == model and row["backend"] == backend}
                                            for backend in backends])
                if len(common) != 1:
                    raise stores.StoreError(f"{stores.POLICY} {stores.label('seat', key)}: --provider is required "
                                            "when reach does not name one common provider")
                provider = common.pop()
            row = found[0] if found else {k: v for k, v in key.items() if v is not None}
            row.update(backends=backends, provider=provider, model=model, effort=effort,
                       stability=opts.get("stability") or row.get("stability", "stable"),
                       when=opts["when"], why=why, since=today)
            if not found:
                rows.append(row)
        elif verb == "remove-seat":
            rows.remove(require_one(rows, f"{stores.POLICY} [[seat]]", **key))
        else:
            if not opts.get("variant"):
                raise stores.StoreError("default-seat requires --variant")
            target = require_one(rows, f"{stores.POLICY} [[seat]]", **key)
            backends = set(target["backends"])
            requested = set(opts.get("backend") or target["backends"])
            if requested != backends:
                raise stores.StoreError(f"{stores.POLICY} {stores.label('seat', target)}: a multi-backend seat "
                                        "defaults as a whole; name all its backends")
            for row in list(rows):
                if row["profile"] != opts["profile"] or row is target:
                    continue
                if not backends.intersection(row["backends"]):
                    continue
                if row.get("variant") is None:
                    moved = sorted(backends.intersection(row["backends"]))
                    variant = "primary-" + "-".join(moved)
                    if any(other.get("variant") == variant and other["profile"] == opts["profile"] for other in rows):
                        raise stores.StoreError(f"{stores.POLICY} [[seat]] profile={opts['profile']}: "
                                                f"variant {variant!r} already exists; rename it by hand first")
                    retained = dict(copy.deepcopy(row), variant=variant, backends=moved)
                    row["backends"] = [backend for backend in row["backends"] if backend not in backends]
                    if row["backends"]:
                        rows.append(retained)
                    else:
                        row.update(retained)
                elif row.get("default"):
                    if set(row["backends"]) - backends:
                        raise stores.StoreError(f"{stores.POLICY} {stores.label('seat', row)}: split the "
                                                "overlapping multi-backend default by hand first")
                    row.pop("default")
            target.update(default=True, why=why, since=today)
    elif verb in {"prohibit", "allow", "rank"}:
        row = require_one(catalog.get("tier", []), f"{stores.CATALOG} [[tier]]",
                          model=opts["model"], effort=opts["effort"])
        if verb == "prohibit":
            row.update(prohibited=True, reason=opts.get("reason") or why)
        elif verb == "allow":
            row.pop("prohibited", None)
            row.pop("reason", None)
        else:
            row.update(rank=opts["rank"], floor=opts["floor"])
    elif verb == "pool-rank":
        where = f"{stores.POLICY} [[seat_rank]] model={opts['model']} effort={opts['effort']} pool={opts['pool']}"
        found = [row for row in policy.get("seat_rank", [])
                 if (row["model"], row["effort"], row["pool"]) == (opts["model"], opts["effort"], opts["pool"])]
        if not found:
            raise stores.StoreError(f"{where}: no such pool rank; a tier gains one with the set-seat --pool-rank "
                                    "edit that seats it")
        found[0]["rank"] = opts["rank"]
    elif verb in {"set-fallback", "remove-fallback"}:
        rows = policy.setdefault("fallback", [])
        key = {k: opts[k] for k in ("profile", "from_provider", "backend")}
        found = [row for row in rows if all(row.get(k) == v for k, v in key.items())]
        if verb == "remove-fallback":
            rows.remove(require_one(rows, f"{stores.POLICY} [[fallback]]", **key))
        else:
            row = found[0] if found else dict(key)
            row.pop("variant", None)
            if opts.get("variant"):
                row["variant"] = opts["variant"]
            if not found:
                rows.append(row)
    elif verb in {"set-review-seat", "remove-review-seat"}:
        rows = policy.setdefault("review_seat", [])
        key = {k: opts[k] for k in ("purpose", "author_family", "backend")}
        if verb == "remove-review-seat":
            rows.remove(require_one(rows, f"{stores.POLICY} [[review_seat]]", **key))
        else:
            found = [row for row in rows if all(row.get(k) == v for k, v in key.items())]
            row = found[0] if found else dict(key)
            row.update(model=opts["model"], effort=opts["effort"], when=opts["when"], why=why, since=today)
            if not found:
                rows.append(row)
    elif verb in {"set-guard", "retire-guard"}:
        rows = policy.setdefault("guard", [])
        key = {k: opts.get(k) for k in ("model", "effort", "profile")}
        if verb == "retire-guard":
            rows.remove(require_one(rows, f"{stores.POLICY} [[guard]]", **key))
        else:
            found = [row for row in rows if all(row.get(k) == v for k, v in key.items())]
            if len(found) > 1:
                raise stores.StoreError(f"{stores.POLICY} [[guard]] {key}: ambiguous scope; edit by hand")
            row = found[0] if found else {k: v for k, v in key.items() if v is not None}
            row.update(rule=opts["rule"], why=why, since=today)
            if opts.get("because"):
                row["because"] = list(dict.fromkeys([*row.get("because", []), *opts["because"]]))
            if not found:
                rows.append(row)
    elif verb == "add-model":
        model = opts["model"]
        if any(row["id"] == model for row in catalog.get("model", [])):
            raise stores.StoreError(f"{stores.CATALOG} [[model]] id={model}: already exists")
        catalog.setdefault("model", []).append({"id": model, "family": opts["family"]})
        if not opts.get("tier") or not opts.get("reach"):
            raise stores.StoreError(f"{stores.CATALOG} [[model]] id={model}: at least one tier and reach are required")
        for table in ("tier", "reach"):
            if not isinstance(opts[table], list) or not all(isinstance(row, dict) and "model" not in row
                                                          for row in opts[table]):
                raise stores.StoreError(f"{stores.CATALOG} [[{table}]] model={model}: supply row objects without model")
        catalog.setdefault("tier", []).extend(dict(model=model, **row) for row in opts["tier"])
        catalog.setdefault("reach", []).extend(dict(model=model, **row) for row in opts["reach"])
    elif verb == "supersede-model":
        row = require_one(catalog.get("model", []), f"{stores.CATALOG} [[model]]", id=opts["model"])
        row.update(status="superseded", successor=opts["successor"])
    else:
        raise stores.StoreError(f"unknown edit verb {verb!r}")


def add_note(records, opts, today):
    note = {k: opts[k] for k in ("model", "effort", "kind", "areas", "claim", "cause", "evidence", "metrics")
            if opts.get(k) is not None}
    note.update(id=field_notes.next_id(records), date=opts.get("date") or today)
    records.append(note)
    return note


def change_notes(records, verb, opts, today):
    if verb == "note":
        return add_note(records, opts, today)["id"]
    target = opts["note"]
    if verb != "undo":
        require_one([row for row in field_notes.project(records) if row["live"]], stores.NOTES, id=target)
    event = {"date": opts.get("date") or today, "event": verb, "note": target}
    if verb == "again":
        event["evidence"] = opts["evidence"]
    else:
        event["reason"] = opts["reason"]
    if verb == "supersede":
        old = require_one(records, stores.NOTES, id=target)
        corrected = {**old, **{key: value for key, value in opts.items() if value is not None
                               and (key in old or key in ("effort", "metrics"))}, "date": opts.get("date") or today}
        corrected.update(claim=opts["claim"], evidence=opts["evidence"])
        event["replacement"] = add_note(records, corrected, today)["id"]
    event["id"] = field_notes.next_id(records)
    records.append(event)
    return event["id"]


def canonical(texts):
    return {stores.CATALOG: stores.emit_catalog(stores.parse_toml(texts[stores.CATALOG], stores.CATALOG)),
            stores.POLICY: stores.emit_policy(stores.parse_toml(texts[stores.POLICY], stores.POLICY)),
            stores.NOTES: stores.emit_notes(stores.parse_notes(texts[stores.NOTES]))}


def row_changes(before, after):
    result = []
    for name in PATHS:
        if before[name] == after[name]:
            continue
        if name == stores.NOTES:
            old, new = stores.parse_notes(before[name]), stores.parse_notes(after[name])
            for row in new[len(old):]:
                result.append(dict(store=name, table="event" if "event" in row else "note", before=None, after=row))
            continue
        a, b = stores.parse_toml(before[name], name), stores.parse_toml(after[name], name)
        for table in dict.fromkeys([*a, *b]):
            if a.get(table) == b.get(table):
                continue
            old, new = a.get(table, []), b.get(table, [])
            if not isinstance(old, list) or not isinstance(new, list):
                result.append(dict(store=name, table=table, before=old, after=new))
                continue
            removed = [row for row in old if row not in new]
            added = [row for row in new if row not in old]
            # A row that changed keeps its identity; rows with different identities are a removal and an addition.
            for row in removed:
                twin = next((other for other in added if stores.label(table, other) == stores.label(table, row)), None)
                if twin is not None:
                    added.remove(twin)
                result.append(dict(store=name, table=table, before=row, after=twin))
            result += [dict(store=name, table=table, before=None, after=row) for row in added]
    return result


def stale_consumers(before, after, root):
    def inputs(texts, backend, profile=None):
        catalog = stores.parse_toml(texts[stores.CATALOG], stores.CATALOG)
        policy = stores.parse_toml(texts[stores.POLICY], stores.POLICY)
        seats = [{key: value for key, value in row.items() if key not in {"when", "why", "since"}}
                 for row in policy.get("seat", []) if backend in row["backends"]
                 and (profile is None or row["profile"] == profile)]
        models = {row["model"] for row in seats}
        return (seats, [row for row in catalog.get("reach", []) if row["model"] in models and row["backend"] == backend],
                [row for row in policy.get("profile", []) if row["id"] in {seat["profile"] for seat in seats}])
    policy = stores.parse_toml(after[stores.POLICY], stores.POLICY)
    repositories = {row["id"]: row["name"] for row in policy.get("repository", [])}
    stale = []
    for row in policy.get("consumer", []):
        if row.get("generated") == "claude-agents" and inputs(before, "claude") != inputs(after, "claude"):
            common = pathlib.Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())
            code_root = pathlib.Path(os.environ.get("AGENT_CODE_ROOT") or common.parent.parent)
            target = str(code_root / repositories[row["repository"]] / row["path"])
            staging = str(pathlib.Path(target).parent)
            stale.append(dict(consumer=row["id"], path=target,
                              refresh=f"agent-routing emit claude-agents --output-dir {shlex.quote(staging)}"))
    interactive_changed = any(inputs(before, backend, "interactive") != inputs(after, backend, "interactive")
                              for backend in {row["id"] for row in stores.parse_toml(after[stores.CATALOG], stores.CATALOG).get("backend", [])})
    if interactive_changed and any(row.get("command", [None])[0] == "agent-harness" for row in policy.get("accessor", [])):
        stale.append(dict(consumer="harness-settings", path="interactive route settings",
                          refresh="agent-harness build"))
    return stale


def attribution(root):
    try:
        run = subprocess.run(["arc", "env"], cwd=root, capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if run.returncode:
        return None
    harness = re.search(r"(?:^|\s)ARC_HARNESS=([^\s]+)", run.stdout)
    model = re.search(r"^# model: (\S+)$", run.stdout, re.M)
    if harness and model:
        acting = shlex.split(harness[1])
        if acting and re.fullmatch(r"[\w.-]+", acting[0]) and re.fullmatch(r"[\w./:-]+(?:#[\w.-]+)?", model[1]):
            return f"{acting[0]}:{model[1]}"
    return None


def atomic_write(path, text):
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, "wb") as output:
            output.write(text.encode())
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def history(root, limit=20):
    raw = git(root, "log", f"-{limit}", "--format=%H%x00%cs%x00%s%x00%B%x00", "--", *PATHS).decode()
    fields = raw.split("\0")
    return [{"commit": fields[i].strip(), "date": fields[i + 1], "subject": fields[i + 2], "body": fields[i + 3].strip()}
            for i in range(0, len(fields) - 3, 4)]


def merge_revert(current, edited, previous, name):
    """Merge a reverse edit into later, disjoint hand edits without changing their bytes."""
    base, ours, theirs = edited.splitlines(keepends=True), current.splitlines(keepends=True), previous.splitlines(keepends=True)
    def changes(other):
        return [(i, j, other[k:l]) for tag, i, j, k, l in difflib.SequenceMatcher(None, base, other, autojunk=False).get_opcodes()
                if tag != "equal"]
    own, inverse = changes(ours), changes(theirs)
    for a, b, replacement in inverse:
        for c, d, other in own:
            if max(a, c) < min(b, d) or a == c or (a == b and c <= a < d) or (c == d and a <= c < b):
                raise stores.StoreError(f"{name}: undo conflicts with a later store edit")
    for start, end, replacement in sorted([*own, *inverse], key=lambda row: (row[0], row[1]), reverse=True):
        base[start:end] = replacement
    return "".join(base)


def undo_candidate(root, before, opts, today):
    records = history(root, limit=1000000)
    latest = next((row for row in records if re.search(rf"^{TRAILER}: \S+",
                                                       row["body"].rsplit("\n\n", 1)[-1], re.M)), None)
    if latest is None:
        raise stores.StoreError("no edit made by a routing verb to undo")
    commit = latest["commit"]
    if opts.get("target"):
        named = git(root, "rev-parse", "--verify", "--end-of-options", f"{opts['target']}^{{commit}}").decode().strip()
        if named != commit:
            raise StaleState(f"the latest verb edit is {commit[:12]}, not {named[:12]}; preview the undo again")
    after_edit = {name: git(root, "show", f"{commit}:{name}").decode() for name in PATHS}
    previous = {name: git(root, "show", f"{commit}^:{name}").decode() for name in PATHS}
    candidate = dict(before)
    for name in (stores.CATALOG, stores.POLICY):
        if after_edit[name] != previous[name]:
            candidate[name] = merge_revert(before[name], after_edit[name], previous[name], name)
    if previous[stores.NOTES] != after_edit[stores.NOTES]:
        prefix = previous[stores.NOTES]
        if not after_edit[stores.NOTES].startswith(prefix):
            raise stores.StoreError(f"{stores.NOTES}: historical edit rewrites append-only evidence")
        notes = stores.parse_notes(before[stores.NOTES])
        for row in reversed(stores.parse_notes(after_edit[stores.NOTES][len(prefix):])):
            change_notes(notes, "undo", dict(note=row["id"], reason=opts["why"]), today)
        candidate[stores.NOTES] = stores.emit_notes(notes)
    return candidate, commit


def apply(root, verb, **opts):
    root = pathlib.Path(root).resolve()
    dry = opts.get("dry_run", False)
    note_verb = verb in {"note", "again", "retract", "supersede"}
    if not note_verb:
        opts["why"] = why_text(opts.get("why"))
    today = edit_date(opts.get("date"))
    expect = opts.pop("expect", None)
    # One lock hold covers the state read, its check against `expect`, the
    # candidate and, unless this is a dry run, the write and the commit.
    with stores.store_lock(root, exclusive=not dry):
        if git(root, "rev-parse", "--show-toplevel").decode().strip() != str(root):
            raise stores.StoreError("edit root must be the Git checkout root")
        before = read_texts(root)
        observed = state(root, before)
        if expect is not None and expect != observed:
            raise StaleState("the stores or their edit history moved since the preview; preview the edit again")
        dirty = git(root, "status", "--porcelain", "--untracked-files=all", "--", *PATHS)
        if dirty and verb != "commit":
            raise stores.StoreError("data paths have uncommitted changes; use `agent-routing commit --why TEXT` or discard them")
        candidate = dict(before)
        because = list(dict.fromkeys(opts.get("because") or []))
        records = stores.parse_notes(before[stores.NOTES])
        ids = {row["id"] for row in records if "event" not in row}
        missing = set(because) - ids
        if missing:
            raise stores.StoreError(f"{stores.NOTES}: --because names no note: {', '.join(sorted(missing))}")
        extra = {}
        if verb == "undo":
            candidate, extra["undone_commit"] = undo_candidate(root, before, opts, today)
        elif note_verb:
            checked(before)
            extra["record_id"] = change_notes(records, verb, opts, today)
            candidate[stores.NOTES] = stores.emit_notes(records)
        elif verb != "commit":
            checked(before)
            catalog = stores.parse_toml(before[stores.CATALOG], stores.CATALOG)
            policy = stores.parse_toml(before[stores.POLICY], stores.POLICY)
            change_rows(catalog, policy, verb, opts, today)
            shape = (stores.shape_problems(catalog, stores.CATALOG_TABLES, stores.CATALOG)
                     + stores.shape_problems(policy, stores.POLICY_TABLES, stores.POLICY, stores.POLICY_SETTINGS))
            if shape:
                raise stores.StoreError("\n".join(shape))
            candidate.update({stores.CATALOG: stores.emit_catalog(catalog), stores.POLICY: stores.emit_policy(policy)})
        # Validate raw shapes before emission, so every malformed row has its store label.
        checked(candidate)
        if verb != "undo":
            baseline = ({name: git(root, "show", f"HEAD:{name}").decode() for name in PATHS}
                        if verb == "commit" else before)
            missing = default_problems(baseline, candidate)
            if missing:
                raise stores.StoreError("\n".join(missing))
        candidate = canonical(candidate)
        checked(candidate)
        committed = {name: git(root, "show", f"HEAD:{name}").decode() for name in PATHS}
        growth = field_notes.grows_only(committed[stores.NOTES].encode(), candidate[stores.NOTES].encode())
        if growth:
            raise stores.StoreError("\n".join(growth))
        if verb != "commit" and field_notes.grows_only(before[stores.NOTES].encode(), candidate[stores.NOTES].encode()):
            raise stores.StoreError(f"{stores.NOTES}: existing lines must be canonical; commit hand edits first")
        comparison = committed if verb == "commit" else before
        changes = row_changes(comparison, candidate)
        paths = [name for name in PATHS if committed[name] != candidate[name]]
        if not paths:
            raise stores.StoreError("edit makes no change")
        result = dict(schema="agent-routing-edit/1", verb=verb, dry_run=dry, state=observed, changes=changes,
                      old_route_version=stores.route_version(comparison), new_route_version=stores.route_version(candidate),
                      stale_consumers=stale_consumers(comparison, candidate, root), commit=None, **extra)
        if verb != "commit":
            result["date"] = today
        reclassified = classification_changes(root, comparison, candidate, changes)
        if reclassified is not None:
            result["classification_changes"] = reclassified
        if any(row["table"] == "tier" and row["before"] and row["after"]
               and any(row["before"].get(key) != row["after"].get(key) for key in ("rank", "floor")) for row in changes):
            result["notice"] = "Rank changes move Arc assurance at once; clearance changes when Arc next imports the ladder."
        if dry:
            return result
        subject = subject_for(verb, opts, result)
        reason = opts.get("why") or opts.get("reason") or opts.get("claim") or f"Record {verb} for {opts.get('note')}."
        body = subject + "\n\n" + reason + "\n"
        if because:
            body += "\nBecause: " + ", ".join(because) + "\n"
        body += f"\n{TRAILER}: {verb}\n"
        identity = attribution(root)
        if identity:
            body += f"Implemented-by: {identity}\n"
        if "\\n" in body:
            raise stores.StoreError("commit message contains literal \\n; use plain sentences")
        written = []
        try:
            for name in PATHS:
                if before[name] != candidate[name]:
                    atomic_write(root / name, candidate[name])
                    written.append(name)
            git(root, "commit", "--quiet", "--only", "--file=-", "--", *paths, input=body.encode())
        except Exception:
            for name in reversed(written):
                atomic_write(root / name, before[name])
            raise
        result["commit"] = git(root, "rev-parse", "HEAD").decode().strip()
        message = git(root, "log", "-1", "--format=%B").decode()
        if "\\n" in message:
            raise stores.StoreError("commit message contains literal \\n; repair the message before continuing")
        return result


def subject_for(verb, opts, result):
    target = opts.get("profile") or opts.get("model") or opts.get("note") or result.get("record_id") or "data stores"
    suffix = f" {opts['variant']}" if opts.get("variant") else ""
    if verb in {"prohibit", "allow", "rank", "pool-rank"}:
        suffix += f" {opts['effort']}"
    if verb == "pool-rank":
        suffix += f" on {opts['pool']}"
    action = {"note": "record note for", "again": "record recurrence of", "retract": "retract note",
              "supersede": "correct note", "rank": "set rank and floor for", "default-seat": "default seat for",
              "pool-rank": "set pool rank for"}
    if verb == "commit":
        return "data: commit hand edits to routing stores"
    if verb in {"set-review-seat", "remove-review-seat"}:
        return (f"data: {verb.split('-')[0]} {opts['purpose']} review seat for {opts['author_family']} "
                f"on {opts['backend']}")
    if verb == "undo":
        return f"data: undo routing edit {result['undone_commit'][:12]}"
    return f"data: {action.get(verb, verb.replace('-', ' '))} {target}{suffix}"


def render(result, *, width=None, data=None, root=None):
    """Readable text with optional catalog context; the result's JSON shape is unchanged."""
    from text_output import render as readable

    return readable(result, width=width, data=data, root=root)


def notes_history_problems(root, base, head="HEAD"):
    """Check every notes-changing revision, including an edit later hidden by a restoration."""
    commits = git(root, "rev-list", "--reverse", "--full-history", f"{base}..{head}", "--", stores.NOTES).decode().split()
    errors = []
    def at(ref):
        run = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{stores.NOTES}"], capture_output=True)
        if run.returncode and not git(root, "ls-tree", ref, "--", stores.NOTES):
            return b""
        if run.returncode:
            raise stores.StoreError(run.stderr.decode().strip())
        return run.stdout
    errors += field_notes.grows_only(at(base), at(head))
    for commit in commits:
        parents = git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()[1:]
        for parent in parents:
            errors += [f"{commit[:12]}: {error}" for error in field_notes.grows_only(at(parent), at(commit))]
    return errors
