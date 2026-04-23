# Slice index

Build in this order. Each slice is self-contained and references the main `handoff/README.md` for deep detail.

1. [`01-tokens.md`](01-tokens.md) — all design constants in one module.
2. [`02-top-bar.md`](02-top-bar.md) — static top bar + menu button.
3. [`03-room-row-rest.md`](03-room-row-rest.md) — the core home-screen list, rest state only.
4. [`04-summary-card.md`](04-summary-card.md) — glanceable summary at top of home.
5. [`05-sheet-and-menu.md`](05-sheet-and-menu.md) — reusable sheet chrome, exercised by the simpler MenuSheet.
6. [`06-profile-sheet.md`](06-profile-sheet.md) — profile override + weekly calendar.
7. [`07-room-row-expansion.md`](07-room-row-expansion.md) — inline mode / target / boost controls.
8. [`08-background.md`](08-background.md) — time-of-day ambient backdrop.

After these eight slices, the home screen matches the prototype end-to-end. Remaining work (schedule editor, whole-home actions, onboarding) is untouched and should be scoped separately.
