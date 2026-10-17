# What to do

- **Nobody takes this release by accident, and every controller needs one deliberate step.** The update URL moved from the site root to `/heat/`, so a controller installed before this release keeps polling a path that will never change again: it will not update itself, and it will not break either. Fetch the pack **in the controller's own directory** — it overwrites the runtime files and touches nothing machine-specific (credentials, `.mac_override`, `map.json`, `volatile-root`, `heatlog-root` are not in the pack), and it writes the `.version` stamp that the updater and the installer both rely on:
  ```
  cd ~/rbr                                    # the controller's install directory
  wget https://rbrheating.com/heat/get-controller.sh
  sh get-controller.sh
  rm -f get-controller.sh rbr-controller.zip   # the pack does not clean up after itself
  ```
  Then `sudo ./rbr-setup.sh` (below) and restart the services. Do the deploy first: until `/heat/` exists, that `wget` has nothing to fetch.
- **If you re-ran the installer on a box that already had Zigbee devices, check its network key before it restarts.** The old `rbr-setup.sh` wrote `/opt/zigbee2mqtt/data/configuration.yaml` from scratch with `network_key: GENERATE`, which is the identity of the whole Zigbee network — Zigbee2MQTT only notices at its next start, when it invents a new network and every paired device drops off. That is fixed in this release, but any box re-run before the fix may be carrying `GENERATE`. `restore-z2m-network-key.py` (new, in the repo root) puts it back from Zigbee2MQTT's own `coordinator_backup.json`, which predates the damage:
  ```
  sudo python3 ~/rbr/restore-z2m-network-key.py --dry-run   # show what it found
  sudo python3 ~/rbr/restore-z2m-network-key.py             # backs up first, then writes
  sudo systemctl restart zigbee2mqtt
  ```
  It refuses to write if it cannot find a key, and backs up `configuration.yaml` before touching it.
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

## The installer could destroy a Zigbee network, and no longer can

Found the hard way, on a live box. STEP 3 wrote `/opt/zigbee2mqtt/data/configuration.yaml` **unconditionally**, with `network_key: GENERATE` and `pan_id: GENERATE`. Re-running the installer therefore reset the identity of a working Zigbee network — silently, and only visible at the next Zigbee2MQTT start, when every paired relay and thermometer would fail to rejoin. Since the documentation presents re-running the installer as the normal repair path, that was a trap rather than an edge case.

- **An existing `configuration.yaml` is now kept**, and the only thing the script corrects in it is `serial.port`, in place and inside the `serial:` block only — the `frontend:` block has a `port:` of its own that a blunt edit would have clobbered.
- **`restore-z2m-network-key.py` is new**, for the boxes that were already caught: it recovers the key and PAN ID from Zigbee2MQTT's own `coordinator_backup.json`, accepts every shape that file has used (a list of ints, a hex string, hex strings, nested objects), refuses to write if it cannot find a key, backs the file up first, and rewrites in place so the ownership stays with the `zigbee2mqtt` user. Tested against all four shapes, both failure paths, `--dry-run`, and repeat runs.

## What is already published, and what still needs a deploy

Release `2610171257` went out at 12:57 and **already carries the controller and bridge fixes** — verified on the server: the `controller.allspeak` in `/heat/` has the `action`/`message` guards and `PrepareMapForDisk`, and the `zigbee-bridge.py` inside the tarball has the cross-filesystem write fix. So no controller is exposed to the crash loop or the missing-readings bug any more.

One thing is **not** published yet, because it came after that release: the `credentials.json` change below, which is what still leaves the browser console showing `403`. One more `./deploy.sh --release` clears it, and it does not need to be urgent.

## Three defects the live install found, and fixed

None of these were reachable from the test scaffolding, and each was found by putting the code on a real controller with a real map, real sensors and a real filesystem split.

- **The stripped map could not be reloaded, so the controller crash-looped.** `map.json` is now written without its readings — but `ProcessRoom` read `entry temperature of Room` unguarded, and four such reads (three of `temperature`, one of `relay`) threw on the first room of the first cycle after any restart. `Restart=always` turned that into a restart every few seconds, and a dead controller answers no map request — which is exactly how it presented: the PWA connecting fine and then reporting "first map didn't arrive in 30s". All four reads now default when the key is absent. The test scaffolding missed it because it never **restarted** the controller after it had written a stripped map.
- **The bridge wrote its readings file across two filesystems, so it never wrote at all.** The atomic write created its temp file beside the script (`~/rbr`) and then `os.replace`d it into the volatile directory (`/run/rbr`) — different filesystems, `EXDEV`, caught by a broad `except OSError` and only printed. With no readings the controller forces every relay off, so this was silently "the heating does not come on". The temp file now goes in the target's own directory. The proposal said this had to be so; the code did not do it.
- **A malformed MQTT message crashed the controller.** `action` and `message` were read unguarded, in the MQTT callback and again in the queue drain, so a message missing either stopped the controller — and a publisher that kept doing it was a crash loop. Two hand-built probes did exactly that during this repair. Both reads are now optional, which is what the `first`/`refresh`/`uirequest` handling already assumed.

