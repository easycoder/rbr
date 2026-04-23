# Room By Room — Design Handoff for Claude Code

This document is the bridge between the visual prototype (`Room By Room.html`, built in React for design-time clarity) and the production implementation in **Webson** (DOM description) + **AllSpeak** (logic).

**Read the prototype as a visual and behavioural spec, not a source to port.** The React/CSS-in-JS structure is disposable; the *layout*, *state shape*, *interactions*, and *design tokens* in this document are what matter.

---

## 0. Contents

1. [Goals & principles](#1-goals--principles)
2. [Design tokens](#2-design-tokens)
3. [Screen architecture](#3-screen-architecture)
4. [State model](#4-state-model)
5. [Component specs](#5-component-specs)
6. [Interaction flows](#6-interaction-flows)
7. [Data bindings — what each element reads](#7-data-bindings)
8. [Edge cases & rules](#8-edge-cases--rules)
9. [Port order — recommended slices](#9-port-order)
10. [Open questions for the user](#10-open-questions)

---

## 1. Goals & principles

- **One-screen system view.** Every room visible above the fold-ish; no sub-pages for the common case.
- **Minimise taps.** Adjust mode, target, and boost for any room from the home screen without a modal — rows expand inline.
- **Recognisable as central heating.** Flame/clock/power iconography, temperature-first typography, warm palette.
- **Mobile PWA first.** All touch targets ≥ 44 px. Designed at 402 × 874 logical px (iPhone 14/15 reference).
- **Clean modern minimal.** White cards, one accent colour, generous whitespace, one type family (system sans). No skeuomorphism.
- **Tagline removed** on the running app; the header is purely functional.

---

## 2. Design tokens

Keep these centralised. In Webson terms, these should be named variables (or whatever constant mechanism you use) — not inline literals.

### 2.1 Colour

| Token | Value | Use |
|---|---|---|
| `color.accent` | `#E86A33` | Primary (warm orange); used for heat calls, active states, focus. Tweakable. |
| `color.accent/12` | accent at 12% opacity | Hover/active backgrounds (`#E86A331E`) |
| `color.accent/10` | accent at 10% opacity | Target card background |
| `color.accent/8` | accent at 8% opacity | Mode-chip background when calling for heat |
| `color.text.primary` | `#1A1A1A` | Titles, temperatures |
| `color.text.secondary` | `#666 – #888` | Sub-labels, next-change line |
| `color.text.muted` | `#999 – #AAA` | Section labels, meta |
| `color.text.disabled` | `#BBB` | Offline temp, chevrons |
| `color.surface.card` | `#FFFFFF` | All card/sheet surfaces |
| `color.surface.chip.neutral` | `#F1F3F5` | Off-mode icon chip, secondary buttons |
| `color.surface.chip.ok` | `#E8F4EC` | Timed mode icon chip (not currently heating) |
| `color.surface.chip.warn` | `#FFF4E0` | Offline icon chip |
| `color.surface.sunk` | `#F4F5F7` | Segmented control background |
| `color.border.hairline` | `#ECECEC` | Card borders, sheet row dividers |
| `color.border.divider` | `#F0F0F0 – #F3F3F3` | Inner card dividers |
| `color.status.ok` | `#3A8C5F` | Timed-mode icon colour |
| `color.status.warn` | `#C78A1A` | Offline label |
| `color.status.heat` | same as accent | Calling-for-heat label, flame |

### 2.2 Time-of-day background gradient

A three-stop linear-gradient, top → bottom, chosen by current hour (0–23). Overlaid with a soft radial white glow at the top (`radial-gradient(ellipse at 50% -20%, rgba(255,255,255,0.5), transparent 70%)`).

| Hour range | Stops (top / mid / bottom) | Label |
|---|---|---|
| 0–5 | `#1E2238` `#2D2A3E` `#433048` | Late night |
| 6–9 | `#FFE8D4` `#FFD3B0` `#F5B994` | Morning peach |
| 10–14 | `#FDF6EC` `#FBEEDD` `#F5E2C9` | Midday cream |
| 15–18 | `#FFE1C2` `#F7B88A` `#E88A5B` | Afternoon amber |
| 19–21 | `#F0A877` `#B66B56` `#5A3A52` | Sunset |
| 22–23 | `#27253A` `#332B42` `#4A3450` | Late night |

Swapping at hour boundaries is fine (no need to animate). If Webson can't do gradients, fall back to a single mid-stop colour.

### 2.3 Type

System sans-serif stack: `-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif`.

| Role | Size / weight / tracking |
|---|---|
| App name (top bar) | 17 / 600 / -0.3 |
| Section heading (sheet title) | 17 / 600 / -0.3 |
| Summary headline | 15 / 600 / -0.2 |
| Room name | 16 / 600 / -0.2 (15 compact) |
| Current temperature (row) | 22 / 500 / -0.8 (20 compact) |
| Target temperature (expanded) | 30 / 500 / -1.0 |
| Stat value | 18 / 600 / -0.3 |
| Body | 13–14 / 500 |
| Sub-line (next change, offline) | 12 / 400–500 |
| Caption / meta | 11 / 400 |
| Section label (uppercase) | 10.5 / 500 / +0.4 / UPPERCASE |

### 2.4 Spacing / radius / shadow

- **Radii**: card 16, pill/sheet 20–24, chip 10–12, segmented pill 9, button 10–14.
- **Card shadow**: `0 1px 2px rgba(0,0,0,0.04), 0 4px 14px -8px rgba(0,0,0,0.08)`.
- **Card shadow (elevated / expanded row)**: `0 1px 2px rgba(0,0,0,0.05), 0 12px 32px -8px rgba(0,0,0,0.12)`.
- **Step-button shadow**: `0 1px 2px rgba(0,0,0,0.06), 0 6px 16px -6px rgba(0,0,0,0.14)`.
- **Horizontal page padding**: 16 px. Card inner padding: 14–18 px.
- **Gap between room rows**: 8 px.

### 2.5 Motion

- Row chevron rotates 180° in 0.25 s when a row expands.
- Bottom sheets slide up with `cubic-bezier(.2, .9, .3, 1)` over 0.28 s; scrim fades 0.24 s.
- Button press: `transform: scale(0.98)` for 50 ms — purely a responsiveness cue, skip if Webson doesn't support transforms easily.
- Heating dot pulses (box-shadow spreads 0 → 8 px transparent over 1.6 s, infinite). Decorative; omit on low-end.

---

## 3. Screen architecture

One primary screen, two bottom sheets.

```
┌──────────────────────────────────────┐
│  [ House ] Room By Room       [ ≡ ]  │  TopBar (sticky optional)
│            QED6 · 214                │
├──────────────────────────────────────┤
│ ┌──────────────────────────────────┐ │
│ │ 🔥 2 rooms calling for heat      │ │
│ │    Kitchen, Lounge               │ │  SummaryCard
│ │ ──────────────────────────────── │ │
│ │ AVG     OUTSIDE   TODAY          │ │
│ │ 22.5°   11.6°     Mon 23 Apr     │ │
│ │ ┌──────────────────────────────┐ │ │
│ │ │ 🗓  TODAY'S PROFILE        › │ │ │  ProfilePill → opens ProfileSheet
│ │ │    Monday-Friday             │ │ │
│ │ └──────────────────────────────┘ │ │
│ └──────────────────────────────────┘ │
│                                      │
│ ┌──[Kitchen row]───────────────────┐ │
│ │ ⏰  Kitchen     🔥heating  19.7° │ │  RoomRow (rest)
│ │    → 20.0° at 17:30    set 20.0° │ │
│ └──────────────────────────────────┘ │
│ ┌──[Sunroom row]───────────────────┐ │
│ ...                                  │
│ ┌──[Outside sensor]────────────────┐ │  sensor = no chevron, no expand
│ │ 📶  Outside               11.6°  │ │
│ │    Outdoor sensor                │ │
│ └──────────────────────────────────┘ │
│                                      │
│       Last sync 12s ago · 8 devices  │
└──────────────────────────────────────┘

Bottom sheets (slide up over scrim):
  • ProfileSheet — toggles profile for today; shows weekly calendar.
  • MenuSheet    — list of settings entries (Profiles & schedules,
                   Rooms & thermostats, Holiday mode, Boiler & system,
                   Notifications, Help & support).
```

Only **one** sheet is ever open at a time. Tapping the scrim or the close button dismisses the sheet.

---

## 4. State model

Minimal app-level state the UI needs to read:

```
rooms       : Room[]           // see below
expandedId  : RoomId | null    // which row is inline-expanded
profileOpen : boolean
menuOpen    : boolean
profile     : 'Monday-Friday' | 'Weekend' | 'All off'   // active today
```

### Room shape

```
Room {
  id          : string                   // stable identifier
  name        : string                   // display name
  temp        : number | null            // current measured °C; null if offline
  target      : number | null            // target °C; null when mode=Off or sensor
  mode        : 'Timed' | 'On' | 'Off' | 'Boost' | 'Sensor'
  boost       : '30 min' | '1 hr' | '2 hr' | null   // set when mode=Boost
  nextChange  : { time: 'HH:MM', target: number } | null
  offline     : boolean                  // device hasn't reported recently
  sensor      : boolean                  // read-only (e.g. Outside)
}
```

Initial data used by the prototype (as a reference for realistic values):

| id | name | temp | target | mode | nextChange | flags |
|---|---|---|---|---|---|---|
| kitchen | Kitchen | 19.7 | 20.0 | Timed | 17:30 → 20.0° | |
| sunroom | Sunroom | 24.0 | 16.5 | Timed | 16:30 → 16.5° | |
| lounge | Lounge | 20.4 | 21.0 | Timed | 17:30 → 21.0° | |
| hall | Hall | null | 17.0 | Timed | 17:00 → 17.0° | offline |
| office | Office | 25.2 | null | Off | — | |
| mainbed | Main Bedroom | 23.0 | 15.0 | Timed | 22:30 → 15.0° | |
| guestbed | Guest Bedroom | 22.9 | null | Off | — | |
| outside | Outside | 11.6 | null | Sensor | — | sensor |

### Derived values

- **`callingForHeat(room)`**: `true` iff `!sensor && !offline && mode !== 'Off' && temp != null && target != null && (target - temp) > 0.2`.
- **Summary count**: `rooms.filter(callingForHeat).length`.
- **Average indoor**: mean of `temp` across rooms where `!sensor && !offline && temp != null`.
- **Outside**: the room flagged `sensor: true`.

---

## 5. Component specs

Each spec has: (a) what it is, (b) what it reads, (c) what it writes, (d) layout, (e) states.

### 5.1 TopBar

- **Reads**: —
- **Writes**: `menuOpen = true` on tap of the `≡` button.
- **Layout**: 10 px top / 8 px bottom padding, 18 px horizontal. 38 × 38 menu button (radius 12). The house mark is a 34 × 34 accent-coloured rounded square (radius 10) with a white house glyph and an accent-tinted drop shadow (`0 4px 12px accent/25`).
- **Text**: left column — "Room By Room" / "QED6 · 214" (system ID).
- **Background**: white at 82% opacity with backdrop blur 16 px; if blur unavailable, use plain white with a hairline bottom border (`#0000000d`).

### 5.2 SummaryCard

- **Reads**: `rooms`, `profile`.
- **Writes**: `profileOpen = true` when the profile pill is tapped.
- **Layout**: full-width card, margin 14/16/0/16, padding 18, radius 20.
- **Content**:
  1. Row 1 (heat status) — icon chip (36 × 36, radius 10, `accent/8` bg when heating else `#F1F3F5`) containing a flame glyph; a pulsing dot overlays top-right when heating. Title + subtitle to the right.
  2. Hairline divider (`#F0F0F0`), padding-top 12.
  3. Stats grid — three equal columns: Average indoor, Outside, Today. Labels are uppercase 10.5 px muted; values 18 px bold (14 px for the date).
  4. Profile pill — full-width button (radius 12, border `#ECECEC`, bg `#FAFAFA`, padding 10/14), calendar icon + two-line label + right chevron.
- **Copy rules (title)**:
  - 0 rooms → `Nothing calling for heat` / subtitle `Boiler idle`
  - 1 room → `{Room} is calling for heat` / subtitle `Boiler firing`
  - n rooms → `{n} rooms calling for heat` / subtitle lists up to 3 names, then `, +{n-3} more`

### 5.3 RoomRow (rest state)

- **Reads**: one `Room`, `expandedId`, `units`, `density`.
- **Writes**: toggles `expandedId` (to this `id`, or back to `null`) on tap. Sensor rows do not toggle.
- **Layout** (comfortable):
  ```
  [ 38px mode chip ]  [ Room name  heating-tag ]   [ Temp 22/500 ]  [ v ]
                      [ next-change / sub-line ]   [ set 20.0°    ]
  ```
  padding 14/16; gap between slots 12; chevron 16 px.
- **Mode chip**: 38 × 38, radius 12. Icon + background/foreground by state (see table).
- **Temperature block**: right-aligned. Current temp 22 px (20 compact), setpoint line 11 px muted.
- **Sub-line copy** (by state):
  - sensor → `Outdoor sensor`
  - offline → `No signal since HH:MM`
  - mode === 'Off' → `Off — no schedule`
  - boost → `Boost · {duration} left`
  - nextChange → `→ {target}° at {time}`

**Mode chip colour matrix:**

| State | Background | Foreground | Icon |
|---|---|---|---|
| sensor | `#F1F3F5` | `#888` | signal/wifi glyph |
| offline | `#FFF4E0` | `#C78A1A` | clock |
| mode = Off | `#F1F3F5` | `#999` | power |
| mode = Boost | `accent/8` | `accent` | lightning/boost |
| mode = Timed, not heating | `#E8F4EC` | `#3A8C5F` | clock |
| mode = Timed/On, calling for heat | `accent/8` | `accent` | clock (or flame) |

### 5.4 RoomRow (expanded — inline)

Appears below the rest row inside the same card, above a thin divider (`#F3F3F3`). Padding 4/16/18/16. Only present when `room.id === expandedId` and `!room.sensor`.

Sections, top-to-bottom:

1. **Mode segmented control** — label "MODE"; 3 equal buttons in a sunk pill (`#F4F5F7`, 4 px inner padding, radius 12). Active button = white pill with slight shadow, 600 weight; inactive = transparent, muted text. Buttons: Timed, On, Off — each with a small leading icon.

2. **Target stepper** (hidden when mode = Off) — label "TARGET"; three children in a row:
   - Minus button — 54 × 54 white disc with accent-coloured `−` glyph and the "step-button shadow".
   - Big central tile — flex 1, padding 14/8, bg `accent/4-ish` (use the 10% swatch), border `accent/20`, radius 14. Inside: the target as 30 px number, unit label in accent at 15 px, and sub-caption "Target temperature" 11 px muted.
   - Plus button — mirror of minus.
   - Step size: **0.5**. Clamp 5 ≤ target ≤ 30.

3. **Boost** (hidden when mode = Off) — label "BOOST" on the left, "Cancel" link on the right (accent, 12 px) if `boost != null`.
   Three equal buttons: "30 min", "1 hr", "2 hr". Active boost = `accent/7` bg, `accent` border (1.5 px), `accent` text. Inactive = white, hairline border. Tapping a chip sets `mode = 'Boost'` and `boost = <duration>`.

4. **Edit schedule** — secondary full-width button (border hairline, white bg, radius 12, padding 12/14). Edit icon + label + right chevron. Tapping navigates to the schedule editor for this room (not mocked here, but maps to the existing "Periods" panel in the current app).

### 5.5 ProfileSheet (bottom sheet)

Trigger: profile pill in SummaryCard.

Contents, top to bottom:
1. **Sheet chrome** — 40 × 4 grabber, title "Profile", close button (30 × 30 circle, `#F1F3F5`).
2. Tagline — 13 px muted: "Override today's profile, or let the calendar decide."
3. **Use now** list — label then one button per profile. Active profile: accent border 1.5, bg `accent/5`, right-side `ACTIVE` chip (accent, 11/600). Inactive: hairline border. Each row has a left radio dot (18 × 18): filled 5 px accent when active, else 1.5 px grey border.
4. **Calendar** list — label then a card with one row per weekday (Mon–Sun). Each row: 38 px day abbreviation + profile name + right chevron. Hairline divider between rows.
5. **Manage profiles…** — secondary full-width button.

Writes: selecting a profile calls `setProfile(p)` and closes the sheet.

### 5.6 MenuSheet (bottom sheet)

Trigger: `≡` button in TopBar.

Entries (label / sub): 
- Profiles & schedules / "3 profiles"
- Rooms & thermostats / "8 devices"
- Holiday mode / "Off"
- Boiler & system / "QED6 · 214"
- Notifications
- Help & support

Single card with hairline dividers between rows. Each row is a full-width button, 14 px padding, label 15 px + sub 12 px muted + right chevron.
Footer: "Room By Room · v4.2 · QED6 214", 11 px muted, centred.

### 5.7 Sheet (shared chrome)

- Scrim: `rgba(0,0,0,0.35)`, fades in with the sheet; taps dismiss.
- Container: 24 px top radius, white, `max-height: 85%`, slides up from the bottom.
- Grabber + title + close are standard across both sheets.
- Shadow above the sheet: `0 -12px 40px -8px rgba(0,0,0,0.2)`.

---

## 6. Interaction flows

### 6.1 Expand a room → adjust target
1. User taps a RoomRow.
2. If that row is already expanded → collapse (set `expandedId = null`).
3. Else → set `expandedId = room.id` (this automatically collapses any other row).
4. Expanded area renders. Tapping `+` or `−` updates `room.target` in 0.5° increments, clamped [5, 30]. Visible target reflects change immediately; persistence is a separate concern handled by AllSpeak.

### 6.2 Change mode
1. User taps Timed / On / Off in the segmented control.
2. Update `room.mode`. Clear `room.boost`.
3. If new mode is 'Off' → set `room.target = null`.
4. If changing from 'Off' → set `room.target` to last-known target, defaulting to 20°C.

### 6.3 Start Boost
1. User taps one of the three duration chips.
2. Set `room.mode = 'Boost'` and `room.boost = '30 min' | '1 hr' | '2 hr'`.
3. Sub-line under room name changes to `Boost · {duration} left`.
4. Cancel link appears beside the BOOST label; tapping it reverts `mode = 'Timed'`, `boost = null`.

### 6.4 Switch profile for today
1. User taps the profile pill → ProfileSheet slides up.
2. User selects a profile in "Use now". `profile` is updated and the sheet closes.
3. The pill on the home screen now shows the new profile name.

Calendar-per-day editing is shown but not wired in the prototype — treat as read-only unless the user asks otherwise.

### 6.5 Open menu
1. User taps `≡`. MenuSheet slides up.
2. Each row navigates to its respective legacy panel in the existing app (route/stub).

### 6.6 Scrim / close
- Any sheet: tap the scrim or the close button → the sheet's `open` flag is set to `false`.

### 6.7 Keyboard / hardware (low priority)
- Esc could close an open sheet. Not essential for mobile PWA.

---

## 7. Data bindings

What each visible element is wired to. Use this as a checklist when rebuilding in Webson.

| Element | Reads | Format |
|---|---|---|
| TopBar system ID | `system.id` (currently hard-coded "QED6 · 214") | literal |
| SummaryCard title | count of `rooms.filter(callingForHeat)` | copy rule in §5.2 |
| SummaryCard subtitle | names from same filter | comma-joined, truncate +N more |
| Pulsing dot | whether count > 0 | show/hide |
| Avg indoor stat | mean of valid `temp` | `XX.X°` |
| Outside stat | `sensor room.temp` | `XX.X°` |
| Today stat | today's date | `Ddd DD MMM` |
| Profile pill label | `profile` | literal |
| RoomRow mode chip icon/colour | `room.mode`, `offline`, `sensor`, `callingForHeat` | mapping in §5.3 |
| "heating" tag | `callingForHeat(room)` | show/hide |
| "offline" tag | `room.offline` | show/hide |
| Room name | `room.name` | literal |
| Sub-line | priority: sensor > offline > Off > boost > nextChange | copy rules in §5.3 |
| Current temperature | `room.temp` | `X.X` + unit; `—` if null |
| Setpoint under temp | `room.target` (only if set and not sensor) | `set X.X°` |
| Mode segmented active | `room.mode` | which pill highlights |
| Target number | `room.target ?? 20` | `XX.X` |
| Boost chip active | `room.boost` | which chip highlights |

Units: the prototype supports °C ↔ °F via a tweak. Production can default to °C. If F-support is kept, convert on display only; store internally in °C.

---

## 8. Edge cases & rules

- **Offline room**: greys the temperature (`#BBB`), shows `offline` tag and `No signal since HH:MM` sub-line. Row still expands — the user may want to change mode/target anyway; commands just queue.
- **mode = Off, but temp reading exists** (e.g. Office at 25.2°): still display the measured temp, but suppress the setpoint line.
- **Sensor row** (Outside): no chevron, no expansion, no setpoint, no heat call. Tap does nothing.
- **Empty summary**: if 0 rooms are calling for heat, title reads "Nothing calling for heat" and the sub-line reads "Boiler idle". Icon chip drops to neutral grey.
- **Only one expanded row at a time**. Tapping a different row collapses the previous one.
- **Boost cancellation**: switching mode or tapping "Cancel" clears `boost`.
- **Target clamp**: 5.0 ≤ target ≤ 30.0, step 0.5.
- **Pulsing / scale animations** are decoration. Skip if awkward in Webson.

---

## 9. Port order — recommended slices

Build in this order, verifying each against the prototype before moving on:

1. **Tokens** — colour, type, spacing, radii, shadows as named constants.
2. **TopBar** — static, no state.
3. **RoomRow rest state** (without expansion, without heat call yet) — for every room in `INITIAL_ROOMS`. Verify layout + temperature typography.
4. **Mode chip** + "heating" / "offline" tags — wire `callingForHeat`, `offline`, `sensor`.
5. **Sub-line copy rules** — exercise each room in the seed data to confirm every branch.
6. **SummaryCard** — stats grid, heat-call title/subtitle, pulse dot, profile pill.
7. **Sheet chrome** — scrim, slide-up, grabber, close button. Reuse for both sheets.
8. **MenuSheet** — simplest sheet; good to validate the shared chrome.
9. **ProfileSheet** — profile list + calendar list.
10. **RoomRow expansion** — mode segmented, target stepper, boost chips, edit-schedule link.
11. **Time-of-day background** — last; cosmetic.

Each slice should be runnable on its own so you can compare side by side with the React prototype.

---

## 10. Open questions for the user

Raise these with the user before committing to the port:

- Schedule editor (the "periods" panel in the old screenshots) hasn't been redesigned yet — is the existing panel staying for now?
- Whole-home quick actions (Holiday mode, Boost all, All off) — user opted to keep the home screen clean. Where should these live? (Currently assumed: MenuSheet → "Holiday mode" entry; others inside "Rooms & thermostats".)
- Onboarding / first-run flow — not designed. Is there an existing one to reuse?
- Dark mode — user chose light-only. Confirm before scoping.
- "QED6 · 214" — is this always two segments (model · serial), or does formatting vary?
- The `nextChange.time` / `nextChange.target` values come from the active profile today. Confirm AllSpeak already exposes this, or whether it needs a derivation step.

---

## Appendix A. Reference artefacts

- `../Room By Room.html` — live interactive prototype (React). Use the Tweaks toggle (toolbar) to cycle accent colour, density, units, time of day.
- `../app.jsx` — full source of the prototype. The `INITIAL_ROOMS` array and `callingForHeat` function are the ground truth for data semantics.
- `../ios-frame.jsx` — iOS bezel component used purely for presentation; not part of the app.
- `screenshots/01-home.png` — home screen with 2 rooms calling for heat, Monday-Friday profile.
