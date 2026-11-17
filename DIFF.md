# Handover channel — what changed and what to do

**Action:** run `./deploy.sh` to publish the new page, endpoints and the new product documentation page, then add the `handover` field to the host settings above the site root. No service restart is needed. Reopen the PWA once to pick up the owner banner. Ship `./deploy.sh --release` when controllers should receive the updater that can act on a handover — the same release also carries the schedule time fields and the morning override below, and both need the controller side.

## What you have to do

1. **Host settings** — in `../rbrheating.com.txt` (beside `rbr-users.json`), add:

       "handover": {
           "passphrase": "the secret for the sealed envelopes",
           "owner_mac": "00:e0:27:5b:31:40",
           "notify": "the mailbox you actually read",
           "days": 14
       }

   `handover` may also be the passphrase alone. An empty passphrase disables the channel. Generate one with `python3 -c 'import secrets; print(secrets.token_urlsafe(24))'`. Keep the host settings outside the document root; the passphrase sits beside the MQTT and SMTP secrets.

2. **Deploy** — `./deploy.sh` now uploads `handover/`, `handover.php` and `handover-lib.php`. The deploy workflow does the same.

3. **Prepare the new site** — it must be an RBR site with a valid HTTPS certificate, a numeric `/heat/version`, a `/credentials.php` that answers 401 without a token, the customer register and a broker (the same or a new one). The readiness check is in `doc/HANDOVER.md`.

4. **Test** — submit a request against a staging new site with the real passphrase; check the notification email, the PWA banner and the email cancellation link. `python3 rbr-updater.py --check` on a controller reports a pending/active handover without changing anything.

5. **Release** — a controller only acts once it runs an updater carrying this code. The release travels through the old update path, so `./deploy.sh --release` (or an equivalent publish) has to reach the fleet before the channel is relied on.

## What changed

- **Website**: new `handover/` page and `handover.php` endpoints (request / status / cancel), with `handover-lib.php` holding the config, state file, passphrase check, rate limit, SSRF guard, readiness check and notification email. `credentials.php` now serves `mqtt_port` and includes an owner-only `handover` alert.
- **PWA**: a flashing owner-only banner in `top-bar.json`, painted by `shell.allspeak` with a Cancel button. It appears only when `credentials.php` returns the alert for `owner_mac`.
- **Controller**: `rbr-updater.py` asks the current site for handover state on every run, writes `.site_url` on an active handover, and reconciles the mosquitto bridge `address`, `username` and `password` from the new site's credentials. `.site_url` and `.handover` are machine-specific and are included in backups/restores.
- **Docs/config**: `doc/HANDOVER.md` is the design and operations guide; `CONTINUITY.md`, `README.md`, `doc/UPDATE-MECHANISM.md` and `doc/CONTROLLER-FILES.md` point at it. `credentials.example.json` documents the field shape. The new checks are wired into `AGENTS.md`, `package.json` and `tests/unit/run-unit-tests.sh`.
- **Product documentation**: new `docs/concept/06-continuity-and-support.md`, in the trade reading path, the map and the roles page. It explains the mechanism to installers as reassurance, and states plainly that the support arrangement around it may not yet be available: as of 16 November 2026 there is no named successor, prepared replacement site or distributed passphrase. Update that page when the arrangement exists.

## Verification

- `tests/unit/run-unit-tests.sh` — controller compiles, 76 AllSpeak tests, 190 Python tests, including the new `handover_test` (12/12).
- `node tests/pwa-compile-check.js` — 12/12.
- `node tests/pwa-handover-alert-check.js` — 14/14 (pending banner, Cancel, non-owner hidden, end-of-period no Cancel).
- `php-parser` syntax check on the three PHP files; `bash -n deploy.sh`; all JSON validates.
- Playwright drove the real page form and cancellation link against a mocked endpoint — 9/9.
- `node tests/docs-reader-check.js` — 72/72, including the new page and its map entry.

`npm run check` runs every PWA suite and stops at `pwa-boot-guard-check.js` with a missing `#app` in its "normal boot" case. That failure is identical on a clean `HEAD` worktree, so it predates this change.

## Caveats

- PHP `mail()` must be available on the host for the notification, and the host must allow outbound HTTPS for the readiness check. Without either, the page says the new site is not ready; without `mail()` the request is still recorded and the PWA alert still shows.
- The PWA learns about a request on its next credentials fetch, which is each time it is opened. A page already open picks it up on reload.
- The 14 days is a technical cancellation window, not the 30-day continuity trigger. It does not transfer the domain, hosting, broker or repository; see `CONTINUITY.md`.

## Also in this release: schedule time fields, and the morning override's off time

- **Schedule times are time fields (PWA).** The period cards used two quarter-hour dropdowns; they are now native `input type=time`, the control Special actions already used, so a phone opens its own dial and a time can be set to the minute. `BuildTimeOptions` and its 96-option list are gone; ids moved from `-start-select`/`-off-select` to `-start-time`/`-off-time`. The rules are unchanged: a loaded period keeps its duration when its start moves, a new period stops an hour after its start until its stop is picked, and **+ Add period** still starts where a running period ends or at the nearest quarter hour.
- **"Move the off time too" (PWA + controller).** Special actions → *Change the morning start time* now opens with a checkbox, ticked by default: the controller moves that morning's off time by the same amount as the start, so the warm-up keeps its interval (`keepoff: yes` in the `Room Override` request). Unticked, the off time stays as the schedule set it — the old behaviour — and a start at or after it still skips the warm-up. A period pushed past midnight is clamped to 23:59 rather than wrapped. The choice is remembered per room in this browser, beside the time.
- **Expiry follows the moved end.** The controller used to retire today's override when the *scheduled* morning ended; with a moved off time that would drop it early, so `OverrideMorningEnded` now judges the effective end.
- **Recapture `docs/operation/images/10-schedule-editor.png`.** It shows the old dropdowns and wants replacing with the time fields; the caption and the surrounding text still hold.

Tests for these: `node tests/pwa-schedule-editor-check.js` 18/18, `tests/ui/schedule.spec.js` (Chromium, saved `periods[]`), `tests/ui/special-override.spec.js` (default ticked, unticked remembered, `keepoff` on the wire), `tests/unit/unit-10-overrides.allspeak` (new cases 16–20: moved off, late start not a skip, midnight clamp, request flag, expiry at the moved end), full UI suite 26/26, unit runner 190 Python tests plus the AllSpeak suite.
