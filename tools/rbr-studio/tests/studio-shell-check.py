"""Headless check for the RBR Studio shell.

Starts studio.allspeak offscreen, switches scenario, clicks Run, waits for the
runner child to finish, and asks the table and logs what they hold.

    cd tools/rbr-studio
    QT_QPA_PLATFORM=offscreen python3 tests/studio-shell-check.py

It needs the runner venv (Run starts .venv/bin/python) and the installed
AllSpeak graphics/process domains.
"""

import json
import os
import re
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[1]
os.chdir(STUDIO)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(STUDIO))

import scenario_library as library  # noqa: E402

TEST_GROUP = "Test group"
TEST_NAME = "Shell brief"
TEST_NAME_2 = "Shell brief two"
TEST_BRIEF = "Brief for the shell check. Keep the summary title visible."
TEST_SOURCE = library.LOCAL / "drafts" / "shell-brief.json"
TEST_SOURCE_2 = library.LOCAL / "drafts" / "shell-brief-two.json"
USER_NAME = "Shell user step"
USER_SOURCE = library.LOCAL / "drafts" / "shell-user.json"
TEST_MAC = "00:e0:27:5b:31:40"
OTHER_MAC = "00:00:00:00:00:01"
OLD_JOURNAL_NAME = "Shell old journal"
RECENT_JOURNAL_NAME = "Shell recent journal"
OTHER_JOURNAL_NAME = "Shell other system journal"
DUP_ROOM_NAME = "Shell Sunroom copy"
CONFIG = STUDIO / "ai-config.json"
CONFIG_BACKUP = CONFIG.read_text(encoding="utf-8") if CONFIG.exists() else None
CONFIG.write_text('{"provider": "prompt"}\n', encoding="utf-8")
SETTINGS = library.LOCAL / "studio-settings.json"
SETTINGS_BACKUP = SETTINGS.read_text(encoding="utf-8") if SETTINGS.exists() else None
SETTINGS.write_text(json.dumps({
    "x": 55, "y": 66, "width": 1000, "height": 700,
    "group": "All",
    "tab": 1,
    "scenario": "fixtures/local/scenarios/examples/advance-at-15-00.json",
    "source": "docs/examples", "day": "2026-11-06", "range": "14:00-19:00",
}), encoding="utf-8")
STUDIO_CONFIG = STUDIO / "studio-config.json"
STUDIO_CONFIG_BEFORE = STUDIO_CONFIG.read_bytes() if STUDIO_CONFIG.exists() else None
TEST_CONFIG = library.LOCAL / "shell-check-config.json"
TEST_CONFIG.parent.mkdir(parents=True, exist_ok=True)
TEST_CONFIG.write_text(json.dumps({
    "systems": {"00:e0:27:5b:31:40": "Home"},
    "viewerAspect": 0.5,
    "mailboxes": {"00:e0:27:5b:31:40": str(STUDIO / "fixtures" / "local" / "shell-check.mbox")},
}), encoding="utf-8")
CONFIG_POINTER = library.LOCAL / "studio-config-path"
CONFIG_POINTER_BACKUP = CONFIG_POINTER.read_text(encoding="utf-8") if CONFIG_POINTER.exists() else None
CONFIG_POINTER.write_text(str(TEST_CONFIG), encoding="utf-8")

ADVANCE_ENTRY = None


