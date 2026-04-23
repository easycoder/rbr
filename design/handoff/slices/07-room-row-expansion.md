# Slice 07 — RoomRow expansion

**Goal:** the inline controls that appear beneath a room row when tapped. This is the feature that justifies the whole redesign — no modal, one tap to control everything.

## Reference
- `handoff/README.md §5.4`.
- `handoff/README.md §6` for flow semantics.

## Output
Extend `RoomRow` so that, when `expandedId === room.id` and the room is not a sensor, a controls block renders inside the same card beneath the rest row. The rest row's chevron rotates 180° and the card gains the raised shadow.

## Container
- Top border `color.border.dividerSoft`.
- Padding `4 / 16 / 18 / 16`.

## 1. Mode segmented control
- Section label `MODE` (`type.sectionLabel`), margin `14 / 0 / 8`.
- Container: bg `color.surface.sunk`, padding 4, radius 12, grid 3 × 1 with gap 6.
- Each button: radius 9, padding `10 / 6`, centred label + 15 px leading icon (clock / plus-in-circle / power).
  - Active: bg white, primary text, `font-weight 600`, shadow `0 1px 3px rgba(0,0,0,0.08)`.
  - Inactive: transparent bg, `color.text.muted`, `font-weight 500`.
- Buttons: `Timed`, `On`, `Off`.

### Mode-change rules
- Clicking a mode: set `room.mode = <mode>`, clear `room.boost`.
- New mode `Off`: set `room.target = null`.
- Moving away from `Off`: if previous target is null, default to 20°C. Otherwise restore last target.

## 2. Target stepper (hidden when `mode === 'Off'`)
- Section label `TARGET`, margin `16 / 0 / 8`.
- Flex row, gap 12:
  - 54 × 54 disc, radius 17, white bg, `shadow.stepBtn`, accent-coloured `−` glyph (22 × 22). Decrements target by 0.5.
  - Flex 1 tile: padding `14 / 8`, bg `color.accent.10`, border 1 `color.accent.20`, radius 14.
    - Big number 30 / 500 / -1, primary colour. Inline unit label (`°C` or `°F`) in accent, 15 / 500, 4 px left margin.
    - Sub caption `Target temperature` — 11 / 400, `color.text.secondary`, margin-top 4.
  - Matching 54 × 54 disc with `+` glyph.
- Clamp: `5.0 ≤ target ≤ 30.0`, step 0.5.

## 3. Boost (hidden when `mode === 'Off'`)
- Header row, margin `18 / 0 / 8`: label `BOOST` on the left, optional `Cancel` link on the right (12 / 500, accent) — shown only when `room.boost != null`.
- 3-column grid, gap 6, three chip buttons: `30 min`, `1 hr`, `2 hr`.
  - Active (matches `room.boost`): border 1.5 `color.accent`, bg `color.accent.10` (roughly `accent/7`), text accent, 600 weight.
  - Inactive: white, border 1 hairline, primary text 500.
- Tap → set `room.mode = 'Boost'`, `room.boost = <duration>`.
- Cancel link → set `room.mode = 'Timed'`, `room.boost = null`.

## 4. Edit schedule link
Secondary full-width button:
- Margin-top 14, padding `12 / 14`, border hairline, white bg, radius 12.
- Edit icon (15 × 15, muted) + label `Edit schedule` (13.5 / 500, primary) + right chevron (14 × 14, disabled).
- For now navigates to the legacy Periods panel. A later slice can replace it.

## Expand/collapse flow
- Tapping a rest row toggles `expandedId`.
- Only one row is expanded at a time. Opening a new row collapses the previous.
- Expanded row has `shadow.cardRaised`; others keep `shadow.card`.
- Chevron rotates 180° via `motion.chevronRotate`.

## Done when
- Every mode / target / boost interaction from `handoff/README.md §6` works.
- Tapping outside the expanded area (on another room) collapses this one and opens the other.
- Target clamping holds: pressing `−` at 5.0 is a no-op; `+` at 30.0 is a no-op.
