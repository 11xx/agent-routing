"""Export the roster's API list prices as a tapes price table.

agent-routing produces the file; tapes never reads this repository. Each
roster row's `api_price_per_million` becomes one `tapes-price-table/1` model,
keyed by the ids harnesses record for it, dated by its `api_price_read`, with
only the categories the row prices. A row whose prices have no read date is
left out and named.
"""

import datetime
import json
import math
import pathlib

from routing_profiles import load_toml, model_identities, route_version

SCHEMA = "tapes-price-table/1"
CURRENCY = "USD"

# Roster price keys and the tapes category each one prices. DeepSeek's rows
# use the provider's cache-miss/cache-hit names for the same two categories.
CATEGORY_KEYS = {
    "input": "uncached_input",
    "cache_miss_input": "uncached_input",
    "cached_input": "cache_read",
    "cache_hit_input": "cache_read",
    "cache_write": "cache_write_5m",
    "cache_write_1h": "cache_write_1h",
    "output": "output",
}
CATEGORIES = ("uncached_input", "cache_read", "cache_write_5m", "cache_write_1h", "output")


def _read_date(value: object) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def price_problems(models: list[dict]) -> list[str]:
    """Problems with the roster's API prices: unknown or doubled category
    keys, prices that are not finite non-negative numbers, and a price with
    neither a read date nor a stated reason it has none."""
    problems: list[str] = []
    for model in models:
        label = model.get("id", "<missing>")
        prices = model.get("api_price_per_million")
        dated = "api_price_read" in model
        undated = "api_price_undated" in model
        if prices is None:
            if dated or undated:
                problems.append(f"{label}: api_price_read or api_price_undated without api_price_per_million")
            continue
        if not isinstance(prices, dict):
            problems.append(f"{label}: api_price_per_million must be a table")
            continue
        seen: dict[str, str] = {}
        for key, value in prices.items():
            category = CATEGORY_KEYS.get(key)
            if category is None:
                problems.append(f"{label}: unknown api_price_per_million key {key!r}")
                continue
            if category in seen:
                problems.append(f"{label}: {seen[category]!r} and {key!r} price the same category")
            seen[category] = key
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                problems.append(f"{label}: api_price_per_million.{key} must be a finite number of at least zero")
        if dated == undated:
            problems.append(f"{label}: api_price_per_million needs api_price_read (YYYY-MM-DD) "
                            "or api_price_undated with the reason no date is known")
        elif dated and _read_date(model["api_price_read"]) is None:
            problems.append(f"{label}: api_price_read must be a YYYY-MM-DD date")
        elif undated and not (isinstance(model["api_price_undated"], str) and model["api_price_undated"].strip()):
            problems.append(f"{label}: api_price_undated must state why no read date is known")
    return problems


def price_export(root: pathlib.Path) -> dict:
    """The exportable rows, the rows left out and why, and which categories
    each exported row leaves unpriced."""
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    problems = price_problems(models)
    if problems:
        raise ValueError("; ".join(problems))
    version = route_version(root)
    exported, omitted, owners = [], [], {}
    for model in models:
        prices = model.get("api_price_per_million")
        if prices is None:
            continue
        if "api_price_undated" in model:
            omitted.append({"id": model["id"], "reason": model["api_price_undated"]})
            continue
        per_million = {CATEGORY_KEYS[key]: float(value) for key, value in prices.items()}
        names = [name for name in model_identities(root, model["id"]) if name != model["id"]]
        for name in [model["id"], *names]:
            if name in owners:
                raise ValueError(f"{model['id']}: {name!r} is already an id of {owners[name]}")
            owners[name] = model["id"]
        exported.append({
            "id": model["id"],
            "aliases": names,
            "effective": model["api_price_read"],
            "source": f"agent-routing routing/models.toml {model['id']} api_price_per_million, route version {version}",
            "per_million": {category: per_million[category] for category in CATEGORIES if category in per_million},
            "unpriced": [category for category in CATEGORIES if category not in per_million],
            "status": model.get("status"),
        })
    return {"schema": SCHEMA, "currency": CURRENCY, "route_version": version,
            "models": exported, "omitted": omitted}


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _number(value: float) -> str:
    return repr(float(value))


def tapes_table(export: dict) -> str:
    """The export as `tapes-price-table/1` TOML."""
    lines = [
        "# A tapes price table exported by `agent-routing prices --format tapes` from",
        f"# routing/models.toml at route version {export['route_version']}. Prices are API list",
        "# prices; a category a row does not price is left out.",
    ]
    for row in export["omitted"]:
        lines.append(f"# Not exported: {row['id']}: {row['reason']}")
    lines += ["", f"schema = {_string(export['schema'])}", f"currency = {_string(export['currency'])}"]
    for row in export["models"]:
        prices = ", ".join(f"{category} = {_number(price)}" for category, price in row["per_million"].items())
        lines += [
            "",
            "[[models]]",
            f"id = {_string(row['id'])}",
        ]
        if row["aliases"]:
            lines.append("aliases = [" + ", ".join(_string(name) for name in row["aliases"]) + "]")
        lines += [
            f"effective = {row['effective']}",
            f"source = {_string(row['source'])}",
            f"per_million = {{ {prices} }}",
        ]
    return "\n".join(lines) + "\n"


def readable_table(export: dict) -> str:
    """The same prices as a table for a reader."""
    header = ["model", "read", *CATEGORIES, "recorded ids"]
    rows = [header]
    for row in export["models"]:
        rows.append([
            row["id"],
            row["effective"],
            *(f"{row['per_million'][category]:g}" if category in row["per_million"] else "-" for category in CATEGORIES),
            ", ".join(row["aliases"]) or "-",
        ])
    out = ["\t".join(cells) for cells in rows]
    out.append("")
    out.append(f"{CURRENCY} per million tokens, API list prices; route version {export['route_version']}.")
    for row in export["omitted"]:
        out.append(f"not exported: {row['id']}: {row['reason']}")
    return "\n".join(out) + "\n"
