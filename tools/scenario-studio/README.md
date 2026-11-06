# Scenario Studio

A desktop tool for building, validating and running UI test scenarios against
Room By Room.

**Status: runner and shell.** `scenario_runner/` executes a scenario JSON
against the real page; `studio.allspeak` is the AllSpeak/PySide shell with Run
wired to it. See `scenario_runner/README.md`; the design is in `docs/SPEC.md`;
the wireframe is `docs/MOCKUP.html`.

## Run it

```bash
cd tools/scenario-studio
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium

.venv/bin/python -m scenario_runner --scenario docs/examples/advance.json
.venv/bin/python -m scenario_runner --scenario docs/examples/temperature.json
.venv/bin/python -m scenario_runner --scenario docs/examples/delay.json
```

## The shell

`studio.allspeak` is the AllSpeak/PySide6 shell, built from the graphics
domain's own `table`, `logpane`, `panes` and `tabs`. It loads the example
scenarios; Run starts `scenario_runner` through the `process` domain, updates
the Result column from `step.finished`, and streams the JSONL into the Steps,
Wire, Console and Artifacts tabs. Validate uses `--validate-only`; Stop
terminates the child.

```bash
cd tools/scenario-studio
allspeak studio.allspeak
```

This uses the system `allspeak`/`pyside6`, not the runner venv; the Run and
Validate buttons use the venv created above. Run it from this directory so the
app's example paths and `.venv/bin/python` resolve.

**Demo** runs the selected scenario headed — the PWA window opens — with the
virtual clock paced at the speed selector (1×, 60×, 120× or 300× scenario
seconds per real second), a 300 ms pause after each step, and repeated refresh
polls collapsed to `refresh ×50` / `refresh polls: N` summaries in Console. The
full console remains in the run's `console.log`. Run stays headless and as fast
as possible.

Headless check (starts the shell, switches scenario, runs Advance, inspects the
table and logs):

```bash
QT_QPA_PLATFORM=offscreen python3 tests/studio-shell-check.py
python3 tests/journal_check.py
```

## Real system maps

Put the controller's `map.json` beside `studio.allspeak` — that is
`tools/scenario-studio/map.json`, which `.gitignore` already covers — then run
the snapshot tool:

```bash
cd tools/scenario-studio
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

The Studio remembers its window position and size, last selected group and scenario, and the last SSH source, journal day and time range. It writes them to `fixtures/local/studio-settings.json` when the window closes, including through the **Quit** button in the toolbar; a missing or stale setting falls back safely.

The three public examples are seeded into the **Examples** group as ordinary library scenarios on first start (`scenario_library.py seed-examples`, run by the shell). They are deletable copies; the public files remain in `docs/examples` for the README and tests. The seed marker is `fixtures/local/.examples-seeded`, so deleting an example does not bring it back on the next start; remove the marker or run `seed-examples --force` to restore it. **Local system** is still a generated snapshot and remains read-only.

The **Group** selector filters the library to one folder; **New group** creates another. The examples and the Local system snapshot are available under **All**, **Examples** and **Local**. A new draft goes into the selected library group, or `Unsorted` from All.

The **BATCH** panel is a working list: select a scenario and press **+ Batch**, remove an entry with **- Batch**, then **Run batch**. It runs each scenario in order through `batch_runner.py`, writes a record under `fixtures/local/batches/`, and appends each scenario's normal output to the log. The batch list is deliberately simple: a saved, named batch library comes later.

## Importing the controller's event journal

The controller records an append-only event journal (`doc/EVENT-JOURNAL.md`). Two command-line tools turn a day of it into a scenario; both are stdlib-only and need no controller runtime on the machine running them.

```bash
# local directory or mounted share
python3 journal_import.py --source /data/rbr-heating/events     --day 2026-11-06 --dest fixtures/local/journal/qed6-2026-11-06     --archive fixtures/local/journal/qed6-2026-11-06.tar.gz

# same network, over SSH (runs only `cat` on known paths)
python3 journal_import.py --ssh linaro@192.168.1.20     --ssh-root /data/rbr-heating/events --day 2026-11-06     --dest fixtures/local/journal/qed6-2026-11-06

# generate a scenario from the bundle
python3 journal_to_scenario.py --bundle fixtures/local/journal/qed6-2026-11-06     --from 07:00 --to 09:30     --out fixtures/local/scenarios/journal/kitchen-morning.json     --name "Kitchen morning"
```

A bundle contains `manifest.json`, `events/YYYY/MM/YYYY-MM-DD.jsonl` and the `maps/` snapshots the day references. It is the transport-neutral unit; the same bundle can come from a local copy, SSH, a downloaded archive or, later, an email attachment or the RBR cloud. `journal_to_scenario.py` uses the latest map snapshot at or before the window start, seeds the state that existed before the window, drops unchanged sensor readings and duplicate room states, and writes controller steps plus visible expectations. It does not replay UI requests as taps: the controller saw the request, not the gesture. The controller effects are included.

The Studio's **Import journal…** button runs `journal_ingest.py`, which chains those two tools and adds the result to the **Journal** group. The source prompt accepts a bundle, a raw `.jsonl`, a local journal root, `user@host` (using `/data/rbr-heating/events`), or `user@host:/journal-root`; the day and window are optional when the source already names them. SSH uses the operating system's client, agent and key, so no SSH credential belongs in `credentials` or in the Studio. Do not add SSH secrets to the controller's existing `credentials` file: that file is fetched from the cloud, backed up, and already carries broker and mail secrets. Use a dedicated key, or a separate 0600 file outside `credentials` if a password is unavoidable.

The generated scenario is ordinary Scenario Studio JSON, so `--validate-only`, the shell, batches and AI editing all work on it. Keep windows short enough to stay under `--max-steps` (default 5000); a full day of frequent readings is usually more than a UI test needs.

The importer never writes to the controller. For SSH it runs `ssh host cat <path>` and captures the file, using the machine's own `ssh` client with `BatchMode=yes`; it uses a key or an agent and will not prompt for a password. `--ssh-bin` and `--ssh-key` are there for non-default setups. The default remote root is `/data/rbr-heating/events`; use `user@host:/other/root` if the controller's journal lives elsewhere (for example `/home/qed6/heating-data/events`). This is deliberate: a GUI import should not need a password stored in the application. `--source` is the simplest path when the journal is already copied or mounted locally.

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
