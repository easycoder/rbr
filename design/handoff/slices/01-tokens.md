# Slice 01 — Tokens

**Goal:** centralise every design constant before touching visuals.

## Input
- `handoff/TOKENS.md` — the full token list.

## Output
A single module (or Webson equivalent) exporting named constants. No UI yet.

## Steps
1. Create `tokens.webson` (or whatever your convention is). Paste in the tokens from `TOKENS.md` as native constants — colours, gradients, type scale, spacing, radii, shadows, motion, temp semantics.
2. Expose the accent colour separately so it can be swapped at runtime (user wants live tweaking).
3. Add two derived helpers:
   - `rgba(hex, alpha)` — for expressing `accent/8`, `accent/20` etc. without hard-coding every variant.
   - `gradientForHour(hour) → [top, mid, bottom]` — the table in `TOKENS.md §2` implemented as a pure function.

## Done when
- Every colour, radius, shadow, and type style referenced in later slices resolves to a token in this module.
- `gradientForHour(17)` returns the afternoon-amber stops.

## Notes
- Don't inline literals in components. If you find yourself typing `#E86A33` in a later slice, add a token instead.
- Tokens are dumb data. No rendering logic lives here.
