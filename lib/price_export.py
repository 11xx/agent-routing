"""Export the roster's API list prices as a tapes price table.

agent-routing produces the file; tapes never reads this repository. Each
roster row's `api_price_per_million` becomes one `tapes-price-table/2` model,
keyed by the ids harnesses record for it, dated by its `api_price_read`, with
only the categories the row prices. A row's `long_context_surcharge` becomes
the model's long-context term: past the threshold the whole request pays the
multiplied rates, under API per-token billing only, since a subscription plan
pays no surcharge.
"""

import datetime
import json
import math
import pathlib

from routing_profiles import load_toml, model_identities, route_version

SCHEMA = "tapes-price-table/2"
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
SURCHARGE_MULTIPLIERS = ("input_multiplier", "cache_multiplier", "output_multiplier")
# The surcharge multiplier each tapes category is scaled by: cache reads and
# cache writes both take the cache multiplier.
CATEGORY_MULTIPLIERS = {
    "uncached_input": "input_multiplier",
    "cache_read": "cache_multiplier",
    "cache_write_5m": "cache_multiplier",
    "cache_write_1h": "cache_multiplier",
    "output": "output_multiplier",
}
# Every vendor the roster prices counts a request's whole prompt, cached and
# cache-written tokens included, toward its long-context threshold.
PROMPT_CATEGORIES = ("uncached_input", "cache_read", "cache_write")
# Long-context surcharges apply to API per-token billing; a subscription plan
# pays none.
SURCHARGE_BILLING = ("api",)


def _read_date(value: object) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _finite_at_least(value: object, floor: float) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= floor


def _surcharge_problems(label: str, surcharge: object) -> list[str]:
    if not isinstance(surcharge, dict):
        return [f"{label}: long_context_surcharge must be a table"]
    problems = []
    threshold = surcharge.get("threshold_input_tokens")
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold <= 0:
        problems.append(f"{label}: long_context_surcharge.threshold_input_tokens must be a positive whole number")
    if not isinstance(surcharge.get("threshold_inclusive"), bool):
        problems.append(f"{label}: long_context_surcharge.threshold_inclusive must be true (a prompt of exactly "
                        "the threshold pays it) or false (only a longer one does)")
    for key in SURCHARGE_MULTIPLIERS:
        if not _finite_at_least(surcharge.get(key), 1):
            problems.append(f"{label}: long_context_surcharge.{key} must be a finite number of at least one")
    return problems


def price_problems(models: list[dict]) -> list[str]:
    """Problems with the roster's API prices: unknown or doubled category
    keys, prices that are not finite non-negative numbers, a price without
    its read date, and a long-context surcharge the export cannot describe."""
    problems: list[str] = []
    for model in models:
        label = model.get("id", "<missing>")
        prices = model.get("api_price_per_million")
        surcharge = model.get("long_context_surcharge")
        if "api_price_undated" in model:
            problems.append(f"{label}: api_price_undated is not accepted; date the price with api_price_read "
                            "or remove it")
        if prices is None:
            if "api_price_read" in model or surcharge is not None:
                problems.append(f"{label}: api_price_read or long_context_surcharge without api_price_per_million")
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
            if not _finite_at_least(value, 0):
                problems.append(f"{label}: api_price_per_million.{key} must be a finite number of at least zero")
        if "api_price_read" not in model:
            problems.append(f"{label}: api_price_per_million needs api_price_read (YYYY-MM-DD), the date it was read")
        elif _read_date(model["api_price_read"]) is None:
            problems.append(f"{label}: api_price_read must be a YYYY-MM-DD date")
        if surcharge is not None:
            problems.extend(_surcharge_problems(label, surcharge))
    return problems


def long_context_term(surcharge: dict, per_million: dict) -> dict:
    """The tapes long-context term for a surcharge on a row pricing
    `per_million`: one multiplier per category the row prices."""
    threshold_key = "from_prompt_tokens" if surcharge["threshold_inclusive"] else "above_prompt_tokens"
    return {
        threshold_key: surcharge["threshold_input_tokens"],
        "prompt_tokens": list(PROMPT_CATEGORIES),
        "billing": list(SURCHARGE_BILLING),
        "multipliers": {category: float(surcharge[CATEGORY_MULTIPLIERS[category]]) for category in per_million},
    }