Verified on the box afterwards: the controller answers a `first` request with the full map (13 KB, three profiles, eight rooms); `thermometers.json`, `zigbee-temperatures.json` and `heatlog-state.json` all appear in `/run/rbr`; `map.json` is 18632 bytes with **zero** `temperature` keys and stops being rewritten every minute; the bridge reports **no** relay set-failures.

## Two defects the end-to-end run found, and fixed

The controller's loop had never been run against a broker in this environment. Standing one up (a local MQTT broker and a stub for the Zigbee bridge) found two crashes on the same code path:

- **My own guard died at the first minute tick.** `LastMapDiskText` was compared before it had ever been assigned, and AllSpeak refuses to compare an unset variable with anything. Under `Restart=always` that is a controller that runs for a minute, dies, and does it again forever. It is now initialised to empty in the startup block — no map text can equal empty, so the first tick always writes, which is what is wanted.
- **A pre-existing crash, not mine.** The version watch loaded `.version` and then `replace`d in it without checking the file was there, so a machine with no `.version` — installed by hand rather than through `get-controller.sh` — stopped about a minute after every start. Now guarded like the rest of that path.

Both are on the minute-long path, which is why neither had shown up: the controller was previously only ever observed starting.

## The PWA's 403 — and the mistake I made trying to silence it

The browser console showed `GET /heat/credentials.json 403 (Forbidden)` on every load. Fixing it was not as simple as it looked, and the first attempt broke pairing, so this is worth writing down.

**Why it 403'd.** `new-ui/credentials.json` was mode 0640 and `deploy.sh` copied it with `--no-perms`, so the server's copy was 0640 too and Apache could not read it.

**What that file was.** Real broker credentials — broker, username, password, MAC. For a *local* install that is correct and useful: `rbr-setup.sh` STEP 7 writes it beside the controller and into `new-ui/` so an interface served from the box can use it. On the public site it is a secret in a public directory that is also useless (`broker: localhost` cannot be reached from a browser).

**The mistake.** I replaced it with `{}` and forced the mode to 0644, so the request returned 200 with no error. That broke pairing completely: the PWA fetches `credentials.json` and **falls back to `credentials.php` only when the fetch FAILS**. A successful, empty response takes the "I have credentials" path, finds no broker in it, and lands in demo mode — which looks exactly like "the password was rejected", because pairing had in fact succeeded and the token was stored. The 403 was load-bearing.

**The fix.** The file is not deployed at all — deleted from the repository, so the rsync's `--delete` prunes it and the request 404s. That is the signal the app's `or` clause keys off, and the fall-back to `credentials.php` works. No broker credentials are published, and the local case is unaffected because `rbr-setup.sh` creates the file on the box.

The console will still show a 404 for `credentials.json`. That is the app's own fall-back mechanism and cannot be removed without changing how the fallback is decided — which would mean testing the *contents* of the response rather than the success of the fetch, and is not worth doing for a console line. **Decided 2026-10-17: leave it.** The alternative considered was to ask the server first and fall back to the local file, which would clear the line on the hosted site but move it to local/offline installs, and would change the order of the pairing path — the path the mistake above broke. Not worth it for a 404 on an optional file.

Verified end to end in a headless browser against the live site: `credentials.json` 404 → `credentials.php` 200 with the stored token → **MQTT connected**, demo mode cleared.

## A pre-flight check for the machine that is about to become a controller

Set up as a tool for the next install rather than this one. `rbr-preflight.py` reports the facts that otherwise cost an hour to discover, and changes nothing: it is read-only, and the only network traffic is a version fetch and a socket connect.

It checks the machine, the access, the clock (NTP and timezone — every schedule decision is local time), reachability of the site *and* the cloud broker, whether the coordinator is attached yet, the runtime (`python3`, `node`, `pnpm`, `mosquitto`, `allspeak`), whether an install already exists, and which of RBR's own ports are taken. `--json` gives the same facts machine-readable; anything marked ✗ sets a non-zero exit code.

