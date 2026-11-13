# 2026-11-12

## 21:13

I'm looking for the most cost-effective PC for use as the RBR system controller. Ali Express have  number of J1800 Mini PC models with 2GB/32GB for around £35. Is this powerful enough for the job?

**Assistant**

**Short answer: the CPU and RAM are fine; the 32GB eMMC is the part to think about.**

What RBR actually asks of the machine, from this repo:

- `rbr-preflight.py` treats 480 MB of RAM, 1 GB of free disk, a wired NIC and a spare USB port as the floor, and `rbr-doctor.py` warns once less than 100 MB is available.
- The bill of materials says the controller "has no performance requirement worth speaking of — it is a scheduler, not a solver."
- The stack on the box is mosquitto, Zigbee2MQTT (Node 22), a small Python bridge and the Python AllSpeak controller. The PWA runs in the phone's browser, not on the controller; the local UI is just static files if you install it at all.
- Steady state should land around 400–600 MB, with Zigbee2MQTT the largest item. 2 GB therefore leaves real headroom, not a squeak.
- CPU: six ten-second decision cycles a minute, a handful of sensor messages per device per hour, and relay commands. A dual-core 2.41 GHz J1800 is far more than that needs. The only heavy moments are one-off: `pnpm install` plus the TypeScript build of Zigbee2MQTT during setup (minutes, and the memory peak of the whole exercise), the daily journal export, the monthly backup zip, and boot.

Two caveats on the 2 GB: use a server distribution rather than a desktop one, and make sure some swap or zram exists for the install step — `pnpm install` is the one thing likely to press on 2 GB. After that the box sits at a few percent CPU, 24/7.

**Storage is the real question.**

- Capacity is ample. Debian, Node, Zigbee2MQTT and its dependencies come to roughly 3–4 GB. The event journal is capped at 1 GiB (about 130 days at the synthetic worst case of 7.9 MiB/day, less in practice, and the 10%-of-free-space cap binds first on a small disk). Heat logs and the 14 daily export bundles are small. Expect roughly 10–30 MB written per day.
- Endurance is probably fine at that rate too, but a cheap 32 GB eMMC is the least reliable part of a £35 box, and unlike a microSD card it is not easily replaced. The docs are firm about "solid-state storage that is not a microSD card" and accept "a board with built-in storage", while `rbr-preflight.py` warns specifically when `/` is on `/dev/mmcblk`. Cheap eMMC also tends to fail badly on power cuts, which matters for something wired into a heating system.
- If the model has a 2.5" SATA or mSATA slot, fit a cheap 120 GB SSD and the concern disappears. Check before ordering: many J1800 mini/firewall boxes have one SATA header plus power, some are eMMC-only. If there is no slot, the eMMC is workable — RBR deliberately keeps logs in RAM, volatile data in `/run`, and writes the plan only when it changes — but keep the monthly archive (ideally with the emailed copy) and expect the flash to be the eventual failure.

**Things to check specifically with these AliExpress J1800 boxes:**

- **64-bit UEFI.** Some Bay Trail boards ship 32-bit UEFI, and a standard amd64 Debian installer will not boot. Ask the seller, or boot a live USB before committing.
- **"Restore AC Power Loss" = Power On** and **ErP/EuP = off**, then test it by cutting the mains and watching the machine come back unaided. On this family there can also be an "AUTO ON" jumper on the board — the docs mention exactly that on a J1900 board — which overrides the firmware setting, so look at the board as well as the setup screen.
- **A wired NIC** (usually Realtek RTL8111, which Debian handles) and **spare USB ports**: one is permanently taken by the coordinator, which wants to sit on an extension lead clear of the metal case.
- **Ventilation.** Fanless is what you want, but give it air; after a day, `rbr-doctor.py` reports the CPU temperature and load average.
- It is a 10 W-class part, so running cost is trivial — roughly £20–25 a year at UK rates.

If the 2 GB is a socketed SO-DIMM, note the J1800 supports up to 8 GB; a 4 GB stick costs very little and removes the install-time worry. If the seller offers 4 GB/64 GB for around £45, that is the better buy — not because RBR needs it today, but because it removes both weak points at once.

