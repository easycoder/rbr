# 2026-10-16

## 16:40

It is observed in the documentation that SD cards are unsuited to systems that write constantly; that SSD is a better choice. A third choice, in conjunction with either of these, may be even better - RAM disk. Can you look into what is involved in keeping all volatile data on a RAM virtual drive, taking into account to mitigate the risk of losing the current status if power is suddently removed. A previous iteration of RBR did just this, but I don't know how much if any of it travelled into the current code.

**Assistant**

**What the previous iteration did.** The Orange Pi / Linaro generation kept the controller's whole live working directory on a 1 MB tmpfs at `/mnt/data`, mounted at boot from `reboot.sh` and an `@reboot` cron entry. `rbr.ecs` set `put /mnt/data/ into RamDisk` and wrote practically all runtime state there — `map.json`, `status.json`, `logs.json`, `advance.json`, `systemdata.json`, `mijia.json`, `config.json`, and more. Exactly one artefact was written through to the card, and only when it changed: `if Changed save prettify Map to `../map.json``, with the reverse at boot. A daily `backup.sh` gave the plan a second net on disk. Two properties mattered more than the mechanics: there was **no RAM-to-disk refresh at all** (the old answer to a power cut was cold start — everything except the plan regenerated), and some of the volatility came from the image rather than the app (`/tmp`, `/var/log`, `/run` and `/dev/shm` were all tmpfs on that box). The counter-example in the same code is `advance.json`: pressing Advance and pulling the plug lost the decision, which is the trap any RAM-disk design must avoid.

**What travelled into the current code: none of it, and the parts that survived went the other way.** No tmpfs appears anywhere outside the docs. I tabulated every writer: `/tmp/rbr-dashboard.json` every loop; `map.json` in full every 60 seconds **unconditionally**; `thermometers.json` about once a minute; `heatlog-state.json` when dirty; `zigbee-temperatures.json` on **every temperature MQTT message**; `map-history/` every 2 minutes; and the heating records on change. Two things stand out: `map.json` became the single persistent carrier of live state, holding the plan and the readings together, which is why its minute save is unconditional; and `zigbee-bridge.py` is the heaviest writer of all. The one part of the old idea that did survive is an improvement already in hand — `advance` now lives on `Room` and is therefore persisted, where the old code kept it in RAM only.

**What putting volatile data in RAM involves.** A dedicated tmpfs, installed the way everything else is (a unit or a `tmpfiles.d` drop-in written by `rbr-setup.sh`, not a `mount` line in cron), a few MB in size, `mode=0750,nosuid,nodev`, owned by the controller user. Four files are candidates: `thermometers.json`, `heatlog-state.json`, `zigbee-temperatures.json` and the dashboard JSON. `zigbee-bridge.py`'s atomic write creates its temp file in the script directory, so the temp file and the target must move together. What must not move: `map.json`, `map-history/`, `map-last-good.json` and the heating-records root. The journal is the one judgement call — making the logs volatile means configuring journald, and a volatile journal vanishes in exactly the incident where the last few lines are wanted.

**What is actually at risk on a power cut.** Almost nothing, and the reasoning is worth stating rather than assuming. The irreplaceable data is never in RAM. Cold start is already safe: a missing file is read as "reset", and an empty `Thermometers` means `Thermometers has entry Sensor` is false, which sets the room's status to `fail` and forces its relay off — the system fails safe, not stale, because `sensorAge` is recomputed as `now - thermometer.ts`. `heatlog-state.json` is the mildest loss of all, since `heatlog.py` already skips a row identical to the file's last line. The one thing genuinely at risk is the **command state** — which rooms are calling for heat, their modes and targets, an unexpired `until`, an engaged Advance — and it is at risk only if it too is moved to RAM. That is the constraint the whole design turns on.

Four ways to preserve continuity, in increasing cost: accept cold start; refresh the RAM disk to a persistent shadow periodically and restore it at boot; flush on clean shutdown; or keep the command state on disk at all times (recommended). The obstacle to the last of these is that `map.json` currently conflates the plan with the readings, so the two must be separated by field before the minute write can be gated — and that split is the real work.

I wrote it up as `doc/PROPOSAL-volatile-storage.md`, and asked how to take it forward; the answer was to write it up.

## 16:55

If at the same time as introducing a RAM disk we also drop all support for RBR-Now (I think Shelly and others are already gone) does that simplify anything? Once the new system is up there will be nothing except Zigbee, so these things may as well be done together.

**Assistant**

Yes — but narrowly, and mostly because both edit the same `map.json` schema rather than because RBR-Now is a storage problem. I checked what the support actually consists of, and it is bigger than the two files you'd expect: `deviceControl.allspeak` (the `config.json` master lookup, `MessageESPDevice`, the relay-type dispatch), `controller.allspeak` (`RecordThermometer` and its Mijia BLE parsing, the ESP reply handling, `relayType` in the `RoomSpec` packet), `config.json` and `rbr-setup.sh` STEP 5c that exists only to create a placeholder for it, the new UI's relay-type pill, the `RBRNow/` firmware, the legacy configurator in `resources/`, and several docs.

