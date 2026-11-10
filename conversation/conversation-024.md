# 2026-11-09

## 20:56

I would like the code that extracts journal bundles from incoming emails to run as a service. Please create the file and call it rbr-bundle-copy.py (rbr-bundle-copy.service). It will use a config file located somewhere appropriate for a service, containing the path in the email folders, the path to save to and the time to run at. It will create yearly folders at the save path. When it runs it will copy all files that don't already exist. Please also list all the Python imports it needs.

**Assistant**

Created three files in the repository:

- `rbr-bundle-copy.py` — the service.
- `rbr-bundle-copy.service` — the systemd unit.
- `rbr-bundle-copy.conf.example` — the config template for `/etc/rbr-bundle-copy.conf`.

**How it works.** The service is resident (`Type=simple`) because the schedule is the config's `run_at`; there is no timer. It sleeps until the next run, performs one pass, and repeats. If it starts after today's run time, it does a catch-up pass first. `--once` runs a pass immediately; `--dry-run` reports without writing.

`email_path` may be a single mbox, a Maildir, a folder of mboxes (including a Thunderbird profile), a folder of saved `.tar.gz` files, or one bundle. It accepts only attachments whose `manifest.json` declares `rbr-journal-bundle`, and writes them to `<save_path>/<YYYY>/<original filename>` using the journal day from the manifest. A filename that already exists is left untouched; new files are written to a temporary file and renamed into place.

**Install:**

1. `sudo install -m 644 rbr-bundle-copy.conf.example /etc/rbr-bundle-copy.conf`, then edit `email_path`, `save_path` and `run_at`.
2. Put `rbr-bundle-copy.py` in the directory named by `ExecStart` (the unit assumes `/home/graham/dev/rbr`) and adjust `User`, `Group`, `WorkingDirectory` and `ExecStart` if needed.
3. `sudo install -m 644 rbr-bundle-copy.service /etc/systemd/system/`, then `sudo systemctl daemon-reload && sudo systemctl enable --now rbr-bundle-copy.service`.
4. Check first with `python3 rbr-bundle-copy.py --once --dry-run --config /etc/rbr-bundle-copy.conf`.

**Python imports** — all standard library, no third-party packages: `argparse`, `configparser`, `datetime`, `io`, `json`, `mailbox`, `os`, `pathlib`, `re`, `sys`, `tarfile`, `tempfile`, `time`, and `from email.header import decode_header, make_header`.

**Verified.** `tests/unit/run-unit-tests.sh` passes: 76 AllSpeak tests, the whole-controller compile, and 126 Python tests. The new `tests/unit/bundle_copy_test.py` drives an mbox, a folder of saved bundles, and a single archive, and checks yearly folders, byte-for-byte content, skip-existing and dry-run.

The service files are not wired into `deploy.sh`, `rbr-setup.sh` or `rbr-updater.py`; that would ship and enable the service on every controller. Tell me if you want that.

## 20:56

Or it can run as a cron task

**Assistant**

I kept the service as the primary path and added `--once` for manual runs; after your next note ("Service is better") I dropped the cron scheduling note and left the config's `run_at` as the only schedule.

## 20:56

Service is better

**Assistant**

Confirmed: `rbr-bundle-copy.service` is a resident `Type=simple` service that reads `run_at` from `/etc/rbr-bundle-copy.conf`; there is no timer or cron entry.

## 21:01

Do I need to run pip to install anyof the imports?

**Assistant**

No. Every import in `rbr-bundle-copy.py` is part of Python's standard library, so there is nothing to install with pip. That covers `argparse`, `configparser`, `datetime`, `io`, `json`, `mailbox`, `os`, `pathlib`, `re`, `sys`, `tarfile`, `tempfile`, `time` and `email.header`. The new test is stdlib-only too.

The service only needs `/usr/bin/python3`; the script's newest feature is `datetime.isoformat(timespec="seconds")`, so Python 3.6 or newer is enough, and the controller's Python 3.12 is fine. A `ModuleNotFoundError` would mean a broken interpreter or a missing standard-library component, not a package you forgot to install.

## 21:11

Do I need to start the service?What is the status command?

**Assistant**

Yes, after installing the unit. It is not started automatically by copying the files, and it is not installed by `rbr-setup.sh`, so systemd does not know it on this machine yet.

Install, start now, and enable at boot in one go:

    sudo install -m 644 rbr-bundle-copy.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now rbr-bundle-copy.service

The status command is:

    systemctl status rbr-bundle-copy.service

A healthy service is `active (running)`, not `inactive (dead)` — it is resident and sleeps until `run_at`, so there is no timer to check. `systemctl is-active rbr-bundle-copy.service` and `systemctl is-enabled rbr-bundle-copy.service` give the two answers on their own.

