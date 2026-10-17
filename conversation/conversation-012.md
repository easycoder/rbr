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
