# 2026-11-19

## 10:09

I am concerned that shell.allspeak is growing too large. Is there any substantial part of it that can be moved to a separate module? I'm thinking maybe the room actions, which take place when a room pill is clicked. Or maybe the part that draws the home screen. Either would help a human reviewer by separating functionalities that aren't deeply intertwined. Any other suggestions welcome.

**Assistant**

**Short answer**

Yes — several things can move. But of your two candidates, **the room actions are the worst of the big ones and the home screen is the second worst**, and neither is where I'd start. There is a cleaner cut in the same file that I'd rank ahead of both.

**Why the boundary is expensive here**

A module is a separate program with its own globals. The existing five modules prove the pattern: `profile-sheet`, `schedule-editor` and `device-editor` each **own their DOM** (attach their own elements by id, register their own `on click` handlers) and take one dict in, one dict out. Two costs follow from that:

- **Every shell routine a module needs becomes a message**, and a message that wants a reply parks the calling program. This runtime gives a program **one reply slot**, which is exactly why `OnMapReceived` holds a map while a sheet module is open (`FlushPendingMap`, the 2026-10-24 bug).
- **Every value that both sides mutate must be copied across** — and `element N of …` / `put … into` aliasing has already cost this project two live rooms. A render cluster that only *reads* state is cheap; an action cluster that mutates `RoomsList`, `Map.profiles` and `PendingRooms` is not.

Measured against those two costs, here is what the file actually contains (shell.allspeak is 5,300 lines / 3,953 code, 151 labels; the next largest module is 984):

| Candidate | Code lines | Boundary crossing | Verdict |
|---|---|---|---|
| **Background gradient + Appearance sheet** | 377 (+59 decls) | **4 names**, two of them internal scratch; 10 handles, 9 ownable | **Best cut** |
| **Systems + About sheet** | 282 (+21 decls) | 6 names (`MAC`, `Token`, `DemoMode`, `ConfirmFlag`, `Response`, row template) | Good, second |
| **Summary card** | 145 (+29 decls) | reads `RoomsList` + a few fields, returns nothing | Clean but small |
| **Room actions** | 609 (+21 decls) | **25 names, mostly bidirectional**; 23 handles; 10 call sites into `PostUiRequest`/`AfterStateChange` | Poor — anti-pattern |
| **Home screen build/refresh** | 523 | calls out to 8 clusters and builds all the sheet chrome | Worst — it is the hub |
| **Room row render** | 268 (+42 decls) | 1 out; but fires per room per map push | Hot path |

**On your two**

**Room actions.** `WireRoomInteractions` through `LowercaseModeForServer` is one *functionality* but not one *boundary*: it mutates `RoomsList`, `Map.profiles`, `PendingRooms` / `PendingUntil`, `ExpandedIndex`, `BoostPanelOpenIndex`, the `Gesture*` set; it calls `PostUiRequest` and `AfterStateChange` ten times, opens four sheets, and calls `ApplyMapToRooms` for the Advance reprojection. The module would need to send the room list and the map in **and get both back**, on every tap — and each tap would park the shell on a reply while a map push can arrive. That is the shape the AllSpeak idiom page explicitly names as "state that's shared bidirectionally"; it reads well in a table of contents and badly in a debugger.

If that is the part you want separated, the version that does work is a larger unit: let a module own the rooms **model** as well as the expansion and actions — send it the projection, get a `uirequest` back for the shell to ship. That is a different, bigger refactor (and would probably also absorb the rowwise render).

**Home screen.** `BuildHomeScreen` is not "drawing the home" — it builds the main column, *and* renders the sheet chrome, *and* renders the Menu / Backup / Journal sheets, *and* forks the three ticks, *and* delegates to `BuildActiveHome`. It has 26 call sites into the sheet openers. Extracting it would leave the shell asking a module to build the structure the shell then hand to other modules. The genuinely separable part is `RenderRoom` + `ResolveRoomStateColour` + `ResolveChipStyle` (268 code lines), but that is the per-room-per-push hot path — the pattern the idiom page says to avoid.

