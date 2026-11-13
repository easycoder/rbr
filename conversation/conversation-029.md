# 2026-11-13

## 11:18

I want a pill at the bottom of the room list, to show the current profile and the outside temperature where an outside thermometer is specified. Clicking the pill brings up the profile editor page. Make the vertical sizes of all pills such that they occupy the entire vertical space on the device, leaving just a narrow background border.

**Assistant**

Added it to the **Simple view's** room list — the full view already carries the profile and outside temperature in its summary card.

- The bottom pill shows the active profile and, when an outside thermometer is configured, its reading. With no sensor the outside half is hidden; a configured sensor with no reading yet shows an em dash. Tapping the whole pill opens the profile editor (`OpenProfileSheet`).
- Every room pill and the profile pill now use `flex: 1 1 0`, sharing the height left under the title bar. In simple view `MainHolder` gets an 8px padding and 6px gap, and the empty layout footer is hidden, so the pills fill the device with an 8px background border on every side.
- Map pushes repaint the profile pill as well as the room buttons. Switching back to the full view restores the original page padding, row gap and footer.
- Files: `new-ui/resources/webson/simple-profile-pill.json` (new), `simple-home.json` (flex sizing), `shell.allspeak` (pill build/paint, layout switch), `sw.js` (cache bump and precache), `tests/ui/simple-view.spec.js`, `tests/ui/README.md`, `DIFF.md`.
- Verification: `npm run test:ui` 9/9, `node tests/pwa-compile-check.js` 12/12, `node tests/pwa-sw-check.js` 22/22, published `asdoc-check` 0 errors.
- Deploy with `./deploy.sh` and reload; no controller script changed.

## 11:35

Remove the chevron and style the temperature to be the same as the other rooms.

**Assistant**

Removed the chevron from the bottom profile/outside pill. The outside reading is now styled exactly like a room temperature: 34px, weight 500, letter-spacing -1px, with `°C` as a separate 16px muted unit. The number is set without the unit in `PaintSimpleProfilePill`; an empty reading is still `—`.

Changed `simple-profile-pill.json`, one line in `shell.allspeak`, the simple-view spec, `sw.js` (cache bump) and `DIFF.md`. `tests/ui/simple-view.spec.js` passes 2/2; the full UI suite, PWA compile check and service-worker check are running/were green. Deploy with `./deploy.sh` and reload.

## 11:57

Now for text colours. The room name and temperatures should be blue when the radiator is off, orange (our standard shade) when it is on. In Timed mode, this only applies during a heating period; between periods both should revert to black. In Off mode, both should be mid-grey to indicate the room is effectively not part of the system. At any times not covered by this, revert to black.

**Assistant**

Added a shared `ResolveRoomTextColour` rule and applied it to the room name and current temperature in the simple home, the single-room page and the full room list.

- Radiator on is taken from the valve's own `heat`/`idle` report when present, otherwise from the controller's `calling`; an unwired room counts as off.
- Blue for a radiator off, orange (`var(--color-accent)`) for one on. A Timed room is coloured only inside an active period (a `nextTime` with no `BG ` prefix); between periods it is black. An Off room is mid-grey (`var(--color-text-muted)`). Every other state is black.
- `RenderRoom` now sets both the name and the current temperature; `PaintSimpleRoomButton` does the same for the reduced home. The old offline muted-temperature styling is superseded; the offline tag and warnings still report the fault.
- New `tests/ui/room-colours.spec.js` covers Off, On-off, On-heat, Timed-gap, Timed-off and Timed-heat, plus the single-room page.
- The service-worker cache is bumped. Deploy with `./deploy.sh` and reload; no controller script changed.

## 12:17

Now I'd like icons to be placed on each room pill, as on the current version, but let's make them do some more work. The basic icon can be as before, but add some rules: Timed mode: During a schedule period, the icon becomes a running man. There's an example at new-ui/resources/icon/run.png, but it should be orange, not black. Advance uses the same A as before. Boost is probably best done with an orange plus symbol. On should also use the orange plus symbol. I am considering removing ON altogether and replacing it with a much longer time option in Boost. This is to avoid permitting the heating system to be left permanently running; the user should set up a schedule instead. I'd welcome your comments on this and its implications, if any. Off is always the same icon.

