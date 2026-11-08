"""Browser side: static server, CDN routes, MQTT stub, clock and locators."""

import hashlib
import json
import os
import re
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import urlopen

from playwright.sync_api import (
    Error as PlaywrightError,
    expect as pw_expect,
    sync_playwright,
)

from . import targets
from .errors import ScenarioError

MAC = "00:11:22:33:44:55"
VIEWPORT = {"width": 390, "height": 844}
# One fast_forward per slice. The shell polls every 10 s and reloads after 60 s
# without a reply; a jump longer than a minute would trip the watchdog before
# the next poll is answered. Slices stay under it.
CLOCK_SLICE_MS = 50_000


class _Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/new-ui/credentials.json":
            return self._json({
                "broker": "broker.invalid",
                "port": 443,
                "username": "scenario-runner",
                "password": "scenario-runner",
            })
        if path == "/credentials.php":
            return self._json({})
        return super().do_GET()


def start_server(repo):
    handler = partial(_Handler, directory=str(repo))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def runtime_source(repo):
    """The pinned AllSpeak runtime named by new-ui/index.html, cached by URL."""
    index = (Path(repo) / "new-ui" / "index.html").read_text(encoding="utf-8")
    match = re.search(r"<script[^>]+src=['\"]([^'\"]*allspeak[^'\"]*\.js[^'\"]*)['\"]", index, re.I)
    if not match:
        raise ScenarioError("new-ui/index.html names no AllSpeak runtime")
    url = urljoin("https://allspeak.ai/", match.group(1))

    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "rbr-studio"
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        cache_root = Path.cwd() / ".runtime-cache"
        cache_root.mkdir(parents=True, exist_ok=True)
    cached = cache_root / ("allspeak-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".js")

    if cached.exists():
        return url, cached.read_text(encoding="utf-8")
    try:
        with urlopen(url, timeout=30) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise ScenarioError(f"could not fetch the AllSpeak runtime at {url}: {exc}")
    try:
        cached.write_text(body, encoding="utf-8")
    except OSError:
        pass
    return url, body


def stub_source():
    source = Path(__file__).with_name("browser_stub.js").read_text(encoding="utf-8")
    return source.replace("__RBR_TEST_MAC__", json.dumps(MAC))


class PageDriver:
    def __init__(self, prepared, repo, headless, on_console=None, speed=0):
        self.prepared = prepared
        self.repo = Path(repo)
        self.headless = headless
        self.speed = speed
        self.on_console = on_console
        self.server = None
        self.port = None
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.console_lines = []
        self.page_errors = []
        self.current_step = None
        self.wire_cursor = 0
        self.current = prepared.start

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start(self):
        self.server, self.port = start_server(self.repo)
        runtime_url, runtime_body = runtime_source(self.repo)

        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport=VIEWPORT,
            timezone_id=self.prepared.scenario.get("clock", {}).get("timeZone") or "UTC",
            locale="en-GB",
            service_workers="block",
        )
        self.context.tracing.start(screenshots=True, snapshots=True)
        self.page = self.context.new_page()
        self.page.clock.install(time=self.prepared.start)

        self.page.on("console", self._on_console)
        self.page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))

        self.page.route("**/dist/allspeak.js*", lambda route: route.fulfill(
            status=200, content_type="text/javascript; charset=utf-8", body=runtime_body))
        self.page.route("**/mqtt.min.js*", lambda route: route.fulfill(
            status=200, content_type="text/javascript; charset=utf-8", body="/* stubbed */"))
        self.page.add_init_script(script=stub_source())

        self.page.goto(f"http://127.0.0.1:{self.port}/new-ui/index.html", wait_until="load", timeout=30000)
        try:
            self.page.wait_for_function(
                "() => !!window.__rbr && window.__rbr.connected === true", timeout=30000)
        except Exception as exc:
            console = "\n".join(entry["text"] for entry in self.console_lines[-20:])
            errors = "\n".join(self.page_errors[-5:])
            raise ScenarioError(
                f"the shell did not connect ({exc}).\nconsole:\n{console}\npage errors:\n{errors}")
        self.push_map(self.prepared.base_map)
        try:
            self.page.wait_for_function(
                "() => !!document.getElementById('special-time-sheet')", timeout=30000)
        except Exception as exc:
            console = "\n".join(entry["text"] for entry in self.console_lines[-20:])
            errors = "\n".join(self.page_errors[-5:])
            raise ScenarioError(
                f"the home screen did not build ({exc}).\nconsole:\n{console}\npage errors:\n{errors}")

    def stop(self, failure=None, trace_path=None):
        try:
            if self.context is not None:
                if failure and trace_path:
                    self.context.tracing.stop(path=str(trace_path))
                else:
                    self.context.tracing.stop()
        except PlaywrightError:
            pass
        try:
            if self.context is not None:
                self.context.close()
        except PlaywrightError:
            pass
        try:
            if self.browser is not None:
                self.browser.close()
        except PlaywrightError:
            pass
        try:
            if self.pw is not None:
                self.pw.stop()
        except Exception:
            pass
        try:
            if self.server is not None:
                self.server.shutdown()
                self.server.server_close()
        except Exception:
            pass

    def _on_console(self, message):
        entry = {"step": self.current_step, "type": message.type, "text": message.text}
        self.console_lines.append(entry)
        if self.on_console:
            self.on_console(entry)

    # ── clock ────────────────────────────────────────────────────────────────

    def advance_to(self, when, speed=None):
        """Move the virtual clock to `when`.

        With no speed this jumps in 50 s slices, as fast as the page allows.
        With a Show speed it advances 10 s of scenario time per slice and sleeps
        the corresponding real time, so the page's poll, clock tick and
        heartbeat are visible. A step may pass its own speed so the pre-marker
        part of a Show run can run at zero while the rest keeps the chosen pace.
        """
        if when is None:
            return
        effective = self.speed if speed is None else speed
        delta_ms = int((when - self.current).total_seconds() * 1000)
        if delta_ms <= 0:
            self.current = when
            return
        remaining = delta_ms
        if effective and effective > 0:
            if effective == 1:
                # At 1x the fake clock is already flowing in real time. Sleeping
                # the gap advances it exactly once; fast_forwarding as well
                # would advance every slice twice and drift the UI clock ahead.
                time.sleep(remaining / 1000.0)
            else:
                pace_slice = 10_000
                while remaining > pace_slice:
                    self.page.clock.fast_forward(pace_slice)
                    time.sleep(pace_slice / (1000.0 * effective))
                    remaining -= pace_slice
                if remaining > 0:
                    self.page.clock.fast_forward(remaining)
                    time.sleep(remaining / (1000.0 * effective))
        else:
            while remaining > CLOCK_SLICE_MS:
                self.page.clock.fast_forward(CLOCK_SLICE_MS)
                remaining -= CLOCK_SLICE_MS
            if remaining > 0:
                self.page.clock.fast_forward(remaining)
        self.current = when
        # Let the 0 ms timers queued by the last poll (and its auto-reply) run.
        self.page.wait_for_timeout(50)

    # ── page actions ────────────────────────────────────────────────────────

    def selector(self, target):
        return targets.resolve(target, self.prepared.base_map, self.prepared.aliases)

    def tap(self, target, timeout):
        self.page.locator(self.selector(target)).click(timeout=timeout)

    def select(self, target, value, timeout):
        self.page.locator(self.selector(target)).select_option(value, timeout=timeout)

    def fill(self, target, value, timeout):
        self.page.locator(self.selector(target)).fill(value, timeout=timeout)

    def scroll(self, target, delta_y, timeout):
        self.page.locator(self.selector(target)).scroll_into_view_if_needed(timeout=timeout)
        if delta_y:
            self.page.evaluate("(dy) => window.scrollBy(0, dy)", delta_y)

    def push_map(self, base_map):
        self.page.evaluate("text => window.__rbr.pushMap(text)", json.dumps(base_map))

    def push_raw(self, text):
        self.page.evaluate("text => window.__rbr.pushRaw(text)", text)

    def connection(self, action, message=None):
        if action == "drop":
            self.page.evaluate("() => window.__rbr.disconnect()")
        elif action == "reconnect":
            self.page.evaluate("() => window.__rbr.connectAgain()")
        elif action == "error":
            self.page.evaluate("(text) => window.__rbr.emit('error', new Error(text))", message or "scenario error")

    # ── assertions ──────────────────────────────────────────────────────────

    def assert_expect(self, expect, timeout):
        locator = self.page.locator(self.selector(expect["target"]))
        if "text" in expect:
            pw_expect(locator).to_have_text(expect["text"], timeout=timeout)
        elif "contains" in expect:
            pw_expect(locator).to_contain_text(expect["contains"], timeout=timeout)
        elif "notContains" in expect:
            pw_expect(locator).not_to_contain_text(expect["notContains"], timeout=timeout)
        elif "visible" in expect:
            if expect["visible"]:
                pw_expect(locator).to_be_visible(timeout=timeout)
            else:
                pw_expect(locator).to_be_hidden(timeout=timeout)
        elif "hidden" in expect:
            if expect["hidden"]:
                pw_expect(locator).to_be_hidden(timeout=timeout)
            else:
                pw_expect(locator).to_be_visible(timeout=timeout)
        elif "value" in expect:
            pw_expect(locator).to_have_value(expect["value"], timeout=timeout)
        elif "count" in expect:
            pw_expect(locator).to_have_count(expect["count"], timeout=timeout)
        else:
            raise ScenarioError("expect has no supported predicate")

    def wait_for(self, wait, timeout):
        locator = self.page.locator(self.selector(wait["target"]))
        locator.wait_for(state=wait.get("state", "visible"), timeout=timeout)

    def messages(self):
        return self.page.evaluate("() => window.__rbr.messages()")

    @staticmethod
    def _outer(text):
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return None

    def wait_wire(self, request, match, not_match, timeout):
        """Find a request at or after the wire cursor; advance the cursor past it."""
        deadline = time.time() + timeout / 1000.0
        seen = []
        while True:
            messages = self.messages()
            for index in range(self.wire_cursor, len(messages)):
                outer = self._outer(messages[index])
                if not isinstance(outer, dict):
                    continue
                candidate = None
                if outer.get("action") == request:
                    candidate = outer
                elif outer.get("action") == "uirequest":
                    inner = outer.get("message")
                    if isinstance(inner, str):
                        inner = self._outer(inner)
                    if isinstance(inner, dict) and (inner.get("Action") == request or inner.get("action") == request):
                        candidate = inner
                if candidate is None:
                    continue
                seen.append(candidate)
                if match and any(candidate.get(key) != value for key, value in match.items()):
                    continue
                if not_match and any(candidate.get(key) == value for key, value in not_match.items()):
                    continue
                self.wire_cursor = index + 1
                return candidate
            if time.time() >= deadline:
                detail = "; ".join(json.dumps(item, ensure_ascii=False) for item in seen[-3:]) or "nothing"
                raise AssertionError(
                    f"no {request} request matched within {timeout} ms (saw: {detail})")
            self.page.wait_for_timeout(50)

    def screenshot(self, path):
        self.page.screenshot(path=str(path), full_page=True)