**Where it genuinely simplifies the design:** the readings get a single origin (today `Thermometers` is fed by the merge *and* by `RecordThermometer`), so the volatile set becomes exactly one file for readings with the bridge as sole writer; the fail-safe argument loses its only caveat (the safety override exists precisely because "an RBR-Now relay could report its own temperature when the configured thermometer is dead"); and one fewer persistent file, with a crash-loop wart removed along with it.

**Where it doesn't:** RBR-Now contributes no disk writes at all — `deviceControl.allspeak` has no `save`, only a `load` — so the write volume is entirely Zigbee-side. And MQTT stays regardless: the controller's MQTT is the UI transport, not an RBR-Now dependency, so the credentials, the broker and `.mac_override` all remain.

**The real reason to couple them** is that RBR-Now's retirement retires two plan fields (`relayType` and the vestigial room `ssid`) while the RAM-disk work reclassifies every field in the same file — one migration instead of two. I swept the map for other dead fields and found six more (`address`, `extenders`, `controller-ssid`, `controller-password`, `user-password`, and the map-level `ssid`/`password`/`email`/`message`), and confirmed `linked`, `prevmode`, `relayfails` and the `relaysFailed`/`relaysTotal` pair are all live. I asked how to capture it and which fields to retire; the answers were to extend the proposal and to sweep for other dead fields.

## 17:08

I want to go ahead with the dual tasks; RAM disk and RBR-Now retirement. Regarding deployment, I want to set up a new heat/ folder on the server, which will be populated with everything needed going forward. The new-ui folder can remain as it is for now, but will eventually be deleted. I've backed up the current controller in case there's a need to resurrect the current code.

**Assistant**

Took the deployment decisions first, because they change the work. `/heat/` becomes the operational set — the PWA plus every controller file and update artifact — with the root left as it is and later becoming a product-information home page, and the update URLs cut over hard. Two findings changed what I proposed to deploy: **`auth.php` and `credentials.php` must stay at the site root**, because both read `../rbr-users.json`, which is deliberately outside the web root; a level deeper would put that file inside the served tree. Both UIs reach them by the same paths from either location. And **`/docs` and `/dist` stay put**, being product rather than controller.

Then the work itself, in three parts, all verified as far as this environment allows.

**Deployment.** `deploy.sh` now assembles `/heat/` in a temp directory and syncs it as one tree, because the PWA and the controller files share the directory and the sync prunes deletions — syncing `new-ui/` straight into it would delete the controller files already there. `version` is uploaded separately and last, preserving the guarantee that a controller mid-check never sees a new stamp with stale source. The workflow mirrors it without `--delete` on `/heat/` for the same reason. `rbr-updater.py`'s default URL, `get-controller.sh`'s base and `test.allspeak` now point at `/heat/`; `doc/UPDATE-MECHANISM.md` gained a section on the layout and the cutover. I also corrected `doc/CONTROLLER-FILES.md`, whose "how updates work" section still described `CheckForUpdate`, a routine that no longer exists.

**RBR-Now retirement.** `deviceControl.allspeak` went from 209 lines to 116 (one transport, the local Zigbee bridge). `controller.allspeak` lost `RecordThermometer`, the BLE branch of `ProcessReply`, `relayType` and two variables — and here I caught a regression before it shipped: `ProcessReply` also carried the numeric-temperature branch, which is how `simulator.allspeak` answers, so removing it along with the BLE branch would have broken simulation mode. It stays, with the doc block now saying which reply shape is which. `config.json` and `devices.json` are deleted — the latter turned out to be a second copy of the same RBR-Now hardware config that `AGENT.md` and `AI/PROJECT_OVERVIEW.md` described as a simulator file and that nothing ever read. The new UI's relay-type pill is gone from both the script and its Webson layout. `retire-rbr-now.allspeak` is a new one-shot migration in the shape of `cleanup-map.allspeak`, run and verified against the dev map: 51 fields removed, nothing else touched.

**RAM disk.** `/run` is already a tmpfs on any systemd distribution, so the volatile directory is `/run/rbr`, created by a `tmpfiles.d` drop-in — no fstab entry, no mount unit, no ordering, nothing to size — with the path recorded in a one-line `volatile-root` file, the same pattern `heatlog-root` already used. Four files moved there. Because the path is configurable and falls back to plain names beside the code, a dev machine and the test suite behave exactly as before.

For the map, I reached §6's goal without its risk. Rather than tracking which fields changed, `PrepareMapForDisk` builds a copy with the eight reading fields deleted and the tick writes only when that text differs from last time — the readings never reach the disk and the file is written only when the plan changes. Establishing that required finding out how to copy a json variable in AllSpeak: assigning one to another **aliases** them, so deleting a field from the copy would delete it from the live map. The idiom that works is `put prettify X into T` then `put json T into Y`, which I confirmed against the runtime before writing any of it. I also stripped the code out of the controller afterwards and ran it against a real map to confirm the live map is untouched and exactly the eight fields go.

Left open and recorded rather than decided in passing: the journal is still on the disk (making it volatile means reconfiguring journald system-wide); `resources/` and `RBRNow/` still hold RBR-Now things; the tracked map fixtures still carry the retired fields; and the full loop has not been run against a broker, because there is none in this environment. One incidental finding worth its own look: the controller never reads `protect` or `ptemp`, so frost protection currently has no effect as far as it is concerned.

