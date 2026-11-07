# 2026-11-07

## 11:53

The next step is for the controller to post the daily export journal bundles, either to the website or by email. The latter is probably simpler so let's start there. I assume an email filter can move incoming bundles to a known folder, then we'll need to work out how to get the Studio to pick them up (or use them as a library resource).

**Assistant**

Email delivery is in place, and the Studio now picks the bundles up automatically.

**Controller side**

- `journal-export.py` gains opt-in email. `rbr-setup.sh` (Step 6e) now asks whether to email each daily bundle and writes `journal-export-config.json` with `enabled` and an optional `address`. With the file absent or `enabled` not on, nothing is emailed.
- `--email-now` sends one bundle regardless of the toggle, `--no-email` overrides an enabled config, and `--to` overrides the recipient. The recipient falls back to the registered address the cloud holds, then `mail_to` in `credentials`.
- `rbr_mail.py` now holds the local-vs-cloud mail merge rule, recipient resolution and SMTP sending for both the monthly backup and the journal export. `rbr-backup.py` keeps its public helper names, so its behaviour is unchanged.
- A send failure is printed to stderr (the systemd journal) but the archive stays and the timer still exits 0. The message subject starts with `RBR journal`, and the attachment is the same `.tar.gz` the exporter writes.

**Studio side**

- `journal_inbox.py` scans a mail-filter folder at startup. The default is `~/RBR-journal`; put another path on one line in `fixtures/local/journal-inbox` to override it.
- Each unseen `.tar.gz` is extracted to `fixtures/local/journal/<system>-<day>/`, converted into a whole-day scenario and added to the **Journal** group. The archive's SHA-256 is recorded in `fixtures/local/journal/inbox-seen.json`, so a rescan does nothing, and a day already imported by another route is not duplicated.
- The attachment is left in the inbox, so the mail filter owns its own retention. A bad or unconvertible archive is recorded as failed rather than retried on every start.
- Run it by hand with `python3 journal_inbox.py --scan --inbox DIR`.

**To use it**

1. Redeploy the controller: `rbr_mail.py` is a new runtime file in the tarball and install pack, and `rbr-updater.py` now requires it.
2. Re-run `rbr-setup.sh` and answer yes in Step 6e.
3. Make the mail filter match the subject prefix `RBR journal` and save the `.tar.gz` attachment to `~/RBR-journal` (or the folder named in the pointer file).
4. Restart Scenario Studio.

The full Python unit suite passes (130 tests), as does `tools/scenario-studio/tests/journal_check.py` (13 tests, including one-time inbox import, the deduplicated rescan and a bad archive). No new Python packages are needed. The whole change is described in `DIFF.md`.

## 12:04

I checked rbr-setup.sh had been updated then ran it. Should it have asked me to confirm I want daily emails?

**Assistant**

Yes — Step 6e should ask, and it defaults to **No**.

It prints these two lines before the question:

> The daily bundle is written locally whether or not it is emailed.
> Email each daily bundle to the registered address? (y/N) [n]:

Pressing Enter leaves email off; answering `y` enables it.

If you did not see that, there are two likely reasons:

- **You ran an older copy.** The updated `rbr-setup.sh` is still uncommitted and undeployed here (`git status` shows ` M rbr-setup.sh`), so an installed controller copy only gets the question after a release deploy and update. Check the file you actually ran with `grep -n "Email each daily bundle" /path/to/rbr-setup.sh`.
- **Step 6e was skipped** because `journal-export.py` was not in the script's directory. It then prints `journal-export.py not found — skipping journal export timer`, and the question lives inside that `else` branch.

If it did ask and you pressed Enter, that is why email is still off. To enable it now without re-running the whole setup, write `journal-export-config.json` next to `journal-export.py` with `{"enabled": "yes", "address": "you@example.com"}`. `address` is optional; an empty one falls back to the registered address, then `mail_to` in `credentials`. Test with `python3 journal-export.py --day 2026-11-06 --email-now`; a failure appears in `journalctl -u rbr-journal-export`.

If you paste the Step 6e output from your run, I can tell which of those it was.

## 12:11

Ah, I forgot to wind back .version here to avoid having to --release.

**Assistant**

Done — I wound the local `.version` back to `2611061436` (the previous release). The repo `version` file is still `2611062009`.

The tarball built at 12:07 already embeds `2611062009` and contains `rbr_mail.py` and the updated `rbr-setup.sh`, so the updater now sees it as newer here. `python3 rbr-updater.py --check --url ./rbr-controller.tar.gz --dir .` reports remote `2611062009`, local `2611061436`. Run `python3 rbr-updater.py` to apply it; that writes `.version` back to `2611062009`. This workspace has no updater timer or controller services installed, so the command only swaps files here. If the target is the remote controller, wind back its own `.version` there and run its updater.

