# RBR Studio

A desktop tool for building, validating and running UI test scenarios against
Room By Room.

**Status: runner and shell.** `scenario_runner/` executes a scenario JSON
against the real page; `studio.allspeak` is the AllSpeak/PySide shell with Run
wired to it. See `scenario_runner/README.md`; the design is in `docs/SPEC.md`;
the wireframe is `docs/MOCKUP.html`.

## Run it

```bash
cd tools/rbr-studio
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium

.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json
.venv/bin/python -m scenario_runner --scenario docs/examples/temperature.json
.venv/bin/python -m scenario_runner --scenario docs/examples/delay.json
```

## Packaged copy

Build a portable copy from this checkout:

```bash
cd tools/rbr-studio
./package-studio.sh
```

It writes `dist/rbr-studio-<stamp>.tar.gz`. Unpack it anywhere and run `./run-studio.sh`; the first run creates `.venv`, installs `requirements-studio.txt` and Playwright's Chromium, and asks for the root folder the controller's daily journal bundles arrive in (default `~/RBR-journal`). Name systems with `--system MAC=Name` (repeatable), or later with `configure-studio.py --system`; `configure-studio.py --show` prints the setting, `--inbox DIR` changes the root, and `--setup-only` installs and configures without opening the window. The development checkout can use the same launcher.

The package deliberately carries no `fixtures/local`, real `map.json`, `ai-config.json` or `.venv`: the first two belong to the machine, and the launcher creates them. Scenario testing is one role; the extracted bundles also carry the day's heating CSVs under `reports/heatlog/`, which is the input a statistics view can use later.

## The shell

`studio.allspeak` is the AllSpeak/PySide6 shell, built from the graphics
domain's own `table`, `logpane`, `panes` and `tabs`. It loads the example
scenarios; Run starts `scenario_runner` through the `process` domain, updates
the Result column from `step.finished`, and streams the JSONL into the Steps,
Wire, Console and Artifacts tabs. The Steps tab keeps its newest 2000 lines;
the trim runs from the shell's idle loop once a second, so a long run does
not grow the log without bound. A trim rewrites the text and therefore loses
the per-line colours of the lines it keeps. Validate uses `--validate-only`;
Stop terminates the child.

```bash
cd tools/rbr-studio
allspeak studio.allspeak
```

This uses the system `allspeak`/`pyside6`, not the runner venv; the Run and
Validate buttons use the venv created above. Run it from this directory so the
app's example paths and `.venv/bin/python` resolve.

**Show** runs the selected scenario headed — the PWA window opens — with a five-second pause at the end before the browser closes, the
virtual clock paced at the speed selector (1×, 60×, 120× or 300× scenario
seconds per real second), a 300 ms pause after each step, and repeated refresh
polls collapsed to `refresh ×50` / `refresh polls: N` summaries in Console. The
full console remains in the run's `console.log`.

A **Mark** marker is a breakpoint. Before starting, Show folds every controller
step before the marker into the base map in Python, sets the clock to the
marker and starts there; the page therefore begins with every room already
initialised, without replaying the day through the browser. Pre-marker UI
actions and expectations are skipped; only controller events are folded. Show pauses after
the marker. **Step** jumps the virtual clock to the next step instantly,
executes it, selects its row and scrolls it into view; the Inspector follows the
selection. **Space** is bound to the same Step action, so a paused Show can be
advanced from the keyboard. The Step button stays enabled so the shortcut
always consumes Space; a repeat while a step is in flight is ignored, and a
press outside a paused Show says so in the log instead of reaching another
control. **Show** again sends continue and restores automatic stepping at the
selected speed. A scenario without a marker runs as before. Run stays headless
and as fast as possible. The Show, Step and Run buttons carry tooltips, as does
the Mark cell of every row.

Headless check (starts the shell, switches scenario, runs Advance, inspects the
table and logs):