Before installing anything, copy `rbr-preflight.py` across and run it: it reports cores, RAM, free disk, whether `/` is on `mmcblk`, the timezone, the ports and whether the cloud broker is reachable, in ten seconds, and changes nothing.

**Verdict:** at £35 it is a reasonable buy for this job — the machine is idle most of the time and nothing about RBR needs more compute. It is not too slow; it is slightly too cheaply stored, so either put an SSD in it or treat the eMMC as the consumable part.

## 21:16

At £35 it may be cheaper to replace the machine than buy an SSD

**Assistant**

Fair point, and for a house you maintain yourself I would take it. The £35 replacement is the right unit of insurance if what you are buying is a spare **machine**: it covers the power supply, the NIC and the board as well as the flash, none of which an SSD upgrade touches. A generic 12 V brick is a more common failure than the eMMC.

Where the arithmetic shifts slightly:

- The comparison is not £35 against £15 — it is £35 against the cost of an outage. If you are the one who notices the controller has stopped and swaps it, the cold spare wins. If it is a customer's house where a dead controller means a callout, an SSD (where the box takes one) is cheaper than one visit.
- A spare only stays a spare if it is ready. Two sensible paths. Either install the full stack on both and keep the second unplugged, restoring the latest monthly archive when it is needed — that carries `.mac_override`, `credentials`, `map.json`, its history and the Zigbee2MQTT data (network key, `database.db`, `coordinator_backup.json`), so the replacement comes up as the *same* system with no re-provisioning on the web host. Or image the first machine's eMMC and write it to the second, which is faster — but then never power both on at once, because they would share one MAC and one MQTT identity.
- Buy the spare **with** the first one. These AliExpress models disappear; in two years the same box may be unobtainable, while a 2.5" SSD is still on the shelf. A different model also works as a replacement (any x86 mini-PC plus `rbr-restore.py`), so you are not locked in, but identical hardware makes the swap trivial.
- Test the second unit when it arrives, before it carries the system identity: run it with the network unplugged, or just check memory, disk and the AC-power-on setting, then power it off.

On wear, your instinct is right, and it is worth stating precisely: at roughly 10–30 MB/day written, with logs in RAM, volatile data in `/run` and the plan written only when it changes, eMMC endurance is not the failure mode here. The risk is cheap-flash quality and what a power cut does to it, which is exactly what a spare machine insures against better than an SSD. `map-history/` and the monthly archive cover a plan caught mid-write, and `rbr-doctor.py` reports I/O errors if the flash starts to go.

Two caveats on the spare strategy:

- **The coordinator is arguably more likely to fail than the PC.** Keep a spare dongle too. `restore-z2m-network-key.py` plus the `coordinator_backup.json` in the archive puts the network key back rather than requiring every device to be re-paired — usually; a coordinator swap is not always seamless.
- **Keep the archive off the machine.** Use **Menu → Backups** to email a copy, or the spare restores from a file that died with the original.

So: yes, two £35 boxes is a defensible answer, and probably the better one for a self-maintained system, provided the second is bought at the same time and checked once. If the model happens to have a SATA port and you already have a 2.5" SSD in a drawer, fit it; but I would not pay £50 more for a machine just to get one.

## 21:23

A site visit will always be necessary, and restoring the system will always be needed in any case. I hope we have already reached the point where this is largely a one-command job. Linux itself can always be preinstalled on a spare machine, so it's just RBR that remains.
A related point: Since we've moved volatile data to RAM, is there anything remaining that causes frequent enough writes to be of concern for an eMMC or an  SSD?

**Assistant**

**On the restore: it is one command, but only once the stack is on the box.**

What exists now, with Linux already installed:

1. `mkdir rbr && cd rbr && wget https://rbrheating.com/heat/get-controller.sh && sh get-controller.sh` — fetches the controller code.
2. `pip install allspeak-ai` — the runtime, deliberately left out of the setup script.
3. `sudo ./rbr-setup.sh` — mosquitto, Zigbee2MQTT, the services and timers. Interactive, and the slow step (`pnpm install` plus the TypeScript build).
4. `sudo python3 rbr-restore.py <archive>` — one command. It validates the manifest and every SHA-256, refuses path escapes, snapshots what it is about to replace into `pre-restore-<timestamp>/`, restores ownership and modes, stops and restarts the three services, and reports whether `map.json` is usable. `--yes` and `--dry-run` exist.