**What I'd actually recommend**

1. **Background gradient + the Appearance sheet** (~436 lines out). One sentence: *"the time-of-day background and the palette that drives it."* It takes `MixHex` / `HexToRgb` / `RgbToHex` / `HexNibbleOf` — pure functions a reviewer can check in isolation — out of a file that is otherwise event routing; it owns the Appearance sheet's DOM and handlers the way the other three editors do; its only real inputs are `SheetsReady` and the view mode, and it already has a natural driver (`BackgroundTick`). One nuance: `BoostTick` and `ClockTick` sit in the same region but are **not** background — leave them in the shell (they reach into rooms and the summary).
2. **Summary card** next (145 lines, nearly pure: data in, DOM out).
3. **Systems + About** third (282 lines) — though note it is two halves: the systems *store* feeds boot (`LoadSystems` sets `MAC`/`Token` before the credential fetch), so the module would hand those back to the bootstrap, or the store stays and only the About sheet moves.

The parent-owned smaller sheets (Special override, Info, System, Backup, Journal, Outside) are each genuinely independent and already the same shape as the extracted modules — but individually they are 30–175 lines, so they read better as a follow-up than as the first move.

**Cost of doing it**

Whichever we take: a sixth file in `new-ui/resources/allspeak/`, added to the hardcoded set list in `tests/pwa-compile-check.js:210` (the readdir compiles it automatically), doc blocks carried across and re-hashed with `asdoc-check.py --write`, `sw.js` needs nothing (it precaches only `shell.allspeak`), and `deploy.sh` copies the whole `new-ui/` tree. Verification is `tests/unit/run-unit-tests.sh`, `node tests/pwa-compile-check.js`, and the `pwa-*-check.js` / Playwright specs that touch the screens moved.

One option worth flagging: the pinned runtime **does** implement `with` / `import` shared references (I checked the bundle), which would make the room-actions cut far cheaper by sharing `RoomsList` live. Nothing in this repo uses it, so I'd want a spike before betting a refactor on it.

## 10:27

Refactor: Background gradient + Appearance sheet (recommended)

**Assistant**

Done. `shell.allspeak` is 4,808 lines (was 5,300) and the Appearance feature now lives in `new-ui/resources/allspeak/appearance.allspeak` (596 lines, ~380 of them code).

**What moved.** The ten-colour palette, the hex maths (`MixHex`, `HexToRgb`, `RgbToHex`, `HexNibbleOf`), the six hour buckets, the stored colour and time choices, `BackgroundTick`, and the Appearance sheet's swatches / hex field / time checkbox — plus the 59 declarations that only they used.

**What stayed, and why.** The shell still renders the sheet's layout, shows and hides it (`HideAllSheets` needs the element), sets the title, and owns the two view pills and Done: the pills rebuild the home and Done closes the shell's chrome, so those are the shell's operations rather than the module's. The module paints the pills; it does not switch the view.

**The interface is deliberately fire-and-forget.** Three messages, never a send that waits: `attach` (the layout is in the DOM — claim the controls), `open`, and `view`. That matters here specifically: a blocking send parks the shell and takes this program's one reply slot, which is how a map push gets stranded. Before relying on it I probed the pinned runtime directly — `send X to Module` with no `and assign reply` is delivered and handled, and the module's handler ran before the next blocking send. Nothing else in the repo uses that form, so it is worth knowing it works.

**One ordering constraint kept.** The module loads at bootstrap where the palette used to be initialised, and `run` does not return until it has painted `#app`, so the first frame still has its gradient. The sheet's layout is still fetched and rendered by the shell inside `BuildHomeScreen`, after `sheet-content` exists, and the module is told with `attach`.

**Verified.** `node tests/pwa-compile-check.js` 14/14 across six modules; all twelve `tests/pwa-*-check.js` pass; `npm run test:ui` 30/30 including both `appearance.spec.js` tests; the published `asdoc-check` reports 0 errors and 122 warnings, down from 129.

