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

## 10:10

On my mobile phone the background grey colour of a room pill is hard to see when the room is Timed and between periods. Can we try a darker shade, closer to 50/50 instead of 75/25.

**Assistant**

The Timed-gap pill is now a true mid-grey mix rather than a 25% tint:

- `--color-pill-bg-default` went from `#EEEEEE` to `#DDDDDD` — that is the pill's neutral border (`#BBBBBB`) mixed **50/50** with white instead of 75/25. The blue and orange pills keep their three-quarters mix; only the black-text (Timed, between periods) case was changed, as you asked.
- The two fallbacks that mirror the token (`shell.allspeak`'s palette and `simple-home.json`'s template default) carry `#DDDDDD` too, so a stale stylesheet still gets the new grey.
- The Off pill stays `#F5F5F5`, still lighter, so an Off room continues to recede behind a Timed one.
- Bumped the `tokens.css` `?v=` pin and the service-worker cache version so the phone actually fetches the new stylesheet.
- `room-colours.spec.js` now expects `rgb(221, 221, 221)` for the Timed-gap pill; that spec, `simple-badges` and the service-worker check pass. DIFF.md is updated.

If `#DDDDDD` is still too pale in daylight, the next step is to mix toward the black text instead (about `#8C8C8C`) — say the word and I'll try that.

## 11:33

I commissioned a website design; the results is at various/website.zip. I would like to use this as the home page of rbrheating.com instead of the placeholder we currently have.
The page links are arbitrary; I don't know if they will serve or will need to be changed, but we can address these later.
We should start by building it not as /index.html but as /home.html, and develop it from there.

**Assistant**

The commissioned page is now in the repo as `home.html`, developed at the site root beside the existing placeholder.

**Files**
- `home.html` — the design's markup, unchanged except two `<head>` lines: a `favicon.ico` link and `<meta name="robots" content="noindex">` (staging guard; remove when it becomes the real home page).
- `styles.css`, `script.js`, `assets/living-room-hero.jpg` — alongside it, exactly as the designer packaged them, so the page runs from any static server and the eventual rename `home.html` → `index.html` needs no other change.
- `deploy.sh` — uploads those four to the site root; `/index.html` is left exactly as it is.
- `doc/CONTROLLER-FILES.md` — lists the new files as cloud-server-only.

Links are untouched: the nav is in-page anchors and contact is `mailto:hello@example.com`. Google Fonts (Nunito Sans) is the one external dependency; the stylesheet has Arial as fallback.

**Verified** in Chromium against a local static server at 1440×900 and 390×844: hero image and font load, no failed requests, no horizontal overflow, mobile menu opens/closes and updates `aria-expanded`, every anchor resolves, footer year 2026. `bash -n deploy.sh` passes.

Nothing is committed. Run `./deploy.sh` and review at `https://rbrheating.com/home.html`; when you're happy, the switch is the rename plus deleting the `noindex` line.

One housekeeping note: `conversation-029.md` is still headed 2026-11-13; say the word if you'd like today split into a new file.

## 13:07

The design of the home screen needs some updates. One is to change all black text to the dark blue used in the website's new /home screen. The other is to move the Profile pill to the top, under the banner. A reviewer has expressed a preference for keeping the date and time, but not the System Firing row. Can we start by creating a single banner containing the existing banner, date/time, a Profile button and the outside temperature? It should be compact but not cramped. Then the rooms with their gradient background occupy the rest of the screen.

**Assistant**

The banner is in place on the simple home.

