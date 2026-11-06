"""Headless check for the Scenario Studio shell.

Starts studio.allspeak offscreen, switches scenario, clicks Run, waits for the
runner child to finish, and asks the table and logs what they hold.

    cd tools/scenario-studio
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
            {"id": "s1", "at": "08:00",
             "expect": {"target": "summary.title", "visible": True}},
        ],
    }, indent=2) + "\n", encoding="utf-8")
    data = json.loads(TEST_SOURCE.read_text(encoding="utf-8"))
    data["name"] = TEST_NAME_2
    TEST_SOURCE_2.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return (library.add(TEST_SOURCE, name=TEST_NAME, group=TEST_GROUP, brief=TEST_BRIEF),
            library.add(TEST_SOURCE_2, name=TEST_NAME_2, group=TEST_GROUP, brief=TEST_BRIEF))


def cleanup_library():
    for entry in (TEST_ENTRY, TEST_ENTRY_2):
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

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit  # noqa: E402
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
            check(steps.item(2, 2).text() == "Delay", "the delay row has the Delay actor")
            check("wait 2 s" in steps.item(2, 4).text(), "the delay row shows its seconds")
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
        check(widget(program, "DeleteScenarioBtn").isEnabled(),
              "a library scenario can be deleted")
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
    results = [steps.item(row, 6).text() for row in range(steps.rowCount())]
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
cleanup_library()
print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("shell check passed")
