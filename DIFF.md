# What to do

- **Use the new directory.** The application and its directory are now **RBR Studio**, under `tools/rbr-studio/`. Any local alias, script or shell history pointing at `tools/scenario-studio` needs updating; `git mv` carried the files and their history across.
- **Rebuild the portable package** from the new path:

      cd tools/rbr-studio
      ./package-studio.sh

  The archive is still `dist/rbr-studio-<stamp>.tar.gz`; unpack it anywhere and run `./run-studio.sh`.
- **Restart RBR Studio** to see the new window and toolbar name. Its configuration, scenario library and extracted journal bundles are unchanged; they live under `tools/rbr-studio/fixtures/local/`.
- **Rerun `./run-studio.sh` if you had already created `.venv` in the old directory.** A venv records absolute paths in its scripts, so the moved copy cannot run its own `pip`; the launcher now detects that and replaces it automatically, then installs the requirements again.
- **The run and cache directories moved** from `~/.local/share/rbr-scenario-studio` and `~/.cache/rbr-scenario-studio` to `~/.local/share/rbr-studio` and `~/.cache/rbr-studio`. Old artefacts stay where they are; nothing reads them.
- **The controller is unaffected.** It still writes and emails bundles for RBR Studio; the bundle format and `reports/heatlog/` contents are unchanged by the rename.

# What changed

- **The product name is RBR Studio.** The window title, toolbar brand, docs, public architecture/testing pages, tests, package text, script names and `studio.allspeak` script name now use it.
- **The checkout path is `tools/rbr-studio/`.** All tracked references and `.gitignore` rules moved with it; the package launcher and tests use their own locations, so they need no absolute paths.
- **Data locations.** The scenario runner's default artefacts directory and the Playwright runtime cache now use `rbr-studio`, matching the package name.
- **No behavioural change.** The journal bundle, inbox scanner, package bootstrap and scenario runner are the same code under the new name.
- **A moved `.venv` is detected and recreated.** Console scripts in a venv contain the absolute path of the directory that created them; after the rename they cannot run. `run-studio.sh` checks its venv's `pip` shebang (or a marker written on creation) and replaces a stale one, and uses `python -m pip` so the stale script cannot block the repair.

# Try it

```bash
cd tools/rbr-studio
./run-studio.sh
python3 tests/journal_check.py
python3 tests/package_check.py
```

`tests/unit/run-unit-tests.sh` still includes `journal_export_test`; its `STUDIO` path now points at `tools/rbr-studio`.
