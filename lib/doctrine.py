"""Readable views rendered from the stores: the doctrine and the delegation facts."""

from __future__ import annotations

import collections
import pathlib

import stores

PRINCIPLES = "doctrine/principles.md"


def _valid(root: pathlib.Path) -> stores.Data:
    data = stores.load(root)
    if data.problems:
        raise stores.StoreError("; ".join(data.problems))
    return data


def _cell(value) -> str:
    return str(value).replace("|", "\\|") if value not in (None, "") else "—"


def _table(header: tuple[str, ...], rows: list[tuple]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(":---" for _ in header) + " |"]
    lines += ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return lines


def render(root: pathlib.Path) -> str:
    """The principles, then every profile with its seats, the bans, the pools and the catalog."""
    root = pathlib.Path(root)
    data = _valid(root)
    policy, catalog = data.policy, data.catalog
    lines = [(root / PRINCIPLES).read_text().rstrip(), ""]
    lines += ["## Profiles and seats", "",
              f"Rendered from `{stores.POLICY}` at route version {data.version}. A seat without a variant answers "
              "an unnamed request on its backends; a variant marked default answers one on a backend the profile's "
              "own seats do not serve.", ""]
    for profile in policy.get("profile", []):
        lines += [f"### {profile['id']}", "", profile["purpose"] + ".", ""]
        if profile.get("escalation_sources"):
            lines += [f"Directed selections may borrow the stable seats of: {', '.join(profile['escalation_sources'])}.", ""]
        seats = [seat for seat in policy.get("seat", []) if seat["profile"] == profile["id"]]
        lines += _table(("variant", "backends", "model · effort", "stability", "when", "why", "since"), [
            (seat.get("variant", "") + (" (default)" if seat.get("default") else ""), ", ".join(seat["backends"]),
             f"{seat['model']} · {seat['effort']}", seat["stability"], seat["when"], seat["why"], seat["since"])
            for seat in seats])
        fallbacks = [rule for rule in policy.get("fallback", []) if rule["profile"] == profile["id"]]
        if fallbacks:
            lines += ["", "When the selected pool is exhausted: " + "; ".join(
                f"from {rule['from_provider']} to {rule['backend']}" + (f" --variant {rule['variant']}"
                                                                         if rule.get("variant") else "")
                for rule in fallbacks) + "."]
        lines.append("")
    banned = [tier for tier in catalog.get("tier", []) if tier.get("prohibited")]
    lines += ["## Prohibited tiers", "", "Never selected, including on explicit request.", ""]
    lines += _table(("model · effort", "reason"), [(f"{tier['model']} · {tier['effort']}", tier["reason"])
                                                   for tier in banned])
    fences = policy.get("fence", [])
    exceptions = policy.get("family_exception", [])
    if fences or exceptions:
        lines += ["", "## Fences and family exceptions", ""]
        lines += [f"- {fence['model']} never serves `{fence['profile']}`: {fence['why']} ({fence['since']})"
                  for fence in fences]
        lines += [f"- {row['reviewer']} may clear {', '.join(row['authors'])} despite the shared family: "
                  f"{row['why']} ({row['since']})" for row in exceptions]
    lines += ["", "## Pools", ""]
    lines += _table(("provider", "plan", "serves", "scarcer than", "why"), [
        (pool["provider"], pool["plan"], ", ".join(pool["serves"]), ", ".join(pool.get("scarcer_than", [])),
         pool["why"]) for pool in data.pools])
    lines += ["", f"Review clearance needs rank {policy['review']['clearance']} or above.", "",
              "## Catalog", "",
              "Rank is reviewer strength and floor the least reviewer rank authored work needs, on one "
              "cross-family scale: 1 bounded work, 2 a working technical peer, 3 the top review band.", ""]
    notes = collections.Counter(note.get("model") for note in stores.load_notes(root))
    rows = []
    for model in data.models:
        tiers = ", ".join(f"{tier['effort']} {tier['rank']}/{tier['floor']}"
                          + (f" {tier['status']}" if tier.get("status") else "")
                          + (" banned" if tier.get("prohibited") else "") for tier in model["effort"])
        price = model.get("api_price_per_million", {})
        cost = " / ".join(f"{price[key]:g}" for key in ("input", "cache_miss_input", "output") if key in price)
        rows.append((model["id"], model["family"], model.get("status", "active"), tiers, cost, notes.get(model["id"], 0)))
    lines += _table(("model", "lineage", "status", "effort rank/floor", "API $ in / out per M", "notes"), rows)
    lines += ["", f"Field notes live in `{stores.NOTES}`; no routing decision reads them."]
    return "\n".join(lines) + "\n"


def delegation(root: pathlib.Path) -> str:
    """The backend, reachability and pool rows, in the stores' own canonical form."""
    data = _valid(pathlib.Path(root))
    catalog = {name: data.catalog.get(name, []) for name in ("backend", "reach", "effort_support")}
    blocks = [stores._row(name, stores.CATALOG_TABLES[name], row)
              for name in ("backend", "reach", "effort_support") for row in catalog[name]]
    blocks += [stores._row("pool", stores.POLICY_TABLES["pool"], row) for row in data.pools]
    return (f"# Backends and reachability from {stores.CATALOG}; pools from {stores.POLICY}.\n\n"
            + "\n".join(blocks))
