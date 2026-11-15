# What to do

- Run `./deploy.sh --release`: one deploy publishes the screenshots, the operation page and reader navigation fix, the PWA with the evenly spaced room pills, the fixed-background change below, and the controller pack. Reload `/docs/` and the phone once online.
- The release is needed now because `controller.allspeak` has changed as well: the System sheet's heating type is stored again (below).
- `tests/unit/system_type_test.py` is new, and `run-unit-tests.sh` runs it.

# What changed

- **Screenshots recaptured.** `01-home-simplified.png` and the rest of the manual's captures now show the current room-pill spacing: equal space above the first pill, between the pills and below the last.
- **Fixed sample time.** The captures are made at 16:53 so the sample states stay stable — Living Area heating, Bedroom 1 between its morning and evening periods, Bedroom 2 Off. Without the fixed clock the same map shows Bedroom 1 in its evening period later in the day and the caption no longer matches. The other room, sheet and profile screenshots were regenerated from the same run; the page text is unchanged.
- **Operation map and navigation.** `docs/README.md` links `operation/01-the-interface.md` and marks it **Draft**. The reader now records a page's slug, folder and position before fetching, so a missing page keeps its own Previous/Next neighbours and address. The manual's screenshots render through the reader's image upgrade.
- **Room pill spacing (PWA).** The space above the first pill and below the last is now the same as the space between them: about 64px each at 390×844, against 8px at the ends and 76px between before. The pills take the height that leaves — about 255px each, down from 313px. The column uses `space-evenly` with no fixed gap, and `BuildSimpleHome` sets the pill height to `100% / (5n+1) * 4`, so every space is a quarter of a pill for any number of rooms.
- **A fixed background uses the afternoon stops (PWA).** With "Time-based changes" off, the gradient was built from the midday stops — 7%, 14% and 24% of the chosen colour towards white — the palest of the six buckets, so the page read as near-white rather than as the shade chosen. It now uses the afternoon set, 14% / 36% / 64%, which carries the most colour of any daytime bucket. The afternoon bucket and the fixed path share `PaintAfternoonStops`, so an edit to one cannot leave the other behind.
- **The System sheet's heating type is stored again (controller).** `ProcessUIRequest` kept the name and the On cap and silently dropped `systemType`, so choosing Heat Pump looked saved and the next map reopened the sheet on Boiler. The branch now lives in `ApplySystemName` (with `NormaliseSystemType` accepting either label and refusing anything else), and a fresh map starts with `systemType` `Boiler`.

# Tests

- `node tests/docs-reader-check.js` — 63/63, including the missing-page chain and the manual's screenshots.
- The pill-spacing change records `simple-view`, `room-colours`, `simple-badges`, `demand-flame` and `demo-mode` passing (7/7).
- `tests/ui/appearance.spec.js` now computes the afternoon stops for the fixed gradient; full UI suite 24/24.
- `tests/unit/system_type_test.py` (12 cases) plus the whole unit runner: 178 Python tests, the AllSpeak tests and the whole-controller compile pass.
- `git diff --check` — clean.
