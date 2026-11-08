#!/usr/bin/env python3
"""Tests for journal_import.py, journal_to_scenario.py and journal_bundle.py.

Run directly:
    python3 tools/rbr-studio/tests/journal_check.py

Only stdlib is used. The fixtures are synthetic; no controller or network is
needed.
"""

import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

STUDIO = pathlib.Path(__file__).resolve().parent.parent
REPO = STUDIO.parent.parent
sys.path.insert(0, str(STUDIO))

import journal_bundle  # noqa: E402
import journal_inbox  # noqa: E402
import journal_ingest  # noqa: E402
import journal_to_scenario  # noqa: E402
import scenario_library  # noqa: E402
from scenario_runner.validate import prepare  # noqa: E402


DAY = "2026-11-06"


def make_base_map():
    return {
        "name": "Test home",
        "profile": 0,
        "calendar": "off",
        "rooms": [
            {"name": "Kitchen", "sensor": "kitchen-therm", "relays": ["kitchen-rad"],
             "linked": "yes", "relay": "off", "status": "good", "temperature": 1900,
             "humidity": 50, "battery": 90, "relaysTotal": 1, "relaysFailed": 0},
            {"name": "Office", "sensor": "office-therm", "relays": ["office-rad"],
             "linked": "yes", "relay": "off", "status": "good", "temperature": 2000,
             "humidity": 50, "battery": 90, "relaysTotal": 1, "relaysFailed": 0},
            {"name": "Outside", "sensor": "outside-therm", "relays": [],
             "linked": "yes", "relay": "off", "status": "good", "temperature": 800,
             "humidity": 60, "battery": 90, "relaysTotal": 0, "relaysFailed": 0},
        ],
        "profiles": [{
            "name": "Weekday",
            "rooms": {
                "Kitchen": {"mode": "timed", "target": 20, "period": 0, "advance": "-",
                            "periods": [{"on": "06:00", "off": "08:00", "temp": "21.0"}]},
                "Office": {"mode": "timed", "target": 20, "period": 0, "advance": "-",
                           "periods": [{"on": "07:00", "off": "09:00", "temp": "21.0"}]},
                "Outside": {"mode": "off", "target": 0, "period": 0, "advance": "-"},
            },
        }],
    }