- The top bar is now one card, inset 8px from the page edges with an 18px radius and sticky 8px from the top, so the time-of-day gradient shows around it. Its second row holds the date and time on the left; on the right, a Profile pill button (calendar glyph + the active profile's name, opening the profile editor) and the outside temperature with the frost snowflake. The bottom profile pill is gone, and the room pills now fill the rest of the screen down to the 8px border.
- The banner measures about 110px on the home and stays under the 140px the spec allows; on the single-room page the second row hides, as the bottom pill never appeared there, and that is what keeps the room card on one screen (measured: card 80–836, no overflow).
- All black text is the website's navy: `--color-text-primary` is now `#12345A` (the `--navy` from `home.html`/`styles.css`) instead of `#1A1A1A`, app-wide.
- The reviewer's note is applied to the full home: its summary card keeps the title and the date/time, and the "System firing" subtitle row is removed (element and all its writers).
- Bumped the `tokens.css` pin and the service-worker cache version, since the stylesheet and the banner both changed.

Full Playwright suite 14/14, PWA compile check 12/12, service-worker check 22/22. Deploy the PWA and reload the phone; no controller change. Note DIFF.md now carries both this and the website's home-page work.

## 13:24

Another comment; the room pills are visually too dominant. Can they be narrowed - we'll start with 10%.

**Assistant**

The room pills are now 90% of the list width and centred, so a strip of the time-of-day gradient frames each room on both sides — 337px of the 374px list at a 390px viewport, 18.7px clear either side of the pill inside the 8px page border. Their height is unchanged (they still share the space under the banner).

That is one `width` value in `new-ui/resources/webson/simple-home.json`, with `margin: 0 auto` keeping them centred; 80% or 85% is a one-line change if 10% is not enough.

`simple-view.spec.js` now pins the 90% width and the equal left/right inset; `simple-view` and `room-colours` pass (3/3). Deploy the PWA and reload the phone to judge it.

## 13:43

Still something not quite right. We think it's that the room pills are too tall. Reduce their heights by 10% so they have more space between them.

**Assistant**

Each room pill is now 90% of its fair share of the column, and the leftover tenth becomes space between the pills: at 390x844 a pill is 313px instead of 348px, and the gap between two pills is 76px instead of 6px. The last pill still sits on the bottom border, so the column reads as separate cards rather than one slab.

That ratio cannot be done in CSS alone (it has to divide by the room count), so `BuildSimpleHome` computes the height as `calc((100% - gaps) * 0.9 / rooms)`; `simple-home.json` no longer lets the pill grow, and `layout.json` gained an `@id` so the simple home can pin its frame to `100vh` — a percentage height only resolves against a definite one. The full home releases the height again so its room list still scrolls. The dial is the `0.9` in that calc.

Two traps worth recording: the arithmetic has to be written with the dialect's verbs (`decrement` / `multiply … by`), not `(RoomCount - 1) * 6`, which the compiler rejects; and the frame's `attach` had to move below the layout render.

`simple-view.spec.js` pins the 90% height and the wider gap; whole Playwright suite 14/14, compile check 12/12. Deploy the PWA and reload the phone.

## 13:50

The new website design has a logo of a house outline with rising heat inside. I'd like that to be our standard logo on the PWA too.

**Assistant**

The website's mark is now the PWA's logo everywhere it appears.

- `resources/icon/house.svg` is the site's artwork exactly: the house outline in navy `#12345A` with three orange `#F47716` heat waves, the same paths and stroke weights as `.brand-mark` in the site's stylesheet. It stands on white rather than on a tile, as it does in the site header — the banner's button and the About sheet's header both lost their orange square and the shadow.
- The installable icon matches: `app-icon.svg` is the mark on a white 512 tile, and `icons/icon-192.png` / `icon-512.png` are regenerated from it with Chromium, so the home-screen icon, the apple-touch icon and the manifest all agree.
- Checked in the browser at 390x844: the banner mark, the About sheet mark and the 512 icon all render correctly; `demo-mode`, `simple-view` and `smoke` pass (4/4), service-worker check 22/22.
- Service-worker cache version bumped. A phone that already has the PWA installed may keep the old home-screen icon until its icon cache turns over — removing and re-adding the shortcut is the sure way to see the new one.

One loose end: `--shadow-house-mark` in `tokens.css` is now unused, left in place in case a raised mark comes back.

## 18:37

A small cosmetic point; the spaces above the top room pill and below the bottom one should be the same height as those between the pills.

**Assistant**

Every space in the column is now the same height — above the first pill, between the pills and below the last. At 390x844 that is about 64px each, where it was 8px at the ends and 76px between; the pills take the height that leaves, about 255px each instead of 313px, since keeping the gaps and squaring the ends can only come out of the pills.

The column now uses `space-evenly` with no fixed gap, and `BuildSimpleHome` sets the pill height to `100% / (5n+1) * 4`: n pills plus four quarters per space fill the column, so every space is a quarter of a pill and the rule holds whatever the room count. The height still has to be computed in the shell because it divides by the number of rooms.

`simple-view.spec.js` now measures the three spaces and the pill-to-space ratio rather than a 90% share. `simple-view`, `room-colours`, `simple-badges`, `demand-flame` and `demo-mode` pass (7/7), compile check 12/12, doc hashes clean. Deploy the PWA and reload the phone.

If the pills now look too small, the dial is the `4` in that calc — `3` leaves half-pill spaces and larger pills, `5` the reverse.