def prepare_library():
    global ADVANCE_ENTRY
    index = library.load_index()
    for item in list(index["scenarios"]):
        if item.get("group") == TEST_GROUP or item.get("name") in (
                OLD_JOURNAL_NAME, RECENT_JOURNAL_NAME, OTHER_JOURNAL_NAME, DUP_ROOM_NAME):
            library.remove(library.SCENARIOS / item["path"])
    advance = library.SCENARIOS / "examples" / "advance-at-15-00.json"
    if not advance.exists():
        ADVANCE_ENTRY = library.add(library.EXAMPLES / "advance.json",
                                    name="Advance at 15:00", group="Examples")
    TEST_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    TEST_SOURCE.write_text(json.dumps({
        "schemaVersion": 1,
        "name": TEST_NAME,
        "description": "A temporary scenario for the shell check.",
        "clock": {"start": "2026-11-05T08:00:00Z", "timeZone": "Europe/London"},
        "home": {"map": "../home.json", "profile": "Weekday"},
        "steps": [
            {"id": "s1", "at": "2026-11-05T08:00:00+00:00",
             "expect": {"target": "summary.title", "visible": True},
             "context": {"target": "22.0", "actual": "22.4"}},
            {"id": "s2", "at": "2026-11-05T08:01:00+00:00",
             "expect": {"target": "summary.title", "visible": True}},
            {"id": "s3", "at": "2026-11-05T08:02:00+00:00",
             "expect": {"target": "summary.title", "visible": True}},
        ],
    }, indent=2) + "\n", encoding="utf-8")
    data = json.loads(TEST_SOURCE.read_text(encoding="utf-8"))
    data["name"] = TEST_NAME_2
    TEST_SOURCE_2.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    USER_SOURCE.write_text(json.dumps({
        "schemaVersion": 1,
        "name": USER_NAME,
        "description": "A recorded UI request followed by a controller effect.",
        "clock": {"start": "2026-11-05T08:00:00Z", "timeZone": "Europe/London"},
        "home": {"map": "../home.json", "profile": "Weekday"},
        "steps": [
            {"id": "u1", "at": "2026-11-05T08:00:30+00:00",
             "user": {"action": "Operating Mode", "event": "Advance",
                      "label": "Advance on", "room": "Kitchen", "screen": "home",
                      "control": "advance", "gesture": "tap", "advance": "A", "seq": 1},
             "note": "seq 1: UI request — Advance on (home/advance/tap)"},
            {"id": "s2", "at": "2026-11-05T08:01:00+00:00",
             "expect": {"target": "summary.title", "visible": True}},
        ],
    }, indent=2) + "\n", encoding="utf-8")
    entries = [library.add(TEST_SOURCE, name=TEST_NAME, group=TEST_GROUP, brief=TEST_BRIEF),
               library.add(TEST_SOURCE_2, name=TEST_NAME_2, group=TEST_GROUP, brief=TEST_BRIEF)]
    library.add(USER_SOURCE, name=USER_NAME, group=TEST_GROUP)
    today = date.today().isoformat()
    entries.append(library.add(TEST_SOURCE, name=OLD_JOURNAL_NAME, group="Journal",
                               system=TEST_MAC, day="2020-01-01"))
    entries.append(library.add(TEST_SOURCE, name=RECENT_JOURNAL_NAME, group="Journal",
                               system=TEST_MAC, day=today))
    entries.append(library.add(TEST_SOURCE, name=OTHER_JOURNAL_NAME, group="Journal",
                               system=OTHER_MAC, day=today))
    return entries


def cleanup_library():
    global ADVANCE_ENTRY
    for entry in (TEST_ENTRY, TEST_ENTRY_2) + tuple(JOURNAL_ENTRIES) + tuple(EXTRA_ENTRIES):
        try:
            if entry:
                library.remove(library.SCENARIOS / entry["path"])
        except (SystemExit, FileNotFoundError):
            pass
    try:
        index = library.load_index()
        for item in list(index["scenarios"]):
            if item.get("group") == TEST_GROUP or item.get("name") == DUP_ROOM_NAME:
                library.remove(library.SCENARIOS / item["path"])
    except (SystemExit, FileNotFoundError):
        pass
    if ADVANCE_ENTRY:
        try:
            library.remove(library.SCENARIOS / ADVANCE_ENTRY["path"])
        except (SystemExit, FileNotFoundError):
            pass
        ADVANCE_ENTRY = None
    try:
        index = library.load_index()
        index["groups"] = [group for group in index.get("groups", []) if group != TEST_GROUP]
        library.save_index(index)
    except SystemExit:
        pass
    TEST_SOURCE.unlink(missing_ok=True)
    TEST_SOURCE_2.unlink(missing_ok=True)
    USER_SOURCE.unlink(missing_ok=True)
    if CONFIG_BACKUP is None:
        CONFIG.unlink(missing_ok=True)
    else:
        CONFIG.write_text(CONFIG_BACKUP, encoding="utf-8")
    if SETTINGS_BACKUP is None:
        SETTINGS.unlink(missing_ok=True)
    else:
        SETTINGS.write_text(SETTINGS_BACKUP, encoding="utf-8")
    TEST_CONFIG.unlink(missing_ok=True)
    if CONFIG_POINTER_BACKUP is None:
        CONFIG_POINTER.unlink(missing_ok=True)
    else:
        CONFIG_POINTER.write_text(CONFIG_POINTER_BACKUP, encoding="utf-8")
    for group in (TEST_GROUP, "Extra"):
        try:
            index = library.load_index()
            index["groups"] = [name for name in index.get("groups", []) if name != group]
            library.save_index(index)
        except SystemExit:
            pass
        try:
            (library.SCENARIOS / library.slug(group)).rmdir()
        except OSError:
            pass


TEST_ENTRY, TEST_ENTRY_2, *JOURNAL_ENTRIES = prepare_library()
EXTRA_ENTRIES = []

from PySide6.QtCore import QPoint, QTimer  # noqa: E402
from PySide6.QtGui import QShortcut  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTableWidgetSelectionRange  # noqa: E402
from allspeak.as_program import Program  # noqa: E402

