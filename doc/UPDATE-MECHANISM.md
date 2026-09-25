# RBR controller update mechanism #

This document describes how controller code gets from the development machine to a running controller — and how that is being automated.

## History ##

Originally the controller updated itself: `CheckForUpdate`, a routine inside `controller.as`, polled `https://rbrheating.com/version` hourly, compared it with a local `.version` file, and if newer downloaded the three `.as` source files (`controller.as`, `deviceControl.as`, `simulator.as`) and relaunched itself.

That worked for the AllSpeak sources but left the Python daemons (`zigbee-bridge.py`, `rbr-dashboard.py`, ...) to be copied by hand — and it only ran while the controller was alive.

## Current design (Option B+C) ##

A standalone updater daemon, **`rbr-updater.py`**, replaces `CheckForUpdate`. It is a one-shot script driven by an hourly systemd timer, installed by `rbr-setup.sh` (Step 6). Being a separate service it keeps delivering updates even when the controller is down, and it can restart the controller and bridge services itself.

### Components ###

| Component | Role |
|---|---|
| `rbr-updater.py` (repo root, controller) | One-shot updater; driven by systemd `rbr-updater.service` + `rbr-updater.timer` (versioned copies of both units live in the repo root; `rbr-setup.sh` Step 6 also generates them with the RBR dir baked in) |
| `rbr-controller.tar.gz` (built by `deploy.sh`) | Versioned bundle of all controller runtime files, served from rbrheating.com |
| `version` (repo, dev machine) | Release stamp `YYMMDDHHMM`, bumped by `deploy.sh --release` |

### The tarball ###

`deploy.sh` builds `rbr-controller.tar.gz` containing exactly these files:

```
controller.as      deviceControl.as   simulator.as
diagnose.as        zigbee-bridge.py   zigbee-pair.py
zigbee-mesh.py     rbr-dashboard.py   heatlog.py
dashboard.txt      rbr-updater.py     rbr-watchdog.sh
rbr-mapbackup.py   VERSION
```

`VERSION` is a copy of the `version` stamp. On a `--release` run the stamp is bumped **before** the tarball is built, so the published tarball carries the new version. On a plain `./deploy.sh` (iteration) the tarball keeps the last release stamp — controllers that already have it skip it, exactly like the old `.as` behaviour.

Machine-specific data is deliberately **not** in the tarball and is never touched by the updater: `credentials`, `.mqtt_password`, `.mac_override`, `config.json`, `map.json`, `thermometers.json`, `zigbee-temperatures.json`, `.version`.

### Update flow ###

1. `rbr-updater.timer` fires (hourly, with a random 0–300 s delay so all controllers don't hit the server simultaneously).
2. `rbr-updater.py` downloads the tarball to a temp file (HTTP with a 60 s timeout; a local path or `file://` URL is accepted for testing).
3. It reads the embedded `VERSION` and compares it with the local `.version` (integers, `YYMMDDHHMM`). If not newer (unless `--force`), it stops.
4. The tarball is extracted to a staging dir inside the RBR directory. Every file in the required set must be present or the update is **refused** — this catches truncated or wrong uploads before anything is touched.
5. Each staged file is sha256-compared with the live file; only changed files are swapped via `os.replace` (atomic, same filesystem).
6. The new version is written to `.version`.
7. Affected services are restarted:
   - `controller.as` / `deviceControl.as` / `simulator.as` changed → restart `controller.service`
   - `zigbee-bridge.py` changed → restart `rbr-zigbee-bridge.service` `rbr-setup.sh` Step 8 can install `controller.service` (optional) so the controller auto-restarts after updates; if no such service is running (e.g. the controller is run manually with `allspeak controller.as` in a terminal), the updater logs a notice instead of killing anything.
8. The controller also watches `.version` itself (in `MainLoop`, about once a minute): when it changes on disk, it logs `Update applied: vX -> vY` and exits. Under `controller.service` (Restart=always) systemd relaunches it; for a manual run the message tells the operator to restart — so even without the service, a manually-run controller picks up new code promptly.
9. If `rbr-updater.py` itself changed it is replaced and the process re-execs once so the new code finishes the run.

`.version` is recorded **after** the service restarts are attempted. A failed restart leaves the old version in place; the next hourly run re-extracts, finds the files identical, and re-attempts the restarts before recording the version — so a transient restart failure self-heals on the next run.

### Manual use ###

```sh
python3 rbr-updater.py --check                 # full self-check: infrastructure
                                              # (files, updater timer, broker,
                                              # bridge, controller) + versions;
                                              # changes nothing, works offline
python3 rbr-updater.py --url ./rbr-controller.tar.gz   # test with a local file
python3 rbr-updater.py --force                 # re-apply current version
```

`--check` exits 0 when the update chain is healthy, 1 when anything required is missing/inactive — so it can be run from cron or a watchdog, not just by hand.

## Bootstrap pack (new installations) ###

`deploy.sh` also builds **`rbr-controller.zip`** — the same runtime files plus `rbr-setup.sh` and the `VERSION` stamp — and uploads it alongside the **`get-controller.sh`** downloader. A brand-new machine needs no repo copy:

```sh
mkdir rbr && cd rbr
wget https://rbrheating.com/get-controller.sh
sh get-controller.sh
```

The downloader fetches the zip, unpacks it over the current directory (existing files are overwritten; machine-specific files not in the pack are untouched), writes `.version` from the embedded `VERSION`, and points the operator at the AllSpeak install and `sudo ./rbr-setup.sh`.

### Failure behaviour ###

- Download failure (controller offline): logged, exit 1; the timer retries next hour. `Persistent=true` also catches up after downtime.
- Corrupt or incomplete tarball: refused before any live file is touched.
- Crash mid-swap: `os.replace` is atomic per file, so each file is either old or new, never torn. Version is recorded only after the swaps.
- Controller run manually: updater still updates the files; the running controller keeps its in-memory code until restarted, and the updater says so.

## Transition from the old mechanism ##

`CheckForUpdate` has been removed from `controller.as`. Existing controllers still running the old code will keep self-updating the `.as` files until they receive a release that contains the removal — at which point they have **no** updater unless the daemon was installed. So:

1. Install the daemon on every controller (`rbr-setup.sh`, or copy `rbr-updater.py` + the two unit files manually) **before** shipping the release that removes `CheckForUpdate`.
2. The user's own RBR Server gets the daemon at rebuild time.

## Files that are still updated manually ##

The AllSpeak editor tooling (`asedit.as`, `asedit.json`, `edit.html`, `server.as`) and `rbr-setup.sh` itself are not in the tarball — they are dev tools, not controller runtime. Copy them by hand when they change.

See also [CONTROLLER-FILES.md](CONTROLLER-FILES.md) for the full list of files a controller needs.
