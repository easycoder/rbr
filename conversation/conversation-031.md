# 2026-11-15

## 10:55

The system doesn't remember the Maximum Time On setting when it is changed. Also the title of that option is awkward. Better would be "MAXIMUM ON DURATION"

**Assistant**

Fixed both.

**The setting was being saved — it was never read back.** `set default of <select> to X` in the pinned JS runtime picks an option by its **value**, not by the text it shows, and it does nothing at all when nothing matches. The sheet handed it the label (`8 hours`) while the options carry `8`…, so every time the sheet opened the selection fell back to the first option, Always On. Choosing 8 and saving sent `onmax: "8"` and the controller stored it; reopening showed Always On, and the next Save quietly wrote that back. `OpenSystemSheet` now passes the option value (`always`, `4`…`12`).

**The label** now reads MAXIMUM ON DURATION — `Maximum on duration`, uppercased by CSS like the other section labels. The menu row's subtitle, the sheet's tagline and its hint follow the same wording.

**One adjacent fix:** an `onmax` that is present but empty means "no cap" to the controller, so the sheet now shows that as Always On instead of clamping it up to "4 hours" and potentially writing 4 back.

Verification: new test *the System sheet reopens on the saved On cap* in `tests/ui/system.spec.js` — it pushes a map with `onmax: "8"`, expects the sheet on 8, changes it to 10, saves, reopens and expects 10. Against the old code it failed with `"always"`. Full UI suite 15/15, `node tests/pwa-compile-check.js` 12/12, `asdoc-check` clean on `shell.allspeak` (hash refreshed).

I also logged the runtime behaviour to `REQUESTS.md` (silent no-match in `set default of`), and rewrote `DIFF.md`: deploy the UI and reload once, since the service worker holds the old files.

## 11:53

I would like the top item of the Hamburger to be "Appearance", subtitled "The look and feel of this app". When clicked it will bring up a shade with 2 main sections:

1 The choice of Detailed or Simplified view. The default for a new installation will be Simplified.

2 A choice of background colour. A palette of 10 sample non-primary colours, including the present orange and other relatively neutral shades including olive green (#808000). A text field will offer the user the means to specify any HTML shade by hex value. The gradient fill will still apply, but a checkbox will offer the option of whether to apply the time-based changes as currently implemented. The default can be the current colour and the choice will be held in browser storage.

**Assistant**

Built as agreed: the colour sets the page background only (the heat/button orange is untouched), with time-based changes off it is one fixed gradient from the chosen colour, and everything applies live with a Done button.

**The menu.** The top row is *Appearance* / "The look and feel of this app"; the old Simple view row is gone and the view is chosen inside the sheet.

**The sheet.** A VIEW pill (Detailed | Simplified) and a BACKGROUND COLOUR section: ten swatches — orange `#E86A33`, ochre, olive `#808000`, moss, teal, slate, heather, rose, walnut, sand — a hex field that accepts `#RRGGBB`, `RRGGBB`, `#RGB` or `RGB` in either case, a note that explains a rejected value, and a *Time-based changes* checkbox.

**The gradient.** Still a gradient, but built from the chosen colour: each of the six hour buckets mixes it a fixed distance towards white (towards the night navy after dark), so every colour keeps the shape of day the old fixed palette had. With the checkbox off, the midday stops are used at every hour. The default orange reproduces the present cream-and-peach look closely. The choice is held in `rbr-bg-colour` and `rbr-bg-time`; a missing value means the orange and time-based changes on.

**The view default.** A device with no stored `rbr-simple-view` now gets Simplified. That is the requested default for a new installation; an existing phone that never touched the old toggle changes with it, and Detailed switches back.

Two bugs the tests found and I fixed: the swatch element array had to be grown before it could be indexed, and the nibble scanner borrowed the variable it was decoding into (it returned 256 for `0x80`). A third, the 3-digit expand, was rewriting the string through a `cat` chain that parsed the wrong way, so `#ABC` is now decoded nibble by nibble.

Verification: new `tests/ui/appearance.spec.js` (fresh install starts simplified; Appearance is the first menu row; live view switch keeps the sheet up and survives reload; swatch persists; invalid hex refused; `5c7a99` normalises to `#5C7A99`; unticking the time box leaves exactly the midday gradient computed from that colour, and the box comes back unticked after reload). The UI harness now marks each test device as having chosen Detailed, with a `freshView` opt-out, and a shared `chooseView` helper replaced the old menu-row clicks. Full UI suite 17/17; `pwa-compile-check` 12/12; the jsdom checks that drive detailed-home rows seed the view key; `asdoc-check` clean.

`DIFF.md` is rewritten: deploy the UI and open it once online, since the service-worker cache version moved and now precaches the new sheet.

## 12:09

The background colour of the OFF rooms is intended to reduce their prominence, but in fact it does the opposite, standing out as near-white. So I'd like to try making this a special case, where the background is dark gray, such that the text is visible but not prominent. The border line should probably be navy.

**Assistant**

Done — the Off pill is now the inverse of its old treatment.

- **Fill** `--color-pill-bg-off` `#4A5057` (dark grey), replacing the near-white `#F5F5F5` that was drawing the eye.
- **Text** `--color-pill-fg-off` `#E6E8EA`, pale but not white, so the room is readable without gaining weight. The name, the temperature and the pill's own glyph all take it.
- **Border** `--color-pill-border-off` `#12345A` — navy, whatever the text colour, so it reads as part of the ink rather than as another state colour.
- **The glyph** used the neutral grey chip tint, which sinks into a dark fill; only that neutral glyph is lifted to the text colour, so an offline or partial-failure chip keeps its amber.

The rule is in `ResolveRoomStateColour`, so the simple home's pill and any other reader of those three colours agree; the other states are untouched. `tests/ui/room-colours.spec.js` now pins the Off pill's pale text, navy border, dark fill and lifted glyph; full UI suite 17/17, `pwa-compile-check` 12/12, `asdoc-check` clean. `tokens.css` changed, so its cache-buster in `new-ui/index.html` moved to `?v=2611151215`.

One observation from the screenshot: dark is visually heavier than pale, so the pill is quieter in brightness but heavier in mass — it no longer screams "white", but it does carry weight. A mid-grey fill would sit further back again if it still draws the eye. Also worth knowing: after 22:00 the page background goes dark, and there the pill becomes the lighter object again (still a quiet block, and the fill is one token to move).

## 12:19

No, that doesn't work any better. Let's try using the same background and border as for Timed rooms, and rely on just the fainter text to indicate the OFF state.

**Assistant**

Switched to that. An Off room now wears exactly the pill a Timed room wears between periods — neutral border `#BBBBBB` (`--color-text-disabled`) and neutral fill `#DDDDDD` (`--color-pill-bg-default`) — and only its text differs: the faint grey `#999999` (`--color-text-muted`), on the name, the temperature and the glyph.

The three Off-only tokens from the dark experiment are gone, along with the chip re-tint that went with them. In `ResolveRoomStateColour` the border rule now treats the black of a Timed gap and the faint grey of Off the same way, so the two pills cannot drift apart: `tests/ui/room-colours.spec.js` compares pill 0 and pill 3 directly on border and background, as well as asserting the faint text and neutral glyph.

Seen in a screenshot, the two pills read as the same object and the Off room sits back without becoming the heaviest thing on the page. Full UI suite 17/17, `pwa-compile-check` 12/12, `asdoc-check` clean; the `tokens.css` cache-buster moved to `?v=2611151218`.

## 12:26

That's optimal.
The hero image on the website shows an elderly white couple. If I produce the same but showing a different age or ethnicity, can I specify a random probability to display the one or the other?

**Assistant**

Yes — and it is a small change in this site, because the hero is a CSS background rather than an `<img>`.

**Where it lives today:** `styles.css` sets `.hero`'s `background` to `url("assets/living-room-hero.jpg")`; the `.hero-photo` div is only the accessible name — `role="img"` plus an `aria-label` describing "a mature couple". The file is 1672×941, and on phones it is cropped to 360px tall at `38% top`.

**How the choice would work.** CSS cannot randomise, so the pick is JavaScript in the page or PHP on the host. For a static landing page, JS is by far the smaller change: an inline snippet in `<head>` — which runs before first paint — marks `document.documentElement` with the chosen variant (e.g. `data-hero="b"`); `styles.css` then carries `html[data-hero="b"] .hero{background-image:url("assets/living-room-hero-b.jpg")}`; and the pick is `Math.random() < 0.5` for 50/50, or `0.3` to give the second image 30% of loads. Doing it in `script.js` instead would flash: that file loads at the end of `<body>`, so the first image would paint and then swap, on the LCP element.

**Two details that matter more than the randomness.** The accessible name must follow the image — two photos of different people cannot share one `aria-label`, so both descriptions belong on `.hero-photo` as data attributes and the snippet sets the matching one. And the two photos have to be composed identically: the copy sits on the right over a white gradient, so the subject must stay left with quiet space right, and the mobile crop takes the top 360px at 38% across — a differently framed photo cannot be rescued by CSS. Same aspect ratio (about 16:9), and the white gradient needs checking if the new photo's right side is darker.

**Probability semantics.** Each page load is independent, so a visitor can see the other photo next time; `localStorage` makes it stick per device. For a clean split across visits, per-load is right, but the page should also report which variant it showed or the split is invisible in analytics. Both files want a `?v=`/new-filename cache stamp like `styles.css`; only the chosen one downloads. The PHP alternative (`index.php` with `mt_rand()`, works without JS) costs more than it buys for a decorative image.

I offered to wire it now with the current photo duplicated so the plumbing is proven, or when the new file lands — and asked for the split and whether the choice should stick per visitor. Nothing was edited in the repository for this answer.

## 12:39

The new image is various/alternate-ethnicity.png. I'd like it to appear about 20% of the time.
Does the visitor have any opportunity to choose? If so, it can stick, but otherwise, random is fine.
I think the inline snippet is best, to avoid a flash.

**Assistant**

No — nothing on the page lets a visitor choose a photo, so there is nothing to remember: the pick is random per page load, one visit in five.

**The picker** is the inline snippet in `index.html`'s `<head>`: `if (Math.random() < 0.2) document.documentElement.setAttribute('data-hero', 'alternate')`. It runs before the stylesheet paints, so the hero never flashes the default. `styles.css` carries the swap — `html[data-hero="alternate"] .hero{background-image:url("assets/alternate-ethnicity.png")}` — and its `?v=` moved to `20261115-1`.

**The image moved to `assets/`.** `deploy.sh` copies `index.html`, `styles.css`, `script.js` and `assets/`, and nothing else from the page's own files (its comment records an earlier hero that 404'd for exactly this reason), so a photo left in `various/` would be missing for one visit in five in production.