If you actually meant the repo `version` stamp (no dot), say so — that is a different lever and changes the stamp embedded in the next tarball.

## 12:50

My mistake - I'm finding it hard to keep up with the pace of development. The monthly email is not relevant here. What I would like is for the journal bundle to carry everything of interest, including for a future statistics module. So it seems logical to add the CSV data to the bundle.
At the moment the only running instance of Studio is inside the development repo. I would like to create a packaged version that can be copied anywhere and when run, be set up to point to a folder containing incoming daily journal bundles. Scenario testing will be only one of its roles; statistics are likely to be an addition before long.

**Assistant**

The bundle now carries the day's heatlog CSVs, and the Studio builds as a portable package that can be pointed at a local inbox.

**Bundle**

- `journal-export.py` copies `<heatlog-root>/<room>/<YYYY>/<MM>/<DD>.csv` into `reports/heatlog/` and lists each file in `manifest.reports` with its room, size and SHA-256. It finds the root from `--heatlog-root`, then the `heatlog-root` file, then the parent of a journal root named `events`.
- `journal_import.py --heatlog-root` does the same for a local bundle; a source named `events` uses its parent automatically.
- The Studio inbox extracts the whole bundle, so `fixtures/local/journal/<system>-<day>/` holds `events/`, `maps/` and `reports/heatlog/`. Scenario conversion ignores the CSVs; a future statistics view can read them without another transfer.
- The default `scenario` mode remains compact. `--mode full` is available if statistics later need every sensor heartbeat and staleness reading; the heatlog CSVs already keep the change-driven outcomes.

**Portable Studio**

- `./package-studio.sh` builds `dist/rbr-studio-<stamp>.tar.gz` without `fixtures/local`, a real `map.json`, `ai-config.json` or a `.venv`.
- Unpack it anywhere and run `./run-studio.sh`. The first run creates `.venv`, installs `requirements-studio.txt` and Chromium, asks for the folder the daily bundles arrive in, writes `studio-config.json`, and creates the inbox and local data folders.
- `./run-studio.sh --inbox DIR` changes the folder; `--setup-only` installs and configures without opening the window; `configure-studio.py --show` prints the current setting.
- `journal_inbox.py` reads `studio-config.json` first, then `fixtures/local/journal-inbox`, then `~/RBR-journal`. No SSH access to the controller is needed for journal records.

**To do**

- Redeploy the controller so `journal-export.py` carries the new `reports/heatlog/` files.
- Rebuild the package with `./package-studio.sh` after changes; `dist/` is gitignored.

**Verified**

132 controller-side Python tests pass, as do 13 journal tests, 4 package tests and the offscreen Studio shell check. `git diff --check` is clean.

## 14:17

With the growing capability and potential of Studio it deserves a name change. I would like it to be "RBR Studio".

**Assistant**

The application is now **RBR Studio** throughout.

- The window title, toolbar brand, `studio.allspeak` program name, docs, public architecture/testing pages, package text and tests use the new name.
- The checkout directory is now `tools/rbr-studio/`; `git mv` carried the files and history across. Update any local aliases or notes that still name `tools/scenario-studio`.
- The portable package is still `dist/rbr-studio-<stamp>.tar.gz`; build it from the new directory with `./package-studio.sh`, unpack it and run `./run-studio.sh`.
- Scenario-run artefacts and the Playwright cache now live under `~/.local/share/rbr-studio` and `~/.cache/rbr-studio`. Old artefacts under the former `rbr-scenario-studio` names are left alone and nothing reads them.
- The controller side is unaffected: the bundle format, `reports/heatlog/` contents and inbox behaviour are unchanged.

The wireframe renders with the new brand, the shell check passes from the new directory, and the journal, package and export tests are green. `git diff --check` is clean.

## 14:20

These's some kind of initialisation problem:
graham@graham-minibookx:~/dev/rbr/tools/rbr-studio$ ./run-studio.sh 
./run-studio.sh: line 54: .venv/bin/pip: cannot execute: required file not found

**Assistant**

That is the moved-venv problem, not a missing package. The `.venv` was created while the directory was still `tools/scenario-studio`, and a venv writes the absolute Python path into the shebang of every console script. After the rename, `.venv/bin/pip` starts with the old path, which no longer exists, so the kernel reports "required file not found".

`run-studio.sh` now detects a venv created in another directory — from a `.venv/.studio-home` marker, or from the `pip` shebang — and replaces it. It also uses `.venv/bin/python -m pip` for installation, so a broken pip script cannot block the repair. Run `./run-studio.sh` again: it will print `Replacing the .venv: it was created in another directory.`, recreate it, and reinstall `requirements-studio.txt` and Chromium. That first run is slower because the packages are installed again.