```bash
QT_QPA_PLATFORM=offscreen python3 tests/studio-shell-check.py
python3 tests/journal_check.py
python3 tests/package_check.py
.venv/bin/python tests/show_check.py
```

`tests/show_check.py` drives the runner's fold/breakpoint/step protocol with a
stub page driver, so it needs the runner venv (for the `playwright` import) but
no browser.

## Real system maps

Put the controller's `map.json` beside `studio.allspeak` — that is
`tools/rbr-studio/map.json`, which `.gitignore` already covers — then run
the snapshot tool:

```bash
cd tools/rbr-studio
python3 snapshot-map.py
# or copy a map from elsewhere:
python3 snapshot-map.py --source /path/to/map.json
```

It writes `fixtures/local/home.json` and `fixtures/local/smoke.json`. The
shell's **Refresh map** button runs the same snapshot and reloads **Local
system** if it is the selected scenario; otherwise restart the shell and the
scenario list gains it. The smoke scenario reports one room's name and
temperature; edit its `rooms` alias, `home.profile` and steps to exercise real
rooms.

When the studio directory is copied to another system, replace `map.json` with
that system's live map and click **Refresh map**. `fixtures/local/` is
gitignored, because a real map carries room names and sensor/relay ids.

It is a **snapshot**, not a live link: replace `map.json` and refresh again
after rooms or schedules change. The copy is disk-shaped, so the script adds
`relaysTotal`/`relaysFailed` and the status defaults the controller normally
adds in its reply; the page reads the result like any other controller map.
The public `docs/examples` fixtures remain synthetic.

## Scenario library, groups and batches

Scenarios live under `fixtures/local/scenarios/<group>/` and each may have a sibling `<stem>.brief.md`. `index.json` drives the shell. Selecting a scenario loads its brief into the sidebar editor, so **Draft scenario** edits the existing scenario with that brief as context. **New scenario** asks for the destination group (defaulting to the current library group, or `Unsorted` from All/Local), clears the table and brief, and opens the editor; **Delete scenario** opens a confirmation popup; accepting moves the scenario and its brief into `fixtures/local/.trash/`.

The right-hand Inspector has **Duplicate…**, **Duplicate for room…** and **Rename…** tools. Duplicate asks for a name and copies the scenario and its brief into the library; **Duplicate for room…** asks for a room and then a name, and the copy keeps only global steps (summary, sheet, profile and wire actions, raw pushes, connections and delays) plus the nominated room's steps. The outdoor sensor is kept as global context because it shows in the summary rather than a room card. Use it to turn a day-long journal scenario into a focused copy for one room; the description and brief record how many steps were dropped. Rename updates a library scenario's display name. Public examples are never renamed in place; duplicate one first.

The table uses AllSpeak's native multi-selection (`set selection of Steps to multiple`). Use Ctrl/Shift-click or drag to select one or more rows; **Delete rows** asks for confirmation and removes the selected steps from a library scenario. Cell editing and row insertion will use the same Tools row. The **Mark** column is clickable: it sets the scenario's single fast-forward marker on that step, or clears it when clicked again. The marker is stored as `marker: true` and is only writable on library scenarios; duplicate a public example first.

The wordy Action column has been replaced by short selectable fields: **S** status, **M** mode, **T** temperature, **H** humidity, **B** battery, **P** period, **A** advance and **R** relay. **Columns…** opens a checkbox window; the default is **S, M, T, R**. The choice is saved in `fixtures/local/studio-settings.json` and restored at startup. Status is a coloured dot, relay is a filled/open circle, and the numeric fields are plain values; the full names appear in the chooser and on the cells' tooltips. Mode uses **T** timed, **A** advance, **B** boost, **O** on and **X** off; all Action columns are centre-aligned. The table and Inspector are in a movable splitter, so the Inspector can be narrowed when its space is not needed.