failures = []
screenshot = Path(tempfile.gettempdir()) / "studio-shell-run.png"


def check(ok, text):
    print(("  OK: " if ok else "  FAIL: ") + text)
    if not ok:
        failures.append(text)


def symbol(program, name):
    return program.code[program.symbols[name]]


def value(program, name):
    record = symbol(program, name)
    holder = record.get("object")
    if holder is None:
        return None
    held = holder.getValue()
    return None if held is None else held.getContent()


def widget(program, name):
    return symbol(program, name)["object"].getValue()


app = QApplication([])
program = Program("studio.allspeak", testMode=False)
state = {"clicked": False, "done": False, "deadline": time.time() + 90, "prompt_path": None}


def fill_group():
    dialog = QApplication.activeModalWidget()
    if dialog is None:
        check(False, "the new-group dialog opened")
        return
    editor = dialog.findChild(QLineEdit)
    if editor is None:
        check(False, "the new-group dialog has a text field")
        dialog.reject()
        return
    editor.setText("Extra")
    dialog.accept()


def answer_confirm(accept):
    dialog = QApplication.activeModalWidget()
    if dialog is None:
        check(False, "the confirmation dialog opened")
        return
    if accept:
        dialog.accept()
    else:
        dialog.reject()


def fill_new_group(group):
    dialog = QApplication.activeModalWidget()
    if dialog is None:
        check(False, "the new-scenario group dialog opened")
        return
    editor = dialog.findChild(QLineEdit)
    if editor is None:
        check(False, "the new-scenario group dialog has a text field")
        dialog.reject()
        return
    editor.setText(group)
    dialog.accept()
    QTimer.singleShot(200, lambda: QApplication.activeModalWidget().reject()
                      if QApplication.activeModalWidget() else None)


def fill_duplicate(name):
    dialog = QApplication.activeModalWidget()
    if dialog is None:
        check(False, "the duplicate dialog opened")
        return
    editor = dialog.findChild(QLineEdit)
    if editor is None:
        check(False, "the duplicate dialog has a text field")
        dialog.reject()
        return
    editor.setText(name)
    dialog.accept()


def fill_brief(text, accept=True):
    dialog = QApplication.activeModalWidget()
    if dialog is None:
        check(False, "the brief dialog opened")
        return
    editor = dialog.findChild(QPlainTextEdit)
    if editor is None:
        check(False, "the brief dialog has a text area")
        dialog.reject()
        return
    editor.setPlainText(text)
    if accept:
        dialog.accept()
    else:
        dialog.reject()