Logs and restarts:

    journalctl -u rbr-bundle-copy.service --since today
    journalctl -u rbr-bundle-copy.service -f
    sudo systemctl restart rbr-bundle-copy.service

If `/etc/rbr-bundle-copy.conf` is missing or has a bad `email_path`, the service exits and `Restart=on-failure` retries every five minutes; `systemctl status` and the journal show the cause. To test without installing anything, run `python3 rbr-bundle-copy.py --once --dry-run --config /etc/rbr-bundle-copy.conf`.

## 21:19

I can't see anywhere it names the Python file. How does it work?

**Assistant**

The service unit is where the Python file is named. In `rbr-bundle-copy.service`:

    ExecStart=/usr/bin/python3 /home/graham/dev/rbr/rbr-bundle-copy.py --config /etc/rbr-bundle-copy.conf

The chain is:

1. systemd loads `/etc/systemd/system/rbr-bundle-copy.service`.
2. Its `ExecStart` runs `/usr/bin/python3` on `rbr-bundle-copy.py`.
3. The script reads `--config /etc/rbr-bundle-copy.conf`.
4. The config only supplies `email_path`, `save_path` and `run_at`; it never names the program.

That is why the `.conf` file does not mention the Python filename. After installing, `systemctl cat rbr-bundle-copy.service` shows the `ExecStart` line, and `systemctl show -p ExecStart rbr-bundle-copy.service` prints the running command.

I can see the example config now points at your Thunderbird `QED6` mbox, `/home/graham/RBR-journal` and `05:00`. That is `rbr-bundle-copy.conf.example`; the service still reads `/etc/rbr-bundle-copy.conf`. Copy the edited file there (or change `--config` in the unit to point at the edited file), or the service will use the stock `/etc` file. I added a comment to the template making that clear.

Your `email_path` is a single Thunderbird mbox file, which the service supports directly. If the script is somewhere other than `/home/graham/dev/rbr`, change `WorkingDirectory` and `ExecStart`, then run `sudo systemctl daemon-reload && sudo systemctl restart rbr-bundle-copy.service`.

## 21:43

I've set up ./rbr-bundle-copy.service to use .rbr-bundle-copy.conf, which has the wanted values in it. I'd prefer to keep this in /home in case of system upgrades wiping out /etc. How do I reinstall the service?

**Assistant**

The repo unit now points at the home config, but the copy installed in `/etc/systemd/system/` is still the old one, which points at `/etc/rbr-bundle-copy.conf`. That is why the running service still uses `/etc`.

I checked the paths: the unit is `/home/graham/dev/rbr/rbr-bundle-copy.service`, and it runs `/usr/bin/python3 /home/graham/dev/rbr/rbr-bundle-copy.py --config /home/graham/dev/rbr/rbr-bundle-copy.conf`. The config has no leading dot; the file that exists is `rbr-bundle-copy.conf`, so that is the one it will read.

Reinstall the unit:

    sudo install -m 644 /home/graham/dev/rbr/rbr-bundle-copy.service /etc/systemd/system/rbr-bundle-copy.service
    sudo systemctl daemon-reload
    sudo systemctl restart rbr-bundle-copy.service

`daemon-reload` is the step that makes systemd read the edited unit; a restart alone would keep the old command. The existing enabled state is preserved.

Verify the result:

    systemctl show -p FragmentPath -p ExecStart rbr-bundle-copy.service
    systemctl status rbr-bundle-copy.service --no-pager
    journalctl -u rbr-bundle-copy.service --since "2 minutes ago"

Expect `ExecStart` to name `--config /home/graham/dev/rbr/rbr-bundle-copy.conf`. Because 05:00 has passed, the restart does a catch-up pass; it should report the three bundles as `already present`, then log `next run 2026-11-10 05:00`.

If you want to stop copying the unit into `/etc` after every edit, link the repo file instead:

    sudo systemctl disable --now rbr-bundle-copy.service
    sudo rm /etc/systemd/system/rbr-bundle-copy.service
    sudo systemctl link /home/graham/dev/rbr/rbr-bundle-copy.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now rbr-bundle-copy.service

After that, editing the unit in the repo and running `sudo systemctl daemon-reload && sudo systemctl restart rbr-bundle-copy.service` is enough. I also corrected the stale comment in the unit that still said the config was in `/etc`.

## 21:43

This turn ended with work still outstanding: run a relevant verification command after the latest write for the current role setting (not documentation-only: "rbr-bundle-copy.service" changed).

**Assistant**

Verified the edited unit with `systemd-analyze verify ./rbr-bundle-copy.service && git diff --check`; both pass.

## 21:52

My colleague just had a controller failure of some kind, but he's vague at reporting the detail and it's now restarted. I believe we have a watchdog to catch this; can you summarise what it does?

**Assistant**

