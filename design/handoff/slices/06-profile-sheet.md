# Slice 06 — ProfileSheet

**Goal:** the profile override + weekly calendar sheet.

## Reference
- `handoff/README.md §5.5`.

## Output
A `ProfileSheet` that reuses the sheet chrome from Slice 05. Reads `profile`, writes `profile`.

## Content (inside the sheet, padding 4 / 20)

### 1. Tagline
13 / 400 / `color.text.secondary`, margin-top 2.
> Override today's profile, or let the calendar decide.

### 2. "Use now" list
- Section label (`type.sectionLabel`), margin `18 / 0 / 8`.
- One button per profile (`Monday-Friday`, `Weekend`, `All off`), 8 px gap between them.
- Button: padding `14`, radius 12, full-width, left-aligned, primary text 15 / 500.
  - Active: border 1.5 `color.accent`, bg `color.accent.10` (roughly — use the `accent/5–10` range), right-aligned `ACTIVE` chip (11 / 600, accent).
  - Inactive: border 1 `color.border.hairline`, white bg.
- Left radio dot (18 × 18 circle, inline): active = 5 px accent ring; inactive = 1.5 px `#CCC` border.
- Tap → set `profile` and close the sheet.

### 3. Calendar list
- Section label (`Calendar`), margin `22 / 0 / 8`.
- Card: border hairline, radius 12, overflow hidden.
- Seven rows (Mon–Sun). Each row: padding `12 / 14`, top border `color.border.dividerSoft` except the first.
  - 38 px day abbreviation (13 / 600, `color.text.secondary`).
  - Flex 1: profile name (14 / 400, primary).
  - Right chevron (14 × 14, `#CCC`).
- Default mapping: Mon–Fri → `Monday-Friday`; Sat–Sun → `Weekend`.
- For now, rows are read-only.

### 4. Manage profiles…
Secondary full-width button, margin-top 14, padding 12, radius 12, bg transparent, border hairline, label 14 / 400, primary. Stub action.

## Done when
- Tapping the profile pill on the home screen opens the sheet with the active profile highlighted.
- Tapping a profile updates the home-screen pill's visible label.
- Tapping the scrim or close button dismisses without side-effects.
