#!/usr/bin/env python3
"""Tests for the controller side of the handover channel.

The website decides *whether* a handover is active; this side has to act on
that answer without ever flying blind. These tests exercise the parts that
would otherwise only be proved by waiting fourteen days and turning off the
old site: a pending request changes nothing, an active one records the new
address and moves the broker, and an active request whose new site is not
ready leaves everything alone so the next hourly run can try again.

They run against a local HTTP server and a temporary RBR directory, so no
broker, controller or root access is involved. Restarting services is disabled
— that is the one side effect the updater cannot take in a unit test.
"""
import http.server
import importlib.util
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_updater():
    spec = importlib.util.spec_from_file_location(
        "rbr_updater_handover", os.path.join(ROOT, "rbr-updater.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


updater = load_updater()

MAC = "00:11:22:33:44:55"
TOKEN = "token-secret"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        self.server.requests.append({
            "path": parsed.path,
            "query": urllib.parse.parse_qs(parsed.query),
        })
        route = self.server.routes.get(parsed.path)
        if parsed.path == "/credentials.php" and not parsed.query and route is not None:
            # The readiness probe expects the bare endpoint to refuse; the
            # controller's own request carries mac and token and gets `route`.
            status, body, ctype = 401, json.dumps({"error": "Unauthorised"}), "application/json"
        elif route is None:
            status, body, ctype = 404, "not found", "text/plain"
        else:
            status, body, ctype = route
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        pass


class Site:
    def __init__(self):
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.routes = {}
        self.server.requests = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base(self):
        return "http://127.0.0.1:%d" % self.server.server_address[1]

    def route(self, path, status, body, ctype="text/plain"):
        self.server.routes[path] = (status, body, ctype)

    @property
    def requests(self):
        return self.server.requests

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class HandoverTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="rbr-handover-")
        self.bridge = os.path.join(self.dir, "rbr-local.conf")
        with open(self.bridge, "w", encoding="utf-8") as fh:
            fh.write(
                "listener 1883\n"
                "address old-broker.example:8883\n"
                "remote_username old-user\n"
                "remote_password old-password\n"
            )
        self.site = Site()

    def tearDown(self):
        self.site.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, name, text):
        with open(os.path.join(self.dir, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def read(self, name):
        with open(os.path.join(self.dir, name), encoding="utf-8") as fh:
            return fh.read()

    def identity(self, token=TOKEN):
        self.write(".mac_override", MAC + "\n")
        if token:
            self.write(".mqtt_token", token + "\n")

    def conf(self):
        with open(self.bridge, encoding="utf-8") as fh:
            return fh.read()

    def handover(self, state, url=None):
        return {
            "state": state,
            "url": url or self.site.base,
            "days_left": 3,
            "effective_at": 1764200000,
        }

    # -- the site address -------------------------------------------------

    def test_site_url_defaults_then_follows_the_recorded_value(self):
        self.assertEqual(updater.site_base_url(self.dir), updater.DEFAULT_SITE)
        updater.write_site_url(self.dir, "https://new.example.com/")
        self.assertEqual(self.read(".site_url").strip(), "https://new.example.com")
        self.assertEqual(updater.site_base_url(self.dir), "https://new.example.com")

    def test_an_unusable_site_url_falls_back_to_the_default(self):
        self.write(".site_url", "not a URL\n")
        self.assertEqual(updater.site_base_url(self.dir), updater.DEFAULT_SITE)

    # -- what each state does ---------------------------------------------

    def test_a_pending_request_changes_nothing(self):
        before = self.conf()
        result = updater.apply_handover(
            self.dir, "https://old.example.com", self.handover("pending"),
            self.bridge, apply_changes=True, restart=False)
        self.assertEqual(result, "https://old.example.com")
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".site_url")))
        self.assertEqual(self.conf(), before)

    def test_a_failed_request_changes_nothing(self):
        before = self.conf()
        record = self.handover("failed")
        record["error"] = "the new site did not answer"
        result = updater.apply_handover(
            self.dir, "https://old.example.com", record,
            self.bridge, apply_changes=True, restart=False)
        self.assertEqual(result, "https://old.example.com")
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".site_url")))
        self.assertEqual(self.conf(), before)

    def test_an_active_request_switches_site_and_broker(self):
        self.identity()
        self.site.route("/heat/version", 200, "2611151200")
        self.site.route("/credentials.php", 200, json.dumps({
            "broker": "new-broker.example",
            "mqtt_port": 1884,
            "username": "new-user",
            "password": "new-password",
        }), "application/json")

        result = updater.apply_handover(
            self.dir, "https://old.example.com", self.handover("active"),
            self.bridge, apply_changes=True, restart=False)

        self.assertEqual(result, self.site.base)
        self.assertEqual(updater.site_base_url(self.dir), self.site.base)
        conf = self.conf()
        self.assertIn("address new-broker.example:1884", conf)
        self.assertIn("remote_username new-user", conf)
        self.assertIn("remote_password new-password", conf)
        self.assertNotIn("old-broker.example", conf)

        record = json.loads(self.read(".handover"))
        self.assertEqual(record["url"], self.site.base)
        self.assertEqual(record["broker"], "new-broker.example")

        credentials = [r for r in self.site.requests
                       if r["path"] == "/credentials.php" and r["query"].get("mac")]
        self.assertEqual(len(credentials), 1)
        self.assertEqual(credentials[0]["query"].get("mac"), [MAC])
        self.assertEqual(credentials[0]["query"].get("token"), [TOKEN])

    def test_an_active_request_whose_site_is_not_ready_does_not_switch(self):
        self.identity()
        before = self.conf()
        # No /heat/version route, so the readiness check gets a 404.
        result = updater.apply_handover(
            self.dir, "https://old.example.com", self.handover("active"),
            self.bridge, apply_changes=True, restart=False)
        self.assertEqual(result, "https://old.example.com")
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".site_url")))
        self.assertEqual(self.conf(), before)

    def test_a_site_without_a_credentials_endpoint_does_not_switch(self):
        self.identity()
        before = self.conf()
        self.site.route("/heat/version", 200, "2611151200")
        # No /credentials.php route, so the readiness probe gets a 404.
        result = updater.apply_handover(
            self.dir, "https://old.example.com", self.handover("active"),
            self.bridge, apply_changes=True, restart=False)
        self.assertEqual(result, "https://old.example.com")
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".site_url")))
        self.assertEqual(self.conf(), before)

    def test_check_mode_reports_but_makes_no_change(self):
        self.identity()
        self.site.route("/heat/version", 200, "2611151200")
        self.site.route("/credentials.php", 200, json.dumps({
            "broker": "new-broker.example",
            "username": "new-user",
            "password": "new-password",
        }), "application/json")
        before = self.conf()
        result = updater.apply_handover(
            self.dir, "https://old.example.com", self.handover("active"),
            self.bridge, apply_changes=False, restart=False)
        self.assertEqual(result, "https://old.example.com")
        self.assertFalse(os.path.exists(os.path.join(self.dir, ".site_url")))
        self.assertEqual(self.conf(), before)
        self.assertEqual(self.site.requests, [])

    # -- the status request ------------------------------------------------

    def test_status_request_carries_mac_and_token(self):
        self.identity()
        self.site.route("/handover.php", 200, json.dumps({
            "ok": True,
            "handover": {"state": "active", "url": "https://new.example.com"},
        }), "application/json")
        result = updater.fetch_handover(self.dir, self.site.base)
        self.assertEqual(result["url"], "https://new.example.com")
        query = self.site.requests[0]["query"]
        self.assertEqual(query.get("action"), ["status"])
        self.assertEqual(query.get("mac"), [MAC])
        self.assertEqual(query.get("token"), [TOKEN])

    def test_status_request_without_a_token_still_asks(self):
        self.identity(token="")
        self.site.route("/handover.php", 200, json.dumps({
            "ok": True,
            "handover": {"state": "active", "url": "https://new.example.com"},
        }), "application/json")
        result = updater.fetch_handover(self.dir, self.site.base)
        self.assertEqual(result["state"], "active")
        query = self.site.requests[0]["query"]
        self.assertEqual(query.get("mac"), [MAC])
        self.assertNotIn("token", query)

    def test_a_site_without_a_handover_channel_is_quiet(self):
        self.identity()
        # No route -> 404, which is the normal answer on a site without the
        # handover configuration.
        self.assertIsNone(updater.fetch_handover(self.dir, self.site.base))

    # -- the bridge address ------------------------------------------------

    def test_a_broker_change_alone_rewrites_the_address(self):
        credentials = {
            "broker": "new-broker.example",
            "mqtt_port": 8883,
            "username": "old-user",
            "password": "old-password",
            "source": "test",
        }
        changed = updater.ensure_bridge_credentials(
            self.dir, self.bridge, apply_changes=True,
            credentials=credentials, restart=False)
        self.assertTrue(changed)
        conf = self.conf()
        self.assertIn("address new-broker.example:8883", conf)
        self.assertNotIn("old-broker.example", conf)
        # The account was already right, so it is untouched.
        self.assertIn("remote_username old-user", conf)
        self.assertIn("remote_password old-password", conf)


if __name__ == "__main__":
    unittest.main()
