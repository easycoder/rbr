# 2026-09-26

## 10:57

Following user feedback, I would like each schedule period to carry an enable flag, that if not set causes that period to be ignored. If the flag is absent the period wil be treated as enabled (avoids updating the entire map). Flags will be added to the map when the schedue is edited. In the UI, the flag will appear to the left of 'Delete period' as a checkbox.

**Assistant**

Asked one scope question first, because the enable flag changes the shared map format and two live editors write `periods[]` back to it. You chose **both the new-ui PWA and the desktop app**, so both got the checkbox; the legacy web UI was left alone (its schedule editor was removed some time ago and now just points at the new UI).

**Data model.** A period is `{on, off, temp}` plus an optional boolean `enabled`. A period with `enabled: false` is ignored everywhere the schedule is read; an absent flag means enabled, so no map has to be rewritten. Both editors write the flag explicitly on every period when a schedule is saved.

**Controller.** `LoadRoomPeriods` now skips periods flagged `enabled: false` as it copies them into `PeriodList`, so every reader — `FindCurrentPeriod`, `ApplyPeriodsAdvance`, `GetNaturalPeriod`, `IdentifyMorningPeriod`, the one-off override — ignores them for free, with one filter in one place. Added two variables (`PeriodSourceCount`, `PeriodIncluded`) and split the source count from `EventCount` (which is now the count of periods that actually apply).

**new-ui.** `schedule-period.json`'s `$DeleteBtn` became a `$FooterRow` holding the Enabled checkbox (plus a matching `label`) to the left of the Delete period button. `schedule-editor.as` carries the flag through clone and save, declares/attaches an indexed `input PeriodEnableBox`, paints it (set the `checked` attribute for enabled, remove it for disabled), and toggles the stored value on `change`. `map-to-rooms.as` filters the room's periods once into `ActivePeriods` so the subline projection and the morning-start lookup skip disabled periods.

**desktop.** `rbrwidgets.py`'s period card gained a `QCheckBox('Enabled')` in the footer next to Delete, emitting `{'event':'toggle','period':i,'enabled':bool}`. `rbr-desktop.as` clones/saves the flag and handles the `toggle` event via a new `ToggleSchedulePeriod`.

**Docs.** `AI/MAP_FORMAT.md` documents `periods[].enabled`. Per the `AGENT.md` note you added, I also wrote `DIFF.md` at the root (action-first, rewritten, this change only).

**Verified:** the unit suite is 63 tests / 167 checks green (new cases cover a disabled period dropped, an explicit `enabled: true` kept, and an all-disabled room); all five new-ui scripts and `controller.as` / `rbr-desktop.as` compile; a jsdom render of the real `schedule-period.json` shows the checkbox, its label and the Delete button; focused jsdom probes confirm the clone/save/toggle conversions and the filter produce proper JSON booleans and the right membership; and the desktop widget tests (the existing one plus a new checkbox probe) pass, with absent→checked, `false`→unchecked, `true`→checked.

**One thing I fixed while here** — in `ProcessUIRequest`'s Operating-Mode `on` branch, the code indexed the room's *raw* `periods` with `PeriodActive`, which is an index into the *effective* list; that mis-picked the period whenever an override (or now a disabled period) had shifted the list. It now uses the effective list `FindCurrentPeriod` already loaded.

Two choices worth flagging: the flag is a real JSON boolean named `enabled` (the project otherwise favours string flags, but a boolean is what "not set vs absent" describes, and it round-trips cleanly through both runtimes — verified); and I gave the checkbox an "Enabled" caption rather than leaving it bare, since the card already labels its other controls. Say the word if you'd rather it were a bare checkbox.

[code omitted]

## 11:17

I added the DIFF note following its inclusion in the main AllSpeak project. I was about to ask you to action it.
 
I've depoyed with --release. While waiting for that to happen I'd like to ask for disabled periods to be non-editable, possibly greyed out or with a grey background behind their controls

**Assistant**

Done in both editors. A disabled period's On-at / Off-at / Target rows are now greyed out and inert, while its Enabled checkbox and Delete period button stay live — so you switch a period back on by ticking the box, or remove it with Delete, rather than nudging its times.

I went with greying out (the codebase's own "inactive" idiom) rather than a grey background block: the rows are set to `opacity: 0.45`, matching how `profile-sheet.as` dims an inactive profile body. For the inert part I set `pointer-events: none` on the three rows, so the steppers stop receiving clicks. If you'd rather see a grey panel behind the controls, that's a one-line change in the same place.

**new-ui.** `schedule-period.json`'s `$TimeRow` and `$TempRow` gained ids (`-time-row`, `-temp-row`; `-off-row` already existed), so each card's three rows can be dimmed as a group. In `schedule-editor.as`, `PaintPeriodEnabled` now paints both the checkbox and the rows (opacity + pointer-events), and `TogglePeriodEnabled` calls it after a toggle so the dimming tracks the box without a full re-render.

**desktop.** `_buildPeriodCard` now puts the three field rows in their own container; for a disabled period it applies a `QGraphicsOpacityEffect(0.45)` to that container and calls `setEnabled(False)` on the six steppers. The checkbox and Delete sit in the footer, outside the faded container, so they stay live.

**Verified.** The unit suite is still 63 tests / 167 checks green; all five new-ui scripts and `controller.as` / `rbr-desktop.as` compile; a jsdom render of the real `schedule-period.json` shows the three row ids, the checkbox, its label and Delete; a jsdom probe of the paint logic shows a disabled period's rows end up with `opacity: 0.45; pointer-events: none` and an enabled period's with `opacity: 1; pointer-events: auto`; and desktop probes confirm the disabled card's steppers are disabled and its body is faded (a widget grab shows the body region lighter, ~252 vs ~248 mean, while the footer is unchanged), with the checkbox and Delete still enabled.

I also rewrote `DIFF.md` for this second change — since you've already released, it needs another `./deploy.sh --release`, and the new UI needs a reload (desktop a restart). Nothing in `map.json` needs editing: an absent flag still means enabled.

[code omitted]

## 11:25

The desktop browser isn't important. The changes look good, so task finished.

**Assistant**

Understood — the Tab-focus caveat on the new-ui steppers only bites in a desktop browser, so it stays as it is (`pointer-events: none`, no further change).

Left as it is, so the working tree is the finished change: `controller.as`, the new-ui card and schedule editor, `map-to-rooms.as`, the desktop widget and app script, `AI/MAP_FORMAT.md`, `DIFF.md` and the unit tests. Nothing else in the repo was touched; `version` and `AGENT.md` are still your own edits.

[code omitted]