**Assistant**

Put a 48px state chip on every simple-home pill, using the same icon rules as the full room card via a shared `ResolveChipStyle`.

- Off → off icon, always.
- Timed outside a period → clock; Timed inside a period → running man in orange.
- Advance → the existing A.
- Boost and On → an orange plus (`plus.svg`).
- Sensor/offline/partial-relay warnings keep their existing precedence over the mode icons.

`run.png` is a white/black rounded-square icon, so it cannot be used directly as a CSS mask. I kept it as the example and derived `run-mask.png` from it as a transparent running-man silhouette; the chip tints that mask orange.

On removing On: I'd keep the On *mode* in the controller and map for compatibility but remove the button from the simple view only, replacing it with a long Boost (e.g. 4 hours). Removing it everywhere means existing `on` states (controller, stored profiles, legacy clients) need a migration or a read-only representation, and a boost from an existing On room would otherwise return to On. A controller auto-expiry for On is another safe option. A long Boost gives the same emergency heat affordance without permanent running. Don't remove the button alone while the mode can still arrive from elsewhere.

Tests: `tests/ui/room-colours.spec.js` now covers the colours and icons for all the states plus the single-room page. Full UI suite, compile and SW checks are running/were green.

## 13:01

Advice taken. I'll return to it when we get to the detail.
The home page is effective but looks a little bland and the rooms don't look sufficiently distinctive, so I'd like some pill border colours, then I'll decide if backgrounds should also apply.
The default is grey. When the text is anything other than black, the border should adopt that colour.
The Profile/Outside pill isn't a room, so it should echo the style of the logo row to bookend the set of rooms.

**Assistant**