Two of its checks only exist because of today. The coordinator has to be attached **before** the setup runs, because the installer derives the udev name and Zigbee2MQTT's port from what it finds at startup — attaching it afterwards leaves placeholders. And `/run` has to be a tmpfs, or the whole volatile-storage design quietly becomes disk writes again.

It stays out of the deployed set deliberately (absent from `CONTROLLER_FILES` and the tarball): it is for a machine *before* it is a controller.

Writing it found three bugs in itself, which is the argument for testing against a known-good machine rather than a blank one. Port 8883 was checked as a local port when the bridge only ever dials *out* to it. `mosquitto` and `zigbee2mqtt` were reported missing on a controller that runs both, because they were looked up in `PATH` — mosquitto lives in `/usr/sbin` and zigbee2mqtt is a directory, not a command. And the port check called RBR's own listeners a conflict, when on a working machine those ports are held by RBR itself.

`doc/setupRBR.md` gains it as step 1, which renumbers the rest of the procedure — and the ten `(step N)` cross-references inside that document were corrected with it.

## The cloud bridge password now looks after itself

The outage earlier was a stale password in mosquitto's bridge config: the box held a 24-character one, the cloud wanted 48, so the bridge was refused, and **the interface silently stopped working on every device while the controller looked perfectly healthy**. Nothing pointed at it — the browser connected, subscribed and asked for the map; the request simply had nowhere to go.

`rbr-updater.py` now checks it on every hourly run, before anything release-shaped:

- the current value comes from `credentials.php` when a token is present in `.mqtt_token` (the same endpoint and token a paired browser uses), and otherwise from the local `credentials` file;
- if it matches, nothing happens; if it differs, the config is rewritten with a timestamped `.bak`, `.mqtt_password` is brought into line (so a later `rbr-setup.sh` prompts with the current value), and `mosquitto` then the controller are restarted — mosquitto rereads its config only on restart, and the controller would otherwise sit on a dead socket;
- **the bridge's own state is logged every run**, from `$SYS/broker/connection/…/state` on the local broker, so this can never fail silently again;
- `--check` reports a mismatch as a problem and changes nothing, so the watchdog/cron exit code reflects it.

`.mqtt_token` is the one thing that makes it self-healing rather than merely diagnostic: without it the box can only bring the config into line with whatever its local `credentials` copy says, which still needs the right password to reach it once.

Deployed to the box and into `.mqtt_token`; the self-check there reports `up to date (from credentials.php)` and `Bridge to the cloud: connected`. Tested against five cases before shipping: missing config, up to date, stale-in-check-mode, stale-and-applied, and no credentials at all — plus the live `credentials.php` path, which fetched the 48-character value and corrected a stale config.

## The leftovers on the live controller are gone, and the map is retired

Cleared the three pre-fix files still sitting beside the code on QED6 (`thermometers.json`, `zigbee-temperatures.json`, `heatlog-state.json`, all written 12:07-12:11 before the switch to `/run/rbr`) and a `config.json` in the retired RBR-Now format. None is read any more — the controller and the bridge resolve their paths through `volatile-root` — but a fallback would have picked them up silently and presented hours-old state as current, which is precisely the failure that is hardest to recognise later. `config.json` has not reappeared since, so nothing recreates it.

Then ran `retire-rbr-now.allspeak` on the live map: 51 fields removed, and checked structurally rather than by eye — 3 profiles and 8 rooms each preserved with identical names, only `relayType` and `ssid` gone from the rooms, no field added, every remaining field byte-identical including schedules, `linked`, `relayfails` and the profile index. A new system never has these fields at all: `LoadMap` builds its map from scratch when `map.json` is absent, so this is a one-off migration for existing installs.

`apply-retired-map.sh` does the swap, because it cannot be done by copying the file over. The controller loads `map.json` once at startup and keeps it in memory, writing it back only when something in it changes — so a swap under a running controller is silently undone by the next write. The script validates the replacement *before* stopping anything (so a bad map costs an error rather than downtime), then stops the controller, keeps a timestamped backup, moves the file into place with its original ownership, restarts, and verifies that the map has no retired fields and the service is up. `--dry-run` validates and reports without root. Tested against four refusals — a retired field still present, a map that does not parse, a map with no rooms, and a non-root run — plus a dry run against the real replacement.

## Provisioning a system can no longer produce one that pairs and then does nothing