So if "Linux preinstalled" means the spare has been through that stack once, the swap really is one command. If it means bare Linux, it is three commands plus one, with an interactive step in the middle. The gap is provisioning, not restore: `rbr-setup.sh` has no non-interactive mode. It prompts for the MAC, MQTT username, mail settings, controller service and desktop UI; most default to what a restored archive already contains, and it leaves an existing `credentials` untouched, so restoring *before* setup is the trick that removes most of the questions. A small wrapper — fetch pack, pip install, setup with defaults, restore — would close it, and because it is the same gap for every replacement rather than just an eMMC death, it is worth doing once. I can write that if you want.

**Writes after the RAM move.**

What still touches persistent storage, from the code:

| Write | Cadence | Volume |
|---|---|---|
| `map.json` | only when the plan or a command field changes; the readings are stripped from the copy before the text comparison | about 13 KB per change |
| `map-history/`, `map-last-good.json` | distinct revisions only; checked every 2 minutes, nothing written when unchanged | about 13 KB each, 10 kept |
| heating CSVs | only when target, actual or mode changes; one `O_APPEND` line per row | roughly 60–100 bytes per row |
| event journal | one batch append a minute, plus immediately after a UI request; the batch file itself lives in `/run` | 7.9 MiB/day at the synthetic worst case, normally less; capped at 1 GiB or 10% of free space |
| daily journal export | one tar.gz per day, newest 14 kept | well under a few MB per day |
| monthly backup | one ZIP a month, newest 12 kept | a few MB per month |

Volatile, no disk at all: `thermometers.json`, `heatlog-state.json`, `zigbee-temperatures.json`, `zigbee-trv.json`, `rbr-dashboard.json`, the journal batch file and `heat-watch-state.json`, all under `/run/rbr`; and the systemd journal (`Storage=volatile`, `RuntimeMaxUse=64M`). Mosquitto has no persistence configured, so there is no broker database. The map save is the only non-atomic persistent write, which is what `map-history/` exists for.

That is roughly 5–15 MB a day, or 2–5 GB a year. Against an SSD rated in tens of TB written, or a 32 GB eMMC's tens of TB, it is noise — well under 0.1% of endurance per year. Frequency is low too: the heaviest RBR write is one append a minute, and the two previous offenders (the whole map every 60 seconds, and `zigbee-temperatures.json` on every temperature message) are gone. So nothing in RBR's own design is a wear concern, and the eMMC will not die of write volume.

**What is still writing, and worth knowing:**

- **Zigbee2MQTT's data directory.** `database.db` (SQLite), its cached last-known state, and `coordinator_backup.json` at startup. The files are small, but their cadence is Zigbee2MQTT's choice rather than RBR's — and it is the one figure in this system nobody has measured. If you want it, read `write_bytes` from `/proc/<z2m pid>/io` a day apart; the difference is the answer.
- **The updater's hourly version check.** It downloads the ~150 KB tarball to `/tmp` every hour just to read its `VERSION` stamp, then deletes it — about 3.7 MB a day. That is the only hourly write RBR still makes, and on a box where `/tmp` is disk-backed it is avoidable: set `TMPDIR=/run/rbr` in `rbr-updater.service`, or make `/tmp` a tmpfs.
- **Debian's own housekeeping.** `unattended-upgrades` if enabled, apt indexes, dpkg logs. Not RBR's, but real.
- **Swap.** This is the one that can genuinely hurt: a swapfile or swap partition on eMMC adds unpredictable writes and makes the controller miss its ten-second timings. With 2 GB, use none or zram — not disk swap. The Debian installer may create a swap partition by default, so check.
- **atime.** `relatime` is the default; `noatime` on `/` removes the residual metadata writes from the map keeper's two-minute read and heatwatch's fifteen-minute read. Optional.