Verification: `asdoc-check` clean on every changed script, 65 unit tests and the heatlog tests pass, everything compiles, and both Python path helpers were run with and without a `volatile-root` file. `DIFF.md` leads with the manual step each controller needs.

## 18:43

_(goal round)_ Continue making concrete progress on the current goal. Verify the work you perform.

**Assistant**

Checked the objective against what was built and found three items it names that were still undone: journald volatility, the `RBRNow/` firmware and legacy configurator, and the tracked map fixtures. All three are now done.

**The journal is volatile.** `rbr-setup.sh` STEP 5d writes `/etc/systemd/journald.conf.d/rbr.conf` with `Storage=volatile` and `RuntimeMaxUse=64M`, so the journal lives in `/run/log/journal`, never reaches the card or the disk, and cannot be filled by a chatty component. The trade-off is stated in the script and in both product docs rather than buried: a volatile journal is emptied on every reboot, and an unexpected restart is exactly when its last lines are wanted. What makes it acceptable is that `controller.service` runs unbuffered, so its lines reach the journal as they are written; the one-line revert is printed by the installer and written into the docs.

**The firmware and toolchain are gone rather than archived in place.** `RBRNow/` (26 files), the legacy configurator `resources/allspeak/config.allspeak` and `flash-device.allspeak` are deleted. I checked first that nothing referenced them: the configurator is orphaned (no link, no loader) and `flash-device.allspeak` existed only to flash `RBRNow/` onto a device. I extended the deletion to the flashing tool because leaving it would leave a repo that cannot work as documented — it copies a directory that no longer exists. `configurator.md` and `setupHardware.md` are kept as the only description of how the hardware worked, with the banners rewritten to say plainly that nothing in them can be run any more, rather than that they are merely "legacy".

**The fixtures are swept.** `map.json`, `map-clean.json`, `map-new.json`, `map-sim.json`, `resources/allspeak/map.json` and `resources/json/newroomspec.json` lost `relayType`, the room `ssid` and the nine legacy map-level fields. Before touching them I checked that a JSON round-trip at each file's own indent reproduces it byte-for-byte — it does, so the sweep is deletions only, and it came out as 257 removed lines with every file still valid and everything else identical.

**Verification.** Both systemd drop-ins were checked against the real systemd rather than assumed: `systemd-tmpfiles --cat-config --root=` reads the tmpfiles file from the path the installer uses, `systemd-analyze cat-config --root=` merges the journald drop-in from its path, and both keys I set appear in the installed `/etc/systemd/journald.conf`. `asdoc-check` is clean on every changed script, the 65 unit tests and the heatlog tests pass, and `bash -n` passes on the installer and `deploy.sh`.

The objective is now complete except for the one thing this environment cannot do: there is no MQTT broker here, so the controller's full loop — the minute tick, the guarded write and the volatile paths together — has still not been run end to end. `DIFF.md` says exactly what to look at on a box. The remaining residue is the legacy UI's own relay-type screens, which are inert and belong with `resources/` when it is deleted.

## 18:55

_(goal round)_ Continue making concrete progress on the current goal. Verify the work you perform.

**Assistant**

Three items the objective names were still undone — journald, the `RBRNow/` firmware and legacy configurator, and the tracked map fixtures — and one verification I had called impossible turned out to be possible, which was the valuable part of this round.

**The journal is now volatile** (STEP 5d): a journald drop-in with `Storage=volatile` and `RuntimeMaxUse=64M`, with the trade-off stated in the script rather than buried and the one-line revert printed by the installer. **The firmware and toolchain are deleted**, not archived in place: `RBRNow/`, the orphaned legacy configurator, and `flash-device.allspeak` — which existed only to flash `RBRNow/` and could not work without it. The two documents that describe that hardware are kept with their banners rewritten to say plainly that nothing in them can be run any more. **The nine tracked fixtures were swept**, and before touching them I confirmed a JSON round-trip at each file's own indent reproduces it byte-for-byte, so the sweep is deletions only.

Both systemd drop-ins were then checked against the real systemd rather than assumed: `systemd-tmpfiles --cat-config` and `systemd-analyze cat-config` both read them from the paths the installer uses, and both keys I set appear in the installed `/etc/systemd/journald.conf`.

**Then I did the thing I had said could not be done here.** There is no mosquitto, but there is network, so I stood up a pure-Python broker in a throwaway venv and ran the controller against it — and, later, a twenty-line stub in place of the Zigbee bridge so the relays would answer. The first run found two crashes on the same minute-long path:

- **My own guard died at the first tick.** `LastMapDiskText` was compared before it had ever been assigned; AllSpeak refuses to compare an unset variable with anything. Under `Restart=always` that is a controller that runs for a minute, dies, and does it forever. This is exactly the class of bug the earlier verification could not reach — I had tested the strip logic in isolation, which never touched the guard, and I had compiled the controller, which proves nothing about a variable's first use.
- **A pre-existing crash on the same path**, which is not mine: the version watch read `.version` and then `replace`d in it without checking the file was there, so a machine installed by hand rather than through `get-controller.sh` stopped about a minute after every start. Fixed, and flagged as pre-existing.

The second run also exposed that the written map still carried `relayMessage`, `relaysFailed` and `relaysTotal` — three derived fields my sweep had missed because I took the field list from the proposal rather than from the code. I enumerated every field the controller writes to a Room (twenty-three) and reclassified, so the strip is now eleven fields.