A new system needed three things and only two of them had a home. `/register` creates the record and its six-digit password, `/verify` marks it verified and mints the token — and then `credentials.php` refuses, because it also requires a `credentials` block that **no endpoint creates**. The visible result is a system that pairs successfully, asks for broker details, gets a 401 and drops into demo mode, with nothing anywhere saying why. That is today's `credentials.json: {}` trap in a second place.

`provision-system.py` writes on the web host, outside the document root beside the file it edits, and leaves one command as the whole job: password, verified, token and broker credentials, or a report that the entry is already complete. Broker defaults come from the host settings file — the same source `credentials.php` falls back to — so the served credentials and the provisioned ones cannot drift apart.

It is built to fail loudly where failing quietly is the danger:

- It **tests the broker login before writing**, with a minimal MQTT 3.1.1 CONNECT over TLS, and refuses if the broker rejects the credentials. Building that probe needed two corrections found by testing against the live broker: the CONNECT payload must begin with the client identifier (without it the broker drops the connection, indistinguishable from a bad password), and the test must use the MQTT port rather than the websocket port the UI is served — 443 answers a websocket listener, not a raw CONNECT.
- It writes **atomically and preserves ownership and mode**, keeping a timestamped backup, because a half-written `rbr-users.json` locks every customer out and the symptom would read as wrong passwords. It re-reads the file before reporting success.
- It **defaults to a dry run**, prints no secret except a newly generated system password (which exists nowhere else and must be written down then), and refuses to change a verified system's email or password without `--force`.

Tested against nine cases: list with a verified-but-credential-less entry, repair of that entry, a fresh system, the write, a repeat run that reports nothing to do, an email change refused without `--force`, a bad MAC, a bad email, a broker refusal that wrote nothing, and a broker acceptance that wrote a complete entry.

`doc/PROVISIONING.md` documents the account fields, which endpoint writes which, the gap, the tool, and what it cannot do — broker-side accounts are on another host and no file here can fence them.

## Rooms move above profiles: one room list, per-profile state keyed by name

Raised in passing and worth pinning down. The controller and the PWA disagree about whether rooms belong to a profile, and the disagreement is joined by an array index rather than a name — so it fails by corrupting rather than by breaking.

The evidence: `ProcessAllRooms` resolves the selected profile and sizes every parallel array from *that* profile's room count, so per-profile room sets are genuinely supported. The PWA assumes the opposite — it never sends `Update Rooms` at all (that string appears once, in a comment), always ships the whole `profiles` array, and edits rooms by index across every profile. `SwapRoomsAcrossProfiles` carries the comment "in every profile" and `RenameRoomAcrossProfiles` does the same; neither checks that index 3 is the same room everywhere. It is safe today only because all three profiles on the live map happen to agree — 8 rooms, same names, same order.

`doc/PROPOSAL-shared-room-list.md` records the decision (room identity above profiles, per-profile state keyed by name), the full field-by-field split, the three boundaries that change in the controller, the two aliasing hazards, the migration, and the staging.

The split was corrected after review: **frost protection moves to identity**, on the grounds that it protects the room's fabric whatever the plan says — and it comes with a bonus, since the frost sheet then writes one record instead of looping every profile. `relayfails` was already identity for the same reason.

The operating state (`mode`, `target`, `prevmode`, `until`, `boostperiod`) stays per profile, and the code says so deliberately rather than by accident: `Select Profile` re-materialises it from the profile selected — which is what makes a profile like `All Off` actually turn everything off — and a mode change clears `until`, `prevmode` and `boostperiod` specifically "so the map doesn't carry zombie state across profile views". Both halves are now written: the controller (stage 1, earlier) and the PWA (stage 2, this session). **Nothing is deployed**, and the live controller still runs the old code against the old map, so nothing about the live system has changed yet.

### The PWA now speaks the same shape

`map-to-rooms` merges the two halves back into one flat record per room — identity from `rooms[]`, schedule state from `profiles[selected].rooms[name]` — because everything downstream (the card, the schedule projection, the offline classification) works best on one record per room. The merge is read-only, and a room the selected profile carries no state for is still listed: part of the system's room set, reading as Off, rather than vanishing from the page.

The device editor shrank to what wiring actually is. Editing a room's relays, thermometer and linked flag used to write the same three fields into every profile through a loop; it now writes the room's identity record once. Moving a room up or down used to be the same two-element swap repeated in every profile — `SwapRoomsAcrossProfiles` — and is now a swap in one list. Renaming and deleting are the only operations left that touch more than one place, and only because a name is a key in every profile: rename moves the state entry to the new key, delete drops it.

