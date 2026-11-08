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
import sys
import tempfile
import time
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
CONFIG = STUDIO / "ai-config.json"
CONFIG_BACKUP = CONFIG.read_text(encoding="utf-8") if CONFIG.exists() else None
CONFIG.write_text('{"provider": "prompt"}\n', encoding="utf-8")
SETTINGS = library.LOCAL / "studio-settings.json"
SETTINGS_BACKUP = SETTINGS.read_text(encoding="utf-8") if SETTINGS.exists() else None
SETTINGS.write_text(json.dumps({
    "x": 55, "y": 66, "width": 1000, "height": 700,
    "group": "All",
    "scenario": "fixtures/local/scenarios/examples/advance-at-15-00.json",
    "source": "docs/examples", "day": "2026-11-06", "range": "14:00-19:00",
}), encoding="utf-8")
STUDIO_CONFIG = STUDIO / "studio-config.json"
STUDIO_CONFIG_BEFORE = STUDIO_CONFIG.read_bytes() if STUDIO_CONFIG.exists() else None
TEST_CONFIG = library.LOCAL / "shell-check-config.json"
TEST_CONFIG.parent.mkdir(parents=True, exist_ok=True)
TEST_CONFIG.write_text(json.dumps({
    "systems": {"00:e0:27:5b:31:40": "Home"},
    "mailboxes": {"00:e0:27:5b:31:40": str(STUDIO / "fixtures" / "local" / "shell-check.mbox")},
}), encoding="utf-8")
CONFIG_POINTER = library.LOCAL / "studio-config-path"
CONFIG_POINTER_BACKUP = CONFIG_POINTER.read_text(encoding="utf-8") if CONFIG_POINTER.exists() else None
CONFIG_POINTER.write_text(str(TEST_CONFIG), encoding="utf-8")


def prepare_library():
    index = library.load_index()
    for item in list(index["scenarios"]):
        if item.get("group") == TEST_GROUP:
            library.remove(library.SCENARIOS / item["path"])
    TEST_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    TEST_SOURCE.write_text(json.dumps({
        "schemaVersion": 1,
        "name": TEST_NAME,
        "description": "A temporary scenario for the shell check.",
        "clock": {"start": "2026-11-05T08:00:00Z", "timeZone": "Europe/London"},
        "home": {"map": "../home.json", "profile": "Weekday"},
        "steps": [
            {"id": "s1", "at": "2026-11-05T08:00:00+00:00",
             "expect": {"target": "summary.title", "visible": True}},
            {"id": "s2", "at": "2026-11-05T08:01:00+00:00",
             "expect": {"target": "summary.title", "visible": True}},
            {"id": "s3", "at": "2026-11-05T08:02:00+00:00",
             "expect": {"target": "summary.title", "visible": True}},
        ],
    }, indent=2) + "\n", encoding="utf-8")
    data = json.loads(TEST_SOURCE.read_text(encoding="utf-8"))
    data["name"] = TEST_NAME_2
    TEST_SOURCE_2.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return (library.add(TEST_SOURCE, name=TEST_NAME, group=TEST_GROUP, brief=TEST_BRIEF),
            library.add(TEST_SOURCE_2, name=TEST_NAME_2, group=TEST_GROUP, brief=TEST_BRIEF))


def cleanup_library():
    for entry in (TEST_ENTRY, TEST_ENTRY_2) + tuple(EXTRA_ENTRIES):
        try:
            if entry:
                library.remove(library.SCENARIOS / entry["path"])
        except (SystemExit, FileNotFoundError):
            pass
    try:
        index = library.load_index()
        index["groups"] = [group for group in index.get("groups", []) if group != TEST_GROUP]
        library.save_index(index)
    except SystemExit:
        pass
    TEST_SOURCE.unlink(missing_ok=True)
    TEST_SOURCE_2.unlink(missing_ok=True)
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


TEST_ENTRY, TEST_ENTRY_2 = prepare_library()
EXTRA_ENTRIES = []

from PySide6.QtCore import QTimer  # noqa: E402
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
        check(widget(program, "ShowBtn").text() == "Show",
              "the paced playback button is labelled Show")
        check(widget(program, "StepBtn").text() == "Step" and
              widget(program, "StepBtn").isEnabled(),
              "the Step button stays enabled so Space is always consumed")
        check(widget(program, "ShowBtn").toolTip() ==
              "Headed, paced playback; a Mark marker starts at the breakpoint and pauses.",
              "Show explains the breakpoint in its tooltip")
        check(widget(program, "StepBtn").toolTip() ==
              "Advance one step while Show is paused at a breakpoint (Space).",
              "Step explains manual advance and Space in its tooltip")
        shortcuts = widget(program, "StepBtn").findChildren(QShortcut)
        check(any(shortcut.key().toString() == "Space" for shortcut in shortcuts),
              "Space is bound to the Step button")
        widget(program, "StepBtn").click()
        app.processEvents()
        check(widget(program, "Win").isVisible(),
              "Step without a Show leaves the window open")
        check("Start a Show to use Step" in widget(program, "Log").toPlainText(),
              "Step explains that a Show is needed")
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
        check(steps.horizontalHeaderItem(5).text() == "S" and
              steps.horizontalHeaderItem(7).text() == "T",
              "the default action columns are S, M, T and R")

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
        check("Advance at 15:00" not in office_names, "examples are hidden in a library group")
        check(TEST_NAME in office_names, "the library scenario is listed")
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
    results = [steps.item(row, 10).text() for row in range(steps.rowCount())]
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