def build_fixture(root: pathlib.Path):
    day_dir = root / "2026" / "11"
    day_dir.mkdir(parents=True)
    maps = root / "maps"
    maps.mkdir()
    base = make_base_map()
    raw = json.dumps(base, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    (maps / f"{digest}.json").write_bytes(raw)

    starter = dt.datetime(2026, 11, 6, 11, 0, tzinfo=dt.timezone.utc)
    start_ms = int(starter.timestamp() * 1000)

    def event(seq, offset, kind, data):
        stamp = starter + dt.timedelta(milliseconds=offset)
        return {"v": 1, "tsMs": int(stamp.timestamp() * 1000), "seq": seq, "boot": start_ms,
                "type": kind, "data": data,
                "ts": stamp.isoformat(timespec="milliseconds"), "tzOffsetMinutes": 0}

    events = [
        event(1, 0, "session.start", {"system": "Test", "profile": "Weekday",
                                      "profileIndex": 0, "mapHash": digest}),
        event(2, 60000, "sensor.reading", {"room": "Kitchen", "sensor": "kitchen-therm",
                                           "temp": 1840, "source": "zigbee",
                                           "sourceTsMs": start_ms + 60000,
                                           "humidity": 50, "battery": 90}),
        event(3, 60000, "sensor.reading", {"room": "Kitchen", "sensor": "kitchen-therm",
                                           "temp": 1840, "source": "zigbee",
                                           "sourceTsMs": start_ms + 61000,
                                           "humidity": 50, "battery": 90}),
        event(4, 61000, "room.state", {"room": "Kitchen", "profile": "Weekday",
                                       "profileIndex": 0, "mode": "timed", "target": 20,
                                       "period": 0, "advance": "A", "relay": "on",
                                       "status": "good", "statusMessage": "",
                                       "relayMessage": "", "relaysFailed": 0,
                                       "relaysTotal": 1, "relayfails": [0]}),
        event(5, 61001, "room.state", {"room": "Kitchen", "profile": "Weekday",
                                       "profileIndex": 0, "mode": "timed", "target": 20,
                                       "period": 0, "advance": "A", "relay": "on",
                                       "status": "good", "statusMessage": "",
                                       "relayMessage": "", "relaysFailed": 0,
                                       "relaysTotal": 1, "relayfails": [0]}),
        event(6, 62000, "ui.request", {"client": "phone", "action": "Operating Mode",
                                       "payload": {"Action": "Operating Mode", "Room": "Kitchen"},
                                       "source": {"app": "pwa", "screen": "home",
                                                  "control": "advance", "gesture": "tap",
                                                  "room": "Kitchen"},
                                       "room": "Kitchen"}),
        event(7, 120000, "sensor.reading", {"room": "Office", "sensor": "office-therm",
                                            "temp": 2010, "source": "zigbee",
                                            "sourceTsMs": start_ms + 120000,
                                            "humidity": 50, "battery": 90}),
        event(8, 180000, "session.stop", {"reason": "test"}),
    ]
    (day_dir / f"{DAY}.jsonl").write_text(
        "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events), encoding="utf-8")
    return digest


def run(script, *args, env=None):
    result = subprocess.run([sys.executable, str(STUDIO / script), *args],
                            capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise AssertionError(f"{script} failed:\n{result.stdout}\n{result.stderr}")
    return result


class ExampleSeedTests(unittest.TestCase):
    def test_seed_examples_creates_deletable_library_copies(self):
        with tempfile.TemporaryDirectory(prefix="rbr-example-seed-") as tmp:
            tmp_path = pathlib.Path(tmp)
            local = tmp_path / "fixtures" / "local"
            scenarios = local / "scenarios"
            old = (scenario_library.LOCAL, scenario_library.SCENARIOS,
                   scenario_library.TRASH, scenario_library.INDEX,
                   scenario_library.SEED_FLAG, scenario_library.EXAMPLES)
            scenario_library.LOCAL = local
            scenario_library.SCENARIOS = scenarios
            scenario_library.TRASH = local / ".trash"
            scenario_library.INDEX = scenarios / "index.json"
            scenario_library.SEED_FLAG = local / ".examples-seeded"
            scenario_library.EXAMPLES = STUDIO / "docs" / "examples"
            try:
                created = scenario_library.seed_examples()
                self.assertEqual([entry["name"] for entry in created],
                                  ["Advance at 15:00", "Kitchen temperature", "Delay demo"])
                self.assertEqual(len(list(scenarios.rglob("*.json"))), 4)  # index + 3 scenarios
                first = scenarios / created[0]["path"]
                data = json.loads(first.read_text(encoding="utf-8"))
                self.assertIsInstance(data["home"]["map"], dict)
                self.assertEqual(scenario_library.seed_examples(), [])
            finally:
                (scenario_library.LOCAL, scenario_library.SCENARIOS,
                 scenario_library.TRASH, scenario_library.INDEX,
                 scenario_library.SEED_FLAG, scenario_library.EXAMPLES) = old


class JournalToolsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="rbr-journal-tools-")
        self.root = pathlib.Path(self._tmp.name) / "events"
        self.digest = build_fixture(self.root)
        self.heatlog = pathlib.Path(self._tmp.name) / "heating-data"
        day_csv = self.heatlog / "Kitchen" / "2026" / "11"
        day_csv.mkdir(parents=True)
        (day_csv / f"{DAY[-2:]}.csv").write_text("30504123,207,205,p\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_window_is_rejected_with_the_journal_range(self):
        out = pathlib.Path(self._tmp.name) / "empty.json"
        result = subprocess.run([
            sys.executable, str(STUDIO / "journal_to_scenario.py"),
            "--journal", str(self.root / "2026" / "11" / f"{DAY}.jsonl"),
            "--map", str(self.root / "maps" / f"{self.digest}.json"),
            "--from", "14:00", "--to", "19:00", "--out", str(out),
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no journal events between 14:00:00 and 19:00:00", result.stderr)
        self.assertIn("11:00:00 to 11:03:00", result.stderr)
        self.assertFalse(out.exists())

    def test_temperature_format_matches_the_page(self):
        # The page truncates hundredths to one decimal; 1939 is 19.3, not 19.4.
        self.assertEqual(journal_to_scenario._format_temp(1939), "19.3")
        self.assertEqual(journal_to_scenario._format_temp(1840), "18.4")
        self.assertEqual(journal_to_scenario._format_temp(2000), "20.0")

    def test_local_import_and_archive(self):
        bundle = pathlib.Path(self._tmp.name) / "bundle"
        archive = pathlib.Path(self._tmp.name) / "bundle.tar.gz"
        run("journal_import.py", "--source", str(self.root), "--day", DAY,
            "--dest", str(bundle), "--archive", str(archive))
        manifest = json.loads((bundle / "manifest.json").read_text())
        self.assertEqual(manifest["events"], 8)
        self.assertEqual(manifest["system"], "Test")
        self.assertEqual(manifest["profile"], "Weekday")
        self.assertEqual([row["hash"] for row in manifest["maps"]], [self.digest])
        self.assertTrue((bundle / "events" / "2026" / "11" / f"{DAY}.jsonl").is_file())
        self.assertTrue((bundle / "maps" / f"{self.digest}.json").is_file())
        self.assertTrue(archive.is_file())

        opened = journal_bundle.open_bundle(archive)
        try:
            self.assertEqual(opened.manifest["day"], DAY)
            self.assertTrue(opened.events_path and opened.events_path.is_file())
            self.assertEqual(opened.load_map(self.digest)["name"], "Test home")
        finally:
            opened.close()

    def test_mail_inbox_imports_each_bundle_once(self):
        bundle = pathlib.Path(self._tmp.name) / "mail-bundle"
        inbox = pathlib.Path(self._tmp.name) / "inbox"
        system_dir = inbox / "00:e0:27:5b:31:40"
        system_dir.mkdir(parents=True)
        archive = system_dir / f"Test-{DAY}.tar.gz"
        run("journal_import.py", "--source", str(self.root), "--day", DAY,
            "--mac", "00:e0:27:5b:31:40", "--heatlog-root", str(self.heatlog),
            "--dest", str(bundle), "--archive", str(archive))
        local = pathlib.Path(self._tmp.name) / "fixtures" / "local"
        scenarios = local / "scenarios"
        old = (scenario_library.LOCAL, scenario_library.SCENARIOS,
               scenario_library.TRASH, scenario_library.INDEX,
               scenario_library.SEED_FLAG, scenario_library.EXAMPLES)
        scenario_library.LOCAL = local
        scenario_library.SCENARIOS = scenarios
        scenario_library.TRASH = local / ".trash"
        scenario_library.INDEX = scenarios / "index.json"
        scenario_library.SEED_FLAG = local / ".examples-seeded"
        scenario_library.EXAMPLES = STUDIO / "docs" / "examples"
        journal_dir = pathlib.Path(self._tmp.name) / "journal"
        drafts = pathlib.Path(self._tmp.name) / "drafts"
        state = journal_dir / "inbox-seen.json"
        try:
            systems = {"00:e0:27:5b:31:40": "Home"}
            handled = journal_inbox.scan(inbox=inbox, journal_dir=journal_dir,
                                         drafts_dir=drafts, state_path=state,
                                         systems=systems, quiet=True)
            self.assertEqual([row["day"] for row in handled], [DAY])
            self.assertEqual(handled[0]["name"], "Home")
            self.assertEqual(handled[0]["mac"], "00:e0:27:5b:31:40")
            target = journal_dir / f"00-e0-27-5b-31-40-{DAY}"
            self.assertTrue((target / "manifest.json").is_file())
            self.assertTrue((target / "reports" / "heatlog" /
                             "Kitchen" / "2026" / "11" / f"{DAY[-2:]}.csv").is_file())
            index = scenario_library.load_index()
            entry = next(item for item in index["scenarios"] if item["group"] == "Journal")
            self.assertEqual(entry["name"], f"Journal {DAY} — Home")
            self.assertTrue((scenarios / entry["path"]).is_file())
            # Reset forgets the day, then the same archive can be imported again.
            archive_bytes = archive.read_bytes()
            removed = journal_inbox.reset(
                system="00:e0:27:5b:31:40", day=DAY, inbox=inbox,
                journal_dir=journal_dir, drafts_dir=drafts, state_path=state,
                quiet=True)
            self.assertEqual(len(removed), 1)
            self.assertFalse(target.exists())
            self.assertFalse(archive.exists())
            self.assertFalse((scenarios / entry["path"]).exists())
            self.assertEqual(json.loads(state.read_text(encoding="utf-8")), {})
            archive.write_bytes(archive_bytes)
            again = journal_inbox.scan(inbox=inbox, journal_dir=journal_dir,
                                       drafts_dir=drafts, state_path=state,
                                       systems=systems, quiet=True)
            self.assertEqual([row["day"] for row in again], [DAY])
            self.assertTrue((target / "manifest.json").is_file())
            # An unchanged inbox is a no-op, and the filter's own file stays put.
            self.assertEqual(journal_inbox.scan(inbox=inbox, journal_dir=journal_dir,
                                                drafts_dir=drafts, state_path=state,
                                                systems=systems, quiet=True), [])
            self.assertTrue(archive.is_file())
            # Losing the state file must not duplicate a day already on disk.
            state.unlink()
            self.assertEqual(journal_inbox.scan(inbox=inbox, journal_dir=journal_dir,
                                                drafts_dir=drafts, state_path=state,
                                                systems=systems, quiet=True), [])
            index = scenario_library.load_index()
            self.assertEqual(len([item for item in index["scenarios"]
                                  if item["group"] == "Journal"]), 1)
        finally:
            (scenario_library.LOCAL, scenario_library.SCENARIOS,
             scenario_library.TRASH, scenario_library.INDEX,
             scenario_library.SEED_FLAG, scenario_library.EXAMPLES) = old

    def test_partial_bundle_gets_its_own_key_and_name(self):
        systems = {"00:e0:27:5b:31:40": "Home"}
        full = {"day": "2026-11-06", "mac": "00:e0:27:5b:31:40", "system": "Test"}
        partial = {"day": "2026-11-06", "mac": "00:e0:27:5b:31:40",
                   "system": "Test", "partial": True, "label": "12:34:56"}
        self.assertEqual(journal_inbox._system_identity(full, systems)[3],
                         "00-e0-27-5b-31-40")
        self.assertEqual(journal_inbox._system_identity(partial, systems)[3],
                         "00-e0-27-5b-31-40-12-34-56")
        self.assertEqual(journal_inbox._scenario_name(partial, systems),
                         "Journal 2026-11-06 — Home 12:34:56")

        journal_dir = pathlib.Path(self._tmp.name) / "partial-journal"
        for name, data in (("full", full), ("partial", partial)):
            directory = journal_dir / name
            directory.mkdir(parents=True)
            (directory / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(journal_inbox._existing_bundle(
            journal_dir, "2026-11-06", "Test", "00:e0:27:5b:31:40"),
            journal_dir / "full")
        self.assertEqual(journal_inbox._existing_bundle(
            journal_dir, "2026-11-06", "Test", "00:e0:27:5b:31:40",
            partial=True, stamp="12:34:56"),
            journal_dir / "partial")

    def test_mail_inbox_records_a_bad_archive_without_retrying(self):
        inbox = pathlib.Path(self._tmp.name) / "bad-inbox"
        inbox.mkdir()
        (inbox / "broken.tar.gz").write_bytes(b"not a tar archive")
        state = pathlib.Path(self._tmp.name) / "bad-state.json"
        self.assertEqual(journal_inbox.scan(
            inbox=inbox, journal_dir=pathlib.Path(self._tmp.name) / "journal",
            drafts_dir=pathlib.Path(self._tmp.name) / "drafts",
            state_path=state, quiet=True), [])
        saved = json.loads(state.read_text(encoding="utf-8"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(next(iter(saved.values()))["status"], "failed")
        self.assertEqual(journal_inbox.scan(
            inbox=inbox, journal_dir=pathlib.Path(self._tmp.name) / "journal",
            drafts_dir=pathlib.Path(self._tmp.name) / "drafts",
            state_path=state, quiet=True), [])

    def test_converter_suppresses_duplicates_and_formats_values(self):
        bundle = pathlib.Path(self._tmp.name) / "bundle"
        run("journal_import.py", "--source", str(self.root), "--day", DAY,
            "--dest", str(bundle))
        out = pathlib.Path(self._tmp.name) / "scenario.json"
        run("journal_to_scenario.py", "--bundle", str(bundle), "--from", "11:00",
            "--to", "12:00", "--out", str(out), "--name", "Kitchen morning")
        scenario = json.loads(out.read_text())
        types = [kind for step in scenario["steps"] for kind in ("controller", "expect") if kind in step]
        self.assertEqual(types.count("controller"), 3, types)  # Kitchen reading + Kitchen state + Office reading
        self.assertEqual(types.count("expect"), 3, types)      # two temperatures and advance
        controllers = [step["controller"] for step in scenario["steps"] if "controller" in step]
        self.assertEqual(controllers[0]["set"]["temperature"], 1840)
        self.assertEqual(controllers[0]["set"]["timestamp"], 1793962860000)
        kitchen_state = next(step["controller"]["state"]["set"] for step in scenario["steps"]
                             if "controller" in step and step["controller"]["room"] == "Kitchen"
                             and "state" in step["controller"])
        self.assertEqual(kitchen_state["advance"], "A")
        self.assertNotIn("statusMessage", controllers[0]["set"])
        expects = [step["expect"] for step in scenario["steps"] if "expect" in step]
        self.assertIn({"target": "room.Kitchen.temp", "contains": "18.4"}, expects)
        self.assertIn({"target": "room.Kitchen.subline", "contains": "(A)"}, expects)
        self.assertEqual(scenario["home"]["profile"], "Weekday")
        self.assertEqual(scenario["clock"]["timeZone"], "Europe/London")
        prepare(out, REPO)

    def test_source_kind_recognises_local_inputs(self):
        self.assertEqual(journal_ingest._source_kind("/data/rbr-heating/events")[0], "root")
        self.assertEqual(journal_ingest._source_kind(str(self.root))[0], "root")

    def test_duplicate_and_rename_library_scenario(self):
        with tempfile.TemporaryDirectory(prefix="rbr-library-edit-") as tmp:
            tmp_path = pathlib.Path(tmp)
            local = tmp_path / "fixtures" / "local"
            scenarios = local / "scenarios"
            old = (scenario_library.LOCAL, scenario_library.SCENARIOS,
                   scenario_library.TRASH, scenario_library.INDEX,
                   scenario_library.SEED_FLAG, scenario_library.EXAMPLES)
            scenario_library.LOCAL = local
            scenario_library.SCENARIOS = scenarios
            scenario_library.TRASH = local / ".trash"
            scenario_library.INDEX = scenarios / "index.json"
            scenario_library.SEED_FLAG = local / ".examples-seeded"
            scenario_library.EXAMPLES = STUDIO / "docs" / "examples"
            try:
                entry = scenario_library.duplicate(
                    STUDIO / "docs" / "examples" / "advance.json",
                    name="Copy of advance", group="Unsorted")
                copied = scenarios / entry["path"]
                self.assertTrue(copied.is_file())
                self.assertEqual(json.loads(copied.read_text())["name"], "Copy of advance")
                renamed = scenario_library.rename(copied, "Renamed copy")
                self.assertEqual(renamed["name"], "Renamed copy")
                index = scenario_library.load_index()
                match = next(item for item in index["scenarios"]
                             if item["path"] == renamed["path"])
                self.assertEqual(match["name"], "Renamed copy")
            finally:
                (scenario_library.LOCAL, scenario_library.SCENARIOS,
                 scenario_library.TRASH, scenario_library.INDEX,
                 scenario_library.SEED_FLAG, scenario_library.EXAMPLES) = old

    def test_ingest_helper_generates_a_draft_without_touching_the_library(self):
        bundle = pathlib.Path(self._tmp.name) / "bundle"
        run("journal_import.py", "--source", str(self.root), "--day", DAY,
            "--dest", str(bundle))
        old_drafts, old_journals = journal_ingest.DRAFTS, journal_ingest.JOURNALS
        journal_ingest.DRAFTS = pathlib.Path(self._tmp.name) / "drafts"
        journal_ingest.JOURNALS = pathlib.Path(self._tmp.name) / "journals"
        journal_ingest.DRAFTS.mkdir()
        try:
            self.assertEqual(journal_ingest.main([
                "--source", str(bundle), "--from", "11:00", "--to", "12:00", "--no-add"]), 0)
        finally:
            journal_ingest.DRAFTS, journal_ingest.JOURNALS = old_drafts, old_journals
        drafts = list((pathlib.Path(self._tmp.name) / "drafts").glob("*.json"))
        self.assertEqual(len(drafts), 1, drafts)
        scenario = json.loads(drafts[0].read_text())
        self.assertGreaterEqual(len(scenario["steps"]), 2)

    def test_raw_journal_with_explicit_map(self):
        map_path = pathlib.Path(self._tmp.name) / "map.json"
        map_path.write_text(json.dumps(make_base_map()), encoding="utf-8")
        out = pathlib.Path(self._tmp.name) / "raw.json"
        run("journal_to_scenario.py", "--journal", str(self.root / "2026" / "11" / f"{DAY}.jsonl"),
            "--map", str(map_path), "--from", "11:00", "--to", "12:00", "--out", str(out))
        scenario = json.loads(out.read_text())
        self.assertGreaterEqual(len(scenario["steps"]), 2)
        prepare(out, REPO)


if __name__ == "__main__":
    unittest.main()
