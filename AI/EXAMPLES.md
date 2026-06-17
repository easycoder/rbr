# Examples and Patterns

## Example: Adding a new room mode
Use this pattern when adding a new operating mode to the controller:
1. Add the mode keyword to mode validation in `controller.as` (look for `timed`, `boost`, `advance`, `on`, `off`)
2. Add a branch in `ProcessRoom` for the new mode — read target temperature, compare to current, set relay
3. Add the mode to the UI mode-selector Webson (`resources/webson/mode.json` or new UI equivalent)
4. Add the mode label/icon in the UI script's mode-rendering logic
5. Ship the `uirequest` so the controller picks it up

## Example: Adding a new UI sheet
The new PWA UI follows a consistent sheet pattern:
1. Add a `div` handle declaration in `shell.as` for the sheet root element
2. Add a Webson template in `new-ui/resources/webson/` with the sheet layout
3. Wire open/close handlers: `on click` to show, Cancel dismisses, Save ships MQTT update
4. Use Editing\* variables for working copies — snapshot on open, discard on Cancel

## Example: Dist/debug pattern
- Use `allspeak.js` (unminified) while diagnosing runtime errors
- Switch to `allspeak-min.js` once stable
- Keep `Webson.js` loaded when `render` command is used

## Example: Controller test with simulator
1. Copy `map-sim.json` to `map.json` and `params.json` to a test directory
2. Run `allspeak simulator.as` alongside `allspeak controller.as` to simulate device responses
3. Check MQTT topics for expected relay state changes
4. The `tests/` directory has Playwright specs for UI-level integration tests

## Pattern: MQTT request/response
```
UI sends:     topic "rbr/<mac>/request"  payload { action: "Update Rooms", rooms: [...] }
Controller:   receives → processes → publishes updated map
UI receives:  topic "rbr/<mac>/response" payload { ...updated map... }
```
Always handle the async gap — the UI mutates its local copy optimistically and reconciles on the next push.
