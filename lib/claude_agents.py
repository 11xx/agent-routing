"""Render static Claude agents and their consumer declarations from resolved routes."""

import json
import pathlib
import re

from routing_profiles import RouteRefusal, load_toml, resolve, route_version, structural_problems


def claude_agent_bundle(root: pathlib.Path, *, profile_id=None, variant_id=None,
                        allow_experimental=False):
    problems = structural_problems(root)
    if problems:
        raise RouteRefusal("manifest-invalid", "; ".join(problems))
    if variant_id is not None and profile_id is None:
        raise RouteRefusal("unknown-profile", "--variant requires --profile")
    profiles = load_toml(root / "routing/profiles.toml")["profile"]
    if profile_id is not None:
        profiles = [profile for profile in profiles if profile["id"] == profile_id]
        if not profiles:
            raise RouteRefusal("unknown-profile", f"unknown profile {profile_id!r}")
    files = {}
    pins = []
    for profile in profiles:
        for selected in [profile, *profile.get("variant", [])]:
            variant = None if selected is profile else selected["id"]
            if variant_id is not None and variant != variant_id:
                continue
            if "claude" not in selected["backends"]:
                continue
            if selected["stability"] != "stable" and not allow_experimental:
                if profile_id is not None and variant_id is not None:
                    raise RouteRefusal("stability", "the requested agent requires --allow-experimental")
                continue
            route = resolve(root, profile["id"], "claude", variant_id=variant,
                            allow_experimental=allow_experimental)
            alias = re.fullmatch(r"(opus|sonnet|haiku|fable)-[0-9.]+", selected["model"])
            if alias is None:
                raise RouteRefusal("unsupported-model", "no Claude native alias for the routed model",
                                   model=selected["model"])
            alias = alias.group(1)
            name = f"{profile['id']}-{variant or alias}"
            if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                raise RouteRefusal("manifest-invalid", "unsafe native agent name", name=name)
            if f"agents/{name}.md" in files:
                raise RouteRefusal("manifest-invalid", f"duplicate native agent name {name!r}")
            if profile["id"] == "implement":
                description = (f"Implementer on the resolved {route['profile']} route "
                               f"({alias.capitalize()}, {route['effort']} effort) for a curated, "
                               "self-contained change brief. Owns one worktree and one change; "
                               "reports what it landed, what it verified, and what it left.")
                template = "claude-implement.md"
            else:
                description = (f"The resolved {route['profile']} route "
                               f"({alias.capitalize()}, {route['effort']} effort) for a curated, "
                               f"self-contained brief: {profile['purpose']}")
                description = json.dumps(description)
                template = "claude-task.md"
            body = (root / "templates" / template).read_text()
            if template == "claude-task.md":
                body = body.replace("{purpose}", profile["purpose"])
                body = body.replace("{access}", "Read-only: do not edit files or record a verdict."
                                    if profile["id"] in {"extract", "explore", "plan", "design"}
                                    else "Read-only: record a verdict only when the brief authorizes it."
                                    if profile["id"] == "review"
                                    else "Write only within the targets and authority the brief names.")
            files[f"agents/{name}.md"] = (f"---\nname: {name}\ndescription: {description}\n"
                                          f'tools: "*"\nmodel: {alias}\neffort: {route["effort"]}\n---\n\n{body}')
            pin = dict(consumer="delegate-agents", path=f"{name}.md", model=alias,
                       effort=route["effort"], profile=profile["id"], backend="claude", generated=True)
            if variant is not None:
                pin["variant"] = variant
            if route["stability"] != "stable":
                pin["allow_experimental"] = True
            pins.append(pin)
    if not files:
        raise RouteRefusal("unsupported-backend", "no requested Claude agent routes")
    pin_table = "\n\n".join("[[pin]]\n" + "\n".join(
        f'{key} = {json.dumps(value)}'
        for key, value in pin.items()) for pin in pins) + "\n"
    files["consumers-pins.toml"] = pin_table
    return dict(schema="agent-routing-claude-agents/1", route_version=route_version(root),
                files=files, pins=pins)
