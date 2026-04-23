# Slice 02 — TopBar

**Goal:** render the static top bar. No state wiring yet.

## Reference
- `handoff/README.md §5.1`
- `handoff/screenshots/01-home.png` — top strip of the image.

## Output
A `TopBar` Webson component.

## Layout
```
┌───────────────────────────────────────────┐
│ [Mark]  Room By Room              [ ≡ ]  │
│         QED6 · 214                        │
└───────────────────────────────────────────┘
```

- Height driven by content; padding **10 px top / 8 px bottom / 18 px horizontal**.
- Left group: 34 × 34 **HouseMark** tile (radius 10, bg `color.accent`, white house glyph, drop shadow `shadow.houseMark`), followed by a two-line text block.
  - Line 1: `Room By Room` — `type.appName`, `color.text.primary`.
  - Line 2: `QED6 · 214` — 11 px, `color.text.muted`, margin-top -1.
- Right: 38 × 38 square button, radius 12, bg `rgba(0,0,0,0.04)`, menu glyph (3 horizontal lines). `aria-label="Menu"`.
- Background of the bar: `rgba(255,255,255,0.82)` with backdrop blur 16. If blur is not available in Webson, use solid `#FFFFFF` + bottom hairline border `color.border.divider`.

## Behaviour
- Menu button emits a `menu:open` event (or sets `menuOpen=true` in AllSpeak). No other interactivity.

## Done when
- Visual matches the home screenshot's top strip.
- System ID ("QED6 · 214") is data-bound, not hard-coded.
- Menu button is tappable with at least 44 × 44 effective hit area.
