"""Export the roster's API list prices as a tapes price table.

agent-routing produces the file; tapes never reads this repository. Each
roster row's `api_price_per_million` becomes one `tapes-price-table/2` model,
keyed by the ids harnesses record for it, dated by its `api_price_read`, with
only the categories the row prices. A row's `long_context_surcharge` becomes
the model's long-context term: past the threshold the whole request pays the
multiplied rates, under API per-token billing only, since a subscription plan
pays no surcharge. Its `time_of_day_prices` become UTC time-of-day windows
priced at the row's rates times each window's multiplier, on the days of
the week a window names. Its
`api_price_changes` split it into one model per price, each in effect from
its date until the next, carrying the row's terms at its own rates.
"""

import datetime
import json
import math
import pathlib
import re

import stores
from routing_profiles import data, model_identities, route_version

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
# The days of the week a time-of-day window may name, as tapes names them.
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MINUTES_PER_DAY = 24 * 60


def _read_date(value: object) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _minute_of_day(value: object) -> int | None:
    if not isinstance(value, str) or not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", value):
        return None
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _window_minutes(start: int, end: int, days: list[str]) -> set[int]:
    """The minutes of a week, from Monday midnight, a window from `start`
    until `end` holds when it opens on `days`; past midnight when `end` is
    not after `start`, into the day after the one it opens on."""
    length = (end - start) % MINUTES_PER_DAY
    week = 7 * MINUTES_PER_DAY
    return {(DAYS.index(day) * MINUTES_PER_DAY + start + minute) % week for day in days for minute in range(length)}


def _days_problems(label: str, days: object) -> list[str]:
    if not isinstance(days, list) or not days:
        return [f"{label}: time_of_day_prices days must list at least one day"]
    unknown = [f"{label}: time_of_day_prices days are written {', '.join(DAYS)}, not {day!r}"
               for day in days if day not in DAYS]
    return unknown or [f"{label}: time_of_day_prices days name {day!r} twice"
                       for day in dict.fromkeys(days) if days.count(day) > 1]


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


def _time_of_day_problems(label: str, windows: object) -> list[str]:
    if not isinstance(windows, list) or not all(isinstance(window, dict) for window in windows):
        return [f"{label}: time_of_day_prices must be a list of tables"]
    problems, held = [], set()
    for window in windows:
        start, end = _minute_of_day(window.get("from")), _minute_of_day(window.get("until"))
        if start is None or end is None:
            problems.append(f"{label}: time_of_day_prices from and until must be UTC times written HH:MM")
            continue
        if start == end:
            problems.append(f"{label}: a time_of_day_prices window must not start where it ends")
            continue
        if not _finite_at_least(window.get("multiplier"), 0):
            problems.append(f"{label}: time_of_day_prices multiplier must be a finite number of at least zero")
        days = window.get("days", list(DAYS))
        day_problems = _days_problems(label, days)
        if day_problems:
            problems.extend(day_problems)
            continue
        minutes = _window_minutes(start, end, days)
        if minutes & held:
            problems.append(f"{label}: time_of_day_prices windows overlap")
        held |= minutes
    return problems


def _price_change_problems(label: str, model: dict, changes: object) -> list[str]:
    if not isinstance(changes, list) or not all(isinstance(change, dict) for change in changes):
        return [f"{label}: api_price_changes must be a list of tables"]
    problems = []
    previous = _read_date(model.get("api_price_read"))
    for change in changes:
        start = _read_date(change.get("from"))
        if start is None:
            problems.append(f"{label}: api_price_changes from must be a YYYY-MM-DD date")
        elif previous is not None and start <= previous:
            problems.append(f"{label}: api_price_changes from {start} must come after the read date and the "
                            "change before it")
        previous = start or previous
        prices = change.get("per_million")
        if not isinstance(prices, dict) or set(prices) != set(model["api_price_per_million"]):
            problems.append(f"{label}: api_price_changes per_million must price the keys api_price_per_million prices")
        elif not all(_finite_at_least(value, 0) for value in prices.values()):
            problems.append(f"{label}: api_price_changes per_million prices must be finite numbers of at least zero")
    return problems


