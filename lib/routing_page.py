"""A local page that reads the routing stores and edits them through the edit verbs.

`PageServer` serves one HTML document and a small JSON API on the loopback
address. Every request carries the launch token, names a loopback host and
the server's own port; a write is a same-origin JSON `POST`. Reads return
what the views compute: `seats --json`, `routes --json`, and the `card`,
`notes` and `log` results. An edit is an argument vector for an edit verb,
parsed by the verbs' own parser and run by the verbs' own `execute`: first
as a dry run, then, when the page confirms with the stores unchanged since
that preview, for real. The server holds no routing rule of its own; the
seat choices it offers are the resolver's own refusals applied to the
catalog's reach rows.
"""

from __future__ import annotations

import hmac
import http.server
import json
import pathlib
import secrets
import shlex
import urllib.parse

import data_edits
import doctrine
import edit_cli
import routing_profiles as routes
import stores

PAGE = pathlib.Path(__file__).resolve().parent / "routing_page.html"
LOOPBACK = ("127.0.0.1", "localhost", "[::1]")
TOKEN_HEADER = "X-Routing-Token"
MAX_BODY = 64 * 1024


class Refused(Exception):
    """A request the page server declines, with its HTTP status."""

    def __init__(self, status: int, message: str, **fields):
        super().__init__(message)
        self.status = status
        self.fields = fields


def stamp(root: pathlib.Path) -> dict:
    """The route version and the stores' state, which moves with any store byte or data commit."""
    observed = data_edits.observe(root)
    return {"route_version": observed["route_version"], "stamp": observed["state"]}


def verb_result(root: pathlib.Path, argv: list[str]) -> dict:
    """What a read verb prints with --json, parsed and computed by the verb's own code."""
    verb, _, args = edit_cli.arguments(argv, raising=True)
    return edit_cli.execute(root, verb, args)[0]


def labs(loaded: stores.Data) -> dict:
    """Each lab in catalog order and the lab of every model."""
    lab_of = {model["id"]: routes._lab(loaded.families, model["family"]) for model in loaded.models}
    return {"labs": list(dict.fromkeys([row["lab"] for row in loaded.families] + list(lab_of.values()))),
            "lab_of": lab_of}


def store_view(root: pathlib.Path) -> dict:
    loaded = routes.data(root)
    return {"catalog": loaded.catalog, "policy": loaded.policy, "models": loaded.models, **labs(loaded),
            "purposes": doctrine.REVIEW_PURPOSE_TEXT, "standing_problems": stores.standing_problems(root, loaded),
            "route_version": loaded.version}