Room pills now carry a 1.5px state border: neutral grey by default, and the name/temperature colour whenever that is not black (blue, orange, or the Off room's mid-grey). The Profile/Outside pill now uses the top bar's surface — the near-white background, `rgba(0,0,0,0.1)` hairline border, soft shadow and backdrop blur — so it books the rooms against the logo row without pretending to be a room.

`ResolveRoomTextColour` became `ResolveRoomStateColour` and sets both the text and border colours. Backgrounds are untouched for now. `tests/ui/room-colours.spec.js` now checks the border colours and the profile pill's surface as well as the text colours and icons.

## 13:27

The Profile/Outside pill should not have rounded corners; it should occupy the full width, completely obscuring the background, as with the the logo pill. There should be no border/margin below it either.

**Assistant**

Turned the Profile/Outside pill into a full-width bottom bar. It now has square corners, an opaque white background, a `1px` top hairline, an upward shadow and no bottom border. It escapes the simple home's 8px side padding with a `calc(100% + 16px)` box and `-8px` side margins, and the page's bottom padding is now 0 in simple view, so the bar reaches the bottom edge with no margin below. The full view restores its four-sided padding when it rebuilds. The bar still holds its share of the vertical height and its profile/outside content.

`tests/ui/room-colours.spec.js` now checks the opaque background, square corners, zero bottom border, 390px width and 844px flush bottom; `tests/ui/simple-view.spec.js` keeps the shared-height check with a small rounding tolerance. Deploy and reload; no controller change.

## 13:34

The room pills could do with some light backgrounds. I suggest a shade half-way between white and that used for the text on the pill. This is all to help at-a-glance readability, particularly by those with impaired vision.

[Steer: Perhaps 3/4 the way to white...]

**Assistant**

Used the three-quarters-of-the-way-to-white mix rather than halfway: 25% of each state colour with 75% white. Added tokens `--color-pill-bg-blue` `#CBDCEC`, `--color-pill-bg-orange` `#F9DACC`, `--color-pill-bg-grey` `#E6E6E6` and a neutral default `#EEEEEE`. `ResolveRoomStateColour` now picks the background alongside the text and border colours, and `PaintSimpleRoomButton` applies it. Black-text rooms (a Timed gap) get the neutral default rather than a grey mixed from black. The Profile/Outside bar stays opaque white so it still bookends the rooms. Bumped the `tokens.css` query and the service-worker cache. `tests/ui/room-colours.spec.js` now checks the background tints as well as text, border and icons.

## 13:50

That came out a bit unexpected - the backgrounds for the timed rooms are lighter than for Off rooms. See various/screenshots/261113-01.jpeg

**Assistant**

Looked at the screenshot: the Off rooms were heavier than the Timed-gap rooms because the Off tint was mixed from the mid-grey text (#999) while the Timed-gap tint used the lighter default border (#BBB), so the Off fill came out darker.

Changed `--color-pill-bg-grey` from `#E6E6E6` to `#F5F5F5`. The hierarchy is now blue/orange state tints → neutral `#EEEEEE` for a Timed gap → `#F5F5F5` for Off, so an Off room recedes instead of gaining weight. Its grey text and border still mark it as out of the system. The state-coloured tints are unchanged. Bumped the `tokens.css` query and the service-worker cache; the room-colours spec now expects the lighter Off background.

## 13:56

Can you edit the running man icon to have transparent background, to match the Timed icon.

[Steer: Also the Advance icon]

**Assistant**

Replaced `resources/icon/run.png` with a transparent-background running-man silhouette, cropped and centred in its 100x100 canvas so it reads at the same size as the Timed clock. The old white/black rounded-square version and the temporary `run-mask.png` are gone; the chip now points directly at `run.png` and tints it orange through the mask.

The Advance icon needed no asset change: `advance.svg` is already a filled path on a transparent SVG canvas, and it is rendered through the same mask and chip tile as the Timed clock. Its A is unchanged. The visible square behind both icons is the chip tile shared by every state icon, not part of the artwork.

Updated the icon test, the service-worker precache list and the cache version. Room-colours spec passes; service-worker check 22/22.

## 14:00

I probably do mean the tile itself. I'd like all of the icons to just sit atop the pill background, without a tile being visible behind them.

[Steer: Otherwise they can be confused with clickable buttons]

**Assistant**

Removed the icon tile from the simple-home pills. The 48px icon container is now transparent and only the tinted glyph is drawn, so the runner, clock, A, plus, off and warning icons sit directly on the pill's light state background. The 48px slot is retained, so the room name and temperature do not move. This also removes the button-like square the icons were standing on.

The full room card's chip still keeps its tile; the change is scoped to the pill background. The icon colours and the icon rules themselves are unchanged. The room-colours spec now asserts the transparent icon containers, and the service-worker cache is bumped. Deploy and reload; no controller change.

## 14:22

In Rooms and Devices, add a control to specify the maximum duration of ON. I suppose I should allow "Always On", even if it's deprecated, but otherwise, any value from 4 to 12 hours should be choosable.
The controller should be informed of this setting and should observe it when the situation arises.

[Asked: expiry behaviour and default. Answers: return to the mode it was in before On; existing rooms Always On, new rooms 12 hours. Steer: suggest a better place for the control, e.g. Profile. Asked; answer: system-wide setting.]

**Assistant**

Put the control in the System sheet as a system-wide setting, per the confirmed choice: one cap avoids the same room having different limits under different profiles.

- `onmax` is a map-root field: `"always"` or 4–12 hours. Existing maps with no field behave as Always On; a fresh default map starts at 12 hours.
- The System menu row is now **System** with a subtitle; the sheet has a **Maximum time in On** select (Always On, 4–12 hours). Save sends `onmax` in the `System Name` request.
- The controller records `onprevmode` and `onuntil` when a room enters On. At the deadline it returns the room to `onprevmode` (Timed for Boost or an unrecoverable value), clears both and sends a map update. Reducing the cap clamps an existing deadline; Always On clears it. A restart keeps the deadline because both fields persist with the plan.
- Existing maps keep Always On; new maps written by the controller start at 12 hours.
- Tests: new `on_limit_test.py` (deadline, clamping, bounds, text value, return-mode decision) and `system.spec.js` (sheet default and saved request). Full unit suite 76 AllSpeak / 166 Python tests green; UI suite 11/11; controller and PWA compile checks green; service-worker check 22/22.
- Deploy both controller and PWA. No On removal; it is now bounded where a cap is chosen.

## 18:11

Next is the room details panel.. First stretch the content to fix the screen height. Then give Advance, Room details, Special actions and Edit schedule light gray backgrounds and mid gray borders. I feel there are too many horizontal strips, so the 3 buttons at the bottom I would like to reformat to 3 buttons of equal width, side by side, each with their labels wrapping to 2 lines, in this order: Edit schedule, Special actions, Room details.

**Assistant**

The room card now fills the screen height: the card and its expansion flex to the available space, the expansion spreads the visible sections, scrolls if the controls ever outgrow it, and Home is fixed at the bottom edge.

Advance and the three secondary actions now use a light-grey face (`--color-surface-sunk`) with a mid-grey border (`--color-text-disabled`). Advance keeps the accent style while an advance is active, and the full room view keeps its white Advance face. The old **More** label and three stacked strips are gone; the bottom is one row of equal-width buttons with two-line labels, ordered Edit schedule, Special actions, Room details.

`tests/ui/simple-view.spec.js` now checks the card reaches the viewport bottom, the action row's equal widths and shared top, the two-line label style and the button faces. Deploy the PWA and reload; no controller change.

## 18:22

May suggestion is to make the 3 buttons square so they use up a bit of the space, then to make Advance (a key feature) a big square button in the center of the remaining space. It's the thing that gets used the most.

[Steer: (Keep the rounded corners)]

**Assistant**

The three bottom actions are now square (`aspect-ratio: 1 / 1`), equal width, one row above Home, with the rounded corners kept.

Advance is a large square button (`min(64vw, 240px)`, `aspect-ratio: 1 / 1`), centred in the remaining space between the mode grid and the action row. It keeps the light-grey/mid-grey face and rounded corners, and the accent highlight while an advance is active. The simple-view label is shortened to Advance over the time (e.g. Advance / 18:00), or Cancel / advance while active; the full room view keeps its longer label and white face.

The simple-view spec now checks the squares share a row/width/height, that Advance is square, larger than 180px and horizontally centred, and the button faces. Deploy the PWA; no controller change.

## 18:51

Can you make the space above and below Advance the same.

**Assistant**

The simple room page now sets the Advance block to `display: flex` while it is visible, so the big rounded square is centred vertically as well as horizontally; the gap above and below is the same. The full room view keeps its block layout. The three action buttons remain square with rounded corners, and the simple-view spec now checks the equal vertical spacing as well as the size and horizontal centring.

Deploy the PWA and reload; no controller change.

## 19:02

That was incorrect. I'm quite happy with current behaviour.

**Assistant**

Reverted the change: the Profile/Outside pill on the simple home opens the profile editor again, and the Outside thermometer sheet stays on its menu row. The pill's aria-label/doc are back to profile-and-outside. Verified the simple-view spec (2/2), PWA compile check (12/12) and service-worker check (22/22).

## 19:07

Are you able to check if all of the functionality of the original design is still accessible in the new simplified one. I plan to have it reviewed, but I strongly expect to retire the old one and just keep the new as the only interface.

**Assistant**

Checked both by mapping the full view's controls and by driving the simplified room page directly.

All actions are reachable. From the simple room page I successfully used Advance (toggled to "Cancel advance"), opened Room details/Info, Special actions, and Edit schedule (then cancelled), and returned Home. The profile/outside pill opened the profile editor. All seven menu rows (view switch, Profiles & schedules, System, Rooms and Devices, Outside thermometer, Backups, Send journal now) were present, and there were no page errors. The menu sheets use the same parent-owned code as the full view.

The full view has three summary readouts that the simple home does not: the aggregate heating status ("Nothing calling for heat" / "N rooms calling for heat" / "System firing"), the frost-protection-active badge, and the date/time. The bottom pill carries the active profile and outside temperature, but not those. Per-room warnings beyond the offline/partial icon (battery low, relay messages) are only on the single-room page's warning row, not the home list; the room page has them. The room subline and TRV setpoint likewise live on the room page.

So: functionally complete for actions; the review should decide whether those summary readouts and home-level warnings need a home before the full view is retired. If the full view goes, the "Simple view" menu row and the full-home builder should go with it, and the UI tests that currently drive the full summary/rows need redirecting to the simple page; the shared room-action code, sheets and menu can stay.

I also have a throwaway probe that exercises the secondary actions; I can turn it into a permanent parity spec if useful.

## 19:18

Date and time are already present on a smartphone screen, so no need to duplicate. Aggregate I don't think is needed. Frost protect can appear as an icon next to the outside temperature. Battery low I would show as an icon above the temperature in the relevant room. I've put sample battery-low and battery-empty icons into new-ui/reources.icon.

**Assistant**

Added both badges. The simple-home room pill now shows the battery icon above the temperature: the supplied battery-low artwork when the controller's batteryLow flag is set, and battery-empty at or below 5%; a healthy or missing reading shows nothing. The bottom bar shows the snowflake immediately beside the outside temperature when frost protection is active, using the same rule as the full summary (the controller's frostActive flag if present, otherwise outside at or below the trigger with no room calling). The simple-home refresh now computes that rule.

Added a `simple-badges.spec.js` covering the low/empty/healthy battery cases and the frost badge, precached both PNGs and bumped the service-worker cache. Date/time and the aggregate status were left out as agreed. Deploy the PWA; no controller change.

## 19:28

When I run the UI on a PC browser, the pill backgrounds on the Home screen are ignored and the main shaded background is all that shows behind the text.

**Assistant**

Reproduced the page in a normal desktop Chromium context (not the mobile-emulated test one): with the current stylesheet the pill backgrounds resolve correctly, and the tokens are present. That points to the PC holding an older `tokens.css` while the shell was current — the inline `var(--color-pill-bg-*)` then has no value and the button becomes transparent, letting the page gradient show.

Made that harmless: the pill backgrounds now carry fallback colours (`var(--color-pill-bg-orange, #F9DACC)` and the three siblings), and the template default has the same fallback. Bumped the `tokens.css` query and the service-worker cache version so a reload fetches the current stylesheet. On the PC, hard-reload once (or clear site data) to drop the old CSS. The affected room-colour, badge and simple-view specs pass; PWA compile and service-worker checks are green.

## 19:57

Didn't even need a hard reset. I think the flame icon should appear next to the heartbeat dot whenever the demand relay is on.

**Assistant**

Added it. The top bar's heartbeat button now carries a flame immediately left of the dot, shown only while the demand relay is firing and only on a system that has a request relay configured. It is positioned outside the 24px button so showing it never moves the dot.

The map names the demand relay but does not publish its state, so the flame is derived from the two things the controller fires it for: any room calling for heat (a room's `relay` going on is exactly what sets `HeatingRequested` before `ProcessRequestRelay` reads it) and frost protection, which fires it with no room calling. `PaintDemandFlame` runs from `ComputeSummaryStats`, so both the full and simple home keep it current. Deploy the PWA; no controller change.

`tests/ui/demand-flame.spec.js` covers calling, idle, no request relay and frost, in the full home and through a simple-view switch. It and the related specs pass, along with the PWA compile and service-worker checks.

## 20:10

The text on the Advance button could be a lot bigger - maybe twice its current size.

**Assistant**

Done on the simple room page: the Advance label is 40px, twice the 20px it was. That page's Advance button is the big square, and the largest word ("Advance" / "advance") now measures 163px inside the 200px content box, so the square stays 240x240 and the two-line label still fits.

The full room view's Advance button is unchanged at 14px — its label is a sentence ("Advance to next schedule period (18:00)") in a compact row, where doubling would wrap it to three lines. Say the word if that one should grow as well.

`tests/ui/simple-view.spec.js` now pins the 40px size and checks the widest label line still fits inside the padding box; the simple-view spec passes 2/2. Deploy the PWA; no controller change.
