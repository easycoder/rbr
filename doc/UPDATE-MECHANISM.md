# RBR controller update mechanism #

This document describes how controller code gets from the development machine to a running controller — and how that is being automated.

## History ##

Originally the controller updated itself: `CheckForUpdate`, a routine inside `controller.allspeak`, polled `https://rbrheating.com/version` hourly, compared it with a local `.version` file, and if newer downloaded the three `.allspeak` source files (`controller.allspeak`, `deviceControl.allspeak`, `simulator.allspeak`) and relaunched itself.

That worked for the AllSpeak sources but left the Python daemons (`zigbee-bridge.py`, `rbr-dashboard.py`, ...) to be copied by hand — and it only ran while the controller was alive.

## Where the files live on the site ##

Everything this document fetches — the update tarball, the install pack, the downloader, the version stamp, and on the controller's side the `.allspeak` sources — lives in **`/heat/`** on `rbrheating.com`. The PWA is served from the same directory, so `/heat/` is the operational set: what a controller and a UI need from the site, in one place.

The move from the site root to `/heat/` was a deliberate hard cutover. Controllers installed before it look for `https://rbrheating.com/rbr-controller.tar.gz` and will not find a newer release at that path any more; reinstalling with the new `get-controller.sh` picks up the new location. `rbr-updater.py`'s default URL and `get-controller.sh`'s base are both `/heat/` now, and `RBR_BASE`/`--url` override them for testing.

Three things deliberately did **not** move into `/heat/`:

- **`auth.php` and `credentials.php`** stay at the site root. They read `../rbr-users.json`, which is kept outside the web root on purpose; one level deeper — inside `/heat/` — that path would resolve to a file inside the served tree. Both the legacy UI and the PWA reach them from either location, because the PWA asks for `../credentials.php` (one level above the page, which is the site root from `/heat/` as it was from `/new-ui/`) and `/verify`, `/register` and `/recover` are absolute.
- **The legacy UI** at the root (`index.html`, `resources/`) is left running and still deployed, unchanged, until it is deleted. The root is to become a product-information home page.
- **The documentation reader** at `/docs` and the pinned AllSpeak runtime at `/dist/` are not part of the operational set and are left where they are.

`deploy.sh` assembles `/heat/` in a temporary directory and syncs it as one tree, because the PWA and the controller files share the directory and the sync prunes deletions — syncing `new-ui/` straight into `/heat/` would delete the controller files already there. `version` is excluded from the tree sync and uploaded on its own afterwards, so a controller mid-check never sees a new stamp paired with stale source.

## Current design (Option B+C) ##

A standalone updater daemon, **`rbr-updater.py`**, replaces `CheckForUpdate`. It is a one-shot script driven by an hourly systemd timer, installed by `rbr-setup.sh` (Step 6). Being a separate service it keeps delivering updates even when the controller is down, and it can restart the controller and bridge services itself.

### Components ###

| Component | Role |
|---|---|
| `rbr-updater.py` (repo root, controller) | One-shot updater; driven by systemd `rbr-updater.service` + `rbr-updater.timer` (versioned copies of both units live in the repo root; `rbr-setup.sh` Step 6 also generates them with the RBR dir baked in) |
| `rbr-controller.tar.gz` (built by `deploy.sh`) | Versioned bundle of all controller runtime files, served from `rbrheating.com/heat/` |
| `version` (repo, dev machine) | Release stamp `YYMMDDHHMM`, bumped by `deploy.sh --release` |

### The tarball ###

`deploy.sh` builds `rbr-controller.tar.gz` containing exactly these files:

```
controller.allspeak      deviceControl.allspeak   simulator.allspeak
diagnose.allspeak        zigbee-bridge.py   zigbee-pair.py
zigbee-mesh.py     rbr-dashboard.py   heatlog.py
dashboard.txt      rbr-updater.py     rbr-watchdog.sh
rbr-mapbackup.py   VERSION
```

`VERSION` is a copy of the `version` stamp. On a `--release` run the stamp is bumped **before** the tarball is built, so the published tarball carries the new version. On a plain `./deploy.sh` (iteration) the tarball keeps the last release stamp — controllers that already have it skip it, exactly like the old `.allspeak` behaviour.

Machine-specific data is deliberately **not** in the tarball and is never touched by the updater: `credentials`, `.mqtt_password`, `.mac_override`, `config.json`, `map.json`, `thermometers.json`, `zigbee-temperatures.json`, `.version`.

### Update flow ###