The watchdog is `rbr-watchdog.sh`, run every 15 minutes by `rbr-watchdog.timer` (Persistent=true, with up to 2 minutes of jitter). It runs as root as a one-shot service. Its job is not to diagnose; it keeps the four core units alive and gives up if repeated restarts do not help.

Every run — component checks. For `mosquitto`, `zigbee2mqtt`, `rbr-zigbee-bridge` and `controller`: if the unit is disabled, it runs `systemctl enable`, so it comes back after a reboot; if it is not active, it restarts it; if it is active, it runs a cheap probe — TCP connect to mosquitto on 1883, HTTP GET zigbee2mqtt on 8080, HTTP `/health` on the bridge's 8889. The controller has no probe; `is-active` is all it checks.

Then — heating check. Unless a service was restarted in this run, it runs `heatwatch.py`. That reads the plan, the room identities, `thermometers.json` and the heat log. It considers a room only if it is linked, has a relay or TRV, has a reading less than 45 minutes old, and has a target at least 0.5 °C above the room. If a room has been calling for heat for 60 minutes and has not warmed by 0.2 °C, it restarts all four installed core services. It has a 3-hour cooldown and at most 3 restarts in 24 hours; after that it logs `needs attention` and leaves it for a person. State is in `heat-watch-state.json` in the volatile directory, so a reboot clears it.

What it does not catch. A plain controller crash is normally restarted by `controller.service` itself (`Restart=always`, `RestartSec=5`) before the watchdog sees it. The watchdog logs nothing for that; the controller journal is the evidence. The controller's probe is a no-op, so a controller that is `active` but wedged is only caught by the heating check, and only after an hour of scheduled demand without warming. It does not monitor CPU, disk, memory, MQTT message flow or the UI, and it does not record why a service failed — only what it restarted. It runs every 15 minutes, so a stopped or disabled unit can be down for up to about 15 minutes (plus jitter) before the watchdog acts.

Where to look for your colleague's incident: `journalctl -t rbr-watchdog --since today` for the script's own log; `journalctl -u rbr-watchdog.service --since today` for the timer's runs and exit status; `systemctl list-timers rbr-watchdog.timer` and `systemctl status rbr-watchdog.timer` to confirm it is scheduled; `systemctl show -p NRestarts -p ActiveEnterTimestamp controller`, `systemctl status controller` and `journalctl -u controller --since "3 hours ago"` to see whether systemd restarted the controller and when; and the matching journals for `zigbee2mqtt`, `rbr-zigbee-bridge` and `mosquitto`.

A one-shot service is `inactive (dead)` after a successful run; that is normal. The timer is the thing that should be `active (waiting)`.

## 12:01

I realise I forgot about the need to handle multiple installations. The content of ~/rbr-journal needs contain a folder for each installation, and inside each of these the year files. I've edited the folder here to match that structure. Can you adjust the service to handle this? I propose that each installation handled will have its own filter that directs to a mail folder whose name is consistent; my own installation presents as QED6 everywhere and I'd mandate the same rule for other installations.

**Assistant**

Done. The archive now has an installation level:

    <save_path>/<installation>/<YYYY>/<original filename>

The installation name comes from the mail folder or mbox the bundle arrived in — `…/Bundles.sbd/QED6` gives `QED6` — so your rule is the one that drives it. For a bare `.tar.gz` source, where there is no mail folder name, it falls back to the manifest's `system`, then `mac`.

I also changed the live `email_path` from the `QED6` mbox to its parent, `…/Bundles.sbd`. That folder is scanned for one mbox per installation; a new `OTHER` mbox beside `QED6` is picked up automatically and lands in `RBR-journal/OTHER/<year>/`. Any `.msf` sidecars and unrelated mboxes are ignored or rejected as non-bundles. If you add an installation whose filter delivers somewhere else, either put its mail folder under the same parent or make `email_path` a common parent of all of them.

I dry-ran it against the real mailbox and archive: `4 message(s), 0 would be copied, 4 already present, 0 not a journal bundle`. The four existing files are reported as `already present QED6/2026/...`, which confirms the moved tree is correct.

Tests: `tests/unit/bundle_copy_test.py` now covers the installation folder, a parent folder with two mboxes (`QED6` and `OTHER`), folder-name-wins-over-manifest, and the manifest fallback. `tests/unit/run-unit-tests.sh` passes: 76 AllSpeak tests, the controller compile, and 127 Python tests.

To apply it, reinstall and restart the unit as before:

    sudo install -m 644 /home/graham/dev/rbr/rbr-bundle-copy.service /etc/systemd/system/rbr-bundle-copy.service
    sudo systemctl daemon-reload
    sudo systemctl restart rbr-bundle-copy.service

The running process still has the old code and the old `/etc` config until that restart. After it, `journalctl -u rbr-bundle-copy.service --since "2 minutes ago"` should show the catch-up pass reading `Bundles.sbd`, with the four bundles as `already present`.







