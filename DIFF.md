# What to do

- **On a fresh install**, Step 5 now asks for the credentials file's contents: broker host/port, then the SMTP settings. Pressing Enter at `Mail server` skips email and writes the old placeholders, as before.
- **Re-running setup is still safe.** Pressing Enter at the new `Update the mail settings in that file? (y/N)` leaves an existing `~/rbr/credentials` exactly as it is. Answer `y` only when you want to change the mail settings; the previous file is kept as `credentials.bak`.
- No map change. `rbr-setup.sh` ships in the normal release.

# What changed

Step 5 of `rbr-setup.sh` wrote `credentials` with placeholder mail settings (`smtp.example.com`, empty password), so anyone wanting the verification emails or the emailed backup had to hand-edit the file afterwards. It now asks for the file it is building:

- **Broker** — host (`localhost`) and port (`1883`). The account is not asked again: it is the MQTT username and password from Step 0.
- **Mail** — SMTP server (empty skips email), port (`465`; 587 for STARTTLS), login, password, `From:` (defaults to the login) and an optional fallback recipient (`mail_to`). The password is not echoed.
- **An existing file** is still left untouched by default; the new question offers to update only its mail fields. That path seeds every prompt with the current value, keeps unrelated keys, and saves `credentials.bak` first.
- **The file is written with `json.dump`**, values passed through the environment, instead of a shell here-document — a quote or backslash in either password can no longer produce invalid JSON. The Step 0 MQTT password prompt is hidden too.
- The closing summary prints the configured broker rather than a hardcoded `localhost:1883`.

Docs updated to match: `docs/installation/06-what-the-setup-script-does.md`, `doc/setupRBR.md`, `doc/CONTROLLER-FILES.md`.

# Tests

`bash -n rbr-setup.sh` and `git diff --check` pass. The Step 5 block was exercised in isolation against five fixtures: fresh file with real mail settings (valid JSON, embedded quote and backslash escaped), fresh file with an empty mail server (byte-identical to the old placeholder output), re-run answering `n` (file byte-identical, no `.bak`), re-run answering `y` with Enter defaults (file unchanged, `.bak` created, extra key preserved), and an invalid-JSON file (no question asked, left untouched). No unit test covers the shell script.
