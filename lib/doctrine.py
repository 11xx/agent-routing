"""Readable views rendered from the stores: the doctrine and the delegation facts."""

from __future__ import annotations

import collections
import pathlib

import stores

PRINCIPLES = "doctrine/principles.md"


def _valid(root: pathlib.Path, *, standing: bool) -> stores.Data:
    data = stores.load(root)
    problems = list(data.problems) or (stores.standing_problems(root, data) if standing else [])
    if problems:
        raise stores.StoreError("; ".join(problems))
    return data


def _cell(value) -> str:
    return str(value).replace("|", "\\|") if value not in (None, "") else "—"


def _table(header: tuple[str, ...], rows: list[tuple]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(":---" for _ in header) + " |"]
    lines += ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return lines


def _scopes(guard: dict, seat: dict) -> bool:
    return guard["model"] == seat["model"] and guard.get("effort", seat["effort"]) == seat["effort"]


def _guard_line(guard: dict) -> str:
    scope = guard["model"] + (f" · {guard['effort']}" if "effort" in guard else "") + (
        f" on `{guard['profile']}`" if "profile" in guard else "")
    because = f"; notes {', '.join(guard['because'])}" if guard.get("because") else ""
    return f"- **{scope}:** {guard['rule']} {guard['why']} ({guard['since']}{because})"


def render(root: pathlib.Path) -> str:
    """The principles, then every profile with its seats, the bans, the pools and the catalog."""
    root = pathlib.Path(root)
    data = _valid(root, standing=True)
    policy, catalog = data.policy, data.catalog
    lines = [(root / PRINCIPLES).read_text().rstrip(), ""]
    lines += ["## Profiles and seats", "",
              f"Rendered from `{stores.POLICY}` at route version {data.version}. A seat without a variant answers "
              "an unnamed request on its backends; a variant marked default answers one on a backend the profile's "
              "own seats do not serve. A guard is a standing instruction for using a tier: leads follow it, and "
              "no verb that selects, validates or refuses a route reads it.", ""]
    guards = policy.get("guard", [])
    shown: set[int] = set()
    for profile in policy.get("profile", []):
        lines += [f"### {profile['id']}", "", profile["purpose"] + ".", ""]
        if profile.get("escalation_sources"):
            lines += [f"Directed selections may borrow the stable seats of: {', '.join(profile['escalation_sources'])}.", ""]
        seats = [seat for seat in policy.get("seat", []) if seat["profile"] == profile["id"]]
        lines += _table(("variant", "backends", "model · effort", "stability", "when", "why", "since"), [
            (seat.get("variant", "") + (" (default)" if seat.get("default") else ""), ", ".join(seat["backends"]),
             f"{seat['model']} · {seat['effort']}", seat["stability"], seat["when"], seat["why"], seat["since"])
            for seat in seats])
        scoped = [(number, guard) for number, guard in enumerate(guards)
                  if guard.get("profile", profile["id"]) == profile["id"]
                  and any(_scopes(guard, seat) for seat in seats)]
        if scoped:
            lines += ["", "Guards on these seats:", ""] + [_guard_line(guard) for _, guard in scoped]
            shown.update(number for number, _ in scoped)
        fallbacks = [rule for rule in policy.get("fallback", []) if rule["profile"] == profile["id"]]
        if fallbacks:
            lines += ["", "When the selected pool is exhausted: " + "; ".join(
                f"from {rule['from_provider']} to {rule['backend']}" + (f" --variant {rule['variant']}"
                                                                         if rule.get("variant") else "")
                for rule in fallbacks) + "."]
        lines.append("")
    unseated = [guard for number, guard in enumerate(guards) if number not in shown]
    if unseated:
        lines += ["## Guards on tiers no seat holds", "",
                  "Followed whenever one of these tiers is selected by name.", ""]
        lines += [_guard_line(guard) for guard in unseated] + [""]
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
    data = _valid(pathlib.Path(root), standing=False)
    catalog = {name: data.catalog.get(name, []) for name in ("backend", "reach", "effort_support")}
    blocks = [stores._row(name, stores.CATALOG_TABLES[name], row)
              for name in ("backend", "reach", "effort_support") for row in catalog[name]]
    blocks += [stores._row("pool", stores.POLICY_TABLES["pool"], row) for row in data.pools]
    return (f"# Backends and reachability from {stores.CATALOG}; pools from {stores.POLICY}.\n\n"
            + "\n".join(blocks))