With all of it fixed, a run of several minutes is clean and behaves as designed: the volatile directory resolves both ways (`thermometers.json` written into it, `zigbee-temperatures.json` read from it), `map.json` is written once and **not** rewritten at the second tick with an identical md5, the file holds the plan and `relayfails` and none of the eleven derived fields, and the rewritten device module drives the stub bridge. What remains unverified is real hardware, which no amount of local scaffolding can substitute for.

## 11:47

_(install session)_ After deploying, the user worked through `sudo ./rbr-setup.sh` on the controller. `pnpm install` appeared to hang at Step 3c; Ctrl-C did not stop the script, and it ran on to Step 7. Then: "Is this OK?" with the network_key check showing GENERATE.

**Assistant**

Two problems, one of them mine.

The Ctrl-C was harmless to `pnpm` but useless as a way to stop the script: the line is `pnpm install 2>&1 | tail -5 || echo "⚠ pnpm install failed"`, so the `||` swallows the failure and the script carries straight on. I had told the user Ctrl-C was a safe abort — wrong about the mechanism.

That mattered because the continuation reached STEP 3's config write, which was unconditional with `network_key: GENERATE` and `pan_id: GENERATE`. On a re-run that resets the identity of the Zigbee network, and Zigbee2MQTT only notices at its next start — so the damage would have surfaced days later looking like a hardware fault. Nothing was broken yet: the service was still running on its in-memory config, and the file still said GENERATE, which proved it had not restarted since.

The recovery came from `coordinator_backup.json`, written by Zigbee2MQTT at 11:25, seven minutes before the 11:32 overwrite. The first repair attempt failed because a multi-line heredoc got scrambled by the terminal — the pasted text showed the script's tail interleaved into its middle — so a garbled script ran and reported no key. Delivery then became the problem rather than the logic: first a single base64-encoded line (verified to decode byte-identically to the tested script), and then, once the user said they could copy files across by hand, a proper tool in the repo.

`restore-z2m-network-key.py` is new. It searches `coordinator_backup.json` for the key in any of the four shapes Zigbee2MQTT has used (list of ints, hex string, list of hex strings, nested objects), refuses to write when it cannot find one, backs the file up first, and rewrites in place so the ownership stays with the `zigbee2mqtt` user. Tested against all four shapes, both failure paths, `--dry-run`, and a repeat run.

The installer defect is fixed too: an existing `configuration.yaml` is now kept, and the only thing corrected is `serial.port`, in place and inside the `serial:` block only — the `frontend:` block has a `port:` of its own that a blunt edit would have clobbered. Verified by test: key and pan_id survive, `serial.port` changes, `frontend.port: 8080` does not.

Also answered along the way: Step 7 is `python3 -m http.server` over the whole controller directory — so it would publish `credentials` and `.mqtt_password` on all interfaces — hence N; Step 8 is y, since it both rewrites the unit and starts the controller that had been stopped.

## 12:56

_(install session)_ "Bridge restarted" — after I found and fixed three defects on the live controller by working on it over SSH.

**Assistant**

Took the offer of direct access. Found the controller at 192.168.1.20 from the MAC in AGENT.md and the ARP table, and key auth worked, so the whole repair could be done without copy/paste — with the limit that says so out loud: sudo needs a password I do not have. That turned out to matter less than expected, because `~/.local/bin/allspeak`, `/run`, and an anonymous local MQTT broker gave me read access to everything and write access to the controller's own directory.

The relay names had to come from the user — relay payloads carry nothing that identifies a room — but the *thermometers* did not: `thermometers.json` still held the old name-keyed entries alongside the new IEEE-keyed ones, and (temperature, humidity, battery) paired all eight uniquely. The heating records then confirmed every pairing independently.

Then three bugs, in order of discovery:

- the stripped map could not be reloaded — four unguarded reads of fields I had deliberately removed from the file — so the controller crash-looped, which is what the PWA's "first map didn't arrive in 30s" actually meant;
- the bridge's atomic write put its temp file beside the script and renamed across filesystems into /run/rbr, so readings were never written at all, and with no readings the controller forces every relay off;
- malformed MQTT messages crashed the controller, twice, while I was probing it.

All three are fixed and verified on the box rather than argued about: the map request returns 13 KB, /run/rbr fills with all three files, map.json is plan-only and stops being rewritten, and the bridge reports no set-failures. I also corrected two device names that did not match the map (`Lounge-radiator` → plural, `Request-relay` → `Demand`), which is the sort of thing only the real map can tell you.

The lesson worth keeping: none of this was reachable from the scaffolding. The end-to-end test restarted nothing and crossed no filesystem. Both classes of bug live exactly in those gaps.

Urgent consequence recorded in DIFF.md: /heat/ still serves the build with the first two bugs, so `./deploy.sh --release` has to go out before any other controller updates.

## 14:18

Do the bridge password updater

**Assistant**

Built it into `rbr-updater.py`, which was the right host: it already runs hourly as root and already restarts services, so the check costs nothing extra and the fix lands where the restart can happen.