`--no-install` now fails with a clear message instead of the kernel error, and the launcher scripts and package tests pass.

## 14:22

A lot of files have been added for the venv. Are these all .gitignored?

**Assistant**

Yes. Every file under `tools/rbr-studio/.venv` is ignored by the `.*` rule at the top of `.gitignore`; `git check-ignore -v tools/rbr-studio/.venv` reports `.gitignore:1:.*`. Nothing is tracked there (`git ls-files tools/rbr-studio/.venv` returns nothing), and `git status --untracked-files=all` shows no `.venv` entries. The visible entries are the intended rename and the new Studio/controller source files, not the virtualenv.

The rule is broad rather than venv-specific. If you would prefer an explicit `.venv/` line for clarity, I can add one, but it would not change what is ignored.

## 14:40

The emails carrying the bundles should identify the system by its MAC address, e.g. RBR journal 00:e0:27:5b:31:40. This is to enable a mail filter to direct to a folder per system, so multiple systems can be managed. RBR Studio will default to ~/RBR-journal/<MAC>. I expect this means it needs a means to define MAC addresses with useful names against them.

**Assistant**

The bundle path now carries the MAC end to end.

- The email subject is `RBR journal <MAC> <YYYY-MM-DD>`, so a filter can match `RBR journal 00:e0:27:5b:31:40` and save that system's attachments under `~/RBR-journal/00:e0:27:5b:31:40/`. The MAC comes from `.mac_override` via the shared `rbr_mail.local_mac()`, with the NIC as a fallback; the body and `manifest.json` carry it too.
- `journal_import.py --mac` records a MAC for a local import. Older bundles without one still import and are keyed by their system name.
- `journal_inbox.py` scans `~/RBR-journal` and its subfolders, so several systems can share the root. The extracted bundle folder uses the MAC (or the system name when a bundle has no MAC) as its stable key; the archive hash still prevents duplicate imports.
- `studio-config.json` now has a `systems` map. Name a system with `./run-studio.sh --system 00:e0:27:5b:31:40=Home` (repeatable), or `python3 configure-studio.py --system 00:e0:27:5b:31:40=Home`; the configured inbox subfolder is created at the same time. Without a mapping, the controller's own system name is used.
- Scenario names use the friendly name (`Journal 2026-11-06 — Home`) while the folder stays keyed by the MAC. `configure-studio.py --show` prints the current mapping.

The export, journal and package tests pass, including the subject/manifest MAC, the recursive per-MAC inbox and the `--system` configuration.

## 14:57

Since bundles arrive daily into a local folder there should be no need for SSH access to the local controller. Unless there is another place it's needed, let's remove the code for it.

**Assistant**

Removed the SSH transport from RBR Studio. I found no other place in the repository that needs it.

- `journal_import.py` no longer has `SSHSource`, `--ssh`, `--ssh-root`, `--ssh-bin`, `--ssh-key` or `--ssh-option`; `--source` is now required and must be a local journal root. It reads the day file and map snapshots directly.
- `journal_ingest.py` accepts a bundle, a raw `.jsonl` or a local journal root. The `user@host` parsing, default remote root and SSH argument pass-through are gone.
- The Studio's **Import journal…** prompt accepts local paths only. Its saved setting is now `source`; an old `ssh` entry in `studio-settings.json` is ignored.
- The fake-SSH tests and SSH documentation are removed. The email/inbox path remains the normal way to get daily bundles, and **Import journal…** remains for a local copy.

The 11 journal tests, 4 package tests, 9 export tests and the offscreen shell check pass; `git diff --check` is clean. No controller release is needed.

## 15:10

And to enable tests to be done on bugs as they are reported, let's have an option under the UI hamburger to request a bundle to be created for the current day up to the current time, and emailed out.

**Assistant**

Added **Send journal now** under the hamburger, with a small Journal sheet.

- The sheet shows the registered address and a **Send today's journal now** button. It sends `Journal Now` with gesture provenance and stays open with a confirmation.
- The controller flushes the pending journal first, so the request and the events leading to it are in the file, then runs `journal-export.py --now --email-now` in the background.
- `--now` exports today's file as it stands into `exports/requests/` as `<system>-<date>-<HHMMSS>.tar.gz`, marks the manifest `partial` with a `label` and `requestedAt`, and puts the time in the email subject. The daily exports are untouched.
- RBR Studio treats a partial bundle as its own scenario (`Journal <date> <time> — Home`), not as a duplicate of the full day.
- The service-worker cache version is bumped, so the PWA needs one reload after deployment. The controller and PWA must be deployed together; an old controller rejects the new action.

The hamburger sheet test passes (22 checks, including the Journal row and request), the PWA compiles, the controller compiles, and the exporter, inbox and package tests pass.