def seat_choices(root: pathlib.Path, profile: str, backends: list[str], variant: str | None = None) -> dict:
    """Every tier the backends reach through one provider, and the pools' orders those tiers would join.

    A choice is withheld with the resolver's own refusals for the model, its
    pool, the tier and the backends' effort support, and with validation's
    refusal of a tier whose status the seat's stability cannot carry. A stable seat on a tier
    its pool has not ranked carries the place the edit would give it, which
    `set-seat --pool-rank` writes in the same commit. Validation of the whole
    candidate on preview stays the authority.
    """
    loaded = routes.data(root)
    by_model, by_pool = loaded.by_model(), {pool["provider"]: pool for pool in loaded.pools}
    backend_rows = {row["id"]: row for row in loaded.backends}
    unknown = [backend for backend in backends if backend not in backend_rows]
    if not backends or unknown:
        raise Refused(400, f"name at least one catalog backend; unknown: {', '.join(unknown) or 'none named'}")
    lab_of = labs(loaded)["lab_of"]
    reach = loaded.catalog.get("reach", [])
    previous = next((row for row in loaded.policy.get("seat", [])
                     if row["profile"] == profile and row.get("variant") == variant), None)
    stability = previous.get("stability", "stable") if previous else "stable"
    ranked_seat = stability == "stable"
    choices = []
    for row in reach:
        if row["backend"] != backends[0] or row["model"] not in by_model:
            continue
        if not all(stores.reach_row(loaded.catalog, row["model"], backend, row["provider"]) for backend in backends):
            continue
        model = by_model[row["model"]]
        refusal = routes._model_role_refusal(profile, model["id"], model)
        pool = routes.pool_refusal(by_pool, profile, row["provider"], model["id"])
        for tier in sorted(model["effort"], key=lambda entry: routes.EFFORT_ORDER.index(entry["effort"])
                           if entry["effort"] in routes.EFFORT_ORDER else len(routes.EFFORT_ORDER)):
            reasons = [error.message for error in (refusal, pool) if error is not None]
            if tier.get("prohibited"):
                reasons.append(f"prohibited: {tier['reason']}")
            status = tier.get("status")
            if status == "explicit-only":
                reasons.append("requires an explicit model request and cannot back a profile")
            elif status == "probationary" and stability not in {"probationary", "experimental"}:
                reasons.append(f"a probationary tier cannot hold a {stability} seat")
            elif status == "experimental" and stability != "experimental":
                reasons.append(f"an experimental tier cannot hold a {stability} seat")
            if model.get("status") == "experimental" and stability != "experimental":
                reasons.append(f"an experimental model cannot hold a {stability} seat")
            reasons += [error.message for backend in backends
                        if (error := routes.backend_effort_refusal(backend_rows[backend], profile, model["id"],
                                                                   tier["effort"])) is not None]
            placement = (data_edits.pool_placement(loaded.policy, previous, model["id"], tier["effort"], row["provider"])
                         if ranked_seat else None)
            choices.append({"model": model["id"], "effort": tier["effort"], "provider": row["provider"],
                            "lab": lab_of[model["id"]], "rank": tier["rank"], "floor": tier["floor"],
                            "pool_rank": placement, "offered": not reasons, "reasons": reasons})
    pools = {choice["provider"]: [{key: row[key] for key in ("model", "effort", "rank")}
                                  for row in data_edits.pool_order(loaded.policy, choice["provider"])]
             for choice in choices}
    return {"choices": choices, "pools": pools}


def review_choices(root: pathlib.Path, backend: str) -> list[dict]:
    """The stable routes of the review profile on a backend: the only readers a review seat may name."""
    loaded = routes.data(root)
    profile = next((entry for entry in loaded.profiles if entry["id"] == "review"), None)
    if profile is None:
        return []
    by_model, lab_of = loaded.by_model(), labs(loaded)["lab_of"]
    choices = []
    for route in routes._review_routes(profile):
        if backend not in route["backends"] or route.get("stability") != "stable":
            continue
        tier = routes._tier_of(by_model, route["model"], route["effort"])
        if tier is None or any(choice["model"] == route["model"] and choice["effort"] == route["effort"]
                               for choice in choices):
            continue
        choices.append({"model": route["model"], "effort": route["effort"], "provider": route["provider"],
                        "lab": lab_of[route["model"]], "rank": tier["rank"], "floor": tier["floor"],
                        "offered": True, "reasons": []})
    return choices


