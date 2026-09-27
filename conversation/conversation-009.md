# 2026-09-27

## 15:19

Please change all .as extensions to .allspeak, in line with new AllSpeak policy

**Assistant**

Checked the policy against the local AllSpeak runtime first (`~/dev/allspeak`) — it prefers `.allspeak` and keeps `.as` only as a legacy fallback (`as_program.py:815`), so the rename is well-founded. Then asked two things before touching anything: whether to rename the `as/` directories too (you said yes) and whether to rewrite the historical `conversation/` logs (you said no).

Done — every `.as` file is now `.allspeak`, and the two UI script directories moved with them.

Renamed, with `git mv` so history follows:
- 50 scripts — the controller, its modules, the editor/tools, the unit tests.
- `resources/as/` → `resources/allspeak/`, and `new-ui/resources/as/` → `new-ui/resources/allspeak/`.

References followed across 85 files: `run … as …` module paths and `rest get … from` fetches, the three unit files and the `rbr-setup.sh` heredocs, the resource lists in `deploy.sh` and `.github/workflows/deploy.yml`, the updater's `TARBALL_FILES`/`SERVICE_RULES`, `.gitignore`, `sw.js`, `index.html`, `edit.html`, `asedit.allspeak` (it now saves with a `.allspeak` suffix), `server.allspeak`'s MIME rule, `asdoc-check.py`'s default `--ext`, and the docs (`AGENT.md`, `ALLSPEAK.md`, `AI/`, `docs/`, `doc/`). `conversation/` left alone as agreed.

Verified:
- The AllSpeak unit suite on the renamed files (dev runtime): 10 files, 63 tests, 167 checks — all pass.
- `asdoc-check.py`: 0 errors. Refreshed the `@hash` lines of the seven files whose `!` comments held a `.as` name; `@verified` untouched.
- Every `.allspeak` reference resolves to a real file.
- `bash -n` on the shell scripts, `py_compile` on the Python, the deploy workflow YAML parses, and git detected the renames as renames.

Two things worth your attention:
1. Deployment hazard — `rbr-updater.py` only adds files and never deletes, so the old `controller.as` lingers on disk and the unit's `ExecStart` still names it; the service would silently keep running stale code. Re-run `rbr-setup.sh` per machine. Detailed in `DIFF.md`.
2. `asedit.allspeak` now has two `verify-stale` sections (the rename changed a `!` comment and a URL inside their blocks) — re-verify in asedit.

Couldn't run the browser E2E smoke test here (needs mosquitto, sudo and Playwright browsers, none present). There is also a separate legacy `.ecs` extension still around — left alone and flagged in `DIFF.md`.

`DIFF.md` rewritten; new session log started here.

## 15:23

Let's clear up the .ecs legacy too.

**Assistant**

Checked the lineage before touching anything: the AllSpeak repo's own `AGENTS.md` records the rename chain `.ecs` → `.as` → `.allspeak`, so sweeping the last EasyCoder-era names to `.allspeak` matches the policy. No `.ecs` files existed in the repo — only 15 mentions across 5 files (plus my own `DIFF.md` note).

Swept `.ecs` → `.allspeak` in:
- `zigbee-bridge.py` — two comments about `deviceControl`.
- `doc/configurator.md` — `rbrconf.ecs`, including the quoted GitHub raw URL and the hidden `.rbrconf.*` save/run/delete names.
- `resources/allspeak/README.md` — the `scripted` editor's `scripted-server.ecs` / `scripted.ecs`.
- `params.json` — `"device_script": "roomController.ecs"`.
- `rbrchat/deploy.sh` — `chat-main.ecs`.

`conversation/` left alone again, consistent with the earlier decision. Verified nothing else in the repo still says `.ecs` — only `DIFF.md`'s prose, which deliberately describes the change.

Findings worth your attention — the names now read correctly, but the things they point at are not in this repo:
- `doc/configurator.md`'s `rbrconf` configurator and its raw GitHub URL — the file isn't here.
- `params.json`'s `device_script` key — nothing reads it.
- `resources/allspeak/README.md`'s `scripted` editor files — this repo uses `asedit.allspeak` / `server.allspeak`.
- `rbrchat/deploy.sh` scp's from `~/dev/chat`, which still has `chat-main.as`, so that project needs the rename or the deploy breaks.

`DIFF.md` updated to cover both sweeps.

## 15:28

The AllSpeak editor needs an addition so it can list .allspeak files.

**Assistant**

Found the cause: the editor's file browser is fed by `server.allspeak`'s `/list` route, which filters by extension — `set FileList to entries in BaseDir type \`as,ecs,md,txt,json,html,css,js,py\``. After the rename, no script matched, so the browser showed no scripts at all.

Checked the canonical AllSpeak repo first, and its `server.allspeak` already reads `allspeak,as,ecs,md,…` — so the addition is to prepend `allspeak`, keeping the legacy entries as upstream does. Applied that to both `/list` lines (root and subdirectory) in this repo's `server.allspeak`. It has no doc blocks, so no `@hash` refresh was needed.

Verified by actually running it: started `allspeak server.allspeak 8099`, and `GET /list` now returns all eleven root `.allspeak` scripts, with `/list/desktop` returning `rbr-desktop.allspeak` too. Stopped it afterwards.

One action for you: the editor server already running on 8080 (and 9090) is the old code — restart it, then reload `edit.html`.

`DIFF.md` updated; nothing else touched.