**The label follows the picture.** `.hero-photo` gained `data-label-alternate`, and `script.js` applies it when the alternate was chosen. That div is `display:none`, so the label is inert today; it is kept in step so it cannot describe the wrong couple if the div is ever shown.

Both files are 1671×941 with the subject on the left, so the shared `background-position` and the phone crop frame them the same; I checked both at desktop width over the white gradient the copy sits on, and the alternate's bright window side reads well. New `tests/ui/hero.spec.js` pins both variants with `Math.random` overridden, including a 200 for the alternate (which is what proves the `assets/` path), and the full suite is 19/19.

One measurement to act on: the PNG is **2.6 MB** against 497 KB for the existing JPEG. At 20% of visits that is a heavy first load on a phone and the largest thing on the page when it happens; converting it to JPEG or resizing to about 1400px wide would bring it near the current file. I left it as supplied and can convert it on your word.

## 12:43

JPEG would be better.

**Assistant**

Converted. `assets/alternate-ethnicity.jpg` is the same 1671×941 picture at quality 86, 4:2:0, metadata stripped: **375 KB against 2.6 MB**, which makes it lighter than the 497 KB default hero as well. At 100% the faces, the knitwear and the window foliage are clean, and it renders through the same `background-position`/`cover` and the phone crop with no change.

The master PNG moved to `various/alternate-ethnicity.png` rather than being deleted — `deploy.sh` copies `assets/` only, so the source stays in the repository without being shipped, and `assets/` holds just the two heroes the page can use.

References: `styles.css` now names the `.jpg` for `html[data-hero="alternate"]`, its `?v=` in `index.html` moved to `20261115-2`, and `tests/ui/hero.spec.js` names the `.jpg` and says why it is a JPEG. Both hero specs pass, the alternate was fetched with a 200 in Chromium and rendered correctly at desktop width, and the full UI suite is 19/19.

## 12:54

