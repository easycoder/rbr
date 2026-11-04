# 2026-11-04

## 17:14

Please add questions to rbr-setup that cover building the 'credentials' file.

**Assistant**

Step 5 asked for nothing and wrote `credentials` with placeholder mail settings, so every install that wanted verification emails or the emailed backup needed a hand-edit. It now asks for the file it builds:

- **Broker:** host (`localhost`) and port (`1883`). The account is not asked again — it is the MQTT username and password from Step 0.
- **Mail:** SMTP server (empty skips email and writes the old placeholders), port (`465`, or `587` for STARTTLS), login, password, `From:` (defaults to the login), and an optional fallback recipient for emailed backups (`mail_to`). The password is not echoed.
- **Re-runs:** an existing file is still left untouched by default. A new `Update the mail settings in that file? (y/N)` question offers a mail-only update — current values as defaults, unrelated keys preserved, previous file kept as `credentials.bak`.
- **Writing:** the file now goes through `json.dump` with values passed in the environment, so a quote or backslash in either password cannot corrupt it; the Step 0 MQTT password prompt is hidden as well, and the final summary prints the configured broker instead of a hardcoded `localhost:1883`.

`docs/installation/06-what-the-setup-script-does.md`, `doc/setupRBR.md` and `doc/CONTROLLER-FILES.md` were updated to describe the prompts. `bash -n` and `git diff --check` pass, and I exercised Step 5 against fixtures for a fresh file with mail, a fresh file skipping mail, a re-run answering `n`, a re-run answering `y` with defaults, and an invalid-JSON file. `DIFF.md` is rewritten.