**Where the remaining risk actually is:** not wear, but power loss. The map save is non-atomic (the history covers it), and Zigbee2MQTT's SQLite and state files can be caught mid-write. That is why a small UPS is the better £40 than an SSD here: it addresses the failure mode both flash types share, and keeps the heating running through a short cut. If you do fit an SSD, enable `fstrim.timer`; if you stay on eMMC, its own wear estimate is readable with `mmc extcsd read /dev/mmcblk0`, looking for `DEVICE_LIFE_TIME_EST_TYP_A` and `_TYP_B` — which turns "how is the flash doing?" into a number rather than an opinion.

So the answer to the write question is no: RBR no longer has a frequent-writer problem. What remains is a few MB a day, one hourly download that could be moved to RAM, Zigbee2MQTT's own small files, and swap — which should not be on flash at all.

## 21:33

Do devices of this nature have a conventional BIOS? And is it likely they'll be able to auto-resume after a power cycle?

**Assistant**

**Yes — these are ordinary x86 PCs, not appliance boards.** A J1800 box will almost certainly have American Megatrends (AMI Aptio) firmware, occasionally InsydeH2O or an older Award-style BIOS, with the usual setup screens: Del or F2 at boot, boot order, CSM/Secure Boot, SATA mode, and a power-management page. That is the important difference from the IXHUB, whose Android board had no ordinary firmware at all — which is exactly why the repo marks that machine superseded.

But "conventional" only goes so far. Expect 2013–2016 firmware with no vendor support and no updates, sometimes a cut-down menu, occasionally a refurbished unit with a BIOS password, and on some Bay Trail variants a 32-bit UEFI that a standard amd64 Debian installer will not boot. You can see what you have from Linux with `sudo dmidecode -t bios -t system`, `ls /sys/firmware/efi`, and `sudo efibootmgr -v`.

**Auto-resume: probably, and this family is one of the better bets — but it is a per-unit property, not a specification.**

J1800/J1900 mini-PCs were built for kiosks, firewalls and industrial jobs, so most have one of the two mechanisms:

1. **A firmware setting.** Usually "Restore AC Power Loss", "AC Back", "After Power Failure", "PWRON after PWR-Fail" or "State After G3". Set it to **Power On**, not **Last State** — with Last State, a clean shutdown before the cut leaves the machine off. The usual menu paths are `Advanced → APM/ACPI`, `Chipset → South Bridge`, or `Chipset → Power Management`.
2. **A board jumper.** The repo documents this on a J1900 of the same family: a three-pin header marked **AUTO ON** beside the clear-CMOS jumper, where the pair the cap sits on decides, and it overrides the firmware setting. Look for `AT/ATX`, `AUTO ON` or `JP1` near the CMOS header. With the jumper set to AT, the machine starts as soon as power arrives; the power button may then stop turning it off, which is fine for a controller.

Also disable **ErP/EuP Ready** (it can cut standby power and stop the machine waking at all) and, on Intel boards, **Deep Sleep / Deep Sx / Deep S4-S5** — those are the two settings that most often make a correctly set "Power On" appear not to work.

**Test it; do not trust it.** Cut the *mains*, not the DC jack and not the button, and do it three ways: a two-second blip, thirty seconds, and ten minutes. Then run `sudo poweroff`, restore the mains, and confirm it comes up by itself. Each time, check it reaches the stack with `systemctl is-active mosquitto zigbee2mqtt rbr-zigbee-bridge controller` without a keyboard attached. Repeat the test after a week: a flat CR2032 on a decade-old board resets the settings silently, and on a used unit that is a common way to lose auto-on. Replace the cell if the clock is wrong at boot.

**If it will not auto-start**, check the jumper before concluding. If there is neither a jumper nor a setting, the unit is unsuitable for this job — the docs are explicit that a controller which does not return by itself is not a controller. A UPS reduces the number of cold starts but does not remove the requirement: a long outage still ends in one.

Two smaller notes:

- A cheap 12 V brick is part of the power path. A marginal one can latch off or brown out, which looks exactly like firmware failing to auto-start. A spare brick is worth having, and it is another reason the second £35 machine is cheap insurance.
- Even when the machine does come back, a reboot currently has a known side effect: Zigbee2MQTT republishes its cached device state and the bridge stamps it with the arrival time, so a thermometer that has been dead for hours looks fresh for the 45-minute staleness window. Fewer needless restarts is therefore worth having, and that is an argument for the UPS as well as for the firmware setting.

