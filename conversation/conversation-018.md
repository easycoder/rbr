# 2026-11-03

## 10:37

This morning, Bedroom 1 should have come on at 7:00, but at 7:25 the radiator was still off as the thermometer hadn't reported for 55 minutes. After 60 minutes it reported and the heating started.
To prevent this happening, when a period starts, the system should use the last reported temperature (if available) to decide if to supply heat. This should soon trigger an update, but if after 30 minutes the thermometer still hasn't reported, turn off the heat.
I believe this doesn't clash with the 45 minute rule, but must ask you to confirm that.

**Assistant**

Implemented. `./deploy.sh --release` (it bumps the version itself); no map change.

**Does it clash with the 45-minute rule?** No — but it is a deliberate, bounded exception, not a no-op:

- The gate itself is unchanged: a reading older than 45 minutes still counts as missing, `TempNow` is still emptied, the room still turns `warn` (then `fail` at 60), and the app still shows the last known value as stale.
- What changes is only the heating decision: at a scheduled period's start, the last preserved reading (`Room.temperature`) is used instead of an empty `TempNow`, so the relay or TRV can start. The status veto that would otherwise force the relay off is suspended for that decision only.
- The exception is capped at 30 minutes from the period's `on`, not from when the reading went stale. After that, an empty `TempNow` forces the heat off in the ordinary way. A room can never heat indefinitely without feedback; the worst case is 30 minutes on the last known value.
- It applies only in Timed mode, only to a genuine scheduled period (not one brought forward by Advance), only if a last reading exists, and not to an all-day (`on == off`) period or one that began before midnight more than 30 minutes ago. Boost and On are unchanged.

In this morning's shape — last report around 06:30 — the reading was 30 minutes old at 07:00, so heat could start; it crossed the 45-minute gate at about 07:15, which is where the old behaviour would cut it. The grace now runs to 07:30, by which time the thermometer reported or the heat goes off.

**Code:** `PeriodHeatGrace` computes the window; `SetRelay` and `ProcessTrv` decide on `TempDecision`/`StaleGrace`. For a TRV room in the window RBR sends `heat` but no stale `external` reading, so the valve modulates on its own sensor while the 30-minute bound still applies.

**Verification:** whole-controller compile check, 76 AllSpeak tests / 188 checks, and 94 Python tests (including new `period_grace_test.py` and extended `setrelay_test.py`) all pass; doc-block analysis has no new warnings. `DIFF.md` is rewritten, and the glossary, architecture page and setup guide now describe the exception.

One property worth knowing: "last reported temperature (if available)" is taken literally, so even a very old last reading can start the heat for those 30 minutes. If you'd rather cap that too (say, no reading older than 24 hours), it is a one-line addition.

## 12:52

After nearly losing all my Z2M data yesterday it seems to me that a regular backup should be in place. Can you set up a service or cron job that saves everything - Z2M, map etc - into a zipped archive at regular intervals, e.g. monthly.
Can you also look at the possibility of the backup to be sent by email to the user at their registered address. This would be an option in the UI, under the hamburger.

It would also be useful to have a recovery script that could take a backup and restore it after a fresh install.

**Assistant**

Implemented, including the restore script.

**What runs.** `rbr-backup.py` plus `rbr-backup.service` + `rbr-backup.timer`: 03:00 on the first of each month, catching up after downtime. It writes one mode-0600 ZIP into `backup/` and keeps the newest twelve. The archive is the full restore set you chose — `map.json` and its history, the credentials and identity files, and the whole Zigbee2MQTT data directory (network key in `configuration.yaml`, a consistent SQLite snapshot of `database.db`, `coordinator_backup.json`, external converters). Heating logs are excluded as agreed. The archive contains secrets and is meant to be treated as sensitive.

**Email.** A new **Backups** row under the hamburger opens a sheet showing the registered address and the last run, an on/off toggle for the monthly email copy, and **Send a backup now**. The controller stores the toggle and address in `backup-config.json` and publishes the status in the map, so the timer can email with no browser open. The address falls back to the one the cloud holds for this controller (credentials.php via `.mqtt_token`) and then to `mail_to` in `credentials`. A mail failure is reported in the sheet without losing the local archive.