The design turned on one question — where does the *current* password come from, since the controller has no token of its own? Two sources, in order: `credentials.php` when a token is present in a new `.mqtt_token` file (the same endpoint and token a paired browser uses), otherwise the local `credentials` file that `rbr-setup.sh` writes. With the token the box heals itself; without it the config still gets brought into line with the local copy, but the right password has to reach the box once. So the token is the difference between self-healing and merely diagnostic, and it is stored at 0600 beside the credentials it belongs with.

Only when the two differ is anything written: a timestamped backup, the config rewritten, `.mqtt_password` brought into line so a later `rbr-setup.sh` prompts with the current value rather than a stale one, then mosquitto and the controller restarted — mosquitto rereads its config only on restart, and the controller would otherwise sit on a dead socket.

The part that matters as much as the fix: it logs the bridge's own `$SYS/broker/connection/…/state` every run. The whole reason today's outage cost an afternoon is that a refused bridge makes nothing else fail — the browser connects, subscribes, asks for the map, and the request goes nowhere.

Tested against five cases before shipping (missing config, up to date, stale in check mode, stale and applied, no credentials at all) and then against the live `credentials.php`, which fetched the 48-character value and corrected a stale config. `--check` now counts a mismatch as a problem so the exit code reflects it. Deployed to the box with the token: the self-check there reports `up to date (from credentials.php)` and `Bridge to the cloud: connected`.

## 14:29

Anything I've missed, and a pre-flight check

**Assistant**

Answered the handover question from what today actually cost: passwordless sudo (every root action was blocked today), the IP rather than the hostname (QED6 never resolved — I found the box by matching the MAC against ARP), the coordinator attached before the setup runs, and the discipline of writing down the six-digit system password when it appears.

Then found one more bug in the thing I had just built: the updater wrote a password straight into a line-oriented config file, so a value carrying a newline would have appended a directive to mosquitto's configuration, and one carrying a space would have corrupted the line. Unlikely — the cloud generates hex — but the local credentials file is hand-editable and the write happens as root. Now validated as a single token with `fullmatch`, not `match`, because `match` anchors only at the start and would let `abc\nevil` through. Tested with a newline injection, a space, and a space in the username: all three refused, config untouched.

Wrote `rbr-preflight.py` for the next install. Testing it against the working controller rather than the dev machine was the point: it caught three bugs in itself. Port 8883 was checked as a local port when the bridge only dials out to it. `mosquitto` and `zigbee2mqtt` came back "not installed" on a controller running both, because they were looked up in PATH — mosquitto is in `/usr/sbin` and zigbee2mqtt is a directory. And the port check called RBR's own listeners a problem, when on a working machine those are exactly what is listening.

Also flagged the two gaps that a new system will meet: nothing creates `.mqtt_token`, so a fresh controller will not self-heal the bridge password; and isolation between two systems rests on MAC-as-topic rather than an ACL, with the broker on a host I cannot inspect.

## 14:49

Power-cut test

**Assistant**

The user pulled the plug for two minutes. Verified rather than trusted, and the design held: `/run/rbr` was recreated by the tmpfiles drop-in, no fallback to disk, all 18 Zigbee devices back with state and all 8 thermometers reporting, the udev symlink recreated, the cloud bridge back at `state 1`, `map.json` valid and written once rather than churning, and the heat log resuming with a gap of about four minutes in the three heated rooms.

One finding worth acting on: z2m republishes cached device state at startup and the bridge stamps `last_seen` with *arrival* time, so a sensor that has been dead for hours reads as fresh for the whole 45-minute window immediately after a reboot — exactly when the staleness gate matters. The Outside thermometer is the live example: its value is cached, it logged nothing all day until the post-boot line, and its file for today was created at 14:35.

Also noted: the retired RBR-Now fields are still in the live map.json, so `retire-rbr-now.allspeak` has never been run on this box; three pre-fix files are still sitting beside the code from 12:0x; and the volatile journal means a crash now leaves no evidence, which is the trade we chose but worth stating plainly.

## 17:24

Remove the pre-fix files, retire the map fields, and where rbr-users.json comes from

**Assistant**

Deleted the three pre-fix files beside the code and an orphaned `config.json` in the retired format — nothing reads any of them now, but a fallback would have picked them up and presented hours-old state as current. `config.json` has not come back, so nothing recreates it.

Ran `retire-rbr-now.allspeak` on the live map and verified it structurally rather than by eye: 51 fields removed, 3 profiles × 8 rooms preserved with identical names, only `relayType` and `ssid` gone, every kept field byte-identical.

Wrote `apply-retired-map.sh` because the swap cannot be a plain copy: the controller holds the map in memory and writes it back when it changes, so swapping under a running controller is silently undone. The script validates before stopping anything, keeps a backup, fixes ownership, restarts and verifies; `--dry-run` needs no root. Tested against four refusals and a dry run of the real replacement.

Then read the server code to answer where rbr-users.json entries come from — and found that registering is not the whole story. `auth.php` creates the entry (with a server-generated six-digit password) at `/register` and marks it verified at `/verify`, minting the token. But the `credentials` block that `credentials.php` demands is written by nothing: a freshly registered system gets a 401 until someone adds it by hand, and the UI's fallback then lands in demo mode without explanation — the same class of trap as today's `credentials.json: {}`.

## 17:39

A provisioning tool, for now and later

**Assistant**

