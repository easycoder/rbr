# 2026-11-19 — the card agrees with the controller about a moved morning, and the home survives a room-count change

**Action:** `./deploy.sh` publishes the PWA and the edited interface page. There is no controller change and no version bump, so nothing restarts. On the phone, reload the app once (or let the service worker's network-first fetch pick it up) — the two runtime-error dialogs from this morning cannot recur after that.

## What changed

`new-ui/resources/allspeak/map-to-rooms.allspeak` — the page's projection of a room's schedule now applies today's armed one-off override before it decides what the room is doing, exactly as the controller's `GetEffectivePeriods` does: the morning `on` moves to the requested time, `keepoff` moves the `off` by the same amount (clamped to 23:59), a `skip` or a late start without `keepoff` drops that period for the morning, and an override dated tomorrow changes nothing today. This is why Bedroom 1 showed black text and "Off until 07:30" while its flame was lit at 06:30 and the pill only went blue at 07:30. The scheduled morning start used to pre-fill the Special time popup is remembered before the shift, so an armed override is not offered back as the next time.

`new-ui/resources/allspeak/shell.allspeak` — a map that brings a different number of rooms now rebuilds the home instead of refreshing past its built rows (the `room-3-name` / `No such element` dialog). The single-room card holds an incoming map while it is being built and flushes it afterwards, and a card whose template never arrived falls back to the room list rather than raising an error on every push (`ModeTimedBtn is not attached to a DOM element`). The room-page refresh also skips the control block for a sensor row, as the open path already did.

`tests/ui/room-count.spec.js` — new: room-list growth, a card across a map push, and the failed-template fallback. `tests/ui/special-override.spec.js` — the moved morning is asserted as orange with the moved stop, and the time popup still offers the scheduled start. `tests/ui/README.md`, `AGENTS.md` and `docs/operation/01-the-interface.md` describe the behaviour.

## Checked

`node tests/pwa-compile-check.js` — 12/12. `tests/unit/controller-compile-check.sh` — the controller compiles. The full Playwright suite passes (29/30 on the first run; the one failure was a minute-boundary in the new test's own expected time, now pinned to one instant — the spec then passes 3/3). `python3 asdoc-check.py` reports 0 errors.

`node tests/pwa-boot-guard-check.js` fails at "a normal boot" on unmodified `HEAD` too (it reads `#app` after the current runtime has replaced it), so it is not from this change.