The Studio remembers its window position and size, last selected group and scenario, and the last local journal source, journal day and time range. It writes them to `fixtures/local/studio-settings.json` when the window closes, including through the **Quit** button in the toolbar; a missing or stale setting falls back safely.

The three public examples are seeded into the **Examples** group as ordinary library scenarios on first start (`scenario_library.py seed-examples`, run by the shell). They are deletable copies; the public files remain in `docs/examples` for the README and tests. The seed marker is `fixtures/local/.examples-seeded`, so deleting an example does not bring it back on the next start; remove the marker or run `seed-examples --force` to restore it. **Local system** is still a generated snapshot and remains read-only.

The **Group** selector filters the library to one folder; **New group** creates another. The examples and the Local system snapshot are available under **All**, **Examples** and **Local**. A new draft goes into the selected library group, or `Unsorted` from All.

The **BATCH** panel is a working list: select a scenario and press **+ Batch**, remove an entry with **- Batch**, then **Run batch**. It runs each scenario in order through `batch_runner.py`, writes a record under `fixtures/local/batches/`, and appends each scenario's normal output to the log. The batch list is deliberately simple: a saved, named batch library comes later.

## Importing the controller's event journal

The controller records an append-only event journal (`doc/EVENT-JOURNAL.md`). Two command-line tools turn a day of it into a scenario; both are stdlib-only and need no controller runtime on the machine running them.

```bash
# local directory or mounted share
python3 journal_import.py --source /data/rbr-heating/events     --day 2026-11-06 --dest fixtures/local/journal/qed6-2026-11-06     --archive fixtures/local/journal/qed6-2026-11-06.tar.gz

# generate a scenario from the bundle
python3 journal_to_scenario.py --bundle fixtures/local/journal/qed6-2026-11-06     --from 07:00 --to 09:30     --out fixtures/local/scenarios/journal/kitchen-morning.json     --name "Kitchen morning"
```

For a local source, `journal_import.py --heatlog-root DIR` copies the day's heating CSVs into `reports/heatlog/` as well; when the source directory is named `events`, its parent is used automatically.

A bundle contains `manifest.json`, `events/YYYY/MM/YYYY-MM-DD.jsonl`, the `maps/` snapshots the day references, and — when heat logging is enabled — the day's `reports/heatlog/<room>/YYYY/MM/DD.csv` files. It is the transport-neutral unit; the same bundle can come from a local copy, a downloaded archive, an email attachment or the RBR cloud. The heating CSVs give a future statistics view the same day's outcomes without a second transfer; `journal_to_scenario.py` ignores them. `journal_to_scenario.py` uses the latest map snapshot at or before the window start, seeds the state that existed before the window, drops unchanged sensor readings and duplicate room states, and writes controller steps plus visible expectations. It does not replay UI requests as taps: the controller saw the request, not the gesture. The controller effects are included.

The Studio's **Import journal…** button runs `journal_ingest.py`, which chains those two tools and adds the result to the **Journal** group. The source prompt accepts a bundle, a raw `.jsonl`, or a local journal root; the day and window are optional when the source already names them. Everything reads local files, so the Studio needs no network access to the controller.

### Emailed bundles

`journal-export.py` can email each daily bundle (opt-in through `journal-export-config.json`; `rbr-setup.sh` asks when it installs the timer). The subject is `RBR journal <MAC> <YYYY-MM-DD>`, so a mail filter can match each system's MAC and save its `.tar.gz` attachments under `~/RBR-journal/<MAC>/`. The Studio scans that root when it starts:

- default root: `~/RBR-journal` (per-system subfolders are scanned)
- system names: `./run-studio.sh --system 00:e0:27:5b:31:40=Home`, repeatable; stored in `studio-config.json`'s `systems` map
- packaged/configured copy: the inbox path in `studio-config.json`, written by `run-studio.sh`/`configure-studio.py`
- override: write the path as one line in `fixtures/local/journal-inbox`
- by hand: `python3 journal_inbox.py --scan --inbox DIR`