I have a third image at various/mixed-ethnicity.png. Please alternate this with the first image on a 50-50 probability. (So that's 40/40/20). Convert to JPEG as before.

**Assistant**

Done: three photos, one draw, two thresholds. In `index.html`'s `<head>`, up to 0.4 takes the default couple, 0.4–0.8 the mixed-ethnicity couple, and above 0.8 the Black couple — so 40/40/20, with the shares readable in the code rather than buried in three separate draws.

- **`assets/mixed-ethnicity.jpg`** is the supplied PNG converted at quality 86 (4:2:0, stripped): **357 KB instead of 2.6 MB**, same 1672×941. The master PNG stays in `various/mixed-ethnicity.png`, which `deploy.sh` does not copy.
- **`styles.css`** gained `html[data-hero="mixed"] .hero{background-image:url("assets/mixed-ethnicity.jpg")}` beside the alternate rule, and its `?v=` moved to `20261115-3`.
- **The label follows the picture**: `.hero-photo` gained `data-label-mixed`, and `script.js` applies the one matching the drawn variant. The div is `display:none`, so it is inert today but cannot describe a different couple if it is ever shown.
- All three are the same size and composition, so the shared gradient, `background-position` and phone crop apply to each; the mixed photo was rendered in Chromium at desktop width and the copy sits legibly over its window.

`tests/ui/hero.spec.js` now pins all three variants with `Math.random` overridden — lower 40%, middle 40%, top 20% — and each asserts its own background, label, a 200 for its own file and no request for the other two. Full UI suite 20/20.

## 13:05

In System, the choice of Heat Pump doesn't get remembered (or restored).

**Assistant**

Found it: the page was doing its part and the controller was throwing the value away. The PWA has always put `systemType` in its `System Name` request, and `map-to-rooms.allspeak` has always read `Map.systemType` back into the sheet — but `ProcessUIRequest`'s `System Name` branch stored only `name` and `onmax`. So Save looked successful, the next map carried no type, and the sheet reopened on the Boiler default.

**The fix** is in `controller.allspeak`. The branch moved into `ApplySystemName` (name, heating type, On cap), which sets `SystemNameApplied` when it has a usable name so the caller still broadcasts only on success. `NormaliseSystemType` accepts `Boiler` or `Heat Pump` in either case, plus the `heatpump` spelling, and stores the canonical label; anything else is refused in the log rather than rewritten to Boiler, and a request with no `systemType` leaves the stored one alone. A freshly created map now starts with `systemType` `Boiler`.

**Tests:** new `tests/unit/system_type_test.py`, twelve cases extracted from the shipped routines (both labels, aliases, refusal, optional field, missing name applies nothing, the On cap still rides along); added to `run-unit-tests.sh`. `tests/ui/system.spec.js` gained a third case — a map with Heat Pump opens on Heat Pump, choosing Boiler ships `systemType: "Boiler"`, and reopening after the reply shows Boiler. Unit suite 178 Python tests all passing plus the AllSpeak tests and the whole-controller compile; UI suite 21/21.

**To take effect:** `./deploy.sh --release`, since the fix lives in the controller pack; the app itself needs no change or reload. On a controller that has never stored a type, `map.json` has no `systemType` until the first Save writes it — and until then the sheet shows Boiler, which is what the page already assumed.

## 13:46

It's worth recording.

**Assistant**

Wrote it up as `doc/SENSOR-REPORTING.md` — the engineering tree beside `EVENT-JOURNAL.md` and `UPDATE-MECHANISM.md`, because the `docs/` tree is the product layer and its device-control page is still "to write".

What the note records: RBR's 45-minute warn and 60-minute fail thresholds and why a heartbeat matters; the finding that Zigbee2MQTT's own converter already configures these sensors for min 10 s, max **1 hour**, change **1.0 °C** — an hour is longer than the gate, which is the real reason a steady room goes quiet; the `device/reporting/read` and `device/reporting/configure` request topics with working temperature and humidity payloads; the units (`reportable_change` in hundredths, 65535 disables reporting); the sleepy-device wake-up caveat; what `Cannot send, WebSocket not open` actually means and why reloading or bypassing a proxy is the fix; how to verify; and that re-pairing or a frontend **Reconfigure** puts the converter's one-hour default back — the answer to "why did it go quiet again months later".

Linked from `doc/setupRBR.md`'s "No recent change is normal" note, where an installer meets the symptom, and from `docs/README.md`'s technical map as a source for the device-control page.

Honesty point recorded in the page itself: the commands have not yet been run against the Sunroom sensor, so the document says the first attempt is the test rather than claiming it verified. Status is draft. No code changed, so no suite was run.

## 14:16

I'd like to work on the user manual. As a first step it would be useful for the entire documentation stack under docs/ to be duplicated on the website. At Find Out More, a button can open the documentation much in the way learn/ does on AllSpeak. Right now it can remain a single structure, but there may be a need later to separate out the user manual.
The title of the docs page can be simple; just the product logo/name and a relevant page title.

**Assistant**

The documentation is now part of the website rather than fetched from GitHub, and Find out more opens it.

- **Deployment:** `deploy.sh` (and the deploy workflow) stage `docs-reader/` and the whole `docs/` tree into one directory and publish it to `/docs/`. The reader fetches `/docs/README.md` and `/docs/<slug>.md` from the site itself; the GitHub/CDN fallback is gone, so the site and the pages it shows are deployed together. `docs/README.md` remains the map, so the tree can stay one structure and a user manual can split out later without changing the reader.
- **Find out more:** a third button, **Read the documentation**, points at `/docs/`, beside Get in touch and Open the web app.
- **Title:** the reader's tab title is **Documentation — Room By Room Heating**, and its top bar is the house mark, "Room By Room Heating", then "Documentation", with the existing Contents/Previous/Next controls.

Verification: `node tests/docs-reader-check.js` 52/52 (including new checks that the README is read from the site and nothing from GitHub), `npx playwright test tests/ui/docs-link.spec.js` 1/1, and `/docs/` rendered from a staged deployment in Chromium at desktop and phone widths with no errors or 404s. `asdoc-check` is clean.

To publish: run `./deploy.sh` (or the deploy workflow); a documentation change now reaches the site on the next deploy. `DIFF.md` says the same.

## 15:18

Does the UI have an option to reset, requiring the system to be re-identified?

**Assistant**

Not in normal use. The pieces exist, but there is no discoverable reset or "forget this system" control once the app is running.

- **Pairing** lives in the About sheet as **Set up my system**: it asks for the controller's MAC and system password, exchanges the password for a token at `/verify`, and stores `dev-mac` and `dev-token`. That CTA is only shown while `DemoMode` is set — no usable credentials or no MAC — so a paired, working app does not show it.
- **Reset** exists as `ResetCredentialsAndReload` in `shell.allspeak`. It confirms, clears `dev-broker`, `dev-username`, `dev-password`, `dev-mac` and `dev-token`, and reloads. It is wired to the hamburger while the page boots, before MQTT connects; when the first map arrives, `BuildHomeScreen` re-binds the hamburger to open the Menu. There is no menu row or System-sheet button that calls it, so it is a panic button for a page stranded before a map arrives, not a user option.
- There is no "Forget this system", "Change system" or "unpair" row in the Menu or System sheet. To re-identify a working installation today you would have to clear the site's browser storage, or reach the panic path while it cannot connect.

A proper version would be cheap: a **Forget this system** row in the Menu or System sheet wired to the existing reset routine, keeping its confirmation, plus a test that it clears the identity keys and reloads. I can add it.

## 15:36

The UI currently permits access to just one system. If a company or individual were to manage a number of installations, these must all be accessible on one or more devices. There won't be a primary system and a number of secondaries - they all share the same level. I think the About sheet is the place for this to happen. The Manual button should call the system browser to load up the new documentation page on the website. A third button will be Systems. It shows a list of systems managed by this PWA instance (one at present here) and provides the means to add or delete. Addition will require the same credentials as now, but the storage will presumably have to be adjusted to cope with an array of installations. A Select button chooses any chosen system to be current and managed.
It's been a while since I was in this area. What implications does this have for rbr-users.json on the website? Is this generated or manually edited?

**Assistant**

`rbr-users.json` already has the right model for this: one entry per system, keyed by MAC, with both endpoints operating per-system. A multi-system PWA does not need a new server-side record shape. What it needs is local storage for several `{mac, token}` pairs and one current MAC.

**Where the file comes from.** It is not generated by a deploy and it is not in the repository. It lives on the web host at `/home/rbrheating/rbr-users.json`, above the document root; `deploy.sh` never touches it. In practice:

- `/register` in `auth.php` creates a pending entry with email, a six-digit password, `verified: false` and `created`.
- `/verify` marks it verified and mints the one `token`.
- The `credentials` block — the broker account `credentials.php` requires — is written by no web endpoint. Only `provision-system.py`, or hand-editing, creates it.
- The current PWA's pairing flow only calls `/verify`; it never calls `/register`. So "Set up my system" can only pair an entry that has already been provisioned. Use `provision-system.py --mac ... --email ... --write` on the host.
- It is plain JSON and can be hand-edited, but that is the risky path: a malformed file or a missing `credentials` block breaks pairing. The tool validates, tests the broker login, writes atomically and keeps a backup.

**What this means for the Systems tab.**

- No `rbr-users.json` change is required for list, add, select or delete. Each system already has its own entry, token and broker credentials.
- Add = the same MAC + system password, call `/verify`, store the returned token in the local array. It does not create the server entry.
- Delete = forget it locally. It does not remove the server entry or revoke the token. To revoke, rotate the token on the host (`provision-system.py --rotate-token`) — which unpairs every device holding that system — or remove the entry.
- Select = set the current MAC and reload. The MQTT client, map and all sheet state are built for one system at boot; switching in place would mean tearing all of that down.
- Multiple devices: each device pairs each system separately with the same MAC + password. Because `auth.php` stores one `token` per system, all devices end up with the same token. Access works, but per-device revocation does not. If you need that, `rbr-users.json` needs multiple tokens or device records and the endpoints need a device identity — a server change, not a UI one.
- There is no owner, group or primary relationship in the file. The same email can appear on several entries, but nothing lists the systems belonging to an email, and `credentials.php` deliberately does not reveal which systems exist. Keep the Systems list local to the PWA; do not add a "list all my systems" endpoint.
- A friendly name is not in `rbr-users.json`; the controller's map has `systemName`, which is only known after connecting. So the list needs a locally stored label, or shows the MAC until the first map.
- The local `credentials.json` override is single-system and bypasses the per-MAC lookup; keep it out of a multi-system deployment.
- Migration: the existing `dev-mac` and `dev-token` keys become the first entry in the new array; keep reading them for one release so an upgraded phone is not stranded.

**The other two things.** The Manual tab currently reads "User manual coming soon"; it can now open `/docs/` — a new tab if you want it in the system browser rather than inside the installed PWA. And `doc/setupRBR.md` steps 8–9 still describe a "System Manager" with an Add button that the current PWA does not have; the new Systems tab would make those steps true again, so they will need rewording for the About sheet.

My recommendation: keep `rbr-users.json` unchanged for the first version and make the Systems tab a local array plus a current MAC, with admin provisioning as it is today. If you want the PWA's Add to create a brand-new system, that is a server-side decision — and a security one — rather than a storage change.

## 15:44

I think I'll follow your recommendation, but before then, some more quetions. I'll shortly be setting up a new system, which will need an entry in rbr-users.json. (Aside: this may one day have to go into a database.) Does this happen as part of the existing setup? If not, can it go in rbr-setup.sh or at another step in the procedure?

**Assistant**

No — not today. `rbr-setup.sh` never touches `rbr-users.json`. It runs on the controller and writes only local controller state (`.mac_override`, `credentials`, services, and so on). The server file is on the web host, above the document root, and the setup script has neither the file nor the credentials to write it.

The entry is created or completed on the web host by `provision-system.py` — the supported path — or partly by `auth.php`:

- `/register` creates email + a six-digit password + `verified: false` + `created`; neither the current setup script nor the PWA calls it.
- `/verify` sets `verified` and mints the token.
- Neither writes the `credentials` block that `credentials.php` requires; only `provision-system.py` or hand-editing does.

So even a setup script that called `/register` would leave the system unprovisioned.

For the new system, the sequence is:

1. Run `rbr-setup.sh`; note the MAC it prints at the end (also in `.mac_override`).
2. On the web host: `./provision-system.py --mac <MAC> --email <owner> --write`. It creates or repairs the entry, tests the broker login, and prints the six-digit system password for a new entry.
3. Pair the PWA with the MAC + that system password.

`doc/PROVISIONING.md` is the accurate checklist.

Can it go in `rbr-setup.sh`? Only as a reminder, not as the provisioning step. Doing it for real from the controller would require either host credentials on the customer box — bad — or a new secure provisioning endpoint. If you want that later, design a one-time provisioning token/API; that is also the natural place to fix `/register`'s missing `credentials` block.

Two things to watch on this install:

- `rbr-setup.sh` Step 0 points at `https://rbrheating.com/credentials.php` for the MQTT password, but that endpoint now requires `?mac=&token=` and returns 401 otherwise. For a new system, take the MQTT username/password from the host settings or the provisioning record; the system password is a different secret.
- `doc/setupRBR.md` steps 8–9 still describe a "System Manager" with an Add button that the current PWA does not have. The new Systems tab will make the UI match; until then, use `provision-system.py` plus "Set up my system".

On the database aside: the file is flat, MAC-keyed JSON, and only `auth.php`, `credentials.php` and `provision-system.py` read or write it. A move to a database would replace those storage calls, not `rbr-setup.sh`. The setup script should stay ignorant of the account store.

## 16:13

OK. Please ensure that the setup documentation records the use of provision-system.py.
We'll go ahead as recommended. Re system naming, I think one should be asked for. It will likely have a different significance to one chosen by the user.

**Assistant**

Done. The setup docs now record provisioning, and the About sheet has the three-way choice.

**Setup documentation.** `doc/setupRBR.md` steps 7–9 now say the system password comes from `./provision-system.py --mac <MAC> --email <owner> --write` on the web host, and that `rbr-setup.sh` installs the controller but does not create `rbr-users.json`. The stale "System Manager"/"register in the UI" wording is gone. The same step is recorded in `docs/preparation/05-preparing-a-unit.md` and `docs/installation/06-what-the-setup-script-does.md`.

**The About sheet.** It now has **About**, **Manual** and **Systems**. **Manual** is a link to `/docs/` opening in a new tab, not a placeholder. **Systems** lists the installations this device manages; each row shows the local name and MAC, with **Select** and **Remove**. Remove only forgets the system here; it does not delete the server entry or the installation.

**Add** asks for the name first, then the MAC and system password, exchanges them at `/verify`, stores the token and selects the new system. The name is a local label for this device's list, deliberately separate from the controller's own **System → Name**; it does not travel to `rbr-users.json` or to another device.

**Storage.** `rbr-systems` is a JSON array of `{name, mac, token}`; `rbr-current-mac` names the current one. A device upgrading from the single-system build is migrated on first boot, keeping its `dev-mac`/`dev-token` pair as the first entry named "My system". Selecting another system reloads, because MQTT and the map are built for one system at boot.

Verification: `node tests/pwa-compile-check.js` 12/12; new `tests/ui/systems.spec.js` 2/2 (Manual link, migrated list, add, select, remove); the full UI suite 24/24 across the capped run and the remaining-spec rerun; `node tests/pwa-backup-sheet-check.js` 22/22, which also proves the migrated system still connects; `node tests/docs-reader-check.js` 52/52; `asdoc-check` clean.

To publish, run `./deploy.sh` and reload the app once online. There is no controller release; the service-worker cache version moved so the new Systems row is precached. If you want the name to live in `rbr-users.json` and follow the installation to other devices, that is a small server-side addition rather than this local label — say the word.

## 16:40

Can you add Rename to Current/Remove

**Assistant**

Done. Each system row now has **Select/Current**, **Rename** and **Remove**.

Rename asks for a new label, updates `rbr-systems` locally, repaints the list and leaves the sheet open. It does not touch the MAC, token or the controller's own **System → Name**. The updated record is written back into the array with `set element … of SystemsData to SystemsEntry` before saving, because the indexed read alone did not persist the change in this dialect.

Docs and tests are updated: `doc/setupRBR.md` now mentions Rename, and `tests/ui/systems.spec.js` exercises add → rename → select → remove, including that the MAC and token survive the rename. `node tests/pwa-compile-check.js` 12/12, the Systems spec 2/2, and `asdoc-check` clean. The service-worker cache version moved to `2611151633`; deploy with `./deploy.sh` and reload once online.

## 17:00

Now the user manual, starting with Operation — living with it; 01-the-interface.md. I'd like to feature the simplified interface, for a sample installation comprising Living Area, Bedroom 1 and Bedroom 2. This is likely to be a big document and may well need to be split into sections, such as for each mode. If you are able to create screenshots this would be immensely helpful. Let's start with the user's first introduction to the PWA. The system is set up with its 3 rooms, so the manual should go through what it represents, the use of colour etc, the operating modes; how to set them up and use them, then Advance and Boost, ending with miscellaneous functions such as Special Actions.

**Assistant**

The first operation page is written and illustrated from the real simplified interface.

**New page — `docs/operation/01-the-interface.md`.** It opens with the PWA and the three-room sample installation, then covers what the home screen represents (top bar, profile, outside reading, room pills), the colour and icon vocabulary, opening a room, the four modes — Timed, On, Boost and Off — with how to choose and use each, Advance, Boost in detail, and the miscellaneous controls: Special actions, Edit schedule, Room details, the profile sheet and the menu. It is divided into `##` sections by mode so it can be split into separate pages later without rewriting the prose.

**Screenshots.** Nine captures under `docs/operation/images/`, made by driving the real PWA with a scripted controller and a map for **Living Area**, **Bedroom 1** and **Bedroom 2**: the simplified home, Timed, On, Boost, Off, Advance, Special actions, Room details and the profile sheet. The home shows the colour story directly: Living Area heating in orange, Bedroom 1 between periods in neutral with a clock, Bedroom 2 Off in faint grey with the power icon.

**Reader.** The runtime's Markdown renderer has no image syntax — it produced a literal `!` and a link — so `docs-reader/index.html` now upgrades those pairs to `<img>` and the reader styles images to the pane width. `tests/docs-reader-check.js` covers the manual's images.

**Map and notes.** `docs/README.md` records the page as **Draft**, updates the operation-layer status and adds the screenshot convention; `TODO-docs.md` now records operation 01 as written and three operation pages left.

Verification: `node tests/docs-reader-check.js` 56/56, including image rendering, paths and alt text; `git diff --check` clean. No PWA or controller code changed in this pass, so the UI suite and controller checks were not rerun.

To publish, run `./deploy.sh` and reload `/docs/`. The page is draft, and the screenshots use a demonstration map rather than a live installation.

## 18:32

A very good page. The reference to it in the document map needs updating with a link and Draft status.
Some of the documentation links are incorrect. For example, in "The interface", clicking Next goes to an as-yet unwritten page, but Previous then heads back to "What rbr-setup.sh does" rather than "The interface". It might be advisable to check all such links.

**Assistant**

The map entry is already updated in the working tree — `docs/README.md` links `operation/01-the-interface.md` and marks it **Draft** — and the operation-layer status and `TODO-docs.md` say the page is written. If the live site still shows the old map, it needs the deploy.

The navigation fault was real and general. `ShowPage` recorded `NowSlug`, `NowNo` and `NowFolder` only after a successful fetch. When the fetch returned 404 for an unwritten page, those values still described the page before it, so the toolbar and the address belonged to the previous page — hence Previous going back to "What rbr-setup.sh does". The page now records its own slug, folder and list position **before** the fetch. A missing page keeps its place: Next from The interface goes to `operation/02`, Previous returns to The interface, and the same holds from one missing page to the next.

I added a test for that chain in `tests/docs-reader-check.js`, alongside the image checks. I also audited every relative Markdown link under `docs/`: the only absent targets are pages the map already marks **To write** (installation 01–05, operation 02–04, technical 02–06 and 08). No link points at the wrong file. The reader still reports unwritten pages rather than skipping them; if you would rather Next skipped them entirely, that is a separate change.

Verification: `node tests/docs-reader-check.js` 63/63; `python3 ./asdoc-check.py docs-reader/docs.allspeak` clean; `git diff --check` clean. No PWA or controller code changed, so the UI suite was not rerun. Run `./deploy.sh` and reload `/docs/` to publish.

## 18:43

Please recapture the home page screenshots to show the new room pill spacing.

**Assistant**

Done. The manual's screenshots have been recaptured from the current simplified interface, and `01-home-simplified.png` now shows the evenly spaced pills: equal space above the first, between them, and below the last.

The captures now use a fixed sample time of 16:53, so the states stay stable — Living Area heating, Bedroom 1 between its morning and evening periods, Bedroom 2 Off. Without that, regenerating later in the day put Bedroom 1 into its evening period and the caption no longer matched. I regenerated the room, sheet and profile screenshots in the same run so the set stays consistent; the page text is unchanged.

Verification: `node tests/docs-reader-check.js` 63/63, including the manual's screenshots and navigation chain; `git diff --check` clean. No PWA or controller code changed in this pass. Run `./deploy.sh` and reload `/docs/` to publish.

## 18:55

In Appearance there is an option to implement time-based changes. When this is not selected, can you take the gradient from the colour specified in Background Colour. I think it's using the lighter morning variant at the moment.

**Assistant**

Your reading was right in effect, though the cause was slightly different: the fixed gradient *was* built from the chosen colour, but from the **midday** stop set — 7%, 14% and 24% of it towards white, the palest of the six buckets. So the colour was present, just so faintly that the page read as near-white, which is why it looked like a light morning variant.

**Changed:** with "Time-based changes" off, the gradient now uses the **afternoon** stops — 14% / 36% / 64% of the chosen colour towards white — the set that carries the most colour at daytime levels while keeping the navy text and white cards legible. The afternoon bucket and the fixed path now share `PaintAfternoonStops`, so an edit to one cannot leave the other behind; `PaintMiddayStops` is still what 10:00–15:00 uses.

**Checked in Chromium** at phone width with orange and with slate: the gradient reads as the chosen colour, cards separate from it, and the text holds. `tests/ui/appearance.spec.js` now computes the afternoon stops for the fixed case (it had the midday values), and the full UI suite is 24/24, including the specs you added meanwhile.

**DIFF.md merged, not overwritten.** It had been rewritten for the screenshots / operation page / pill-spacing work in the same working tree, and that deploy is still pending, so I kept it and added this change plus a correction: a release is now needed because `controller.allspeak` also carries the heating-type fix from earlier. Both `git diff --check` and `node tests/docs-reader-check.js` (63/63) re-run clean.

## 19:31

The About...Manual link should open "The interface", since this is probably most relevant to the user arriving from here.

**Assistant**

Changed: the About sheet's Manual tab now opens `/docs/#operation/01-the-interface` instead of `/docs/`. Agreed on the reasoning — someone tapping Manual from inside the app is asking what the screen in front of them does, not how to fit a system.

The reader routes on the fragment and builds its page list from `docs/README.md`, where `operation/01-the-interface.md` is listed as **Draft**, so the address resolves to a real page rather than a "not written yet" notice. `tests/docs-reader-check.js` already opens that exact fragment directly and asserts the title, so the destination is covered; what I changed is the link and its two documentation comments (`about-sheet.json` and the `OpenAboutSheet` block, which now say why it points there).

`tests/ui/systems.spec.js` was asserting the old `/docs/` address, so it now asserts the new one and its header says what the control is for. Full UI suite 24/24.

`DIFF.md` merged again rather than overwritten: the pending deploy now also carries this, so `./deploy.sh --release` publishes the lot — site, `/docs/`, the PWA and the controller pack — and one reload of the phone is still all it takes.

## 19:38

1. The word "documentation" in the title of the documentation page looks awkward and can be removed.
2. In technical/01-architecture, at "How many brokers?", the URL rbrheating.duckdns.org should be removed as deployment on any scale will probably require several different brokers. Just say "in the cloud". If it's used anywhere else, the same applies.

**Assistant**

Both done.

**1. "Documentation" removed from the reader's chrome.** There were three places it appeared: the top bar's fixed label beside the product name (`$PageTitle` in `docs-reader/docs.json`), the browser tab (`<title>Documentation — Room By Room Heating</title>`), and the contents page's own H1 ("Room By Room — product documentation"). The top-bar label is gone entirely — the bar now carries the brand and the buttons, checked in a screenshot at 1000px — the tab reads "Room By Room Heating", and the heading is "Room By Room". `tests/docs-reader-check.js` asserted all three, so its checks now expect the new strings.

**2. The broker is named by role, not host.** In `technical/01-architecture.md` the cloud row now says "RBR's server, in the cloud"; the same address also appeared in `installation/06-what-the-setup-script-does.md`, so that bullet now reads "a bridge to the RBR cloud broker, in the cloud on port 8883". Nothing under `docs/` or `docs-reader/` mentions the hostname any more.

I left it where it has to be machine-accurate: `rbr-setup.sh`, `rbr-preflight.py`, `zigbee-pair.py`, `credentials.example.json`, and the engineering notes in `doc/` and `AI/` (which describe today's deployment for whoever maintains it). Say the word if you want it out of those too.

One thing I did not change, since it is not the URL: the paragraph after that table still says the cloud broker "is **shared**: it is one address that every system is pointed at". With several brokers at scale that becomes "one of RBR's brokers", if you want it generalised now.

`node tests/docs-reader-check.js` 63/63; `git diff --check` clean. Merged into `DIFF.md` — this rides the same pending `./deploy.sh --release`.

## 19:44

Actually, I don't think it's linguistically incorrect, in that every system is pointed at one address. It's just that in future it may not always be the same one. Not worth changing.

**Assistant**

Agreed — "one address that every system is pointed at" is true of any deployment; which address that is can change without the sentence becoming wrong. Left as it is, nothing changed, and the docs now read: the cloud broker is shared, and the hostname is not part of the documentation at all. The only outstanding action remains the pending `./deploy.sh --release`.

## 19:51

A question: Do we need Opertation: 02-modes-schedules-profiles.md? Does it overlap 01-the-interface.md? If there's more to add, let's do it now.

**Assistant**

Yes, keep it — but not as originally scoped. 01 now covers the modes themselves, so a second page that re-explained Timed, On, Boost, Off and Advance would mostly repeat it. I rewrote 02 as **the plan behind Timed**:

- the schedule editor, one room in one profile;
- the period card — On at, Off at, Target, Enabled, Delete — and the quarter-hour time list;
- adding, removing and enabling periods, the one-hour default for a new period, overnight periods and the 24-hour period;
- saving to one profile, and why other profiles are untouched;
- profile selection, rename, delete and duplicate, including the rule that names are the join and renames move the calendar;
- the calendar: OFF means one profile for every day; ON maps Monday–Sunday, with the active profile coming from the day.

The page links back to [The interface](01-the-interface.md) for the modes, Advance, Boost and Special actions, so the overlap is a cross-reference rather than duplicated prose. It uses the same three-room sample installation. The map now links `02-modes-schedules-profiles.md` and marks it **Draft**, and `TODO-docs.md` records two operation pages written and two left.

I also captured two new screenshots from the fixed 16:53 sample: the Living Area's Weekday schedule with morning and evening periods, and the profile sheet with the calendar active — Monday–Friday Weekday, Saturday–Sunday Weekend. The docs reader test now checks the schedules page and its images as well as the interface page.

Verification: `node tests/docs-reader-check.js` 66/66; `git diff --check` clean. The missing-page navigation test now walks from the written schedules page to the still-unwritten `operation/03` and `operation/04`. The link audit leaves only pages the map marks **To write**. Run `./deploy.sh` to publish the page and images.

## 20:06

The Special Actions - Morning start time brings up a time selector dial on Android (I don't have access to IOS to compare). Can this also be made to appear in the Schedule for event times? It allows times to be set to the minute, but I can't see that being a problem.

**Assistant**

Done — the schedule's two times are now native time fields (`input type=time`), the same control the Special actions sheet uses for its Morning start time, so Android (and iOS) open their own dial and any minute can be set.

**What changed.** `schedule-period.json`'s two `<select>`s became `<input type="time">` with ids `-start-time` / `-off-time` (they were `-start-select` / `-off-select`), styled as before. In `schedule-editor.allspeak` the symbols are now `input PeriodStartTime` / `PeriodOffTime`; `BuildTimeOptions`, the 96-option list and the "off-grid time appended to the list" fallback are gone, since a field holds any `HH:MM` the model carries. `PaintPeriodValues` writes the stored string straight in, and both change handlers read the field instead of `the selected item of`; a cleared field repaints from the model rather than leaving a blank.

**Behaviour is unchanged** except the precision: a loaded period keeps its duration when its start moves (across midnight too), a new period stops an hour after its start until its stop is picked, and **+ Add period** still starts at the end of a running period or at the nearest quarter hour — a tidy default now that the field itself takes any minute.

**Tests.** `tests/pwa-schedule-editor-check.js` now asserts both controls are `type=time` and adds a minute-precision case (07:17 → 09:17); 18/18. `tests/ui/schedule.spec.js` fills the same field in Chromium and checks the saved request. Full UI suite 24/24, `pwa-compile-check` 12/12, `asdoc-check` clean. `AGENTS.md` and `docs/operation/02-modes-schedules-profiles.md` no longer describe quarter-hour lists.

**One thing for you:** `docs/operation/images/10-schedule-editor.png` (added with the operation page today) shows the old dropdowns, so it wants recapturing — the caption and text still hold. It is in `DIFF.md` with the rest of the pending deploy.

## 20:12

docs/operation/images/10-schedule-editor.png  needs to be recaptured as the time editor has changed.

**Assistant**

Recaptured. `10-schedule-editor.png` now shows the native time fields with their clock-picker buttons, in the same two-period Living Area schedule — 06:00–08:00 at 20.0° and 17:00–22:00 at 21.0° — with the room behind it in its between-periods state.

The 02 page already describes the native picker (any minute, no quarter-hour list), so the caption and prose needed no change. The other screenshots were left untouched; this was a single-image refresh at the fixed 16:53 sample time.

Verification: `node tests/docs-reader-check.js` 66/66, including the schedules page and its images; `git diff --check` clean. No PWA or controller code changed. Run `./deploy.sh` to publish the refreshed image.

## 20:18

I'd like complete the Operation section, so let's do 03-managing-many-systems.md next.

**Assistant**

Written. `docs/operation/03-managing-many-systems.md` covers the local Systems list for an installer or estate manager:

- the list as an address book — Oak House, Willow Cottage and Flat 2 in the sample — with one current system and no primary/secondary hierarchy;
- the distinction between the controller's own System name and the local label this phone uses;
- adding a system: a local name, the MAC and the six-digit system password, with the account already provisioned on the web host;
- selecting a system and why that reloads the app;
- renaming the local label without touching the controller or the server;
- removing a system locally, and the fact that removal is not server-side revocation;
- several phones, the one-token-per-system model, and rotating the token as the only revocation path;
- the limits — no combined dashboard, no account roles, no audit trail — and a working checklist.

It has one screenshot, `12-systems-list.png`, showing the three-system list with the current row and the Select/Rename/Remove actions. `docs/README.md` now links the page and marks it **Draft**; `TODO-docs.md` records three operation pages written and one left.

Verification: `node tests/docs-reader-check.js` 69/69, including the new page and its screenshot; `git diff --check` clean. The missing-page navigation test now starts at the written 03 page and walks to the still-unwritten `operation/04`. Run `./deploy.sh` to publish the page and image.

## 20:28

That looks fine. Let's finish today with Troubleshooting.

**Assistant**

The operation layer is complete. `docs/operation/04-troubleshooting.md` covers:

- reading the app's signals: connection status, the offline tag, the warning row and Room details;
- the first checks, including **Reconnecting…**, demo mode, the wrong system, offline devices, stale sensors, low batteries, missing radiators, rooms that will not heat or stop, and the whole house being cold;
- rooms that will not heat, worked from mode and target through sensor state to the boiler;
- rooms that will not stop, with valve safety and the boundary between an app setting and a hardware fault;
- sensor and battery warnings, including the 45-minute/one-hour reading age and the first 30 minutes of a scheduled period;
- schedules and profiles when the plan seems ignored — mode, profile, calendar, clock, period, one-off changes and the On cap;
- stale data, boiler/frost behaviour and several systems;
- when to call the installer, with the safety boundary around gas, water and electrical work;
- a short installer section with `rbr-doctor.py`, `allspeak diagnose.allspeak`, `zigbee-mesh.py`, the bridge health endpoint and the controller journal.

Two new screenshots: `13-room-offline.png` shows a relay-not-responding room; `14-room-warning.png` shows a stale sensor with a low battery. `docs/README.md` links the page and marks it **Draft**; operation is now complete in `TODO-docs.md`.

Verification: `node tests/docs-reader-check.js` 72/72, including the new page and its images; `git diff --check` clean. The missing-page navigation test now uses `technical/01` → `technical/02`, since all four operation pages are written. The link audit leaves only the pages the map marks **To write**. Run `./deploy.sh` to publish the page and images.

## 20:44

One more thin tonight. I asked DSeek Chat about how to ensure that if I were to become unavailable, someone else would be able to provide support. The suggestion was:

1. Write a "succession document" that any programmer can follow
Don't just put it in the repository—write a standalone CONTINUITY.md or GOVERNANCE.md that clearly states: if you're unable to continue participating, who should do what, and in what order. Reference existing practices: some projects specify in the document the criteria for "confirming the original maintainer is unavailable" (e.g., 30 days of inactivity and no response to emails), as well as the steps for the successor to obtain repository and publishing permissions. This way, a heating engineer can see that even if you're gone, there's a clear "emergency plan," rather than a pile of code that no one can touch.

2. Make good use of GitHub's "deceased user policy" and organizational transfer mechanisms
GitHub has explicit procedures for handling account ownership transfer in the event of a maintainer's death or permanent incapacity. You can document in the repository's README or governance document: "In the event of my permanent incapacity, the designated successor may apply to GitHub Support for transfer of repository ownership in accordance with GitHub's Deceased User Policy." This way, the project won't be forever locked in your personal account.

Can we start by writing one of the suggested documents. Ask me whatever you need. I may be able to supply a contact name if that's needed.

**Assistant**

Wrote `CONTINUITY.md` as the standalone succession plan, plus the MIT licence you chose and a README pointer.

**The plan.** It names the maintainer, the successor *role* (an installer/company or trusted developer, with the named person and contact kept in a private signed addendum), the 30-day trigger after two contact attempts on separate channels, who may invoke it, and the order of action: GitHub, domain/hosting, broker, data, users, licence, then update the plan. It includes an access inventory for the repository, site, controller update channel, `rbr-users.json`, host settings, broker, mail, deployment key and backups; the GitHub pre-designated-successor, organization and Deceased User Policy routes; credential rotation and emergency-access requirements; what a successor must not do; communication; annual review; and the open items.

**The open items are deliberate:** name the successor in the addendum, place and test the emergency-access material, and pre-designate the successor on GitHub (and consider an organization owner). The plan records the role and process until those are done.

**Licence.** Added `LICENSE` under MIT with `Copyright (c) 2026 Graham`; change the holder if you want your full legal name or a company. The README now has a **Continuity and licence** section linking both, and states the GitHub transfer route.

**Assumption to check:** I used the public project contact `info@rbrheating.com` and GitHub `@easycoder` rather than your personal email. No secrets or private contact details are in the repository.

Verification: prose only, so no suite was run; `git diff --check` is clean and the local links in `README.md` and `CONTINUITY.md` resolve. Commit and push the two documents and README; no site deploy is needed for them. The pending `--release` is separate.

## 21:05

It's been suggested that my README.md should explicitly state that I am looking for a co-maintainer able to take over if need be. "This project has been maintained by an AI agent (DeepSeek). A successor only needs to be able to direct the agent to understand the code and drive maintenance, without needing to write code from scratch." Can you put together a suitable addition to the file?

**Assistant**

Added a **Looking for a co-maintainer** section to `README.md`, immediately before **Continuity and licence**. It says:

- Room By Room is currently maintained by Graham, with much of the code and documentation produced by an AI agent (DeepSeek) working under his direction.
- That makes the project dependent on one person, so it needs someone who can take over if he is no longer able to continue.
- A successor does **not** need to write the code from scratch. The practical requirement is to direct the agent, understand and review what it produces, run the project's checks, and hold or receive the accounts described in `CONTINUITY.md`.
- Familiarity with Python, Git and the command line helps; the agent is a tool, not a substitute for judgement, and a co-maintainer must review changes and be accountable for releases.
- Interested people should write to `info@rbrheating.com` with **Co-maintainer** in the subject.

I used "much of the code and documentation produced by an AI agent under his direction" rather than "maintained by an AI agent" so the human accountability stays explicit. `CONTINUITY.md` now points at the same call.

Verification: prose only; `git diff --check` clean and local links resolve. Commit/push the README and continuity change; no site deploy needed.

## 10:48

In Special Actions I want to modify "Change the morning start time". At present is keeps the off time unchanged. I want to change this to the default being to make the off time track the on time to keep the same interval. A checkbox will be ticked when the end time tracks the start time, unticked when it remains as set by the schedule.

**Assistant**

Done. The time popup now carries a checkbox, **"Move the off time too"**, ticked by default, and the controller honours it.

**PWA.** `special-time-sheet.json` gained the row (checkbox plus a sub-line: "Keeps the same interval. Unticked, the off time stays as the schedule set it"), the tagline no longer claims the off time is unchanged, and the hint is now just the "used once" fact plus the unticked caveat. `shell.allspeak` pre-fills the time as before, ticks the box unless this phone unticked it for this room (remembered beside the time as `rbr-override-track-<room>`), and sends `keepoff: yes|no` in the `Room Override` request.

**Controller.** `SetRoomOverride` stores `keepoff` on the entry when asked (an older UI sends nothing and keeps the old behaviour). `GetEffectivePeriods` shifts the morning's `off` by the same delta as the `on` when the flag is set, clamping at 23:59 rather than wrapping past midnight, and in that mode a start after the scheduled off is simply a later warm-up instead of a skip. `OverrideMorningEnded` — the expiry that clears the badge — now judges the *moved* end, so the last part of the warm-up is not pruned away early.

**Tests.** `tests/unit/unit-10-overrides.allspeak` mirrors the controller and gained cases 16–20: the moved off, a late tracked start not skipping, the midnight clamp, the request flag (and its absence), and expiry at the moved end; 31 tests / 55 checks pass there. New `tests/ui/special-override.spec.js` proves the ticked default sends `keepoff: yes`, that unticking sends `no`, and that the choice comes back on the next open. Full UI suite 26/26, unit runner 190 Python tests plus the AllSpeak suite, `pwa-compile-check` 12/12, docs-reader 72/72.

**Docs.** `docs/operation/01-the-interface.md` describes the checkbox. `DIFF.md` had been rewritten for the handover work, so I kept it and appended this release's share — the release note now says the same `./deploy.sh --release` carries both, and that the morning override needs the controller side.
