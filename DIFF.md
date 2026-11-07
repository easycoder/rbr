# What to do

- **Deploy the controller and the PWA together.** The hamburger has a new **Send journal now** row; the controller must know the `Journal Now` action. A controller still on the old build will reject the request with `UIRequest rejected: unsupported action Journal Now`. The service-worker cache version is bumped, so reload the PWA once to pick up the new shell and sheet.
- **No mail-setting change is needed** if the daily journal email already works. The request forces one send (`--email-now`) even when the daily toggle is off; if no address or SMTP settings are configured, the controller logs the failure.
- **Look for the file in `exports/requests/`.** A requested bundle is partial: it covers today up to the moment of the tap and is named `<system>-<date>-<HHMMSS>.tar.gz`, separate from the daily exports in `exports/`.
- **RBR Studio imports it as its own scenario.** The manifest marks it `partial` with a `label`; the inbox keys it by MAC and time, so it does not collide with the full-day bundle and appears as `Journal <date> <time> — <name>`.

# What changed

- **PWA.** The hamburger's menu has a **Send journal now** row opening a small Journal sheet. It shows the registered address and sends `Journal Now` with gesture provenance; the sheet stays open and confirms the request.
- **Controller.** `ProcessUIRequest` accepts `Journal Now`, flushes the pending journal so the request and its preceding events are in the file, and runs `journal-export.py --now --email-now` in the background.
- **Exporter.** `journal-export.py --now` uses today's file as it stands, writes a partial bundle under `exports/requests/` (newest 14 kept), and records `partial`, `label` and `requestedAt` in the manifest. The email subject adds the time: `RBR journal <MAC> <date> <HH:MM:SS>`.
- **Studio inbox.** Partial bundles get a time-suffixed folder and scenario name and are not deduplicated against the full-day bundle. The full-day path is unchanged.
- **Tests and docs.** The hamburger sheet test now covers the Journal row and request; `journal_export_test` covers `--now`, the partial manifest and the timed subject; `journal_check` covers the partial key/name. `doc/EVENT-JOURNAL.md`, `doc/CONTROLLER-FILES.md` and the Studio README describe the new path.

# Try it

1. Open the PWA, tap the hamburger and **Send journal now**.
2. Check the registered mailbox for `RBR journal <MAC> <date> <time>`.
3. Restart RBR Studio and let its inbox scan import the partial bundle.

```bash
# controller-side equivalent
python3 journal-export.py --now --email-now
```
