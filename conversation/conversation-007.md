# 2026-09-22

## 15:59

A comment made by my partner revived a thought I'd had some while ago. The timing schedule for a room is a fairly inflexible entity. A common situation occurs where an early start is called for, on a single day and to deal with this means reprogramming the morning heating on time for that room, then remembering to put it back later in the day. There has to be a more friendly way.

What I'm considering is a button in the expanded room box, that calls for one of any number of special actions. Initially there's only one I can think of; to specify a different start time for the following morning. I would expect to see a popup that asks for the new time. If this is later than the off time corresponding to the current on time, the entire period will be skipped; otherwise the heating for that room will come on at the time requested and the off time will be unchanged. The action will only take place for the following morning; once deal with it reverts to the schedule.

Can you consider this, suggest a better implementiton if there is one, and plan how to implement it. Don't write any code just yet.

**Assistant**

Read the controller's period logic, the room map format, the new PWA's expanded room box and the schedule editor first. Short version: the idea is right, and the codebase already has almost all the machinery for it — the one thing to avoid is *editing the schedule*.

**1. Where this sits in the existing design**

- A room's schedule is `periods[]` — `{on, off, temp}` — held per room per profile in `map.json`. (The old `events[]` form is legacy; the controller prefers `periods`.) `ConvertTimeToInt` anchors every schedule time to *today's* midnight, and `MainLoop` already detects the day rollover (`today is not TodayWas`).
- The controller is the single writer of `map.json`, and it *already* stores user-set, self-clearing, transient state on the room: `advance` (`A`/`-`), and `until` + `prevmode` + `boostperiod` for a boost. These persist to disk on the once-a-minute save tick and are cleared by the controller when they lapse. Your feature is a new member of that family, not a new subsystem.
- Read path: `ProcessRoom` → `FindCurrentPeriod` (which period contains `now`, wrap-aware) → `ApplyPeriodsAdvance` → `Target`. `GetNaturalPeriod` is the side-effect-free twin used by the boost latch.
- The expanded room box exists only in the new PWA (`new-ui/resources/webson/room-row.json`: Mode / Target / Advance / Boost / Edit schedule). The legacy UI has no expansion, so this is a PWA feature.
- UI→controller actions are `uirequest`s. Per-room mode changes use the `Operating Mode` action; schedule edits ship the *whole* `Update Profiles` (a wholesale replacement of `Map.profiles`). There is no generic "special action" channel yet.

**2. Suggested better implementation — stored one-off overrides, applied at read time**

The key decision: **do not touch `periods`.** Instead store a dated override and let the existing period logic read *through* it:

- At arm time the controller resolves and stores an override: the room, the calendar date it applies to (`YYYY-MM-DD`), and the requested `on` time. Location: a **top-level** `overrides` dictionary on `Map`, keyed by room name — *not* a field inside each profile's room.
- At read time, a new helper (used by both `FindCurrentPeriod` and `GetNaturalPeriod`) builds the *effective* period list for today: if an override matches today's date for this room, substitute its `on`; if the substituted `on` is at/after that period's `off`, drop the period entirely (the skip case). Everything else (advance, boost latch, wrap-around handling, background target) keeps working unchanged.
- Auto-revert is then free, not a feature: the override only matches on its own date. The day-rollover branch in `MainLoop` prunes entries whose date has passed (and marks the map changed), which is also what clears the armed badge in the UI.

Why top-level rather than per-room-in-profile: (a) it makes the override *cross-profile* — arm "Kitchen, 08:30" and it works whether tomorrow resolves to Monday-Friday or Weekend; (b) it survives `Update Profiles` / `Update Rooms`, which replace `Map.profiles` wholesale. Store it inside a profile room and the obvious sequence — arm the override, then open the Schedule sheet and Save a few minutes later, before the UI has refreshed — silently wipes it.

**3. Ambiguities to settle**

- "Following morning" needs a definition. Next occurrence of the day's first period (today's if it hasn't started yet, else tomorrow) is the forgiving reading; strictly-tomorrow is the literal one. I'd resolve the date once at arm time and store it, so the meaning can't drift.
- "The morning" period. Use the period with the earliest `on` that day. Guard the wrap-around case (`on` later than `off`), where "morning" and the off-time comparison stop meaning what you expect.
- Clamp boundary: is the period skipped when the new `on` *equals* `off`, or only when it's later? I'd skip on `>=` (a zero-length period is the same as no heat).
- Interaction with mode and the other overrides: the room may be `on` / `off` / `boost` tomorrow morning, or have Advance engaged. My recommendation: the one-off is a *schedule* tweak, so it applies in `timed`; a deliberate `on`/`off`/`boost` still wins. Advance and the morning override can collide — worth deciding whether the override cancels Advance or refuses to arm.
- Two edits to the same morning should replace, not stack.