Built `provision-system.py` because the gap is structural rather than a one-off: register and verify were the whole of the visible story, and the `credentials` block that `credentials.php` demands had no writer at all.

The design keeps the danger loud. It tests the broker login before writing anything, using a hand-built MQTT CONNECT over TLS so the host needs no packages — and that probe taught me two things only a live test could: the CONNECT payload must begin with the client identifier or the broker simply drops the connection, which is indistinguishable from a wrong password; and the test has to use the MQTT port, because 443 answers a websocket listener and a raw CONNECT dies there.

Writes are atomic and ownership-preserving with a backup, since a half-written rbr-users.json would lock everyone out and read as wrong passwords. It defaults to a dry run and prints no secret except a new system password.

Nine cases tested, including the two that matter most: a broker refusal that wrote nothing, and a repair of a verified entry that was missing its credentials — the exact state a UI-only registration produces.

## 18:04

Rooms above profiles

**Assistant**

Graham raised as an aside that the PWA assumes a common room set while the map keeps rooms inside each profile. Checking it in the code, the disagreement is real and worse than stylistic: the controller sizes its arrays from the selected profile, while the PWA edits rooms by index across every profile, and nothing checks that an index means the same room everywhere. It is safe only because all three profiles on the live map happen to agree.

He chose the proper fix rather than a guard, on the grounds that a running system rarely needs profiles with different room sets and the controller should match what the PWA presents.

Wrote doc/PROPOSAL-shared-room-list.md: the decision, the field-by-field split (identity gains relays, sensor, linked, relayfails and the readings; state keeps mode/target/periods/events/advance and the frost pair), the three boundaries that change, the two aliasing hazards, the migration, and the staged rollout. No code changed — the controller and the PWA have to move together, and a half-applied format change is worse than the status quo.

## 18:19

Two field placements corrected

**Assistant**

Graham corrected two placements in the proposed split: relay failure counts have little to do with profiles, and frost protection is not profile-specific. He is right on both — the second is the better reading, since frost protection protects the room's fabric whatever the plan says, and putting it in identity also removes another per-profile loop from the PWA.

Checked the remaining per-profile fields rather than assuming they belonged there, and found the code states the intent explicitly: `Select Profile` re-materialises operating state from the profile selected — which is what makes `All Off` actually turn things off — and the operating-mode code clears `until`, `prevmode` and `boostperiod` on a mode change "so the map doesn't carry zombie state across profile views". So `mode`/`target`/`until`/`prevmode`/`boostperiod` stay per profile on purpose, and the proposal now says why.

Also verified the map swap he ran at 14:47: retired fields gone, 3 profiles and 24 rooms intact, controller restarted with zero restarts, and map.json stable over 20 seconds.

## 19:14

Stage 1, the controller

**Assistant**