Each unseen archive is extracted into `fixtures/local/journal/<MAC-or-system>-<day>/`, converted into a whole-day scenario and added to the **Journal** group, so the day is in the list when the window opens. The MAC is the stable folder key; a name from the `systems` map is used in the scenario name (`Journal 2026-11-06 — Home`), falling back to the controller's system name. The extraction keeps the bundle's `events/`, `maps/` and `reports/heatlog/` trees, so the statistics data sits beside the scenario. `fixtures/local/journal/inbox-seen.json` keeps the archive hashes; a rescan does nothing, and a corrected bundle (a new hash) is imported. A bundle that cannot be converted is recorded as failed rather than retried every start. The inbox file is left alone, so the mail filter owns its own retention.

### Extracting from an mbox

If the mail client keeps the messages in an mbox rather than saving attachments, `journal_mbox.py` reads the mailbox and writes each valid bundle into `<root>/<MAC>/`:

```bash
python3 journal_mbox.py --mbox ~/Mail/RBR-journal --dry-run
python3 journal_mbox.py --mbox ~/Mail/RBR-journal
python3 journal_mbox.py --mbox ~/Mail/RBR-journal --remove
```

The root is the same one the Studio scans (`studio-config.json`, the pointer file, or `~/RBR-journal`). The MAC comes from the subject, with the bundle manifest as a fallback. The `mailboxes` path may be an mbox file, a folder of mboxes, or a Thunderbird profile: a Thunderbird profile is searched for mbox files whose names contain `RBR` or `journal` (pass `--all-mailboxes` to scan every mbox); a plain folder of mboxes is scanned as it is. Identical files are skipped; a different file with the same name gets a `-2` suffix. Without `--remove` the mailbox is untouched; with it, messages whose attachments were all handled are removed and the mbox is rewritten. A message with an invalid attachment is left alone.

### Systems and mailboxes

The sidebar starts with a **System** selector, filled from the `systems` map in `studio-config.json`, and an **Import mbox** button. The mailbox for the selected MAC comes from the same file:

```json
{
  "journalInbox": "~/RBR-journal",
  "systems": {
    "00:e0:27:5b:31:40": "Home"
  },
  "mailboxes": {
    "00:e0:27:5b:31:40": "~/Mail/RBR-journal"
  }
}
```

Edit the file by hand, or set the entries with `configure-studio.py --system MAC=Name --mailbox MAC=PATH` (both repeatable). The button runs `journal_mbox.py --system <MAC> --list --limit 5`, which extracts new attachments into `~/RBR-journal/<MAC>/` and fills **Available journals** with the five newest filenames; the Studio then scans the inbox and adds new scenarios to the **Journal** group. Selecting a name there shows it in the log and status line.

**Reset today** forgets the selected system's imported journal for today: it removes the Studio state, extracted bundle, generated scenario and inbox archive, but leaves the mbox alone. Click **Import mbox** afterwards to extract and import today's attachment again. The command is also available directly:

```bash
python3 journal_inbox.py --reset --system 00:e0:27:5b:31:40
```

In the **Batch** panel, the add and remove controls are one row, **+ Batch -**.

### Send a bundle now

The PWA's **Send journal now** row under the hamburger asks the controller to flush the journal, export today up to that moment and email the result. The controller writes those requests under `exports/requests/` and marks them as partial, so they do not overwrite the daily export. In RBR Studio a partial bundle is imported as its own scenario with the time in the name (`Journal 2026-11-06 14:22:10 — Home`); it is not treated as a duplicate of the full day.

The generated scenario is ordinary RBR Studio JSON, so `--validate-only`, the shell, batches and AI editing all work on it. Keep windows short enough to stay under `--max-steps` (default 5000); a full day of frequent readings is usually more than a UI test needs.

The importer never writes to the controller and only reads local files. `--source` is the path to a journal root, a raw day, or a bundle already copied or mounted locally.

