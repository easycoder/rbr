# What to do

- **Nobody takes this release by accident, and every controller needs one deliberate step.** The update URL moved from the site root to `/heat/`, so a controller installed before this release keeps polling a path that will never change again: it will not update itself, and it will not break either. Fetch the pack **in the controller's own directory** — it overwrites the runtime files and touches nothing machine-specific (credentials, `.mac_override`, `map.json`, `volatile-root`, `heatlog-root` are not in the pack), and it writes the `.version` stamp that the updater and the installer both rely on:
  ```
  cd ~/rbr                                    # the controller's install directory
  wget https://rbrheating.com/heat/get-controller.sh
  sh get-controller.sh
  rm -f get-controller.sh rbr-controller.zip   # the pack does not clean up after itself
  ```
  Then `sudo ./rbr-setup.sh` (below) and restart the services. Do the deploy first: until `/heat/` exists, that `wget` has nothing to fetch.
- **Re-run `sudo ./rbr-setup.sh` on each controller.** That creates `/run/rbr` (the volatile directory, via `/etc/tmpfiles.d/rbr-volatile.conf`), writes the one-line `volatile-root` file pointing at it, and adds the journald drop-in. Without it everything still works — the readings and the logs simply keep being written where they were — so this is not urgent, but it is where the wear saving lives.
- **Decide about the journal.** The installer now keeps it in RAM (`/etc/systemd/journald.conf.d/rbr.conf`, `Storage=volatile`, capped at 64M). That is the docs' own classification of the logs, but it means a reboot you did not ask for takes its own last few lines with it — usually the moment they are wanted. If you would rather keep the evidence:
  ```
  sudo rm /etc/systemd/journald.conf.d/rbr.conf
  sudo systemctl restart systemd-journald
  ```
- **Run `retire-rbr-now.allspeak` against any map that predates this release.**
  ```
  allspeak retire-rbr-now.allspeak     # writes map-retired.json
  diff map.json map-retired.json       # inspect
  mv map-retired.json map.json         # only then replace
  ```
  It strips `relayType` and `ssid` from every room and nine legacy fields from the top of the map. The controller ignores all of them now, so leaving them is harmless — tidiness, not repair. **Your own map is already clean**, and the six tracked fixtures have been swept for you.
- **Nothing is deployed.** `./deploy.sh` and the workflow both populate `/heat/`; the first `--release` publishes this. It will also prune the deleted configurator from `/resources/allspeak/` on the site, since that rsync carries `--delete`.
- **A controller with no `.version` file was broken, and is now fixed.** The version watch read `.version` unguarded, so on a machine installed by hand rather than through `get-controller.sh` it raised about a minute after every start — a crash loop under `Restart=always`. If any of your boxes were installed that way, this release is the fix. Nothing to do beyond taking it.
- **What has been checked, and what has not.** The full loop was run against a local broker and a stub bridge, and it works: the volatile directory resolves both ways, `map.json` is written once and **not** rewritten on the next tick (identical md5), the file holds the plan and none of the eleven derived fields, and the rewritten device module drives the bridge. What is still untested is real hardware — no relay or thermometer has driven this, and no power cut has been staged. That is worth a look on a box.

# What changed

Three pieces of work, done together because two of them edit the same `map.json` schema: the RAM disk, the retirement of RBR-Now, and the move of the deployment to `/heat/`.

## Volatile data now lives in RAM

`/run` is a tmpfs on any systemd distribution, so `rbr-setup.sh` creates `/run/rbr` with a `tmpfiles.d` drop-in — no fstab entry, no mount unit, no ordering, nothing to size — and writes a one-line `volatile-root` file naming it. Four files moved in: `thermometers.json`, `heatlog-state.json`, `zigbee-temperatures.json` and `rbr-dashboard.json`. Three of those are the machine's heaviest writers: the bridge rewrites its file in full on every temperature message, and the controller rewrote the dashboard JSON on every loop cycle.

**The logs went with them (STEP 5d).** A journald drop-in sets `Storage=volatile` and `RuntimeMaxUse=64M`, so the journal lives in `/run/log/journal` and never reaches the card or the disk. The trade-off is in the script and in the product documentation rather than buried: a volatile journal vanishes in exactly the incident where its last lines are wanted, and what makes it acceptable is that `controller.service` runs unbuffered, so its lines reach the journal as they are written.

- **The path is configurable, not hard-coded.** `volatile-root` is the same pattern `heatlog-root` already used. `controller.allspeak`, `diagnose.allspeak`, `zigbee-bridge.py` and `rbr-dashboard.py` all resolve it, and with no such file each falls back to plain names beside the code — so a dev machine and the test suite behave exactly as before.
- **Losing the directory costs nothing.** The controller already read a missing file as "reset", as on a first run, so a reboot gives fresh readings within minutes and re-decides every relay from the plan.

## `map.json` is written when it changes, not every minute

It was rewritten in full every 60 seconds whether or not anything had changed. Now the copy that reaches the disk has the readings removed from it — `temperature`, `humidity`, `battery`, `status`, `statusMessage`, `timestamp`, `sensorAge`, `relay` — and the write is skipped when that text is identical to last time. The readings stay in memory for the UI's benefit; only the copy going to disk is stripped.

`relayfails` is deliberately kept: it is stable while the relays are answering, and losing it to a restart would delay the next fault being noticed.

## RBR-Now has been retired