def price_export(root: pathlib.Path) -> dict:
    """The priced rows, which categories each leaves unpriced, and the
    long-context term of a surcharged row."""
    models = load_toml(root / "routing" / "models.toml").get("model", [])
    problems = price_problems(models)
    if problems:
        raise ValueError("; ".join(problems))
    version = route_version(root)
    exported, owners = [], {}
    for model in models:
        prices = model.get("api_price_per_million")
        if prices is None:
            continue
        surcharge = model.get("long_context_surcharge")
        per_million = {CATEGORY_KEYS[key]: float(value) for key, value in prices.items()}
        per_million = {category: per_million[category] for category in CATEGORIES if category in per_million}
        source = f"agent-routing routing/models.toml {model['id']} api_price_per_million, route version {version}"
        names = [name for name in model_identities(root, model["id"]) if name != model["id"]]
        for name in [model["id"], *names]:
            if name in owners:
                raise ValueError(f"{model['id']}: {name!r} is already an id of {owners[name]}")
            owners[name] = model["id"]
        exported.append({
            "id": model["id"],
            "aliases": names,
            "effective": model["api_price_read"],
            "source": source,
            "per_million": per_million,
            "unpriced": [category for category in CATEGORIES if category not in per_million],
            "long_context": long_context_term(surcharge, per_million) if surcharge is not None else None,
            "status": model.get("status"),
        })
    return {"schema": SCHEMA, "currency": CURRENCY, "route_version": version, "models": exported}


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _number(value: float) -> str:
    return repr(float(value))


def _inline(values: dict) -> str:
    return "{ " + ", ".join(f"{key} = {_number(value)}" for key, value in values.items()) + " }" if values else "{}"


def _strings(values: list[str]) -> str:
    return "[" + ", ".join(_string(value) for value in values) + "]"


def tapes_table(export: dict) -> str:
    """The export as `tapes-price-table/2` TOML."""
    lines = [
        "# A tapes price table exported by `agent-routing prices --format tapes` from",
        f"# routing/models.toml at route version {export['route_version']}. Prices are API list",
        "# prices; a category a row does not price is left out. A long-context term",
        "# applies to API per-token billing only: a subscription plan pays no surcharge.",
        "",
        f"schema = {_string(export['schema'])}",
        f"currency = {_string(export['currency'])}",
    ]
    for row in export["models"]:
        lines += [
            "",
            "[[models]]",
            f"id = {_string(row['id'])}",
        ]
        if row["aliases"]:
            lines.append(f"aliases = {_strings(row['aliases'])}")
        lines += [
            f"effective = {row['effective']}",
            f"source = {_string(row['source'])}",
            f"per_million = {_inline(row['per_million'])}",
        ]
        term = row["long_context"]
        if term:
            lines += ["", "[models.long_context]"]
            for key, value in term.items():
                if key == "multipliers":
                    lines.append(f"multipliers = {_inline(value)}")
                elif isinstance(value, list):
                    lines.append(f"{key} = {_strings(value)}")
                else:
                    lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def term_summary(row: dict) -> str:
    """A row's terms priced by the request, for a reader."""
    term = row["long_context"]
    if not term:
        return "-"
    threshold = (f"from {term['from_prompt_tokens']:,}" if "from_prompt_tokens" in term
                 else f"above {term['above_prompt_tokens']:,}")
    scaled = ", ".join(f"{factor:g}x {category}" for category, factor in term["multipliers"].items())
    return f"{threshold} prompt tokens, {'/'.join(term['billing'])} billing: {scaled}"


def readable_table(export: dict) -> str:
    """The same prices as a table for a reader."""
    header = ["model", "read", *CATEGORIES, "recorded ids", "terms"]
    rows = [header]
    for row in export["models"]:
        rows.append([
            row["id"],
            row["effective"],
            *(f"{row['per_million'][category]:g}" if category in row["per_million"] else "-" for category in CATEGORIES),
            ", ".join(row["aliases"]) or "-",
            term_summary(row),
        ])
    out = ["\t".join(cells) for cells in rows]
    out.append("")
    out.append(f"{CURRENCY} per million tokens, API list prices; route version {export['route_version']}.")
    out.append("A long-context term charges the whole request at the scaled rates under API billing only.")
    return "\n".join(out) + "\n"