Two behaviours the old array allowed and this cannot:

- **Room names must be unique.** A name is the join between identity and every profile's state, so a duplicate is refused (rename says so, add picks "Unnamed", "Unnamed 2", …). The old room arrays allowed duplicates by accident of the path taken, not by design.
- **The card's `legacyIdx` is gone.** Requests were already addressed by room name; the index existed only to index into per-profile room arrays. `outsideRoomLegacyIdx` became `outsideRoomName` for the same reason.

The payload every Save ships now carries `rooms` as well as `profiles`, from `Map.rooms` in `SendUpdateProfiles` — one source for what is sent, and a caller that edits identity writes it into `Map.rooms` first.

### What the controller does with an identity list

`MergeIdentityRooms` rebuilds `Map.rooms` from the incoming names and order, taking only the six fields a UI owns (`relays`, `sensor`, `linked`, `relayfails`, `protect`, `ptemp`) and keeping its own readings and derived status for every room it already knew. A page reports what it saw a few seconds ago; its temperatures must not win, or the interface flickers backwards. A new name keeps nothing — the controller fills the readings when the sensor next reports. Names absent from the list are deletions.

`Update Profiles` accepts `rooms` alongside `profiles` and applies identity first, so the state validation runs against the list it just stored. That validation now covers **every** profile rather than item 0, and `ReportUnknownStates` names any per-profile state whose room no longer exists — a rename that arrived without its identity half, or a stale page, is reported rather than left as a schedule nothing can run.

`Update Rooms` was rewritten: it used to append each incoming room to a list it had just assigned from the same message, and rebuild the selected profile's state from the incoming records, which under the new shape would have overwritten schedules with identity. It is now an identity replacement followed by a re-materialise.

### No migration script is needed

An old-shape map is converted in memory by `EnsureSharedRooms` when the controller loads it, and the converted shape is what gets written back on the next save. A machine with no map never sees the old format at all. This replaces the standalone `propose-shared-rooms.allspeak` the proposal called for: a script would have to be run, validated and undone by hand, where the controller already has the conversion, and running it twice is a no-op.

### How it was verified

There is no compiler on this machine that understands the PWA's dialect: the `allspeak` CLI is a different implementation (declared types, language differences), so pointing it at these files reports differences rather than mistakes. Two things now fix that, and the first is in the repository.

- **`tests/pwa-compile-check.js`** compiles all five modules in the real runtime, at the URL `new-ui/index.html` names, through a virtual page that mimics the PWA's own bootstrap. Run it with `node tests/pwa-compile-check.js`. It catches compile errors and unused-variable warnings, which is how a rewrite leaves a declaration behind. Checked by breaking a module on purpose: the error surfaced in that module and in `shell`, which loads it.
- **A throwaway harness** (jsdom, a stub MQTT client, a converted copy of the live map) drove the real page: map-to-rooms produced output identical field-for-field and room-for-room to what the old shape produced from the old map; the device editor's edit / rename / duplicate-name refusal / add / move / delete each produced the right identity and state; the schedule editor wrote by name, created state for a room that had none, and honoured a profile switch inside the sheet; the page rendered from the shared room list; and the payloads the page published on save — reassembled from their `!part!` chunks — carried `rooms` and name-keyed `profiles` with the user's edits and no identity field leaked into any state. `MergeIdentityRooms` was checked separately against a synthetic identity list: edits taken, deletions applied, stale readings refused, unknown state reported once per profile.

### What this breaks, deliberately and not silently

- **The desktop app.** It renders rooms from `profiles[].rooms` as a list and saves the same shape, so after the migration it shows no rooms and its saves are refused by the new validation (with a log line). It is the secondary UI, and porting it is a separate piece of work with the same shape as stage 2.
- **The legacy UI in `tests/`** (`tests/resources/allspeak/rbr.allspeak` and the Playwright setup specs) reads the same old shape, so that suite no longer matches the controller.
- **`new-ui/demo-map.json`** was converted, since demo mode feeds it straight through `map-to-rooms`. Its second profile carried a single room, which the shared list cannot express — every profile now carries state for all seven rooms, the ones the Weekend profile never had set to Off.

## The migration ran on the live controller

Deployed on 2026-10-17, in the order that fails safely rather than the order that reads better. **Controller first, then the page**: a new controller with an old page shows no rooms and refuses that page's saves, while an old controller with a new page is the dangerous pairing — a page shipping name-keyed profiles to a controller that expects lists, which is how a working map gets overwritten. The window was seconds, not the hour the release mechanism would have taken.