1. `rbr-updater.timer` fires (hourly, with a random 0–300 s delay so all controllers don't hit the server simultaneously).
2. `rbr-updater.py` downloads the tarball to a temp file (HTTP with a 60 s timeout; a local path or `file://` URL is accepted for testing).
3. It reads the embedded `VERSION` and compares it with the local `.version` (integers, `YYMMDDHHMM`). If not newer (unless `--force`), it stops.
4. The tarball is extracted to a staging dir inside the RBR directory. Every file in the required set must be present or the update is **refused** — this catches truncated or wrong uploads before anything is touched.
5. Each staged file is sha256-compared with the live file; only changed files are swapped via `os.replace` (atomic, same filesystem).
6. The new version is written to `.version`.
7. Affected services are restarted:
   - `controller.allspeak` / `deviceControl.allspeak` / `simulator.allspeak` changed → restart `controller.service`
   - `zigbee-bridge.py` changed → restart `rbr-zigbee-bridge.service` `rbr-setup.sh` Step 8 can install `controller.service` (optional) so the controller auto-restarts after updates; if no such service is running (e.g. the controller is run manually with `allspeak controller.allspeak` in a terminal), the updater logs a notice instead of killing anything.
8. The controller also watches `.version` itself (in `MainLoop`, about once a minute): when it changes on disk, it logs `Update applied: vX -> vY` and exits. Under `controller.service` (Restart=always) systemd relaunches it; for a manual run the message tells the operator to restart — so even without the service, a manually-run controller picks up new code promptly.
9. If `rbr-updater.py` itself changed it is replaced and the process re-execs once so the new code finishes the run.

`.version` is recorded **after** the service restarts are attempted. A failed restart leaves the old version in place; the next hourly run re-extracts, finds the files identical, and re-attempts the restarts before recording the version — so a transient restart failure self-heals on the next run.

### The cloud bridge password ###

The local mosquitto bridges every topic to `rbrheating.duckdns.org`, and the web UI reaches the controller over that bridge. When the bridge is refused the interface silently stops working on every device, while the controller itself looks perfectly healthy — which is exactly how it failed on 17 October: the config carried a 24-character password while the cloud expected a 48-character one.

The bridge authenticates with `remote_password` in `/etc/mosquitto/conf.d/rbr-local.conf`, which is a **copy** of an account the cloud owns. Every updater run now compares that copy with the current value and corrects it if it has drifted:

- the current value comes from `credentials.php` when a token is present in `.mqtt_token` — the same endpoint and token a paired browser uses — and otherwise from the local `credentials` file that `rbr-setup.sh` writes;
- only when the two differ is the config rewritten, with a timestamped `.bak` beside it, and `mosquitto` then the controller restarted, because mosquitto rereads its configuration only on restart and the controller would otherwise sit on a dead socket;
- `.mqtt_password` is updated to match, so a later `rbr-setup.sh` reuses the current value rather than prompting with a stale one;
- the bridge's own state is logged every run (`$SYS/broker/connection/…/state` on the local broker: 1 connected, 0 not), so this can no longer fail silently.

`.mqtt_token` is optional. With it the box can heal itself; without it the local `credentials` copy is used, which means the password still has to reach the box once by running the setup script.

### Manual use ###

```sh
python3 rbr-updater.py --check                 # full self-check: infrastructure
                                              # (files, updater timer, broker,
                                              # bridge, controller) + versions;
                                              # changes nothing, works offline
python3 rbr-updater.py --url ./rbr-controller.tar.gz   # test with a local file
python3 rbr-updater.py --force                 # re-apply current version
```

`--check` exits 0 when the update chain is healthy, 1 when anything required is missing/inactive or when the bridge password no longer matches the cloud's — so it can be run from cron or a watchdog, not just by hand.

## Bootstrap pack (new installations) ###

`deploy.sh` also builds **`rbr-controller.zip`** — the same runtime files plus `rbr-setup.sh` and the `VERSION` stamp — and uploads it alongside the **`get-controller.sh`** downloader. A brand-new machine needs no repo copy:

```sh
mkdir rbr && cd rbr
wget https://rbrheating.com/heat/get-controller.sh
sh get-controller.sh
```

The downloader fetches the zip, unpacks it over the current directory (existing files are overwritten; machine-specific files not in the pack are untouched), writes `.version` from the embedded `VERSION`, and points the operator at the AllSpeak install and `sudo ./rbr-setup.sh`.

### Failure behaviour ###

- Download failure (controller offline): logged, exit 1; the timer retries next hour. `Persistent=true` also catches up after downtime.
- Corrupt or incomplete tarball: refused before any live file is touched.
- Crash mid-swap: `os.replace` is atomic per file, so each file is either old or new, never torn. Version is recorded only after the swaps.
- Controller run manually: updater still updates the files; the running controller keeps its in-memory code until restarted, and the updater says so.

## Transition from the old mechanism ##

`CheckForUpdate` has been removed from `controller.allspeak`. Existing controllers still running the old code will keep self-updating the `.allspeak` files until they receive a release that contains the removal — at which point they have **no** updater unless the daemon was installed. So:

1. Install the daemon on every controller (`rbr-setup.sh`, or copy `rbr-updater.py` + the two unit files manually) **before** shipping the release that removes `CheckForUpdate`.
2. The user's own RBR Server gets the daemon at rebuild time.

## Files that are still updated manually ##

The AllSpeak editor tooling (`asedit.allspeak`, `asedit.json`, `edit.html`, `server.allspeak`) and `rbr-setup.sh` itself are not in the tarball — they are dev tools, not controller runtime. Copy them by hand when they change. **`server.allspeak` is the one to watch**: it is published by AllSpeak and moves with it, and a copy old enough serves nothing at all — the 27 September copy answered `503 Server handler not ready` to every request, silently (see `AGENT.md`). Refresh it from `https://allspeak.ai/code/server.allspeak` whenever you use the editor on a box. The `.code-version` file the old copy kept for its own update check is not needed by the current one, and was removed on 2026-10-16.

See also [CONTROLLER-FILES.md](CONTROLLER-FILES.md) for the full list of files a controller needs.
