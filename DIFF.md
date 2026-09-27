# What to do

- **Regenerate the controller unit on every machine — this is the one that bites.** `rbr-setup.sh` now writes `ExecStart=… allspeak controller.allspeak` (and the desktop unit `rbr-desktop.allspeak`). An existing unit still says `controller.as`, and the updater only *adds* the renamed files — it never deletes the old ones — so without this the service carries on running the stale `controller.as` without a murmur. Re-run `rbr-setup.sh`, or edit `ExecStart` by hand, then `rm controller.as deviceControl.as simulator.as diagnose.as` so nothing stale is left behind.
- **Re-deploy, then delete the old directory.** `./deploy.sh --release` now syncs `resources/allspeak/`; the old `resources/as/` tree on rbrheating.com is no longer in the loop's list, so remove it by hand.
- **Reload the PWA** — `index.html`, `sw.js` and the shell all point at `resources/allspeak/…` now. A normal reload (or waiting for the service worker to update) is enough.
- **Restart the desktop app** if you use it.
- **The chat project needs the same sweep.** `rbrchat/deploy.sh` now copies `chat-main.allspeak`, but `~/dev/chat` still has `chat-main.as` — its scp will fail until that project is renamed too.
- **In `asedit.allspeak`, two sections are now `verify-stale`** — re-check them in asedit. The rename changed a `!` comment and a URL inside their blocks, so their sign-off hash no longer matches. (The baseline already carried 25 stale verifies elsewhere; these two are new.)
- **Restart the editor server.** `server.allspeak`'s file list now includes `.allspeak`, so the editor can open the scripts. A server already running (e.g. port 8080) is the old code — stop and re-run `allspeak server.allspeak`, then reload `edit.html`.

# What changed

The AllSpeak source extension is swept to `.allspeak`, in two steps: first the `.as` files, then the last legacy `.ecs` mentions. The lineage is documented in the AllSpeak repo itself (`AGENTS.md`): `.ecs` → `.as` → `.allspeak`.

The editor's file browser gained `.allspeak`, which it had been missing: `server.allspeak`'s `/list` route filters by extension, and the list began at `as,ecs,…`. It now reads `allspeak,as,ecs,md,txt,json,html,css,js,py` — matching the canonical AllSpeak repo's own `server.allspeak`, which had already been updated. Without it the browser showed no scripts at all once they were renamed. The legacy `as` and `ecs` entries are kept, as upstream keeps them, so a stray older file is still openable.

## `.as` → `.allspeak`, and the directories with it

Every `.as` file is now `.allspeak`, and the two UI script directories are renamed to match: `resources/as/` → `resources/allspeak/` and `new-ui/resources/as/` → `new-ui/resources/allspeak/`.

- 50 files renamed with `git mv`, so history follows them: the controller, its modules, the UI scripts, the editor, the tools and the unit tests.
- Every reference followed it: `run … as …` module paths, `rest get … from` fetches, the three unit files and the `rbr-setup.sh` heredocs, the resource lists in `deploy.sh` and `.github/workflows/deploy.yml` (`for dir in allspeak css …`), the updater's `TARBALL_FILES`/`SERVICE_RULES`, `.gitignore`, `sw.js`, both `index.html` loaders, `edit.html`, `asedit` (it now saves with a `.allspeak` suffix), the file server's MIME rule (`server.allspeak` treats `.allspeak` as `text/plain`), and `asdoc-check.py`'s default `--ext`.
- Docs updated to match: `AGENT.md`, `ALLSPEAK.md`, `AI/*`, `docs/`, `doc/*`, `desktop/README.md`. The `conversation/*.md` logs are deliberately untouched — they are a record of past sessions, not current documentation.
- Doc-block `@hash` lines were refreshed with `asdoc-check.py --write` for the seven files whose `!` comments held a `.as` name (`!` comments are inside the hash). `@verified` lines were not touched. `asdoc-check.py` reports 0 errors.

## `.ecs` → `.allspeak`

The remaining EasyCoder-era names are gone:

- `zigbee-bridge.py` — two comments now say `deviceControl.allspeak`.
- `doc/configurator.md` — `rbrconf.ecs` → `rbrconf.allspeak` (including the quoted GitHub URL and the hidden `.rbrconf.*` save/run/delete names).
- `resources/allspeak/README.md` — `scripted-server.ecs` / `scripted.ecs` → `.allspeak`.
- `params.json` — `"device_script": "roomController.ecs"` → `.allspeak`.
- `rbrchat/deploy.sh` — `chat-main.ecs` → `chat-main.allspeak`.

# Noticed while in there

Stale references that predate this sweep. They are now internally consistent in name, but the things they point at are not in this repo — worth a look; none of them was otherwise touched:

- `doc/configurator.md` documents a `rbrconf` configurator that does not exist in this repo, and the `raw.githubusercontent.com/easycoder/rbr/…/rbrconf.*` URL it quotes points at a file that is not here either.
- `params.json`'s `device_script` key is read by nothing in the repo (the simulator reads the per-room keys, not this one).
- `resources/allspeak/README.md` describes a `scripted` editor whose five files are not here — this repo uses `asedit.allspeak` and `server.allspeak` instead.
- `rbrchat/deploy.sh` pulls from `~/dev/chat`, which still has `chat-main.as`.
