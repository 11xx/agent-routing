"""The routing page's server: who may reach it, what it reads, and that it edits only through the verbs."""

import contextlib
import http.client
import io
import json
import threading

from edit_fixture import GitStoreTest
import data_edits
import edit_cli
import routing_page
import routing_profiles
import stores

SEAT = ["set-seat", "implement", "--variant", "flat", "--backend", "pi", "--model", "orbit-flash", "--effort", "low",
        "--when", "Fixed-scope implementation from pi.", "--why", "Use the cheaper measured tier."]
NOTE = ["note", "--model", "orbit-flash", "--kind", "observation", "--area", "latency", "--claim",
        "Answered the fixture probe quickly.", "--cause", "executor", "--evidence", "fixture:page", "--date", "2030-02-01"]
BAN = ["prohibit", "ts-3-core", "max", "--reason", "The tier is unreliable.", "--why", "Reject a seated tier."]


class PageTest(GitStoreTest):
    def setUp(self):
        super().setUp()
        self.server = routing_page.PageServer(self.root)
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.address = f"127.0.0.1:{self.server.port}"

    def request(self, method, path, body=None, *, token=True, host=None, origin=True):
        headers = {}
        if token:
            headers[routing_page.TOKEN_HEADER] = self.server.token if token is True else token
        if host:
            headers["Host"] = host
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
            if origin:
                headers["Origin"] = f"http://{self.address}" if origin is True else origin
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request(method, path, data, headers)
            response = connection.getresponse()
            payload = response.read()
        finally:
            connection.close()
        if response.headers.get_content_type() == "application/json":
            payload = json.loads(payload)
        return response.status, payload

    def read(self, path):
        status, payload = self.request("GET", path)
        self.assertEqual(status, 200, payload)
        return payload

    def edit(self, argv, *, confirm=False, expect=None, **options):
        body = {"argv": argv, "confirm": confirm}
        if expect is not None:
            body["expect"] = expect
        return self.request("POST", "/api/edit", body, **options)

    def confirmed(self, argv):
        status, preview = self.edit(argv)
        self.assertEqual(status, 200, preview)
        status, answer = self.edit(argv, confirm=True, expect=preview["stamp"])
        self.assertEqual(status, 200, answer)
        return answer

    def verb(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = edit_cli.main(self.root, [*argv, "--json"])
        self.assertEqual(code, 0, out.getvalue())
        return json.loads(out.getvalue())

    def unchanged(self, texts, head):
        self.assertEqual(self.texts(), texts)
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_nothing_is_served_without_the_launch_token(self):
        """Claim: the page, every read and the write each need this
        launch's token: the page takes it from its query, the API only from
        its header. Rejects a server that serves or edits for any process
        on the machine, or one that accepts the token where a link could
        carry it to the API."""
        texts, head = self.texts(), self.base
        for token in (False, "not-the-token"):
            for path in ("/", "/api/version", "/api/stores", "/api/card?model=orbit-flash", "/api/log"):
                self.assertEqual(self.request("GET", path, token=token)[0], 403, path)
            self.assertEqual(self.edit(SEAT, token=token)[0], 403)
            self.assertEqual(self.edit(SEAT, confirm=True, token=token)[0], 403)
        self.assertEqual(self.request("GET", f"/?token=not-the-token", token=False)[0], 403)
        self.assertEqual(self.request("GET", f"/api/version?token={self.server.token}", token=False)[0], 403)
        status, page = self.request("GET", f"/?token={self.server.token}", token=False)
        self.assertEqual(status, 200)
        self.assertIn(b"<script nonce=", page)
        self.assertEqual(self.request("GET", "/../data/policy.toml")[0], 404)
        self.unchanged(texts, head)

    def test_a_foreign_host_or_origin_is_refused(self):
        """Claim: with the right token, a request whose Host is not this
        server's own loopback address and port is refused, and a write must
        carry the page's own Origin. Rejects a page that a rebound DNS name
        can read, or that another site's page can make write."""
        texts = self.texts()
        for host in ("evil.example", f"evil.example:{self.server.port}", "127.0.0.1:1", f"10.0.0.1:{self.server.port}"):
            self.assertEqual(self.request("GET", "/api/version", host=host)[0], 403, host)
            self.assertEqual(self.request("GET", f"/?token={self.server.token}", token=False, host=host)[0], 403, host)
        self.assertEqual(self.request("GET", "/api/version", host=f"localhost:{self.server.port}")[0], 200)
        stamp = self.read("/api/version")["stamp"]
        for origin in ("http://evil.example", f"http://evil.example:{self.server.port}", f"https://{self.address}", False):
            self.assertEqual(self.edit(SEAT, origin=origin)[0], 403, origin)
            self.assertEqual(self.edit(SEAT, confirm=True, expect=stamp, origin=origin)[0], 403, origin)
        self.unchanged(texts, self.base)

    def test_each_read_returns_what_its_view_computes(self):
        """Claim: the seats, routes, card, notes and log reads equal the
        JSON the verbs print, and the stores read equals the loaded catalog
        and policy at the same route version. Rejects a page that computes
        its own copy of a view."""
        normal = lambda value: json.loads(json.dumps(value))
        self.assertEqual(self.read("/api/seats"), normal(routing_profiles.seats_view(self.root)))
        self.assertEqual(self.read("/api/routes"), normal(routing_profiles.routes_view(self.root)))
        self.assertEqual(self.read("/api/card?model=orbit-flash"), self.verb("card", "orbit-flash"))
        self.assertEqual(self.read("/api/notes?model=orbit-flash&kind=measurement&liveness=all"),
                         self.verb("notes", "orbit-flash", "--kind", "measurement", "--liveness", "all"))
        self.verb(*NOTE)
        self.assertEqual(self.read("/api/notes"), self.verb("notes"))
        self.assertEqual(self.read("/api/log?limit=5"), self.verb("log", "--limit", "5"))
        self.assertRegex(self.read("/api/log?limit=1")["edits"][0]["date"], r"^\d{4}-\d{2}-\d{2}$")
        loaded = stores.load(self.root)
        view = self.read("/api/stores")
        self.assertEqual([view["catalog"], view["policy"], view["models"], view["route_version"]],
                         normal([loaded.catalog, loaded.policy, loaded.models, loaded.version]))
        status, refused = self.request("GET", "/api/card?model=no-such-model")
        self.assertEqual((status, refused["error"]), (422, f"{stores.CATALOG} [[model]] id=no-such-model: no such model"))

    def test_a_preview_writes_nothing(self):
        """Claim: an edit sent without confirmation answers the verb's own
        dry-run result and leaves the stores, HEAD and the index as they
        were. Rejects a preview made by committing and reverting, or one
        that writes the candidate to disk."""
        texts = self.texts()
        status, answer = self.edit(SEAT)
        self.assertEqual(status, 200, answer)
        verb, _, args = edit_cli.arguments([*SEAT, "--dry-run"])
        self.assertEqual(answer["result"], json.loads(json.dumps(data_edits.apply(self.root, verb, **args))))
        self.assertEqual((answer["result"]["dry_run"], answer["result"]["commit"]), (True, None))
        self.assertEqual(answer["command"].split()[:3], ["agent-routing", "set-seat", "implement"])
        self.unchanged(texts, self.base)

    def test_a_confirmed_edit_is_the_commit_the_verb_makes(self):
        """Claim: a previewed and confirmed edit lands as one commit whose
        tree, changed paths and message equal what the CLI verb commits
        from the same arguments. Rejects a page that writes the stores or
        the commit its own way."""
        answer = self.confirmed(SEAT)
        page = [self.git("rev-parse", "HEAD^{tree}"), self.git("log", "-1", "--format=%B"),
                self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")]
        self.assertEqual(answer["result"]["commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")
        self.git("reset", "--quiet", "--hard", self.base)
        self.verb(*SEAT)
        self.assertEqual(page, [self.git("rev-parse", "HEAD^{tree}"), self.git("log", "-1", "--format=%B"),
                                self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")])

    def test_a_refused_edit_returns_the_validators_words_and_writes_nothing(self):
        """Claim: a candidate the validator refuses comes back, previewed or
        confirmed, with exactly the message the edit library raises, and an
        argument the verb's parser refuses comes back in the parser's words;
        nothing is written either way. Rejects a page that paraphrases a
        refusal or writes before validating."""
        texts = self.texts()
        verb, _, args = edit_cli.arguments([*BAN, "--dry-run"])
        with self.assertRaises(stores.StoreError) as raised:
            data_edits.apply(self.root, verb, **args)
        stamp = self.read("/api/version")["stamp"]
        for confirm in (False, True):
            status, answer = self.edit(BAN, confirm=confirm, expect=stamp)
            self.assertEqual((status, answer["error"]), (422, str(raised.exception)))
        status, answer = self.edit(BAN[:-2], confirm=True, expect=stamp)
        self.assertEqual((status, answer["error"]), (422, "the following arguments are required: --why"))
        status, answer = self.edit(["lint"])
        self.assertEqual(status, 400)
        self.unchanged(texts, self.base)

    def test_undo_restores_the_previous_bytes(self):
        """Claim: undo confirmed from the page restores the catalog and
        policy bytes from before the latest verb edit, as a new undo commit
        on top of that edit. Rejects an undo that rewrites history or leaves
        the edit's bytes in place."""
        before = self.texts()
        edited = self.confirmed(SEAT)["result"]["commit"]
        self.assertNotEqual(self.texts(), before)
        undo = ["undo", "--why", "Return to the measured tier."]
        status, preview = self.edit(undo)
        self.assertEqual((status, preview["result"]["undone_commit"]), (200, edited))
        self.confirmed(undo)
        self.assertEqual(self.texts(), before)
        self.assertEqual(self.git("rev-parse", "HEAD^"), edited)
        self.assertIn("Routing-edit: undo", self.git("log", "-1", "--format=%B"))

    def test_a_verb_edit_between_reads_is_a_new_route_version(self):
        """Claim: an edit made by a CLI verb while the page runs shows in
        the next version read as the stores' new route version, and in the
        next seats read; a note filed by a verb moves the stamp the page
        watches but not the route. Rejects a server that keeps what it read
        at launch."""
        first = self.read("/api/version")
        self.verb(*SEAT)
        second = self.read("/api/version")
        self.assertNotEqual(second["route_version"], first["route_version"])
        self.assertEqual(second["route_version"], stores.route_version(self.texts()))
        flat = [seat for seat in self.read("/api/seats")["seats"]
                if (seat["profile"], seat["variant"]) == ("implement", "flat")]
        self.assertEqual([seat["effort"] for seat in flat], ["low"])
        self.verb(*NOTE)
        third = self.read("/api/version")
        self.assertEqual(third["route_version"], second["route_version"])
        self.assertNotEqual(third["stamp"], second["stamp"])

    def test_a_confirmation_after_the_stores_moved_is_refused(self):
        """Claim: a confirmation whose preview predates a change to the
        stores is refused as stale and writes nothing. Rejects committing an
        edit whose effect the operator never saw previewed."""
        status, preview = self.edit(SEAT)
        self.assertEqual(status, 200)
        self.verb(*NOTE)
        texts, head = self.texts(), self.git("rev-parse", "HEAD")
        status, answer = self.edit(SEAT, confirm=True, expect=preview["stamp"])
        self.assertEqual((status, answer.get("stale")), (409, True))
        status, answer = self.edit(SEAT, confirm=True)
        self.assertEqual(status, 409)
        self.unchanged(texts, head)

    def test_seat_choices_offer_unranked_tiers_with_their_pools_order(self):
        """Claim: the seat choices for a profile and backends list every
        tier those backends reach; an unranked tier is offered with the
        place its pool rank would take and the pool's current order, and
        only tiers resolve refuses (prohibited, unstable, fenced, beyond
        the backend's efforts) are withheld, with the resolver's reason.
        Every offered choice previews as a valid seat at its suggested
        rank and every withheld one is refused. Rejects a picker that hides
        unranked tiers or offers what validation then refuses."""
        answer = self.read("/api/choices?profile=implement&backend=codex")
        choices = {(row["model"], row["effort"]): row for row in answer["choices"]}
        self.assertEqual(choices["ts-3-prime", "high"]["pool_rank"],
                         {"current": None, "suggested": 2, "basis": "keeps the place ts-3-core max held"})
        self.assertTrue(choices["ts-3-prime", "high"]["offered"])
        self.assertEqual(choices["ts-3-core", "max"]["pool_rank"]["current"], 2)
        self.assertEqual(answer["pools"]["tessel-plan"][:2], [{"model": "ts-3-core", "effort": "low", "rank": 1},
                                                              {"model": "ts-3-core", "effort": "high", "rank": 1}])
        self.assertTrue(choices["ts-3-prime", "max"]["reasons"][0].startswith("prohibited: Fixture ban"))
        pi = {(row["model"], row["effort"]): row
              for row in self.read("/api/choices?profile=implement&variant=flat&backend=pi")["choices"]}
        self.assertIn("unsupported effort 'xhigh'", pi["ts-3-prime", "xhigh"]["reasons"][0])
        self.assertIn("experimental tier", pi["orbit-trial", "high"]["reasons"])
        self.assertEqual(pi["ts-3-prime", "low"]["pool_rank"]["basis"], "starts at the bottom of the pool, outranking nothing")
        review = {(row["model"], row["effort"]): row
                  for row in self.read("/api/choices?profile=review&backend=pi")["choices"]}
        self.assertIn("cannot serve profile 'review'", review["orbit-trial", "high"]["reasons"][0])
        for row in pi.values():
            rank = row["pool_rank"]
            argv = [*SEAT[:6], "--model", row["model"], "--effort", row["effort"], "--provider", row["provider"],
                    *(["--pool-rank", str(rank["suggested"])] if rank and rank["current"] is None else []), *SEAT[10:]]
            status, answer = self.edit(argv)
            self.assertEqual(status, 200 if row["offered"] else 422, (row, answer))
        readers = self.read("/api/choices?for=review_seat&backend=claude")["choices"]
        self.assertEqual([(row["model"], row["effort"]) for row in readers], [("nw-atlas-2", "xhigh")])
        self.assertEqual(self.request("GET", "/api/choices?profile=implement&backend=nowhere")[0], 400)