The box (QED6): `map.json`, `controller.allspeak` and `.version` copied aside with a timestamp first, then the new controller **compile-checked on the box itself** with its own runtime (`ascheck.py`, compile-only — running it would have started a second controller against the same broker). That mattered: the box runs AllSpeak 2610071115, a week older than this laptop's 2610142212, and it is the only opinion that counts. The restart went through the unit rather than `systemctl`: the service is `Restart=always`, and the sudo password was not accepted over a non-interactive ssh session, so signalling the controller process let systemd bring it back — which is also why `NRestarts` now reads 3.

The conversion ran on load and the disk map was rewritten inside a minute: 17100 bytes to 13372, one `rooms[]` with eight identity records, three profiles each carrying eight name-keyed states, and the readings stripped as designed (they are re-derived within a cycle). The schedules survived it — Weekend's Kitchen still has its 12:15–14:00 and 18:00–20:00 periods, `All Off` still has no periods at all.

### The bug the live run found

`CommitRooms` copied the readings outward from the working room into the identity record but not the **derived** fields — `status`, `statusMessage`, `relayMessage`, `relaysFailed`, `relaysTotal`, `relay`. Before the split those lived inside each profile's room record, which is what the page was reading; after it they lived only in the working array, so the map the controller sent carried neither a status nor a relay for any room. The page reported every room online, calm and idle, and called out nothing.

It was found by asking the live controller for its map over MQTT and reading what a room actually held, not by any test that existed. The local harness could not have caught it: its fixture was built from the old map in this repository, which carried those fields inside the profiles, so the merge had something to read. Fixed in `CommitRooms`, redeployed, re-checked — rooms now carry `status: good`, `relay: off` and the controller's own message ("Sensor: no report for 34 min").

The lesson is worth stating plainly: a fixture derived from the *old* format proves the translation, not the source. The only test that finds this class of bug is the real controller's own output.

### The bug that only showed up in use

The first live test drove the *page*; the second drove the *system*, and it failed. Tapping Advance on Sunroom, or On, or Off, took effect for about a second and then reverted on the card. Underneath, the relay was following the change — the room really heated — while the card, which reads the profile, kept showing the old state, and the next full processing cycle would have thrown the change away.

The cause is an aliasing assumption that the split made wrong. `MaterialiseRooms` builds the working array with `append`, and **`append` copies** — measured on the box's own runtime:

| form | effect |
| --- | --- |
| `put A into B` | aliases |
| `put entry K of D into V` | aliases |
| `put item I of L into V` | aliases |
| `append A to L` | copies |
| `set … to …` | copies |
| `index X to N` | not a list read at all — it is the indexed-collection form (`set the elements of Room to N` then `index Room to N`), and on an ordinary list it yields an empty dictionary |

Before the split, a working record *was* the stored record — the profile's room list held the very objects the per-room routines mutated — so `set entry 'mode' of Room` reached the map. After it, the working record is a copy, and `CommitRooms` pushed identity outward and nothing else: mode, target, periods, advance, prevmode, until and boostperiod were written into a copy that was discarded on the next materialise. Everything looked right until the first per-room interaction.

Two changes fix it, and both are needed:

- **`CommitRooms` now commits the state half too** — the nine schedule fields, copied by name into `profiles[MaterialisedProfile].rooms[name]`, replacing the entry so a field a handler deleted stays deleted. A whitelist rather than "everything that is not identity", because the working record also carries per-cycle scratch (`advance-rq`, `responses`) that has no business in somebody's plan.
- **`MaterialiseRooms` now builds the working record from a copy**, `prettify` then `json`, instead of aliasing the stored state. With the aliasing in place the merge was writing relays, sensors and readings *into* every profile's state — the duplication the shared room list exists to remove — and the page shipped them back on its next save.

`MaterialisedProfile` (new) records which profile the working array was built for, so a commit that happens between `Select Profile` and the next materialise still lands in the profile the records came from rather than the one just selected. And `Update Profiles` now re-materialises *before* the map is pushed, so a save cannot be overwritten by the working array that predates it.

The probe that nails it is now a repo test rather than a note: `tests/unit/commit_roundtrip_test.py` builds a two-room map, extracts `MaterialiseRooms`, `CommitRooms` and `UpdateRooms` **from `controller.allspeak` at run time**, materialises, changes `mode` and `advance` on a working room, commits, materialises again, and demands the change survived with no identity fields and that a deleted field stays deleted. It needs no broker, no browser and no controller box. Both halves of the fix were removed in turn to check that it notices: disabling the state commit fails three of its four assertions (including the live symptom, `'off' != 'on'`), and putting the aliasing back fails the fourth with `'name' leaked into the profile state`.

