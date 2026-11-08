# What to do

- **Restart RBR Studio** (`./run-studio.sh`). The Studio's `.venv` has been upgraded to `allspeak-ai 2611082058`, which supplies the keyboard shortcut.
- Open a scenario with a **Mark** marker and press **Show**. Show folds the steps before the marker into the base map, starts at the marker and pauses there; **Step** or **Space** advances one step, and **Show** again resumes the selected pace.
- No controller, PWA or deploy step is needed.

# What changed

- **Safe start:** `--fold-to-marker` replays every pre-breakpoint controller step into the base map in Python, sets the clock to the marker and starts there. The selected room (and every other room) is already initialised, so no earlier events need to reach the browser. The source scenario is untouched; the run snapshot is trimmed and the log reports `folded N controller step(s) and skipped M pre-breakpoint step(s)`.
- **Breakpoint:** the marker now pauses a Show run after it executes. The runner emits `run.paused`; the Studio enables **Step** and **Show**, selects the step's row, scrolls it into view and shows it in the Inspector.
- **Step:** jumps the virtual clock to the next step instantly, executes it and pauses again. **Space** is bound to the same action with `set the shortcut of StepBtn to Space`. The Step button now stays enabled so the shortcut always consumes Space; a `Stepping` flag ignores a rapid repeat, and a press outside a paused Show logs `Start a Show to use Step.` instead of falling through to another button. **Show** again sends `continue`, restoring automatic advance at the speed selector.
- The runner gains `--fold-to-marker`, `--pause-at-marker`, `step` / `continue` stdin commands and the `run.paused` event. Pre-breakpoint UI actions and expectations are skipped; only controller events are folded.
- The Show, Step and Run buttons and the Mark cell carry tooltips. Row selection and scrolling use the new AllSpeak `select row` / `scroll to row` and `set the tooltip of` statements; the row-selection request is completed in `REQUESTS.md`.

# Try it

- Use the **Bedroom 1** journal scenario and its marker at `s160`; Show should log the fold, pause after `s160`, and Step through the rest.
- `tools/rbr-studio/.venv/bin/python tools/rbr-studio/tests/show_check.py`
- `python3 tools/rbr-studio/tests/journal_check.py`
- `cd tools/rbr-studio && QT_QPA_PLATFORM=offscreen python3 tests/studio-shell-check.py`