**4. Better shape than a time popup**

The common case is "let them sleep in", where a relative nudge is friendlier and needs no arithmetic on the off time: an `[+30 min] [+1 hr] [custom…]` row, showing the resulting absolute time, plus the custom-time popup you described. And since the skip case is really a distinct intent, I'd surface **"Skip the morning warm-up"** as its own named action rather than making the user discover it by typing a time past the off time. Both are the same stored override under the hood.

Equally important: **show the armed override on the room row** ("Tomorrow from 08:30", tap to cancel), and make the subline projection reflect the overridden start. That is the actual answer to "remembering to put it back" — visibility plus automatic expiry, so nothing has to be remembered at all.

**5. Implementation plan (no code yet)**

Controller (`controller.as`):
- New top-level store, loaded/saved with the map (no new file).
- `GetEffectivePeriods` helper; `FindCurrentPeriod` and `GetNaturalPeriod` switch to it.
- New `uirequest` action (e.g. `Room Override`) with set/clear ops, validation (room exists, time parses, date is sane), then `ForceUpdate`.
- `MainLoop` day-rollover: prune expired overrides, mark the map changed.
- `SetRelay` / `ProcessRoom` unchanged.

UI (new-ui):
- `room-row.json`: a `$SpecialBlock` in the expansion, plus an armed pill/badge; `shell.as`: open-sheet, arm/clear handlers, optimistic local update, `PostUiRequest`; a small `special-sheet.json` (and a time-stepper reusing the schedule editor's pattern, or a native time input as the device editors already use).
- `map-to-rooms.as`: surface the override on the room entry and fold it into the `nextTime` projection.
- `SyncCurrentRoomToMap` must not disturb the top-level store.

Tests:
- Extend `tests/unit/unit-04-periods.as` (the mirrored period logic) with override cases: new-on honoured, `on >= off` skips the period, expiry after the date, no effect on other periods, wrap-around guard.
- Add an ops spec alongside `tests/ops-01-boost-advance.spec.js` for the end-to-end arm/fire/revert path through the simulator.

Risks: DST (keep the date + wall-clock comparison rather than adding 86400000), the wrap-around period, and profile-save races (all mitigated by the top-level store).

I asked three questions before writing the detailed plan.

## 16:01

The user answered:
- Mechanism: Generic store + two actions now
- Occurrence: Next occurrence of the day's first period
- Entry style: Absolute time popup only

**Assistant**

Locked in: a generic dated one-off override store, two actions shipped now ("Change tomorrow's morning start" and "Skip the morning warm-up"), resolved against the next occurrence of the day's first period, armed through an absolute-time popup.

**A. Data model** — a top-level `overrides` dictionary on `Map`, a sibling of `profiles`, keyed by room name. Each entry is `{kind, date, on, was, at}` where `kind` is `start` or `skip`, `date` is the resolved `YYYY-MM-DD` the override applies to, `on` is the requested start time (absent for a skip), `was` is the scheduled `on` at arm time (for display and for explaining the clamp), and `at` is the arm timestamp. Keyed by room name deliberately: it makes the override cross-profile, and it survives `Update Profiles` and `Update Rooms` because both replace `Map.profiles` wholesale. A per-room-in-profile field would be wiped by the obvious sequence — arm the override, then Save the Schedule sheet before the UI has refreshed. Multiple entries per room are allowed (today and tomorrow), but the UI only ever arms the next morning; the controller consults the entry whose `date` is today. No new file: it rides in `map.json` on the existing once-a-minute save tick.

One trade-off to state plainly: we store the *request* (`on`) and evaluate the clamp at fire time, so a schedule edit between arming and firing still governs the `off`. Freezing the resolved effect at arm time would be more predictable but makes the override stale the moment the schedule changes. I recommend the former, with the UI showing the resulting time at arm time so the consequence is visible.

**B. Controller** — new routines in `controller.as`:

1. `GetEffectivePeriods` becomes the single source of truth for "what periods apply today": the room's `periods` plus any matching override, with the day's first period's `on` replaced, or that period removed. `FindCurrentPeriod` and `GetNaturalPeriod` both switch to it; nothing else changes, so advance, the boost latch, wrap-aware containment and the background target all keep working unchanged.
2. `IdentifyMorningPeriod` picks the day's first period (smallest `on`) and explicitly refuses a wrap-around period (`on` later than `off`, e.g. 22:00–06:00) — it is not a morning period.
3. `ResolveOverrideDate` implements "next occurrence": today if `now` is before today's first `on`, else tomorrow, stored as a date string.
4. The clamp, at fire time: if the requested `on` is at or after that period's `off`, the period is dropped. I'd use `>=` (a zero-length period is no heat).
5. A new `uirequest` action, `Room Override`, with `op` (`set`/`clear`), `kind` (`start`/`skip`), `time` (`HH:MM`), and `Room`. The controller resolves the date itself, validates (room exists, time parses, a morning period exists), writes `Map.overrides` and calls `ForceUpdate`. It uses the existing "UIRequest rejected: …" logging style and refuses rooms with no `periods` or only a wrap-around period.
6. Day-rollover pruning in `MainLoop`: drop entries whose `date` is past, and mark the map changed if anything went — that is what clears the armed badge on every connected UI.
7. `ProcessRoom` and `SetRelay` are untouched: a room explicitly in `on`/`off`/`boost` keeps that mode, and the override only shapes `timed`.

Precedence I'd write into the doc block rather than ask about: arming the override cancels any engaged Advance for that room — one morning, one intention — and the UI's Advance control is hidden for the target morning. Boost already wins over `timed` and expires on its own, so it is left alone.

**C. UI (new PWA)** — `room-row.json` gains a `$SpecialBlock` in the expansion (under Boost, above Edit schedule) with a full-width `Special actions…` button, plus an armed indicator on its own line under the subline (reusing the `$WarnRow` pattern so it never competes for space), reading `Tomorrow: heat from 08:30` or `Tomorrow morning skipped` in accent, tappable to cancel. That indicator is what actually removes the "remember to put it back" burden; automatic expiry does the rest. Two new webson files: `special-sheet.json` (the action list — the two actions, each with a subtitle drawn from the projection such as `Usually on at 06:30`; a `Cancel the override` row replaces them once armed) and `special-time-sheet.json` (the popup — a native `input type="time"` prefilled with the current morning `on`, plus OK/Cancel; the device, outside and system sheets already use bare inputs, and the schedule editor's stepper is the fallback if native time inputs prove inconsistent). In `shell.as`: `OpenSpecialsSheet`, `ArmMorningStart`, `ArmMorningSkip`, `ClearOverride`, each doing an optimistic local patch then `PostUiRequest`, reconciling on the next map push — the same shape as `ToggleAdvance`/`ApplyBoost`. In `map-to-rooms.as`: attach the matching override to each room entry and fold it into the schedule projection so the subline reads `Tomorrow from 08:30` rather than the plain schedule. `SyncCurrentRoomToMap` is left alone; the override is top-level and never travels in `Update Profiles`.

**D. Tests** — extend `tests/unit/unit-04-periods.as` (the mirrored period logic) with `GetEffectivePeriods` cases: new `on` honoured; `on == off` skips; `on > off` skips; an earlier `on`; a date that doesn't match changes nothing; a wrap-around period is never the morning. Add an ops spec beside `tests/ops-01-boost-advance.spec.js` driving the simulator: arm, fire at the new time, revert the following day; the skip case produces no heat that morning; cancel restores the schedule; a profile switch on the target day still honours it.

**E. Docs** — `AI/MAP_FORMAT.md` gains the top-level `overrides` key and schema (it is controller-written, but uniquely it lives outside `profiles`); a short `doc/` note describing the special-actions surface so the next action is a small addition rather than a new design.

**F. Sequence** — (1) `GetEffectivePeriods` + `IdentifyMorningPeriod` wired into the period lookups, with unit tests; (2) the `Room Override` action + rollover pruning; (3) the simulator ops spec; (4) UI sheet and time popup; (5) armed indicator and projection; (6) docs, `python3 asdoc-check.py --write controller.as`, deploy.

**G. Left to settle while implementing** — confirm the AllSpeak date primitive for the day key against `learn/reference/` rather than assuming (the repo currently uses `today` and `weekday`); decide whether pruning also drops entries for rooms absent from every profile (I would keep them until their date passes — they are inert); and whether the armed line should also appear on the collapsed rest row (I would keep it to the expansion plus the subline projection).

## 16:20

Since this kind of event may happen more thn once (but not frequently enough to justify a new profile) it would be nice if the time popup comes preloaded with the last such time requested (defaulting to the current start time). With that in mind, go ahead.

**Assistant**

Built it, and verified it. Summary of what changed and how I checked it.

**Controller (`controller.as`)** — a top-level `overrides` map keyed by room name; `LoadRoomPeriods` (copies the room's `periods`, because AllSpeak collections are held by reference and an in-place edit would rewrite the stored schedule), `GetRoomOverride`, `GetEffectivePeriods` (replaces the morning `on`, or drops the period for a skip / a start at-or-after that period's own `off`), `IdentifyMorningPeriod` (earliest `on`, excluding wrap-around), `ResolveOverrideDate` ("next occurrence": today if the period has not begun, else tomorrow), `SetRoomOverride` / `ClearRoomOverride`, and `PruneOverrides` on the midnight roll-over. `FindCurrentPeriod` and `GetNaturalPeriod` now read the effective list, so Advance, the boost latch and the background target all keep working. New `Room Override` uirequest with `op` / `kind` / `time`, plus lowercase aliases.

**UI (new PWA)** — `room-row.json` gains a Special block (button plus an accent-coloured override row with Cancel); new `special-sheet.json` (change the morning start / skip the morning warm-up / cancel) and `special-time-sheet.json` (a native time input); `shell.as` gets `OpenSpecialSheet`, `PaintSpecialSheet`, `SpecialChooseStart` / `SpecialChooseSkip`, `PrefillSpecialTime`, `SaveSpecialTime`, `ArmSpecialOverride`, `ClearSpecialOverride`, `FormatOverrideText` and `TodayDateKey`; the subline carries the armed override so it is visible while the row is collapsed. `map-to-rooms.as` surfaces the raw override fields plus `morningOn`.

**The preload you asked for** — the time popup reads `rbr-override-time-<room>` from browser storage, falling back to the room's current scheduled morning start (`morningOn`), then to 07:00. It is per room and browser-local: a convenience for the household's own phone, not system state, so it deliberately does not travel in the map or reach the controller. Arming remembers the choice, so the second and later uses default to the last time requested.

**Verification** — the controller compiles and the doc-block hashes are refreshed; a new mirrored unit suite `tests/unit/unit-10-overrides.as` covers the effective-period rules, the "is a copy" guard, the arm/validate/clear/prune paths (17 tests, 33 checks); the full unit suite is 61 tests / 164 checks, all green; the UI scripts compile against the real JS runtime; and a headless Chromium run of the actual PWA in demo mode walks the whole flow — expand, Special, sheet, prefill 06:30, arm 08:15, override row and subline, reopen and see 08:15 remembered, skip, cancel — all pass.

**One real bug found and fixed** — I also drove the controller's override routines directly (extracted verbatim from `controller.as`) rather than only a mirror, which caught `SetRoomOverride` accepting a `start` request with no `time`: `OverrideOn` is a script-level global, so a stale value from an earlier request satisfied the "time required" check. It now clears that variable at the top, and there is a regression case in the unit suite.

Two deliberate deviations from the earlier plan. The "last requested time" is browser-local rather than stored in the map (stateful in the controller only if you want it shared across devices). And I did not add the simulator ops spec: `tests/run-ops-tests.sh` needs mosquitto and a Playwright browser, neither available here, so the headless PWA run stands in for it. The controller's own end-to-end path is still unexercised against a live broker — worth a quick click-through on the box before release, and `./deploy.sh --release` bumps the version when you are ready.

## 16:55

I think there's space to put Special actions alongside Edit schedule, to compact the display a little. The latter doesn't need a chevron so that can go too. And the titles 'ADVANCE' and 'SPECIAL' aren't really needed as they're in the text of the buttons. 'MODE' can stay.

**Assistant**

Done — all three in `room-row.json`, no script changes needed.

- **Side by side.** The expansion's tail is now one `$ActionRow` (flex, 10px gap, 18px top margin) holding `$SpecialBtn` and `$EditScheduleBtn`, each `flex: 1` with `min-width: 0` so they split the width evenly. The old full-width `$EditBtn` block is gone; `$OverrideRow` moves up to sit directly under the row, unchanged.
- **Chevron gone from Edit schedule.** Dropped the `$Label`/`$Spacer`/`$Chev` stack and made it a plain centred button, matching Special actions.
- **Labels gone.** `$AdvanceLabel` and `$SpecialLabel` removed, and their content arrays trimmed. The advance button picks up the 16px top margin the label used to provide, which keeps the spacing right for the Timed/no-boost case where the target tile is hidden and the advance button is the first thing under the mode pill. MODE stays, and so does BOOST — its duration chips (Off / 30 min / 1 hr / 2 hr) don't say "boost" on their own.

Element ids are untouched (`room-<i>-advance-block`, `-special-btn`, `-edit-schedule`, `-override-row`, `-override-text`, `-override-cancel`), so `WireRoomInteractions` and `PaintExpansion` are unaffected.

Verified in the headless Chromium run, with the layout assertions added: both buttons on one row (same y), equal width (173px each), neither clipping its text, the advance block and action row holding nothing but their buttons, no leftover Advance/Special labels, the MODE label still present, and the whole arm/reopen/skip/cancel flow plus "Edit schedule still opens the schedule editor". Screenshot checked by eye.

One pre-existing thing I noticed while reading, and did not touch: the comments in `shell.as` and `design/handoff/slices/07-room-row-expansion.md` both claim the rest row has a chevron that rotates 180° on expand. `room-row.json` has no chevron in `$Rest` — that slot holds the info button instead, and `ToggleExpansion` never rotates anything. The doc/code disagreement is unrelated to this change, so I have left it for you to decide on.

## 17:03

Yes, that's a lot tidier.
Please clean up the issues relating to chevrons.

**Assistant**

Asked first, because it was a real fork: the design handoff and the React prototype both put a chevron on the rest row, but the port replaced it with the info button. You chose to leave the UI alone and amend the docs, so that is what I did — the port's docs and comments now describe what was actually built.

Changed:

- `design/handoff/slices/03-room-row-rest.md` — the layout diagram's `[ v ]` is now `[ i ]`, and the "Chevron: 16 × 16" bullet is replaced with the info button it actually has (16 × 16 `info` glyph in `color.text.disabled`, 28 px circular button, hidden for sensor rows), stating plainly that the rest row carries no chevron. The "Done when" list no longer says "Outside (sensor, no chevron)".
- `design/handoff/slices/07-room-row-expansion.md` — the rest-row chevron/rotation sentence is gone, the "Chevron rotates 180° via `motion.chevronRotate`" bullet is gone, and the Edit schedule bullet no longer claims an edit icon or a right chevron (it now reads "centred label … no leading icon and no chevron" — the edit icon was never built, a claim that predated this session).
- `design/handoff/README.md` — dropped "Row chevron rotates 180° in 0.25 s" from the Motion list; the rest-row layout diagram and its "chevron 16 px" line now describe the info button; the Outside sensor annotation and the edge-case list say "no info button"; the Edit schedule summary lost "Edit icon + right chevron" and no longer says "full-width".
- `design/handoff/TOKENS.md` and `new-ui/resources/css/tokens.css` — removed `motion.chevronRotate` / `--motion-chevron-rotate`. Nothing consumed either: the only thing that described was the rest-row chevron. (Verified: the profile-sheet calendar chevron flips via an inline `transform`, not this token.)
- `new-ui/resources/as/shell.as` — the two comments that asserted sensor rows "have no chevron" now say "no info button", and the `WireRoomInteractions` doc notes that non-sensor rows carry no chevron either.

Left alone deliberately: every chevron that really exists — the profile pill, the menu rows, the calendar day rows and the device-editor rows — plus their specs in slices 04, 05 and 06 and the four README sections that describe them. Also left alone: `design/app.jsx` and `design/Room By Room.html`, the React prototype, which still shows the rest-row chevron. It is the reference artefact for the port rather than the spec of record, so I did not edit it; say the word if you want it brought into line too.

Re-verified: `shell.as` doc-block hashes refreshed (0 errors, 0 warnings), all five new-ui scripts compile, the Webson JSON is valid, the unit suite is still 61 tests / 164 checks green, and the headless PWA run passes unchanged — so this was a docs-and-comments change with no behavioural effect.

Two things I found while working through this, both flagged rather than fixed, since fixing either means changing the UI:

- The rest row now has no expand affordance at all. With no chevron, the only cue was meant to be the raised shadow — and `--shadow-card-raised` is defined in `tokens.css` but never applied; `shell.as` never sets the card's `box-shadow`, so the card looks identical whether open or closed. The row does have `transition: box-shadow 0.2s` in `room-row.json`, so the intent was clearly there. Worth a small follow-up, and now more so, because the chevron is gone.
- `profile-sheet.as` does rotate the calendar chevron, but through an inline `transform` with no transition, so it snaps rather than animating.

Separately: I notice `version` was bumped to `2609221657` at 16:57, which I did not do — presumably your `./deploy.sh --release`. I have left it as it is. All the code changes landed before then, so a release at that moment would have packaged everything; only this doc/CSS tidy-up came afterwards.