def click_run():
    try:
        brief = value(program, "Brief")
        check(isinstance(brief, str) and "Advance is tapped" in brief,
              "the brief starts with the selected scenario's description")
        long_brief = "First paragraph: the Office advance at 15:00.\n\nSecond paragraph: the controller clears it at 18:00."
        QTimer.singleShot(300, lambda: fill_brief(long_brief, True))
        widget(program, "EditBriefBtn").click()
        app.processEvents()
        check(value(program, "Brief") == long_brief, "the saved multi-paragraph brief is kept")
        QTimer.singleShot(300, lambda: fill_brief("this text is cancelled", False))
        widget(program, "EditBriefBtn").click()
        app.processEvents()
        check(value(program, "Brief") == long_brief, "Cancel keeps the previous brief")

        widget(program, "DraftBtn").click()
        deadline = time.time() + 20
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.1)
            if "Brief saved" in widget(program, "StatusLabel").text():
                break
        check("Brief saved" in widget(program, "StatusLabel").text(),
              "Draft writes a prompt in prompt mode")
        prompt_path = value(program, "PromptPath")
        check(isinstance(prompt_path, str) and prompt_path.startswith("fixtures/local/drafts/"),
              "the prompt path is recorded")
        check(widget(program, "CopyPathBtn").isEnabled(), "Copy path is enabled after a prompt")
        widget(program, "CopyPathBtn").click()
        app.processEvents()
        copied = QApplication.clipboard().text()
        check(copied == prompt_path, f"Copy path puts the prompt path on the clipboard ({copied!r})")
        state["prompt_path"] = prompt_path

        steps = widget(program, "Steps")
        print(f"  ..    shell ready: {steps.rowCount()} rows x {steps.columnCount()} columns")
        check(steps.rowCount() == 13, "the advance example seeds 13 rows")
        check(value(program, "WindowX") == 55 and value(program, "WindowY") == 66,
              "the saved window position is restored")
        check(widget(program, "SystemBox").count() == 1,
              "the system selector has the configured system")
        check(widget(program, "SystemBox").currentText() == "Home",
              "the system selector shows the MAC's name")
        check(widget(program, "MboxBtn").isEnabled(),
              "the mbox button is enabled when a mailbox is configured")
        check(widget(program, "ResetJournalBtn").isEnabled(),
              "the reset button is enabled when a system is selected")
        check(widget(program, "ShowBtn").text() == "▶ Run",
              "the Show tab's paced run button is labelled Run")
        check(widget(program, "StepBtn").text() == "Step" and
              widget(program, "StepBtn").isEnabled(),
              "the Step button stays enabled so Space is always consumed")
        check(widget(program, "ShowBtn").toolTip() ==
              "Paced run in the embedded viewer; a Mark marker starts at the breakpoint and pauses.",
              "the paced run explains the breakpoint in its tooltip")
        check(widget(program, "StepBtn").toolTip() ==
              "Pause a running Show at the current step, or advance one step while paused (Space).",
              "Step explains pausing and manual advance in its tooltip")
        check(widget(program, "RefreshBtn").toolTip().startswith(
                  "Rebuild the Local system map"),
              "Refresh map explains that it rebuilds the local snapshot")
        source = (STUDIO / "studio.allspeak").read_text(encoding="utf-8")
        buttons = re.findall(r"^pushbutton (\w+)$", source, re.MULTILINE)
        check(len(buttons) >= 20, f"the source declares the Studio buttons ({len(buttons)})")
        for name in buttons:
            check(bool(widget(program, name).toolTip()),
                  f"{name} has a tooltip")
        shortcuts = widget(program, "StepBtn").findChildren(QShortcut)
        check(any(shortcut.key().toString() == "Space" for shortcut in shortcuts),
              "Space is bound to the Step button")
        widget(program, "StepBtn").click()
        app.processEvents()
        check(widget(program, "Win").isVisible(),
              "Step without a Show leaves the window open")
        check("Start a Show to use Step" in widget(program, "Log").toPlainText(),
              "Step explains that a Show is needed")
        for name in ("DuplicateBtn", "DuplicateRoomBtn", "RenameBtn", "DeleteRowsBtn"):
            check(widget(program, name).width() > 100,
                  f"{name} sits in the Scenarios left panel")
        tabs = widget(program, "MainTabs")
        check(tabs.count() == 3, "the main panel has Scenarios, Show and Statistics tabs")
        check([tabs.tabText(i) for i in range(tabs.count())] == ["Scenarios", "Show", "Statistics"],
              "the main tabs are named")
        check(tabs.currentIndex() == 1, "the Studio opens on the saved Show tab")
        check(not widget(program, "Steps").isColumnHidden(1),
              "the first Show visit shows the Mark column")
        tabs.setCurrentIndex(0)
        app.processEvents()
        check(widget(program, "Steps").isVisible(), "the table is visible on Scenarios")
        check(widget(program, "Steps").isColumnHidden(1),
              "the Scenarios tab hides the Mark column")
        for _ in range(5):
            app.processEvents()
            time.sleep(0.05)
        page = widget(program, "ScenariosPage")
        log = widget(program, "LogTabs")
        check(abs(log.width() - page.width()) <= 30,
              f"the Scenarios log spans the page ({log.width()} of {page.width()})")
        log_top = log.mapToGlobal(QPoint(0, 0)).y()
        for name in ("DuplicateBtn", "DuplicateRoomBtn", "RenameBtn", "DeleteRowsBtn"):
            button = widget(program, name)
            check(button.mapToGlobal(QPoint(0, button.height())).y() <= log_top + 2,
                  f"{name} sits above the Scenarios log")
        tabs.setCurrentIndex(1)
        app.processEvents()
        check(not widget(program, "Steps").isColumnHidden(1),
              "the Show tab shows the Mark column")
        check(widget(program, "ViewPane").isVisible(), "the Show tab shows the view pane")
        for _ in range(5):
            app.processEvents()
            time.sleep(0.05)
        pane = widget(program, "ViewPane")
        log = widget(program, "LogTabs")
        check(pane.height() >= widget(program, "Steps").height() + log.height() - 12,
              "the viewer fills the Show tab, including the space beside the log")
        check(abs(pane.width() - int(pane.height() * 0.5)) <= 4,
              f"the viewer follows viewerAspect ({pane.width()}x{pane.height()})")
        check(abs(log.width() - widget(program, "Steps").width()) <= 30,
              "the log panel sits under the table, not under the viewer")
        check(widget(program, "LogTabs").isVisible(),
              "the log panel stays visible on either tab")
        tabs.setCurrentIndex(0)
        app.processEvents()
        check(widget(program, "Steps").isColumnHidden(1),
              "returning to Scenarios hides the Mark column again")
        check(widget(program, "AddBatchBtn").text() == "+" and
              widget(program, "RemoveBatchBtn").text() == "-",
              "the batch add/remove buttons are condensed")
        check(value(program, "JournalSource") == "docs/examples",
              "the saved journal source is restored")
        check(value(program, "JournalDay") == "2026-11-06",
              "the saved journal day is restored")
        check(value(program, "JournalRange") == "14:00-19:00",
              "the saved time range is restored")
        scenarios = widget(program, "Scenarios")
        temperature = next((i for i in range(scenarios.count())
                            if scenarios.item(i).text() == "Kitchen temperature"), -1)
        if temperature >= 0:
            scenarios.setCurrentRow(temperature)
            scenarios.itemClicked.emit(scenarios.item(temperature))
            app.processEvents()
        check(steps.rowCount() == 5, "selecting the temperature scenario seeds 5 rows")
        delay = next((i for i in range(scenarios.count())
                      if scenarios.item(i).text() == "Delay demo"), -1)
        if delay >= 0:
            scenarios.setCurrentRow(delay)
            scenarios.itemClicked.emit(scenarios.item(delay))
            app.processEvents()
            check(steps.rowCount() == 5, "the delay demo seeds 5 rows")
            check(steps.item(2, 3).text() == "Delay", "the delay row has the Delay actor")
        local = next((i for i in range(scenarios.count())
                      if scenarios.item(i).text() == "Local system"), -1)
        if local >= 0:
            scenarios.setCurrentRow(local)
            scenarios.itemClicked.emit(scenarios.item(local))
            app.processEvents()
            check(steps.rowCount() == 3, "the local system snapshot seeds its starter steps")
        advance = next((i for i in range(scenarios.count())
                        if scenarios.item(i).text() == "Advance at 15:00"), -1)
        if advance >= 0:
            scenarios.setCurrentRow(advance)
            scenarios.itemClicked.emit(scenarios.item(advance))
            app.processEvents()
        check(steps.rowCount() == 13, "selecting Advance restores 13 rows")
        check(steps.horizontalHeaderItem(5).text() == "Event" and
              steps.horizontalHeaderItem(6).text() == "S" and
              steps.horizontalHeaderItem(8).text() == "T",
              "the Event column precedes the default action columns")

        groups = widget(program, "GroupBox")
        group_names = [groups.itemText(i) for i in range(groups.count())]
        check(TEST_GROUP in group_names, "the library group is in the group selector")
        office = next((i for i in range(groups.count())
                       if groups.itemText(i) == TEST_GROUP), -1)
        groups.setCurrentIndex(office)
        app.processEvents()
        check(widget(program, "StatusLabel").text() == "Group " + TEST_GROUP,
              "selecting a group filters the scenario list")
        office_names = [scenarios.item(i).text() for i in range(scenarios.count())]
        check("Delay demo" not in office_names and "Kitchen temperature" not in office_names,
              "other examples are hidden in a library group")
        check("Advance at 15:00" in office_names,
              "the current example is pinned under its name")
        check(TEST_NAME in office_names, "the library scenario is listed")
        journal_index = next((i for i in range(groups.count())
                              if groups.itemText(i) == "Journal"), -1)
        check(journal_index >= 0, "the Journal group is in the selector")
        groups.setCurrentIndex(journal_index)
        app.processEvents()
        journal_names = [scenarios.item(i).text() for i in range(scenarios.count())]
        check(OLD_JOURNAL_NAME not in journal_names,
              "the week filter hides an old journal")
        check(RECENT_JOURNAL_NAME in journal_names,
              "the week filter keeps a recent journal")
        check(OTHER_JOURNAL_NAME not in journal_names,
              "the system filter hides another system's journal")
        widget(program, "MoreBtn").click()
        app.processEvents()
        years = widget(program, "BrowseYears")
        year_texts = [years.item(i).text() for i in range(years.count())]
        check("2020" in year_texts, "More lists an older year")
        year_row = year_texts.index("2020")
        years.setCurrentRow(year_row)
        years.itemClicked.emit(years.item(year_row))
        app.processEvents()
        browsed = widget(program, "BrowseScenarios")
        brow_names = [browsed.item(i).text() for i in range(browsed.count())]
        check(OLD_JOURNAL_NAME in brow_names, "More lists the old journal")
        brow_row = brow_names.index(OLD_JOURNAL_NAME)
        browsed.setCurrentRow(brow_row)
        browsed.itemClicked.emit(browsed.item(brow_row))
        app.processEvents()
        check(widget(program, "BrowseOpenBtn").isEnabled(),
              "Open is enabled by a selected scenario")
        widget(program, "BrowseOpenBtn").click()
        app.processEvents()
        check(value(program, "ScenarioPath").endswith(JOURNAL_ENTRIES[0]["path"]),
              "opening a browsed scenario sets its path")
        check(steps.rowCount() == 3, "opening a browsed scenario loads its steps")
        check(not widget(program, "BrowseWin").isVisible(),
              "opening a browsed scenario closes the browser")
        check(OLD_JOURNAL_NAME in [scenarios.item(i).text()
                                   for i in range(scenarios.count())],
              "the browsed old journal is pinned under its name")
        QTimer.singleShot(300, lambda: fill_duplicate("Sunroom"))
        QTimer.singleShot(600, lambda: fill_duplicate(DUP_ROOM_NAME))
        widget(program, "DuplicateRoomBtn").click()
        deadline = time.time() + 10
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
            if widget(program, "StatusLabel").text() == "Duplicate for room complete":
                break
        check(widget(program, "StatusLabel").text() == "Duplicate for room complete",
              "duplicating an old journal for a room completes")
        dup_names = [scenarios.item(i).text() for i in range(scenarios.count())]
        check(DUP_ROOM_NAME in dup_names,
              "the room copy of an old journal is listed immediately")
        check("Current scenario" not in dup_names,
              "the room copy is listed under its own name")
        groups.setCurrentIndex(office)
        app.processEvents()
        office_row = next(i for i in range(scenarios.count())
                          if scenarios.item(i).text() == TEST_NAME)
        scenarios.setCurrentRow(office_row)
        scenarios.itemClicked.emit(scenarios.item(office_row))
        app.processEvents()
        check(TEST_BRIEF in value(program, "Brief"),
              "selecting a scenario loads its stored brief")
        check(steps.item(0, 2).text() == "08:00:00",
              "the Time column shows the event time, not the full ISO timestamp")
        check(steps.rowCount() == 3, "the temporary scenario has three rows")
        steps.selectRow(0)
        app.processEvents()
        check("target at the time: 22.0" in widget(program, "Inspector").toPlainText(),
              "the Step tab shows the heatlog target at the step's time")
        QTimer.singleShot(300, lambda: fill_duplicate("Shell duplicate"))
        widget(program, "DuplicateBtn").click()
        deadline = time.time() + 10
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
            if widget(program, "StatusLabel").text() == "Duplicate complete":
                break
        check(widget(program, "GroupBox").currentText() == TEST_GROUP,
              "duplicating a scenario stays in the current group")
        check("Shell duplicate" in [scenarios.item(i).text()
                                    for i in range(scenarios.count())],
              "the duplicate is listed in the current group")
        check(steps.item(0, 1).toolTip() == "Breakpoint: Show pauses here",
              "the Mark cell explains the breakpoint")
        steps.cellClicked.emit(0, 1)
        app.processEvents()
        check(steps.item(0, 1).text() == "●",
              "clicking the Mark cell sets the fast-forward marker")
        steps.cellClicked.emit(0, 1)
        app.processEvents()
        check(steps.item(0, 1).text() == "",
              "clicking the marked cell again clears it")
        steps.setRangeSelected(QTableWidgetSelectionRange(0, 0, 1, 10), True)
        app.processEvents()
        check(widget(program, "DeleteRowsBtn").isEnabled(),
              "Delete rows is enabled by a native multi-row selection")
        QTimer.singleShot(300, lambda: answer_confirm(False))
        widget(program, "DeleteRowsBtn").click()
        app.processEvents()
        check(steps.rowCount() == 3, "cancelling row deletion keeps all rows")
        QTimer.singleShot(300, lambda: answer_confirm(True))
        widget(program, "DeleteRowsBtn").click()
        app.processEvents()
        check(steps.rowCount() == 1, "the two selected rows are deleted")
        check(widget(program, "StatusLabel").text() == "Deleted 2 row(s)",
              "the row deletion reports its count")
        scenario_path = STUDIO / value(program, "ScenarioPath")
        saved = json.loads(scenario_path.read_text(encoding="utf-8"))
        check(saved["clock"]["start"] == "2026-11-05T08:02:00+00:00",
              "the clock start follows the first remaining row")
        check(saved["steps"][0]["id"] == "s1",
              "the remaining step is renumbered from one")
        check(steps.item(0, 0).text() == "s1",
              "the Steps table shows the renumbered id")
        steps.setRangeSelected(QTableWidgetSelectionRange(0, 0, 0, 10), True)
        app.processEvents()
        QTimer.singleShot(300, lambda: answer_confirm(True))
        widget(program, "DeleteRowsBtn").click()
        app.processEvents()
        check(steps.rowCount() == 0, "the remaining row can be deleted")
        check(widget(program, "DeleteScenarioBtn").isEnabled(),
              "a library scenario can be deleted")
        original_row = next(i for i in range(scenarios.count())
                            if scenarios.item(i).text() == TEST_NAME)
        scenarios.setCurrentRow(original_row)
        scenarios.itemClicked.emit(scenarios.item(original_row))
        app.processEvents()
        check(steps.rowCount() == 3, "the original scenario is ready for the room copy")
        QTimer.singleShot(300, lambda: fill_duplicate("Office"))
        QTimer.singleShot(600, lambda: fill_duplicate("Office global copy"))
        widget(program, "DuplicateRoomBtn").click()
        deadline = time.time() + 10
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
            if widget(program, "StatusLabel").text() == "Duplicate for room complete":
                break
        check(widget(program, "StatusLabel").text() == "Duplicate for room complete",
              "Duplicate for room completes")
        check("Office global copy" in [scenarios.item(i).text()
                                       for i in range(scenarios.count())],
              "the room copy is listed in the current group")
        check(steps.rowCount() == 3,
              "the room copy keeps the scenario's global steps")
        check("Filtered copy" in value(program, "Brief"),
              "the room copy's brief records the filter")
        copied_path = value(program, "ScenarioPath")
        if copied_path.startswith("fixtures/local/scenarios/"):
            EXTRA_ENTRIES.append(
                {"path": copied_path[len("fixtures/local/scenarios/"):]})
        widget(program, "RefreshScenariosBtn").click()
        app.processEvents()
        check(widget(program, "DeleteScenarioBtn").isEnabled(),
              "Delete stays enabled after refreshing scenarios")
        second_row = next(i for i in range(scenarios.count())
                          if scenarios.item(i).text() == TEST_NAME_2)
        scenarios.setCurrentRow(second_row)
        scenarios.itemClicked.emit(scenarios.item(second_row))
        app.processEvents()
        check(widget(program, "DeleteScenarioBtn").isEnabled(),
              "the second library scenario can also be deleted")
        widget(program, "RefreshScenariosBtn").click()
        app.processEvents()
        check(widget(program, "DeleteScenarioBtn").isEnabled(),
              "Delete stays enabled for the second scenario after refresh")
        QTimer.singleShot(300, lambda: answer_confirm(False))
        widget(program, "DeleteScenarioBtn").click()
        app.processEvents()
        check(widget(program, "StatusLabel").text() == "Delete cancelled",
              "cancelling the Delete confirmation leaves the scenario alone")
        check(TEST_NAME_2 in [scenarios.item(i).text() for i in range(scenarios.count())],
              "the scenario remains listed after cancelling Delete")

        widget(program, "AddBatchBtn").click()
        widget(program, "RunBatchBtn").click()
        deadline = time.time() + 40
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.1)
            if "Batch passed" in widget(program, "StatusLabel").text():
                break
        check("Batch passed" in widget(program, "StatusLabel").text(),
              "the shell runs the selected scenario in a batch")
        batch = widget(program, "BatchList")
        batch.setCurrentRow(0)
        widget(program, "RemoveBatchBtn").click()
        app.processEvents()
        check(batch.count() == 0, "the batch entry is removed after the run")

        QTimer.singleShot(300, fill_group)
        widget(program, "NewGroupBtn").click()
        deadline = time.time() + 10
        while time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
            names = [groups.itemText(i) for i in range(groups.count())]
            if "Extra" in names:
                break
        check("Extra" in names, "New group adds a folder to the selector")

        QTimer.singleShot(300, lambda: fill_new_group(TEST_GROUP))
        widget(program, "NewScenarioBtn").click()
        app.processEvents()
        check(value(program, "DraftGroup") == TEST_GROUP,
              "New offers the chosen destination group")
        check(steps.rowCount() == 0, "New clears the step table")
        check(value(program, "Brief") == "", "New clears the brief")
        check(not widget(program, "DeleteScenarioBtn").isEnabled(),
              "New is not deletable until it is saved")

        groups.setCurrentIndex(0)
        app.processEvents()
        advance = next((i for i in range(scenarios.count())
                        if scenarios.item(i).text() == "Advance at 15:00"), -1)
        if advance >= 0:
            scenarios.setCurrentRow(advance)
            scenarios.itemClicked.emit(scenarios.item(advance))
            app.processEvents()
        check(steps.rowCount() == 13, "returning to All restores Advance")
        user_row = next((i for i in range(scenarios.count())
                         if scenarios.item(i).text() == USER_NAME), -1)
        check(user_row >= 0, "the user-step scenario is listed")
        if user_row >= 0:
            scenarios.setCurrentRow(user_row)
            scenarios.itemClicked.emit(scenarios.item(user_row))
            app.processEvents()
            check(steps.rowCount() == 2, "the user scenario seeds two rows")
            check(steps.item(0, 3).text() == "PWA",
                  "the user step is acted by the PWA")
            check(steps.item(0, 4).text() == "Kitchen",
                  "the user step names its room")
            check(steps.item(0, 5).text() == "Advance",
                  "the user step's event is Advance")
            check("UI request — Advance on" in steps.item(0, 4).toolTip(),
                  "the user step's detail records the request")
            advance = next((i for i in range(scenarios.count())
                            if scenarios.item(i).text() == "Advance at 15:00"), -1)
            if advance >= 0:
                scenarios.setCurrentRow(advance)
                scenarios.itemClicked.emit(scenarios.item(advance))
                app.processEvents()
            check(steps.rowCount() == 13, "returning to Advance after the user-step check")
        all_names = [scenarios.item(i).text() for i in range(scenarios.count())]
        check(OLD_JOURNAL_NAME not in all_names,
              "the week filter applies in All")
        check(RECENT_JOURNAL_NAME in all_names,
              "a recent journal is listed in All")
        widget(program, "AddBatchBtn").click()
        app.processEvents()
        batch = widget(program, "BatchList")
        check(batch.count() == 1, "the batch list takes the selected scenario")
        check(batch.item(0).text() == "Advance at 15:00", "the batch entry is named")
        batch.setCurrentRow(0)
        widget(program, "RemoveBatchBtn").click()
        app.processEvents()
        check(batch.count() == 0, "the batch entry can be removed")
        widget(program, "RunBtn").click()
        state["clicked"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL: could not start the run: {exc}")
        failures.append("start the run")
        QApplication.quit()


def poll():
    if not state["clicked"] or state["done"]:
        return
    if time.time() > state["deadline"]:
        state["done"] = True
        print(f"  FAIL: timed out; status={widget(program, 'StatusLabel').text()!r}")
        failures.append("timeout")
        inspect()
        return
    try:
        running = value(program, "Running")
        status = widget(program, "StatusLabel").text()
        if running in (0, None) and ("run " in status or "validation" in status):
            state["done"] = True
            inspect()
    except Exception as exc:  # noqa: BLE001
        print(f"  ..    poll: {exc}")


def inspect():
    steps = widget(program, "Steps")
    log = widget(program, "Log").toPlainText()
    wire = widget(program, "WireLog").toPlainText()
    status = widget(program, "StatusLabel").text()
    print(f"  ..    status={status!r}")
    check("run passed" in status or "validation valid" in status,
          f"the run reports success ({status!r})")
    check(widget(program, "ErrorLabel").text() == "",
          "a passing run leaves the title row clear")
    results = [steps.item(row, 11).text() for row in range(steps.rowCount())]
    check(all(mark == "✓" for mark in results),
          f"all 13 result cells are ticks ({results})")
    check("run passed" in log, "the readable log carries the run summary")
    check('"event": "run.finished"' in wire, "the wire log carries the raw JSONL")
    check("artefacts:" in widget(program, "ArtifactsLog").toPlainText(),
          "the artefacts path is shown")
    try:
        widget(program, "Win").grab().save(str(screenshot))
        print(f"  ..    screenshot {screenshot}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ..    screenshot failed: {exc}")
    try:
        widget(program, "Win").close()
    except Exception:
        pass
    QApplication.quit()


QTimer.singleShot(4000, click_run)
timer = QTimer()
timer.timeout.connect(poll)
timer.start(1000)
program.start()
timer.stop()
if state.get("prompt_path"):
    (STUDIO / state["prompt_path"]).unlink(missing_ok=True)
saved = json.loads(SETTINGS.read_text(encoding="utf-8")) if SETTINGS.exists() else {}
check(saved.get("x") is not None and saved.get("width") is not None,
      "closing the Studio writes window geometry")
check(saved.get("tab") == 0, "closing the Studio keeps the active tab")
split = saved.get("scenariosSplit")
check(isinstance(split, list) and len(split) == 2,
      "closing the Studio keeps the splitter sizes")
check(saved.get("group") == "All", "closing the Studio keeps the selected group")
check(saved.get("scenario") == "fixtures/local/scenarios/examples/advance-at-15-00.json",
      "closing the Studio keeps the selected scenario")
check(saved.get("source") == "docs/examples",
      "closing the Studio keeps the journal source")
check(saved.get("day") == "2026-11-06", "closing the Studio keeps the journal day")
check(saved.get("range") == "14:00-19:00", "closing the Studio keeps the time range")
after = STUDIO_CONFIG.read_bytes() if STUDIO_CONFIG.exists() else None
check(after == STUDIO_CONFIG_BEFORE,
      "the shell check leaves the real studio-config.json alone")
cleanup_library()
print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("shell check passed")