Implemented the shared room list in the controller: EnsureSharedRooms (old-shape conversion on load, names unioned across profiles, selected profile first), MaterialiseRooms (identity merged into each room's state for the working array), CommitRooms (identity copied outward by name), plus the call sites — ProcessAllRooms, SendMapToUI, PrepareMapForDisk, Add Room, Update Rooms, and a guard that refuses an Update Profiles payload whose profile rooms are not name-keyed rather than emptying the room set.

Two corrections to things I had asserted earlier. asdoc-check is a *documentation* linter, not a parser: "0 errors" from it meant nothing about syntax, and the real parser then found five genuine errors (undeclared variables, parenthesised expressions, `not X has entry`, `the count of` on a dictionary). And an aliasing probe showed `index X to 0` does not make an indexed dictionary and its list entry the same object, which matters because the per-room code mutates through `index`. I restored the explicit write-back the old code had, rather than trusting a comment about aliasing.

The controller now compiles (2734 lines) and starts; it stops where it always would without credentials. A throwaway harness against a synthetic old-shape map confirmed the conversion and the disk copy. The PWA is untouched, so the two halves are inconsistent and nothing may be deployed yet.

## 19:34

Stage 2 sized, and stopped at the boundary

**Assistant**

Looked at the PWA before editing it, and the size answer is what decided to stop. The read path is contained: map-to-rooms can iterate identity and merge the profile's state by name, and legacyIdx simply becomes an index into identity.

The write paths are not contained. Around forty-five sites treat a profile's rooms as an index-addressable list — fifteen in device-editor alone — and three of the operations are index-mutating: swap, delete and reorder. Those have no meaning in a name-keyed dictionary; ordering belongs to the identity list, so each needs redesigning rather than translating. That is the simplification the change buys, but it is a genuine rewrite of the device editor's data handling, not a mechanical rename, and it cannot be done blind or half-done.

So I stopped at a clean boundary instead of starting a rewrite I could not finish or verify. The PWA is untouched, the controller compiles, and nothing is deployed.

## 19:44

The PWA has no compiler here

**Assistant**

Checked whether the browser dialect supports computed property names before writing any of stage 2, and found something more fundamental: `allspeak` cannot parse these files at all. It fails on `put property 'profiles' of Map into Profiles`, the first data statement in map-to-rooms. The `property` keyword simply is not in the CLI's grammar, so `new-ui/resources/allspeak/*.allspeak` are a different dialect compiled in the browser at runtime.

The consequence: there is no local way to syntax-check a PWA change. The only verification is loading the page and watching the console, which needs the whole stack up - broker, controller, served UI, headless browser. Editing forty-five call sites, three of which need redesigning, in a dialect with no compiler and no test path in this session is precisely the blind rewrite that breaks things quietly.

So stage 2 needs its own session with the stack running and one file changed at a time, starting with the shell's sync path. Also worth noting for that session: the computed-property question is still open for this dialect, and everything now keys rooms by name, so it has to be settled first.

## 20:30

The PWA can be checked after all

**Assistant**

Resumed stage 2, which had stopped on the belief that nothing here can compile the PWA's dialect. That was true of the tool I had tried and false as a conclusion: the browser runtime is a different implementation from the `allspeak` CLI, and it is reachable — the same `https://allspeak.ai/dist/allspeak.js` that `new-ui/index.html` loads. Driving it under jsdom, against a virtual page that mimics the PWA's own `rest get` + `run` bootstrap, compiles every module and reports what the compiler says.

Writing that as `tests/pwa-compile-check.js` turned up a second thing worth knowing: `tests/resources/allspeak.js` is a May build and is *older* than what production loads, so the vendored copy the Playwright suite uses is not the dialect the site runs. The check therefore takes the runtime URL from `index.html` rather than carrying its own copy, so it cannot drift from the pin.

Nothing about the PWA's own size changed, but the ground under it did: I could now see a compile error in seconds, and — with a stub MQTT client and a converted copy of the live map — drive the real page. Graham's call was to go through the whole of stage 2 in this session, one file at a time, and to keep the compile check in the repository.

## 20:55

Stage 2, and what the split bought

**Assistant**

Worked through the PWA in the order the data flows: map-to-rooms, device editor, schedule editor, profile sheet, shell. The read path merged identity and state back into one record per room, and the translated output turned out identical — field by field, room by room — to what the old shape had produced from the old map, which is the check worth having before touching anything that writes.

The write paths were where the proposal expected a rewrite and instead got a deletion. Editing a room's relays, thermometer and linked flag was the same three fields written into every profile through a loop; it is now one write to one record. Moving a room was `SwapRoomsAcrossProfiles` — the same two-element swap repeated in every profile, trusting that index 3 meant the same room everywhere — and is now a swap in one list. Rename and delete are the only operations left that touch every profile, and only because a name is the key.

Two constraints fell out that the old array allowed by accident: room names have to be unique, so rename refuses a duplicate and add numbers its default ("Unnamed", "Unnamed 2"); and the card's `legacyIdx` could go entirely, since requests were already addressed by name and the index existed only to reach into per-profile arrays. `outsideRoomLegacyIdx` became `outsideRoomName` for the same reason.

The controller needed one addition the proposal had not spelled out: the payload had no way to carry identity. `Update Profiles` now accepts `rooms` alongside `profiles`, and takes only the six fields a UI owns from it — a page reports what it saw a few seconds ago, and its temperatures must not win over the controller's. Names it has not seen are added, names absent from the list are deletions, and per-profile state naming a room that no longer exists is reported rather than left as a schedule nothing can run. `Update Rooms`, which nothing sends, was also wrong under the new shape — it overwrote the selected profile's schedules with the incoming identity records — and now replaces identity and re-materialises.

The verification is worth recording because it is unusual for this repository: the device editor's edit, rename, duplicate refusal, add, move and delete each checked against a converted live map in a real page; the schedule editor's write-by-name, creation of missing state and in-sheet profile switch likewise; the page rendered from the shared list; and the payloads it published, reassembled from their `!part!` chunks, carried identity and name-keyed state with the user's edits and no identity field leaked into any state. `MergeIdentityRooms` was checked separately, including that a stale temperature from the page is refused while a real edit is taken.

What it breaks, it breaks loudly and on purpose. The desktop app renders rooms from the old shape and will show none, and its saves are now rejected with a log line; the legacy UI in `tests/` reads the same shape, so that suite no longer matches the controller. No migration script is needed — the controller converts an old map when it loads it and writes the new shape back on the next save, which is why the proposal's `propose-shared-rooms.allspeak` was not written. `new-ui/demo-map.json` did have to be converted, and its second profile, which carried one room, now carries all seven with the rest set to Off: a shared room list cannot express a short profile.

## 21:20

The migration, on the live system

**Assistant**

Graham's call was to run it now, accepting hours of trouble if it came to that, and to treat `/heat` as the only UI that matters. So the migration went in, in the order that fails safely rather than the order that reads better: controller first, page second. A new controller with an old page shows no rooms and refuses that page's saves; an old controller with a new page accepts name-keyed profiles it cannot read, which is how a working map gets overwritten.

The box was found at 192.168.1.20 rather than the address in the old scratch script — the DHCP lease had moved, and the first two attempts were aimed at a phone holding the old address. Backed up `map.json`, `controller.allspeak` and `.version`, compile-checked the new controller **on the box** with its own runtime before installing it (2610071115, a week older than this laptop's — the only opinion that counts), then let the unit's `Restart=always` bring it back, since sudo would not take a password over a non-interactive ssh. The conversion ran on load: 17100 bytes to 13372, eight identity records, three profiles of eight name-keyed states, schedules intact.

Then the bug, which is the part worth keeping. Asking the live controller for its own map over MQTT showed every room with no status and no relay: `CommitRooms` copied the readings outward but not the derived fields, and before the split those had lived inside each profile's room record, which is where the page read them. The page was reporting a house that was entirely online, entirely calm and calling for nothing. No test in this repository could have found it — the fixture came from the old map in the repo, which carried those fields inside the profiles, so the merge had something to read. A fixture derived from the old format proves the translation, not the source.

Fixed, redeployed, and this time verified against reality: the controller's map over MQTT (identity, readings, status, relay, name-keyed state), the deployed `/heat` page in headless Brave joined to the cloud broker with the system's own MAC and token (seven rooms, temperatures, "Off until" projections from the live schedules), and a real `Update Profiles` round-trip from the Devices sheet — plan identical before and after across all three profiles, identity unchanged, readings still live.

The site took the five PWA modules, `demo-map.json` and the controller at both `/heat` and `/new-ui`. The first attempt put the modules at the root of each directory instead of `resources/allspeak/`; corrected and the strays removed. The version stamp was deliberately left alone so nothing self-updates, and `deploy.sh` without `--release` rebuilt the tarball and install pack afterwards — which matters for the next install rather than this one, since `get-controller.sh` would otherwise have handed a fresh machine the pre-migration controller to go with the post-migration page.

Still old-shape, as recorded before the deploy: the desktop app, the legacy UI in `tests/`, and the product docs. The outside thermometer had been silent for two hours by the time the page was checked, which is pre-existing and shows on the card as "—".

## 21:50

A change that did not stick

**Assistant**

Graham found what my verification had missed: tapping Advance on Sunroom cancelled itself after about a second, and so did On and Off. It was the most useful kind of report, because the page was telling the truth about the system and I had only checked that the page could read.

The cause was an aliasing assumption the split invalidated. `MaterialiseRooms` builds the working array with `append`, and `append` copies — while `put A into B`, `put entry K of D into V` and `put item I of L into V` all alias. Measured on the box's own runtime, because the project has been wrong about this twice now. Before the split the working record *was* the stored record, so `set entry 'mode' of Room` reached the map; afterwards it reached a copy, and `CommitRooms` pushed identity outward and nothing else. The relay followed the copy — the room really heated — while the card, reading the profile, kept the old state, and the next processing cycle would have thrown the change away.

Interesting wrinkle in the diagnosis: `index X to N` is not a list read at all. It is the indexed-collection form (`set the elements of Room to RoomCount` then `index Room to N`), and on an ordinary list it yields an empty dictionary — which is how my first probe managed to destroy the fixture's first room and then report the controller's commit as broken. The real code reads rooms with `put item I of Rooms into Room`.

Two changes, both needed. `CommitRooms` now writes the nine schedule fields back into `profiles[MaterialisedProfile].rooms[name]`, replacing the entry so a deletion by a handler stays deleted, and using a whitelist so per-cycle scratch never lands in somebody's plan. `MaterialiseRooms` now copies the stored state through `prettify`/`json` instead of aliasing it — without that, the merge was writing relays, sensors and readings *into* every profile's state, and the page was shipping them back. `MaterialisedProfile` keeps a commit that happens between a profile switch and the next materialise pointing at the right profile, and `Update Profiles` now re-materialises before anything can push the map.

Verified the way it failed: a probe on the box's runtime that materialises, changes mode and advance, commits, materialises again and demands the change still be there with no identity fields; then the live page — Advance 1.2 s, 13 s, still held, card showing `21.5° → 20:00`, and cancelling it returning "Off until 18:00" and staying. Sunroom is back exactly as it was found. The fixed controller is on the box, in `/heat`, and in the tarball and install pack, with the version stamp still untouched.

The lesson I would keep from today: the first live test proved the page could read the new map, and that is all it proved. A map-format change has to be exercised by *doing something* to a room, and the only place that shows is the system itself.

## 22:15

What stays behind

**Assistant**

Graham asked whether everything was in the repository, having seen /tmp paths go past. It was — but only the product code. The harnesses and probes I had used to verify the migration lived in /tmp and would be gone by morning, and he asked which of them were worth keeping.

The commit round-trip probe earned its place. It is now `tests/unit/commit_roundtrip_test.py`, wired into `tests/unit/run-unit-tests.sh` beside the heatlog tests: it extracts `MaterialiseRooms`, `CommitRooms` and `UpdateRooms` **from `controller.allspeak` at run time** rather than mirroring them — the mistake the desktop unit tests warn about in their own header — builds a two-room map, changes `mode` and `advance` on a working room, commits, materialises again, and asserts the change survived, the profile has it, the plan absorbed no identity, and a deleted field stayed deleted. No broker, no browser, no controller box.

Then I removed each half of the fix in turn to see if the test noticed: with the state commit disabled three of its four assertions fail, including the live symptom as `'off' != 'on'`; with the aliasing put back the fourth fails with `'name' leaked into the profile state`. A test that cannot fail is a story people tell themselves.

`AGENT.md` gained the aliasing table under "Traps worth knowing before editing", because it is the second time this project has lost an afternoon to it, and the two commands that check this work without a browser now sit in "Running". The rest of the /tmp scaffolding — page drivers, the MQTT map fetcher, the card-tap script — stays out: it carries the live broker password and the system MAC, and the method is written up in DIFF.md instead.