**What you need to do:** `./deploy.sh`, then reload the app once on the phone. No controller change, no version bump, nothing restarts.

**Next, if you want it:** the summary card (145 lines, almost pure render) is the cheapest remaining cut, then Systems + About (~300 lines). The room actions are still the expensive one, for the reasons in the analysis above.

## 11:01

Do the two you suggest, then we can consider whether to go further.

**Assistant**

Done — both. `shell.allspeak` is 4,207 lines (it was 5,300 at the start of this session), and two more modules now sit beside `appearance.allspeak`:

- `status.allspeak` (345 lines) — the summary card and the top bar's live readouts: date, profile, outside reading, frost badge, demand flame, system name, and the aggregate "N rooms calling for heat" title.
- `systems.allspeak` (438 lines) — the device's systems list, its storage and migration, the `mac` / `token` boot reply, and the whole About sheet including the pairing flow.

**What the boundaries look like.** The shell sends `status` a snapshot dict (`mount`, `paint`, `unmount`) and keeps no copy of the aggregates or the frost flag — that is the point: the card and the banner both read one computed flag, so they cannot disagree. The `systems` module is asked once, at boot, and answers with the current `mac` and `token`; that is the only waiting send in the three, and it waits because the credential fetch cannot start without the answer. Everything else is fire-and-forget, so nothing parks the shell and no map push is stranded behind a reply. The shell kept what is chrome in every case: it renders each sheet's layout, shows and hides it, sets the title, and owns the controls that rebuild the home or close the chrome.

**One finding, not fixed** (the review-while-documenting rule): `ActivateBoost30`, `ActivateBoost1h`, `ActivateBoost2h` and `CloseInfoSheet` are labels with no caller anywhere in `shell.allspeak`. They are dead code that predates this change — the boost buttons go through `ApplyBoost`, and the info sheet closes with the shared chrome. Say the word and I will remove them.

**One gap worth knowing.** `tests/pwa-compile-check.js` compiles but does not link: `gosub` targets are resolved at run time. During this change a section cut took `ToTenths` with it, the compiler stayed silent, and the simple-view spec caught it the moment it tapped a mode button. I have checked every `gosub` / `fork` / `go to` target in all eight modules since, and they all resolve — but the check is worth adding to `pwa-compile-check.js` if you touch this area again.

**Verified.** `node tests/pwa-compile-check.js` 16/16 across eight modules; all twelve `tests/pwa-*-check.js` pass; `npm run test:ui` 30/30; the published `asdoc-check` 0 errors and 113 warnings, down from 129 at the start.

**What you need to do:** `./deploy.sh`, then reload the app once on the phone. No controller change, no version bump, nothing restarts.

**Going further.** The remaining big one is still the room board (rows, expansion and actions together, owning `RoomsList` and `PendingRooms`), which is roughly 900 lines and the only cut left that changes where state lives rather than just where code lives. The smaller independent sheets (Special override, Info, System, Backup, Journal, Outside) would each be a tidy 100–175-line module but add boot fetches, so I would do them only if a particular one keeps getting in the way of reviews.

## 11:05

We'll leave it there for now. The file is at a more reasonable size.

**Assistant**

Good place to stop. `shell.allspeak` is 4,207 lines, down from 5,300 — about a fifth of it moved into three modules that each have one stated job, and everything still passes: 16/16 compiles, all twelve node checks, 30/30 in the browser.

When you are ready to ship it, `./deploy.sh` then one reload on the phone covers all three migrations. Nothing on the controller changes and the version does not move.

Two things are parked rather than done, for whenever you come back to this: the four dead labels (`ActivateBoost30`, `ActivateBoost1h`, `ActivateBoost2h`, `CloseInfoSheet`) still have no caller, and `tests/pwa-compile-check.js` still cannot see a `gosub` target that no longer exists — worth a linker check there before the next cut.
