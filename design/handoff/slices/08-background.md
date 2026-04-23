# Slice 08 — Time-of-day background

**Goal:** give the screen a warm, ambient backdrop that subtly shifts through the day.

## Reference
- `handoff/README.md §2.2` and `TOKENS.md §Time-of-day gradient`.

## Output
The outermost app container gets a vertical 3-stop gradient picked by the current hour, plus a soft radial white glow overlaid at the top to lift contrast.

## Implementation
1. Pick gradient stops by `gradientForHour(now.hour)` (from `tokens`). Returns `[top, mid, bottom]`.
2. Apply as a vertical linear gradient:
   `linear-gradient(180deg, top 0%, mid 45%, bottom 100%)`.
3. Overlay a non-interactive element on top with:
   `radial-gradient(ellipse at 50% -20%, rgba(255,255,255,0.5) 0%, transparent 70%)`.
4. Keep all cards / sheets / top bar above the gradient in z-order.

## Behaviour
- Re-pick the gradient at hour boundaries. A once-an-hour tick is enough; no animation needed.
- If the user opts out (some preference could be exposed later), fall back to a flat `#F6F6F8`.

## Accessibility
- Card surfaces must stay readable at every hour bucket. The provided palettes all pair with white cards well; verify the night palettes in particular.

## Done when
- The app background visibly changes at the six hour boundaries (00, 06, 10, 15, 19, 22).
- No card or text loses legibility during the sunset / night buckets.