def price_problems(models: list[dict]) -> list[str]:
    """Problems with the roster's API prices: unknown or doubled category
    keys, prices that are not finite non-negative numbers, a price without
    its read date, and a long-context surcharge, time-of-day window or dated
    price change the export cannot describe."""
    problems: list[str] = []
    for model in models:
        label = model.get("id", "<missing>")
        prices = model.get("api_price_per_million")
        surcharge = model.get("long_context_surcharge")
        windows = model.get("time_of_day_prices")
        changes = model.get("api_price_changes")
        if "api_price_undated" in model:
            problems.append(f"{label}: api_price_undated is not accepted; date the price with api_price_read "
                            "or remove it")
        if prices is None:
            if any(key in model for key in ("api_price_read", "long_context_surcharge", "time_of_day_prices",
                                            "api_price_changes")):
                problems.append(f"{label}: api_price_read, long_context_surcharge, time_of_day_prices or "
                                "api_price_changes without api_price_per_million")
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
        if windows is not None:
            problems.extend(_time_of_day_problems(label, windows))
        if changes is not None:
            problems.extend(_price_change_problems(label, model, changes))
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


def time_of_day_terms(windows: list[dict], per_million: dict) -> list[dict]:
    """The tapes time-of-day windows for `windows` on a row pricing
    `per_million`: every category the row prices, scaled, on the days a
    window names, or every day."""
    return [{
        "from": window["from"],
        "until": window["until"],
        "per_million": {category: price * window["multiplier"] for category, price in per_million.items()},
        **({"days": window["days"]} if "days" in window else {}),
    } for window in windows]


def price_export(root: pathlib.Path) -> dict:
    """The priced rows, which categories each leaves unpriced, and the terms
    each is priced by per request."""
    models = data(root).models
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
        names = [name for name in model_identities(root, model["id"]) if name != model["id"]]
        for name in [model["id"], *names]:
            if name in owners:
                raise ValueError(f"{model['id']}: {name!r} is already an id of {owners[name]}")
            owners[name] = model["id"]
        changes = model.get("api_price_changes", [])
        periods = [(None, "api_price_per_million", prices),
                   *((change["from"], f"api_price_changes from {change['from']}", change["per_million"])
                     for change in changes)]
        for index, (start, origin, period_prices) in enumerate(periods):
            per_million = {CATEGORY_KEYS[key]: float(value) for key, value in period_prices.items()}
            per_million = {category: per_million[category] for category in CATEGORIES if category in per_million}
            exported.append({
                "id": model["id"],
                "aliases": names,
                "effective": model["api_price_read"],
                "effective_from": start,
                "effective_until": periods[index + 1][0] if index + 1 < len(periods) else None,
                "source": f"agent-routing {stores.CATALOG} {model['id']} {origin}, route version {version}",
                "per_million": per_million,
                "unpriced": [category for category in CATEGORIES if category not in per_million],
                "long_context": long_context_term(surcharge, per_million) if surcharge is not None else None,
                "time_of_day": time_of_day_terms(model.get("time_of_day_prices", []), per_million),
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
        f"# {stores.CATALOG} at route version {export['route_version']}. Prices are API list",
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
        lines.append(f"effective = {row['effective']}")
        lines += [f"{key} = {row[key]}" for key in ("effective_from", "effective_until") if row[key]]
        lines += [
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
        for window in row["time_of_day"]:
            lines += [
                "",
                "[[models.time_of_day]]",
                f"from = {_string(window['from'])}",
                f"until = {_string(window['until'])}",
                f"per_million = {_inline(window['per_million'])}",
            ]
            if "days" in window:
                lines.append(f"days = {_strings(window['days'])}")
    return "\n".join(lines) + "\n"


def term_summary(row: dict) -> str:
    """A row's terms priced by the request, for a reader."""
    terms = []
    if row["effective_from"] or row["effective_until"]:
        terms.append(f"in effect {row['effective_from'] or ''}..{row['effective_until'] or ''}")
    term = row["long_context"]
    if term:
        threshold = (f"from {term['from_prompt_tokens']:,}" if "from_prompt_tokens" in term
                     else f"above {term['above_prompt_tokens']:,}")
        scaled = ", ".join(f"{factor:g}x {category}" for category, factor in term["multipliers"].items())
        terms.append(f"{threshold} prompt tokens, {'/'.join(term['billing'])} billing: {scaled}")
    for window in row["time_of_day"]:
        prices = ", ".join(f"{category} {price:g}" for category, price in window["per_million"].items())
        days = f" {'/'.join(window['days'])}" if "days" in window else ""
        terms.append(f"{window['from']}-{window['until']} UTC{days}: {prices}")
    return "; ".join(terms) or "-"


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
