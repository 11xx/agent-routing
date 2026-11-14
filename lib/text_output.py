"""Readable terminal views of store results, separate from their JSON contracts."""

import os
import re
import subprocess
import sys
import textwrap


def terminal_width():
    try:
        return os.get_terminal_size(sys.stdout.fileno()).columns if sys.stdout.isatty() else 80
    except (AttributeError, OSError, ValueError):
        return 80


def wrapped(text, width, prefix="", indent=None):
    indent = " " * len(prefix) if indent is None else indent
    if len(prefix) >= width - 4:
        return (textwrap.wrap(prefix.strip(), width, initial_indent="  ", subsequent_indent="    ")
                + textwrap.wrap(str(text), width, initial_indent="    ", subsequent_indent="    ",
                                break_on_hyphens=False))
    return textwrap.wrap(str(text), width, initial_indent=prefix, subsequent_indent=indent,
                         break_on_hyphens=False) or [prefix.rstrip()]


def value(item):
    if item is None:
        return "(absent)"
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, list):
        return ", ".join(value(part) for part in item) or "none"
    if isinstance(item, dict):
        return "; ".join(f"{key}: {value(part)}" for key, part in item.items()) or "none"
    return str(item)


def row_name(table, row):
    if table == "seat":
        profile = row["profile"] + (f":{row['variant']}" if row.get("variant") else "")
        return f"seat {profile} (backends: {', '.join(row['backends'])})"
    if table in {"note", "event"}:
        return f"{table} {row.get('id', '')}" + (f" for {row['model']}" if row.get("model") else "")
    if table == "fallback":
        return f"fallback {row['profile']} from {row['from_provider']} on {row['backend']}"
    keys = {"guard": ("model", "effort", "profile"), "tier": ("model", "effort"),
            "reach": ("model", "backend", "provider")}.get(table, ("id", "model", "profile", "provider", "path"))
    return " ".join([table, *(str(row[key]) for key in keys if key in row)])


def note_lines(row, width, *, leading_model=False):
    dates = row["date"]
    if row["last_seen"] != row["date"]:
        dates += f" → {row['last_seen']}"
    coordinate = (f"{row['model']}" + (f" {row['effort']}" if row.get("effort") else "") + "  ") if leading_model else ""
    prefix = f"  {coordinate}{row['id']}  ×{row['occurrences']}  {dates}   "
    disposition = row.get("disposition", {})
    if not row["live"]:
        status = "retracted" if disposition["event"] == "retract" else "superseded"
        prefix = prefix.rstrip() + f" · {status}   "
    lines = wrapped(row["claim"], width, prefix)
    for evidence in row["evidence"]:
        dated = f"{evidence['date']} " if len(row["evidence"]) > 1 else ""
        lines += wrapped(dated + evidence["reference"], width, "    evidence: ")
    if disposition:
        detail = disposition["reason"]
        if disposition.get("replacement"):
            detail += f" (replacement {disposition['replacement']})"
        lines += wrapped(detail, width, "    reason: ")
    if row.get("metrics"):
        lines += wrapped(value(row["metrics"]), width, "    metrics: ")
    return lines


def section(lines, heading, entries):
    lines.append(heading)
    lines.extend(entries or ["  none"])


