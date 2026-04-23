# Slice 05 — Sheet chrome & MenuSheet

**Goal:** reusable bottom-sheet container, then fill it with the simplest content (the menu). This validates the chrome before building the profile sheet on top of it.

## Reference
- `handoff/README.md §5.6`, `§5.7`.

## Output
- A `Sheet` component (scrim + container + grabber + title + close button).
- A `MenuSheet` that uses it.

## Sheet chrome
- **Scrim**: full-screen `color.scrim`, fades in over `motion.scrimFade`. Clickable → emits `close`.
- **Container**:
  - White, top radii 24 (bottom 0).
  - `max-height: 85%` of the screen, overflow auto.
  - Slide up from the bottom: translateY(100%) → 0, `motion.sheetSlide`.
  - Shadow `shadow.sheet` above the top edge.
- **Header row**:
  - 40 × 4 centered grabber at the very top (bg `#E5E5E7`, radius 2, top padding 10).
  - Below: title (`type.sheetTitle`) on the left, 30 × 30 circular close button on the right (bg `color.chip.neutral.bg`, X glyph, fg `color.text.secondary`). Horizontal padding 20.

Tap on scrim **or** the close button triggers the same `close` event.

## MenuSheet content
Render a single card containing six rows:

| Label                    | Sub               |
|--------------------------|-------------------|
| Profiles & schedules     | 3 profiles        |
| Rooms & thermostats      | 8 devices         |
| Holiday mode             | Off               |
| Boiler & system          | QED6 · 214        |
| Notifications            | (none)            |
| Help & support           | (none)            |

- Card: border `color.border.hairline`, radius 14, margin-top 10, overflow hidden.
- Each row: full-width button, padding `14 / 14`, top border `color.border.dividerSoft` except for the first row.
  - Left: label (15 / 500, primary) + optional sub (12 / 400, muted, margin-top 2).
  - Right: chevron 14 × 14, `color.text.disabled`.
- Footer caption (outside the card, margin-top 18, centred): `Room By Room · v4.2 · QED6 214` in 11 / 400, `color.text.meta`.

## Behaviour
- Each row can be a stub route for now (no navigation target); log the intent.

## Done when
- Sheet slides up smoothly and scrim darkens the page underneath.
- Close button and scrim both dismiss.
- Menu entries are vertically centred and tappable with at least 44 × 44 hit area.