- **`deviceControl.allspeak`** lost `MessageESPDevice`, the `config.json` master lookup and the relay-type dispatch; it is now one transport, the local Zigbee bridge. 209 lines to 116.
- **`controller.allspeak`** lost `RecordThermometer` (the Mijia BLE parsing), the BLE branch of `ProcessReply`, `relayType` in the `RoomSpec` packet, and the `Reply`/`RelayType` variables. **The simulator still works**: `ProcessReply` keeps its numeric-temperature branch, because that is how `simulator.allspeak` answers — removing it along with the BLE branch would have broken simulation mode. The doc block now says which reply shape is which.
- **Deleted, not archived in place:** `config.json`, `devices.json`, the 26 files of ESP32 firmware under `RBRNow/`, the legacy configurator `resources/allspeak/config.allspeak` (orphaned — nothing loaded it), and `flash-device.allspeak`, which existed only to flash `RBRNow/` and could not work without it. `rbr-setup.sh` STEP 5c went with them; it existed only to create a config.json placeholder. **All of it is in git history** if any of it is wanted back.
- **`devices.json` turned out to be a second copy of the same RBR-Now hardware config that nothing read** — `AGENT.md` and `AI/PROJECT_OVERVIEW.md` called it a simulator file, and neither the simulator nor anything else ever opened it.
- **The new UI's relay-type pill is gone** from `device-editor.allspeak` and from its Webson layout, and the load default that read an empty field as `RBR-Now` went with it.
- **`retire-rbr-now.allspeak`** is new: a one-shot migration in the shape of `cleanup-map.allspeak`, run and verified against the dev map (51 fields removed, nothing else touched).
- **The tracked fixtures are swept**: `map.json`, `map-clean.json`, `map-new.json`, `map-sim.json`, `resources/allspeak/map.json` and `resources/json/newroomspec.json` no longer carry the retired fields — 257 lines removed between them, deletions only, every file still valid JSON and byte-identical in everything else.
- **Docs:** `configurator.md` and `setupHardware.md` carry a "Removed — historical description only" banner, since the tools they describe are gone; `docs/README.md` lost its reading-map entry for `technical/07-legacy-rbr-now.md`, a page that was never written; `README.md`, `AGENT.md`, `AI/{ARCHITECTURE,MAP_FORMAT,PROJECT_OVERVIEW}.md`, `doc/CONTROLLER-FILES.md`, `doc/setupRBR.md` and the two product pages under `docs/` were corrected.

## The deployment moved to `/heat/`

`deploy.sh` assembles `/heat/` locally and syncs it as one tree — the PWA and the controller files share that directory and the sync prunes deletions, so syncing `new-ui/` straight into it would delete the controller files already there. `version` is uploaded separately and last, preserving the guarantee that a controller mid-check never sees a new stamp with stale source.

- **URLs that moved:** `rbr-updater.py`'s default, `get-controller.sh`'s base, `test.allspeak`'s download.
- **URLs that deliberately did not:** `auth.php` and `credentials.php` stay at the site root, because both read `../rbr-users.json`, which is kept outside the web root on purpose — a level deeper would put that file inside the served tree. Both UIs reach them by the same paths from either location. `/docs` and `/dist` also stay, being product rather than controller.
- **The legacy root and `/new-ui/` keep being deployed**, unchanged, until you delete them. The workflow publishes the PWA to both `/new-ui/` and `/heat/`, and uses no `--delete` on `/heat/` for the reason above.

## Two defects the end-to-end run found, and fixed

The controller's loop had never been run against a broker in this environment. Standing one up (a local MQTT broker and a stub for the Zigbee bridge) found two crashes on the same code path:

- **My own guard died at the first minute tick.** `LastMapDiskText` was compared before it had ever been assigned, and AllSpeak refuses to compare an unset variable with anything. Under `Restart=always` that is a controller that runs for a minute, dies, and does it again forever. It is now initialised to empty in the startup block — no map text can equal empty, so the first tick always writes, which is what is wanted.
- **A pre-existing crash, not mine.** The version watch loaded `.version` and then `replace`d in it without checking the file was there, so a machine with no `.version` — installed by hand rather than through `get-controller.sh` — stopped about a minute after every start. Now guarded like the rest of that path.

Both are on the minute-long path, which is why neither had shown up: the controller was previously only ever observed starting.

## Two findings recorded rather than acted on

- **`protect` and `ptemp` are controller-ignored.** The frost-protection fields are written by the new UI's frost sheet and read by the legacy room editor, but `controller.allspeak` never reads either — zero references. As far as the controller is concerned frost protection has no effect. Not part of this work, and not obviously a bug (the UI computes its own indicator), but it deserves its own look.
- **`map.json` aliasing in AllSpeak.** Assigning one json variable to another aliases them, so `put Map into MapDisk` followed by `delete entry … of MapDisk` deletes the field from the live map. The idiom that copies is `put prettify X into T` then `put json T into Y`. Established against the runtime before any of this code was written.

## Still open

1. **The legacy UI's own RBR-Now screens.** `resources/allspeak/{roomedit,roomtools,rbr,mode}.allspeak`, `resources/webson/getdevices.json` and a stale copy of the device module at `resources/allspeak/deviceControl.allspeak` still offer a relay-type choice and carry the ESP transport. They are inert — the controller ignores the field and nothing loads the stale module — and `resources/` is itself due to be deleted, so editing them now would be throwaway work.
2. **Not verified on real hardware**, as above. Everything the environment allows has been checked: the loop runs against a broker, both systemd drop-ins were validated against the real systemd, `asdoc-check` is clean on every changed script, and the unit suite passes.