def card(result, width, data):
    model = result["model"]
    family = data.by_model()[model]["family"] if data is not None else None
    if data is not None:
        family = next((row["lab"] for row in data.families if family in row["values"]), family)
    lines = wrapped(model + (f" · {family}" if family else ""), width)
    seats = []
    for row in result["seats"]:
        name = row["profile"] + (f":{row['variant']}" if row.get("variant") else "")
        default = "default" if "variant" not in row or row.get("default") else ""
        description = (f"{row['stability']} · " if row["stability"] != "stable" else "") + row["when"]
        seats.append(([name, ", ".join(row["backends"]), row["effort"], default], description))
    widths = [max(len(columns[index]) for columns, _ in seats) for index in range(4)] if seats else []
    entries = []
    for columns, description in seats:
        prefix = "  " + "  ".join(item.ljust(size) for item, size in zip(columns, widths)) + "  "
        entries += wrapped(description, width, prefix)
    section(lines, "Seats", entries)
    section(lines, "Prohibited", [line for row in result["prohibited"]
                                 for line in wrapped(row["reason"], width, f"  {row['effort']}: ")])
    guards = []
    for row in result["guards"]:
        scope = ", ".join(row[key] for key in ("effort", "profile") if row.get(key))
        guards += wrapped((scope + ": " if scope else "") + row["rule"], width, "  · ", "    ")
        guards += wrapped(row["why"], width, "    why: ")
        metadata = "since " + row["since"]
        if row.get("because"):
            metadata += "   because " + ", ".join(row["because"])
        guards += wrapped(metadata, width, "    ")
    section(lines, "Guards", guards)
    for heading, kinds in (("Weaknesses", {"weakness"}), ("Strengths", {"strength"}),
                           ("Observations and measurements", {"observation", "measurement"})):
        section(lines, heading, [line for row in result["notes"] if row["kind"] in kinds
                                 for line in note_lines(row, width)])
    inherited = {}
    for row in result["inherited_unverified"]:
        inherited.setdefault(row["model"], []).append(row)
    if not inherited:
        section(lines, "Inherited, unverified for this model", [])
    for predecessor, rows in inherited.items():
        section(lines, f"Inherited from {predecessor}, unverified for this model",
                [line for row in rows for line in note_lines(row, width)])
    return lines


def edit(result, width):
    lines = [f"{result['verb']}{' (dry run)' if result['dry_run'] else ''}"]
    for change in result["changes"]:
        old, new = change["before"], change["after"]
        name = row_name(change["table"], new if new is not None else old)
        suffix = " removed" if new is None else " added" if old is None else ""
        lines += wrapped(f"{change['store']} {name}{suffix}", width, indent="  ")
        if new is None:
            continue
        for key in dict.fromkeys([*(old or {}), *new]):
            if old is not None and key in old and key in new and old[key] == new[key]:
                continue
            text = value(new.get(key)) if old is None else f"{value(old.get(key))} → {value(new.get(key))}"
            lines += wrapped(text, width, f"  {key}: ")
    lines += wrapped(f"route_version: {result['old_route_version']} -> {result['new_route_version']}", width, indent="  ")
    for row in result["stale_consumers"]:
        lines += wrapped(f"stale {row['consumer']} ({row['path']}): {row['refresh']}", width, indent="  ")
    if not result["stale_consumers"]:
        lines.append("stale consumers: none")
    for key in ("notice", "record_id", "undone_commit", "commit"):
        if result.get(key):
            lines += wrapped(str(result[key]), width, f"{key}: ")
    return lines


def history(root, edits):
    from data_edits import PATHS, git, row_changes

    lines = []
    for row in edits:
        commit = row["commit"]
        date = git(root, "show", "-s", "--format=%cs", commit).decode().strip()
        trailer = re.search(r"^Routing-edit: (\S+)$", row["body"].rsplit("\n\n", 1)[-1], re.M)
        verb = trailer[1] if trailer else "hand"
        changed = git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit, "--", *PATHS).decode().splitlines()
        before, after = {name: "" for name in PATHS}, {name: "" for name in PATHS}
        for name in changed:
            for revision, texts in ((commit, after), (f"{commit}^", before)):
                shown = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{name}"], capture_output=True)
                texts[name] = shown.stdout.decode() if shown.returncode == 0 else ""
        try:
            names = list(dict.fromkeys(row_name(change["table"], change["after"] or change["before"])
                                       for change in row_changes(before, after)))
        except (ValueError, TypeError, KeyError):
            names = changed
        names = [" ".join(name.split()) for name in names]
        body = row["body"].partition("\n\n")[2].split("\n\n", 1)[0].strip()
        reason = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)[0] or row["subject"]
        lines.append(f"{commit[:12]}  {date}  {verb}  {'; '.join(names) or 'stores'}  {' '.join(reason.split())}")
    return lines or ["none"]


def render(result, *, width=None, data=None, root=None):
    width = terminal_width() if width is None else width
    schema = result.get("schema")
    if schema == "agent-routing-card/1":
        lines = card(result, width, data)
    elif schema == "agent-routing-notes/1":
        lines = [line for row in result["notes"] for line in note_lines(row, width, leading_model=True)] or ["none"]
    elif schema == "agent-routing-history/1":
        lines = history(root, result["edits"])
    elif schema == "agent-routing-edit/1":
        lines = edit(result, width)
    else:
        lines = [f"{key}: {value(item)}" for key, item in result.items()]
    return "\n".join(lines)
