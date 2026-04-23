# Slice 04 — SummaryCard

**Goal:** the single glanceable piece at the top of the home screen.

## Reference
- `handoff/README.md §5.2`
- `handoff/screenshots/01-home.png` — the card above the room list.

## Output
A `SummaryCard` component. Reads `rooms` and `profile`; writes `profileOpen=true`.

## Layout
```
┌────────────────────────────────────────┐
│ [🔥]  2 rooms calling for heat         │  — heat-status row
│       Kitchen, Lounge                  │
│  ───────────────────────────────────   │  — hairline
│  AVG INDOOR   OUTSIDE   TODAY          │
│  22.5°        11.6°     Mon 23 Apr     │
│  ┌───────────────────────────────────┐ │
│  │ 🗓  TODAY'S PROFILE             › │ │  — profile pill button
│  │    Monday-Friday                  │ │
│  └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

- Margin: `14 px top / 16 px horizontal / 0 bottom`.
- Card: white, radius 20, padding 18, card shadow.

## Heat-status row
- Flex, gap 10, bottom margin 14.
- Icon chip 36 × 36, radius 10.
  - If heating count > 0: bg `color.chip.heat.bg`, fg `color.chip.heat.fg`, with a pulsing dot overlay (7 × 7, accent, top/right 5 px, pulses box-shadow 0 → 8 px transparent over 1.6 s).
  - Else: bg `color.chip.neutral.bg`, fg `color.text.muted`. No dot.
- Title (`type.summaryTitle`, primary). Copy rules:
  - `n == 0` → `Nothing calling for heat`
  - `n == 1` → `{Room} is calling for heat`
  - `n > 1`  → `{n} rooms calling for heat`
- Subtitle (12 / 400, muted, margin-top 2):
  - `n == 0` → `Boiler idle`
  - `n == 1` → `Boiler firing`
  - `n > 1`  → names joined by `, ` (first three) + `, +{n-3} more` if more than 3.

## Stats row
- Top border `color.border.divider`, padding-top 12.
- Grid, three equal columns, each with padding `0 / 4 px`.
- Cell: label (`type.sectionLabel`, margin-bottom 4) + value (`type.statValue`, or `type.statDate` for the date column).
- Values:
  - AVG INDOOR — mean of `temp` over rooms that are not sensors, not offline, and have a reading. `XX.X°`.
  - OUTSIDE — `sensor room.temp`. `XX.X°`. If no sensor room, `—`.
  - TODAY — `Ddd DD MMM` for today.

## Profile pill
- Full-width button, margin-top 14.
- 1 px border `color.border.hairline`, bg `color.surface.pill`, radius 12, padding `10 / 14`.
- Calendar icon (16 × 16, `color.text.secondary`) + two-line text block + right chevron (16 × 16, `color.text.disabled`).
- Label 1: `TODAY'S PROFILE` in `type.sectionLabel`.
- Label 2: `{profile}` in 14 / 500, primary.
- Tapping emits `profile:open` (AllSpeak sets `profileOpen=true`).

## Done when
- Title changes correctly as rooms shift in/out of heating.
- Pulsing dot is shown only when at least one room is heating.
- Profile pill opens the (still-stub) profile sheet.
