# Slice 03 — RoomRow (rest state)

**Goal:** render one room card in its rest (collapsed) state, for every room in the seed data. No expansion yet.

## Reference
- `handoff/README.md §5.3` — full spec.
- `handoff/README.md §4` — Room shape and seed data.
- `handoff/screenshots/01-home.png` — the stacked rows.

## Output
A `RoomRow` component rendered inside a vertical list with 8 px gaps and 16 px horizontal page padding.

## Data
Hard-code `INITIAL_ROOMS` from `app.jsx` as the seed list for now. Don't worry about device communication in this slice.

## Layout (comfortable density)
```
[ 38px mode chip ]  [ Name   (tags) ]   [ 22.5°C ]  [ v ]
                    [ sub-line     ]    [ set 20° ]
```
- Row bg: white, radius 16, card shadow.
- Row padding: `14 px vertical / 16 px horizontal`.
- Gap between slots: 12 px.
- Chevron: 16 × 16, colour `color.text.disabled`. Hidden for sensor rows.

## Mode chip
38 × 38, radius 12. Icon + fg/bg per the matrix in §5.3. Icons:
- Timed / Boost → clock (boost uses the lightning glyph)
- On → plus-in-circle
- Off → power
- Sensor → signal/wifi glyph
- Offline → clock (fg colour changes)

## Text block
- Name: `type.roomName`, `color.text.primary`.
- Inline tags (only when applicable):
  - `heating` — 10.5 / 600, accent, leading flame glyph. Shown when `callingForHeat(room)`.
  - `offline` — 10.5 / 500, warn colour, leading wifi-off glyph. Shown when `room.offline`.
- Sub-line copy rules (pick the first that applies):
  1. `room.sensor` → `Outdoor sensor`
  2. `room.offline` → `No signal since HH:MM` (the timestamp is illustrative; if unavailable, omit the time)
  3. `room.mode === 'Off'` → `Off — no schedule`
  4. `room.boost` → `Boost · {room.boost} left`
  5. `room.nextChange` → `→ {target}° at {time}` (use the gradient-arrow glyph, not literal `->`)
  Else → no sub-line.

## Temperature block (right-aligned)
- Current temp: 22 / 500 / -0.8. `null` → em-dash. Offline colour is `color.text.disabled`.
- Unit suffix: 11 px, `color.text.muted`, 2 px left margin.
- Setpoint line (only if `room.target != null && !room.sensor`): `set 20.0°` — 11 px muted with the number itself in `color.text.secondary` / 500.

## Derived
Implement `callingForHeat(room)` per `handoff/README.md §4`:
- `!sensor && !offline && mode !== 'Off' && temp != null && target != null && (target - temp) > 0.2`

## Done when
- All eight seed rooms render correctly, including the Hall (offline), Office/Guest Bedroom (Off), Outside (sensor, no chevron).
- Kitchen and Lounge show the `heating` tag.
- Compact density is toggleable via a prop (smaller name + temp; tighter padding).