### The rename that rewrote the wrong room

Asked what a rename actually propagates, I audited every place that refers to a room and then did one, in the live Devices sheet. It renamed the right room and wrote **Outside's wiring over it**: identity slot 2 came back as "Snug Test" carrying `relays: []` and `sensor: Outside-thermometer`, with Outside still in the list, so the room's own relays and thermometer were gone and a copy of the outside sensor occupied its slot.

The mechanism is old and unremarkable once seen. `RenameRoomInEditingRooms` held the room in `RoomEntry`, a shared scratch variable, then called `gosub to NameInUse` to refuse a duplicate name — and that loop ends with `RoomEntry` pointing at the last room it scanned. The rename then set the name on *that* record and stored it back into the renamed room's slot. That is why the name and the state key were right, and the wiring was somebody else's.

Two things made it catchable only by doing it:

- **The harness asserted the wrong thing.** Its rename scenario checked the new name and that the state key had moved — the two facts a rename is "about" — and never compared the rest of the record. It has been tightened to check the whole identity record, plus that no other room was rewritten. A test that checks only the field you changed proves only the field you changed.
- **It is a scratch-variable collision, not a logic error.** Nothing in the rename is wrong in isolation; the routine that checks a name is what breaks it. `AGENT.md` now carries the trap: a shared record variable plus a `gosub` is a borrowed record, because there is no block scope.

The fix is both halves: `NameInUse` gets its own scratch (`NameRoom`), and the rename re-reads the room after the check. The second is not redundant — it makes the whole class impossible for the next routine that loops between reading a record and writing it.

Repairing the live map was its own lesson. Renaming back through the sheet restored the name and the state keys in all three profiles, but not the wiring: the sheet's Save writes the form into the *selected* room, and the damaged room was the selected one, so re-typing the right sensor and relays there did nothing useful. The wiring went back through an `Update Rooms` uirequest instead — the identity replacement path — framed `!part!<i> <n> …` / `!last!<n> …` because the runtime drops unframed payloads. Verified afterwards: Snug with `Lounge-radiators` / `Lounge-thermometer`, its temperature re-derived at 22.0 °C from the Lounge sensor within a cycle, Outside untouched, eight identity records and eight state keys in every profile, disk map rewritten, controller stable.

### What verified the deployment

- **The controller's map, over MQTT** — a `first` request framed as `!last!1 {…}` (the runtime silently drops unframed payloads, loudly but only into its own log): eight identity rooms with readings and derived fields, three profiles name-keyed, per-room state with no identity field left in it.
- **The page, against the live controller** — `/heat/` in headless Brave with the system's MAC and token in localStorage, so `credentials.php` answers and the page joins the cloud broker: seven room cards, temperatures, "Off until HH:MM" projections from the live schedules, the Weekend profile, no console errors beyond the expected `credentials.json` 404.
- **A real write** — the Devices sheet opened on the live system (sensor field showing `Kitchen-thermometer`, which is identity read back through the shared list) and saved with nothing changed. The plan before and after is identical across all three profiles, identity is unchanged, the readings stayed live, and the disk file was rewritten at the same size. The name-keyed payload the page ships and the controller's merge both work against real data.
- **Real heat** — the Office card pressed to "On" in the deployed page: the controller took the request, the map showed the room calling, the summary turned to "System firing", and `zigbee2mqtt/Office-heater/set {"state":"ON"}` went out with the heater drawing 39 W and then 15 W. Turned back off two minutes later (`{"state":"OFF"}`, power 0), with the room off in all three profiles and the wiring untouched. That is the whole chain — page, broker, controller, Zigbee relay, actual current — on the new format, and it is the check worth having before trusting a map change.
- **A change that sticks** — after the state-commit fix, Sunroom's Advance sent from the deployed page: 1.2 s later the button read "Advance to next schedule period (20:00)" and 13 s later it still did, with the card showing the period brought forward (`21.5° → 20:00`), and cancelling it put the card back to "Off until 18:00" and kept it there through several map pushes. The profile state carried `advance: A`, then `-`, with the room's `period` following. Sunroom was left exactly as it was found (`mode: timed`, `advance: -`, back in the gap).

### The site