class PageServer(http.server.ThreadingHTTPServer):
    """The page and its API for one checkout, on a free loopback port, behind one launch token."""

    daemon_threads = True

    def __init__(self, root: pathlib.Path, *, token: str | None = None):
        super().__init__(("127.0.0.1", 0), Handler)
        self.root = pathlib.Path(root).resolve()
        self.token = token or secrets.token_urlsafe(24)

    @property
    def port(self) -> int:
        return self.server_address[1]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/?token={self.token}"

    # --- reads -------------------------------------------------------------

    def read(self, path: str, query: dict) -> dict:
        root = self.root
        one = lambda key: (query.get(key) or [None])[-1]
        if path == "/api/version":
            return stamp(root)
        if path == "/api/stores":
            return store_view(root)
        if path == "/api/seats":
            return routes.seats_view(root)
        if path == "/api/routes":
            return routes.routes_view(root)
        if path == "/api/card":
            return verb_result(root, ["card", one("model") or ""])
        if path == "/api/notes":
            argv = ["notes", *([one("model")] if one("model") else [])]
            for key in ("kind", "area", "liveness"):
                if one(key):
                    argv += [f"--{key}", one(key)]
            return verb_result(root, argv)
        if path == "/api/log":
            return verb_result(root, ["log", "--limit", one("limit") or "20"])
        if path == "/api/choices":
            if one("for") == "review_seat":
                return {"choices": review_choices(root, one("backend") or "")}
            return seat_choices(root, one("profile") or "", query.get("backend", []), one("variant"))
        raise Refused(404, f"no such page resource: {path}")

    # --- the one write -----------------------------------------------------

    def edit(self, body: dict) -> dict:
        argv, confirm = body.get("argv"), body.get("confirm") is True
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise Refused(400, "argv is the edit verb and its arguments, as strings")
        command = shlex.join(["agent-routing", *argv])
        if argv[0] not in edit_cli.EDITS:
            raise Refused(400, f"{argv[0]!r} is not an edit verb", command=command)
        try:
            verb, _, args = edit_cli.arguments(argv, raising=True)
        except edit_cli.UsageError as error:
            raise Refused(422, str(error), command=command) from None
        # A preview reports the state it was computed from; a confirmation is the
        # same edit only from that state, which the edit checks under its own lock.
        args["dry_run"] = not confirm
        args["expect"] = None
        if confirm:
            if not isinstance(body.get("expect"), str) or not body["expect"]:
                raise Refused(409, "a confirmation names the state its preview saw; preview the edit first",
                              command=command, stale=True)
            args["expect"] = body["expect"]
        try:
            result = edit_cli.execute(self.root, verb, args)[0]
        except data_edits.StaleState as error:
            raise Refused(409, str(error), command=command, stale=True) from None
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise Refused(422, str(error), command=command) from None
        return {"result": result, "command": command, "stamp": result["state"]}


class Handler(http.server.BaseHTTPRequestHandler):
    server: PageServer
    protocol_version = "HTTP/1.1"
    server_version = "agent-routing-page"
    sys_version = ""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def dispatch(self, method: str) -> None:
        try:
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            host = self.headers.get("Host", "")
            if host not in {f"{name}:{self.server.port}" for name in LOOPBACK}:
                raise Refused(403, "the page answers only its own loopback address")
            page = method == "GET" and url.path == "/"
            token = (query.get("token") or [""])[-1] if page else self.headers.get(TOKEN_HEADER, "")
            if not hmac.compare_digest(token.encode(), self.server.token.encode()):
                raise Refused(403, "this needs the launch token; open the address `agent-routing page` printed")
            if page:
                return self.send_page()
            if method == "POST":
                if self.headers.get("Origin") != f"http://{host}":
                    raise Refused(403, "a write must come from the page itself")
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    raise Refused(415, "a write is a JSON body")
                if url.path != "/api/edit":
                    raise Refused(404, f"no such page resource: {url.path}")
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    raise Refused(413, "the edit is too large")
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    raise Refused(400, "the body is not JSON") from None
                if not isinstance(body, dict):
                    raise Refused(400, "the body is a JSON object")
                return self.send_json(200, self.server.edit(body))
            try:
                answer = self.server.read(url.path, query)
            except (routes.RouteRefusal, OSError, ValueError, TypeError, KeyError) as error:
                raise Refused(422, str(error)) from None
            self.send_json(200, answer)
        except Refused as refusal:
            # A refused request may leave its body unread, so its connection cannot carry another.
            self.close_connection = True
            self.send_json(refusal.status, {"error": str(refusal), **refusal.fields})

    def headers_common(self, content_type: str, length: int, csp: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", csp)
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()

    def send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.headers_common("application/json; charset=utf-8", len(data), "default-src 'none'")
        self.wfile.write(data)

    def send_page(self) -> None:
        nonce = secrets.token_urlsafe(16)
        data = PAGE.read_text().replace("<script>", f'<script nonce="{nonce}">', 1).encode()
        self.send_response(200)
        self.headers_common("text/html; charset=utf-8", len(data),
                            f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
                            "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; "
                            "frame-ancestors 'none'")
        self.wfile.write(data)
