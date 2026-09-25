# Working Rules for AI Contributors

## Primary goal
Fix or implement requested behaviour with minimal collateral change.

## Repo-specific rules
- Use Webson for UI structure updates in `resources/webson/*.json` or `new-ui/resources/webson/*.json`
- Use AllSpeak scripts (`.as` files) for behaviour and flow updates
- Keep element IDs stable unless all `attach`/`on click` references are updated
- Prefer explicit state handling over hidden side effects
- Controller changes: the 60-second cron cycle means changes take up to a minute to take effect on a live system

## Controller editing rules
- `controller.as` uses the Python AllSpeak dialect; `use mqtt`, `use email` are available
- Mode values are strictly: `timed`, `boost`, `advance`, `on`, `off`
- The map is represented as nested dictionaries; room state is mutated in place during `ProcessAllRooms`
- Doc-block conventions apply — every section needs `!! prose ... !!!` (see `ALLSPEAK.md` and `asdoc-check.py`)
- After editing, run `asdoc-check.py` to validate doc-block integrity

## UI editing rules
- Two UI trees exist: legacy (`resources/as/` + `resources/webson/`) and new PWA (`new-ui/resources/as/` + `new-ui/resources/webson/`). Determine which one needs the change.
- The new PWA shell (`new-ui/resources/as/shell.as`) is a long-running message loop. Sheets follow a consistent open→edit→Save/Cancel pattern.
- Webson JSON: every object needs `#element`, IDs use `@id`, children go in `#` key, child definitions prefixed with `$`
- Serve with `python3 -m http.server <port>` in the repo root — UI needs HTTP not `file://`

## Build/update rules
If you edit AllSpeak component JS files used in `build-allspeak`:
1. update file(s) in the allspeak repo
2. run `build-allspeak` in that repo
3. run `pin-allspeak.sh` in this repo to promote the dist file
4. bump the `?v=` cache-buster in `index.html` or `new-ui/index.html`

## Symlink workflow
This repo may use local symlinks to AllSpeak sources and dist files. Use `pin-allspeak.sh` to refresh links from a local build.

## Debug checklist
- UI glyphs/text appearing unexpectedly: inspect literal HTML around script tags
- "Webson engine is not loaded": verify `Webson.js` script include is active
- Controller not responding to UI changes: verify MQTT connectivity (`mosquitto_pub`), check no stale instance is running
- Startup state issues: verify initialisation order plus post-load recompute

## Document as you go
Add short notes for any non-obvious fix that would save another AI 15+ minutes. Keep them in the `AI/` directory or as memory entries.