## 22:23

One of the primary initial market areas for RBR is middle-class elderly people living singly or as couples in houses they cannot bring themselves to move from. These people are not poor but their houses are too large and becoming expensive to run. Many of these have support (non-financial) from their own children. RBR would save them substantial amounts on heating. Many are poorly sighted or have problems with technology, and the current UI is too detailed for them. So I have in mind an option under the Hamburger that presents an simplified view, as follows:

The title bar remains, but under it are buttons for the rooms, possibly showing current temperatures only. Not too different from the current screen but with less detail. Clicking a room button brings up a full-screen page holding the card for that room, with more spacing and larger buttons where possible. For example the mode buttons could appear as 2 rows of 2; Timed & Boost, On and Off. The aim is to not confuse such people by having all the other rooms still visible. There would have to be a large Home button at the bottom of the card. everything else should work just as it does now.

Please consider the above. The steps would be
1. Build the alternate home screen and wire to Hamburger
2. Build the new room card and wire to buttons
3. Complete all the room functionality

**Assistant**

This fits the architecture well, and the cleanest implementation is to treat it as a **view mode**, not a second app. The map, the polling loop, the optimistic per-room state, the sheets and every existing action (`ChangeMode`, the target steppers, `ApplyBoost`, `ToggleAdvance`, the schedule and special sheets) stay exactly as they are. Only the home surface changes:

- A `SimpleMode` flag, stored per device, chosen from a new Hamburger row. The title bar and its menu remain available in both modes.
- A second home template: large room buttons, each showing the room name, its temperature and a plain status word. No summary card, no per-room detail.
- A single-room page built from a template that deliberately keeps the **same element IDs** (`room-<i>-name`, `room-<i>-mode-timed`, …) the existing render and action code already uses. That is what lets "everything else work just as it does now": `RenderRoom`, `PaintExpansion`, the mode buttons, target steppers and boost path are reused rather than copied. The layout changes — 2×2 mode grid, bigger spacing — and a large Home button returns to the room list.
- Switching views rebuilds only `#layout-main`; the shell chrome, sheets and MQTT loop are untouched.

The main trade-offs to settle before I build are how the mode is switched and remembered, what a room button shows, and how much of the room's secondary controls should appear on the single-room page. Those change the UX and the amount of wiring, so I'd rather ask than guess.

**Assistant (continued)**

Built all three steps.

- **View mode.** The hamburger has a **Simple view** row, stored per device in `localStorage` under `rbr-simple-view`. The title bar, menu, MQTT loop and all other sheets are untouched. The menu also gains a **Profiles & schedules** row so the profile sheet stays reachable without the summary card's profile pill.
- **Simple home.** One large button per room, showing the room name and current temperature only, as chosen. Map pushes repaint the buttons in place; a changed room count rebuilds the list.
- **Single-room page.** Bigger type and spacing, a 2×2 mode grid (Timed / Boost, On / Off), the larger target stepper, boost durations, Advance, Room details, Special actions, Edit schedule, the override row, and a sticky full-width **Home** button. It deliberately keeps the compact row's element IDs, so `RenderRoom`, `PaintExpansion`, `WireRoomInteractions`, `ChangeMode`, the target steppers, `ApplyBoost`, `ToggleAdvance` and the schedule/special sheets work unchanged.
- Summary-only painting and the boost-countdown repaint now skip elements the simple view does not have. The service worker cache is bumped and the two new templates are precached.
- Tests: `tests/ui/simple-view.spec.js` covers the toggle, the reduced home, the one-room page, a mode change, a target step, a boost, Home, and persistence across a reload. `npm run test:ui` is 8/8 green; the PWA compile check is 12/12; the service-worker check is 22/22; the published asdoc-check reports 0 errors. The remaining asdoc warnings are pre-existing long-title/wrapped-paragraph warnings in older blocks.

While refreshing doc hashes I found two pre-existing missing doc-block terminators — one before `DefaultGestureSource`, one before `PostUiRequest` — which made the published checker report `doc-after-code`. I added the missing `@hash`/`!!!` tails; no behaviour changed.

Deploy with `./deploy.sh`, then reload the PWA and select **Simple view** on the resident's device. No controller script changed.