**Restore.** `rbr-restore.py <archive>` verifies the manifest and every checksum, refuses paths that would escape the destination, snapshots what is already there under `pre-restore-<timestamp>/`, restores ownership and permissions, and restarts the services. `--dry-run` lists the files only.

**To make it live:** `./deploy.sh --release`, then re-run `sudo ./rbr-setup.sh` on each controller (it installs the new timer in Step 6d). Put real `mail_*` values in `credentials` — the setup script writes placeholders — then turn email on under **Menu → Backups**. No map change.

**Verification:** the full unit suite (76 AllSpeak tests / 188 checks, 94 Python tests) passes, the whole controller compiles, all PWA modules compile, and the new browser-runtime check drives the menu row, address, toggle payload and Send now. `DIFF.md` is rewritten.

## 14:45

Something seems off here...

qed6@QED6:~/rbr$ sudo systemctl start controller
qed6@QED6:~/rbr$ sudo systemctl status controller
● controller.service - RBR Controller
     Loaded: loaded (/etc/systemd/system/controller.service; enabled; preset: enabl>
     Active: activating (auto-restart) since Tue 2026-11-03 14:39:34 GMT; 4s ago
...
qed6@QED6:~/rbr$ sudo journalctl -u controller -n 80 --no-pager
...
Runtime Error in Controller at line 921 (if BackupInfoText is LastBackupInfoText return):
-> Both items must have a value for comparison

**Assistant**

Found and fixed. `LastBackupInfoText` had never been assigned when `LoadBackupState` first compared it, and this AllSpeak runtime refuses to compare an unset variable with anything. `LastMapDiskText` already carries the same warning in the startup block; the new variable now gets the same empty seed, and the comparison is guarded.

`LastBackupInfoText` is set to empty beside `LastMapDiskText`, and `LoadBackupState` only compares when it has a value. The backup feature itself is unchanged. Deploy with `./deploy.sh --release`; controllers that already took the broken release stop looping as soon as the corrected `controller.allspeak` is applied (restart now or wait for the hourly updater).

Added a regression test that extracts the real `LoadBackupState` from `controller.allspeak` and runs it under AllSpeak: twice with no backup files (the crash case), then with `backup-config.json` and `backup-status.json` populated. The old comparison fails it; the fix passes. Controller compile check and the 9 backup/restore tests are green. `DIFF.md` now leads with the deploy/restart action.

## 14:49

Does rbr-setup.sh rewrite 'credentials' each time? If it already exists it should be left untouched.

**Assistant**

Yes — it did, unconditionally. Step 5 wrote `credentials` with `cat >` every run, so a working `mail_server` / `mail_login` / `mail_password` / `mail_from` was silently replaced by placeholders each time setup was re-run. That is exactly what would break verification emails and the emailed backup.

Fixed: if `credentials` exists, the installer now leaves it untouched and says so. It parses the existing `username` and `password` only to compare them with the broker account written into mosquitto in Step 2; a mismatch prints a warning and leaves the repair to you (edit the file, or delete it and re-run). A fresh install still creates the file as before.

I also fixed the same class of problem with `.mac_override`: the prompt now defaults to the existing override rather than the NIC address, so pressing Enter on a re-run cannot rename the system's MQTT topic.

If you already re-ran setup after setting real mail values, restore the `mail_*` fields in `~/rbr/credentials`; future runs will preserve them. Deploy the corrected installer with `./deploy.sh --release`. `bash -n rbr-setup.sh` and `git diff --check` pass; `DIFF.md` leads with the restore-mail-values action.

## 15:04

In the UI, my email address is shown as gt@pobox.com. Can you confirm the server also knows this?

**Assistant**

Clarified after your steer: the controller, not the hosted server. The UI showing `gt@pobox.com` proves the browser fetched it from `credentials.php`; it does **not** by itself prove the controller has stored it.

The controller's own copy is `~/rbr/backup-config.json`, written when the Backups sheet's email toggle is used. `rbr-backup.py` resolves the recipient in this order: `backup-config.json` address, then credentials.php via `~/rbr/.mqtt_token` if present, then `mail_to` in `~/rbr/credentials`. `.mqtt_token` is optional and is not created by setup, so without it the controller cannot ask the cloud for the address.

To confirm on QED6:

```bash
cd ~/rbr
python3 - <<'PY'
import json
for name in ("backup-config.json", "backup-status.json"):
    try:
        data = json.load(open(name))
        print(name, {k: data.get(k) for k in ("enabled", "address", "last_display", "emailed", "email_to", "error") if k in data})
    except FileNotFoundError:
        print(name, "not present")
PY
ls -l .mqtt_token 2>/dev/null || echo ".mqtt_token not present"
```

If `backup-config.json` has `"address": "gt@pobox.com"`, the controller knows it and the timer/Send now will use it. If it is missing, open **Menu → Backups** once and toggle the email option (on or off); that sends the address with the `Backup` request and the controller writes it. After a run, `backup-status.json` records `email_to`.

The controller also needs real `mail_*` values in `~/rbr/credentials`; the address alone is not enough to send.

## 15:06

The UI has "Send a backup now". Is this in addition to the monthly send?

**Assistant**

Yes — it is an extra one-off on top of the monthly schedule, not a replacement for it.

`Send a backup now` sends `Backup Now`; the controller runs `python3 rbr-backup.py --email-now` in the background. That writes another archive into `backup/` and emails it immediately. The monthly timer is untouched and its next run still happens.

Three consequences worth knowing:

- It **forces the email** even if the monthly email toggle is off, because you explicitly asked for this one. If no registered address is known, it still writes the local archive and reports that email was not sent.
- It counts towards the `--keep 12` retention, so an immediate extra backup can prune the oldest monthly archive sooner.
- It does not change `backup-config.json`; the toggle and address stay as they were.

The sheet's **Last backup** line updates from the map when the run finishes.

## 15:11

I tapped "Send a backup now" and it ended with "mail settings are not configured (edit 'credentials')" But I have edited credentials.

**Assistant**

There was a real merge bug behind that. `rbr-backup.py` combined the local `credentials` with the cloud host settings by taking any non-empty value from either, cloud last. The cloud host file can still carry `smtp.example.com` / `REPLACE_WITH_SMTP_PASSWORD`; those overrode your real local SMTP settings, so the check failed even though you had fixed `credentials`.

Fixed: a real local value now wins, and the cloud only fills fields the local file has not configured. A value counts as real when it is non-empty, is not `smtp.example.com` / `*.example.com`, and contains no `replace_with`.

The error now names the field, e.g. `mail settings are not configured in credentials: mail_password is empty`; an unreadable local `credentials` is logged instead of silently ignored; and `credentials.example.json` documents the optional `mail_port` (465 by default, 587 for STARTTLS).

Deploy with `./deploy.sh --release` and restart the controller (or wait for the hourly updater), then tap **Send a backup now** again. Confirm you edited `~/rbr/credentials` on the controller, not the site's `credentials.php` or host `.txt`: `mail_server` must not be `smtp.example.com`, `mail_login` and `mail_password` must be set, and `mail_password` must not contain `REPLACE_WITH`. Add `"mail_port": 587` if your provider uses STARTTLS. All 12 backup/restore tests pass, including the new precedence tests.

## 19:34

In Step 7 of rbr-setup.sh, the default answer to "Run the controller as a service" should be Y. That's how we're both set up and how I'd set up any new installation.

**Assistant**

Changed. Step 7 now asks `Run the controller as a service (auto-restart after updates)? (Y/n)` and pressing Enter installs it. Only an explicit `n`/`no` skips it; the check is case-insensitive, and `yes` also installs.

The prompt now uses the existing `prompt_value` helper, so a closed stdin aborts with a clear message rather than silently taking an empty answer. The install guide and `doc/setupRBR.md` now describe the new default.

`bash -n rbr-setup.sh` and `git diff --check` pass, and the acceptance table was exercised directly: `y`, `Y`, `yes`, `YES` install; `n`, `N`, `no`, `NO` skip. `DIFF.md` is rewritten.