Five PWA modules, `demo-map.json` and `controller.allspeak` went to both `/heat/` (the operational set) and `/new-ui/`, byte-identical to this repository. First attempt dropped the modules at the root of each directory instead of `resources/allspeak/` — corrected, and the strays removed.

The version stamp was deliberately **not** bumped, so no controller self-updates and nothing re-fetches the tarball. `deploy.sh` (without `--release`) then rebuilt `rbr-controller.tar.gz` and `rbr-controller.zip` from the current tree, which matters for the next install rather than for this one: without it, `get-controller.sh` would have handed a fresh machine the pre-migration controller to go with the post-migration page.

### If it has to be undone

The box holds `map.json.pre-shared-rooms-2610171627`, `controller.allspeak.pre-shared-rooms-2610171627` and the matching `.version`. Rollback restores **both** the map and the controller: the old controller reads `profiles[].rooms` as a list, so it cannot start from the new map any more than the new controller can be left with a map that has no `rooms[]`.

One thing to watch that is not ours: the outside thermometer had been silent for about two hours by the time the page was checked (`status: fail`, no reading, "—" on the card). Pre-existing, and the sort of thing the card is supposed to say out loud.

The tracked sample `map.json` was converted afterwards, so the repository no longer contradicts the format it documents: 8 identity records, three profiles of 8 name-keyed states, 17,100 bytes to 16K, and — checked the same way as everything else — byte-identical translated output to the sample it replaced. The one-off outputs `cleanup-map.allspeak` and `migrate-periods.allspeak` leave behind (`map-clean.json`, `map-new.json`), `map-sim.json` (regenerated under `--simulate`) and the legacy UI's `tests/map-sim.json` are still old shape, and `AI/MAP_FORMAT.md` now says that readings and derived status are absent from a written file by design.

## Two findings recorded rather than acted on

- **`protect` and `ptemp` are controller-ignored.** The frost-protection fields are written by the new UI's frost sheet and read by the legacy room editor, but `controller.allspeak` never reads either — zero references. As far as the controller is concerned frost protection has no effect. Not part of this work, and not obviously a bug (the UI computes its own indicator), but it deserves its own look.
- **`map.json` aliasing in AllSpeak — and it depends on the runtime.** In the Python CLI (`controller.allspeak`) assigning one json variable to another aliases them, so `put Map into MapDisk` followed by `delete entry … of MapDisk` deletes the field from the live map; the idiom that copies there is `put prettify X into T` then `put json T into Y`. In the **browser** runtime the opposite is true, and it was measured this time rather than assumed: `put A into B`, `set property k of A to B` and `set element 0 of L to A` all copy, so mutating the copy leaves the original alone. The PWA's `put IdentityRoom into MergedRoom` relies on that, and the controller's merge keeps using `prettify` + `json`.

## Settled after the migration

Decisions taken once the live system had been running on the new format for a couple of hours. They are recorded so they are not re-raised as findings.

- **A deleted room's relay is left in its last state.** Nothing commands it once the room leaves the shared list, and that is accepted: the hardware is recovered and reset when a room goes, and Zigbee2MQTT covers anything the controller leaves behind. No code change.
- **A rename splits the heat-log history into a new `<root>/<room>/` folder.** Accepted as a property of the data rather than a fault — the records are joined when they are processed, not when they are written.
- **The desktop app and the legacy UI in `tests/` still speak the old format.** `desktop/rbr-desktop.allspeak` renders rooms from `profiles[].rooms` as a list, so it shows none against the live controller and its saves are refused; `tests/resources/allspeak/rbr.allspeak` and the Playwright setup specs read the same shape. Neither will be ported. `/heat` is the only UI that matters, it is to be redesigned, and **all legacy code the new system does not need is being removed** — RBR-Now, Shelly, the ESP transport and the old UI tree along with it. Backups of the earlier work exist, so nothing has to be preserved in the current tree to keep it.
- **The old live system will not be updated again.** It is being replaced by a Zigbee installation on a new controller, so compatibility with it is not a constraint on anything here.

## Still open

1. **The product documentation says nothing about the map format**, by design rather than omission — `docs/` describes profiles and schedules in English and never the JSON, so nothing there went stale. `AI/MAP_FORMAT.md` is the format of record.
2. **Not verified on real hardware for the new format's own sake.** Everything the environment allows has been checked: the loop runs against a broker, both systemd drop-ins were validated against the real systemd, `asdoc-check` is clean on every changed script, the three repo checks pass, and the live controller has been exercised through the page — but the heating season proper is the real test.