## AI authoring

The shell's **Draft scenario** button calls `ai-draft.py`. It builds a prompt
from the scenario schema, the target catalogue, a reduced summary of the live
map, the worked examples and the currently selected scenario; the provider
returns one scenario object. The helper then fills in `home.map`/`home.profile`,
validates the result with the runner's own `prepare`, and adds it to the local
library. The AI never runs a scenario; Run remains a separate action.

Configure the provider in `ai-config.json` (copy `ai-config.example.json`; the
real file is gitignored):

```bash
cp ai-config.example.json ai-config.json
```

### Reasonix Studio — the default

The default provider is `prompt`. Click **Edit brief…**, write at any length in the text area, and choose OK to save it (Cancel keeps the previous brief). Then press **Draft scenario**. The helper writes a complete prompt to
`fixtures/local/drafts/<date>-brief.prompt.md` and stops. The **Copy path** button
beside **Draft scenario** copies that prompt file path to the system clipboard
with `clipboard copy`, ready to paste into Reasonix or another AI. Give that file to
Reasonix Studio — or ask Reasonix in the session, which can read the brief and
the workspace directly. Save the reply and validate/install it:

```bash
python3 ai-draft.py --check fixtures/local/drafts/reply.json --name "Office advance"
```

Or let Reasonix write the library file and run `--check` itself. Click
**↻ Scenarios** in the shell, select the new entry, and Run.

For an edit, select the scenario first: the Draft button passes it with
`--scenario`, so the prompt contains the current JSON. The helper writes a new
version plus a `*.diff` file; review it, then delete the old version if you do
not want both.

### Claude CLI

Set `"provider": "claude"` in `ai-config.json`. The default command is:

```json
["claude", "-p", "--output-format", "json", "--permission-mode", "plan"]
```

`Draft scenario` runs the installed CLI, reads its `result` envelope, extracts
the scenario and validates it. No API key lives in the app; the CLI's own auth
is used. Plan mode keeps it from editing files. The default command can be
overridden under `providers.claude.command`.

### Reasonix Command Line

Set `"provider": "reasonix"` and put the CLI's print command under
`providers.reasonix.command`:

```json
{
  "provider": "reasonix",
  "providers": {
    "reasonix": {
      "command": ["reasonix", "…its print/exec flags…"],
      "timeout": 240
    }
  }
}
```

The contract is simple: the prompt goes to the command on stdin, and the
scenario JSON comes back on stdout. No Reasonix CLI is installed on this
machine, so this path is configured but not exercised here; the same
`command` provider *is* exercised with a stand-in executable, which is also
how the Claude envelope path is checked.

### Any other CLI

Use `"provider": "command"` and put the command under
`providers.command.command`. Anything that accepts a prompt on stdin and prints
JSON on stdout works. There is no HTTP provider in the first version; a small
command wrapper is the integration point.

### What is sent, and what is not

The prompt contains room names, profile names, `has_relay`/`has_trv` booleans,
the schema, the target catalogue, the examples and the current scenario. It does
**not** contain sensor/relay ids, credentials, the full map or the live
temperature values. A remote provider (Claude, a cloud CLI) does see the room
and profile names. Validation, review and the explicit Run are the safety
boundary.

## Docs

- `docs/SPEC.md` — the design: model, execution, controller stub, targets, UX,
  AI authoring, packaging, roadmap.
- `docs/PROTOCOL.md` — the JSONL contract between the PySide app and the runner.
- `docs/scenario.schema.json` — machine-readable scenario schema.
- `docs/examples/` — the worked scenarios, including the short demo-delay example.
- `docs/MOCKUP.html` — a static wireframe of the main window.

The app is an AllSpeak/PySide6 graphics app in the same family as `desktop/`.
The runner is a separate Python process using Playwright for Python; no Node
runtime is needed on the machine running the studio.
