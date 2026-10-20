# Feature requests

Features wished for while working in RBR. Add a row when a task works around a missing feature, and review the list at the end of the session.

| Date | Area | Request | Workaround used | Status |
| --- | --- | --- | --- | --- |
| 2026-10-19 | AllSpeak JS dialect | Support `delete entry <key> of <dict>` (parity with the Python/CLI dialect). | `json delete property <key> of <dict>` in `device-editor.allspeak`. | Completed 2026-10-20 (upstream) |
| 2026-10-19 | AllSpeak JS dialect | Allow `entry <key> of <dict>` as a value expression. | `property <key> of <dict>` in `map-to-rooms.allspeak`. | Open |
| 2026-10-19 | AllSpeak language / JS runtime pin | Add `loop` with explicit forms: counted (`loop from 0 to Count - 1 as N`) for variable arrays and parallel arrays; ordered list/JSON array (`loop over List as Item`, optional `as Index, Item`); dictionary (`loop over Dict as Key` or `as Key, Value`); properties (`loop over properties of Obj as Name, Value`). Define copy vs alias, iteration order, termination bound (snapshot/captured at entry), snapshot vs live mutation, and loop-variable scope. Confirm the upstream spelling: the public `09-control-flow.md` fetched 2026-10-20 still documents only `while` and label-driven loops, and the pinned `?v=26051101` lacks `loop`. Keep Python/JS parity, then pin the JS build. | `while` + counter; `item`/`element`; dictionaries have no generic iteration today. | Open |
| 2026-10-19 | AllSpeak syntax | Define the `loop` body as the existing `begin ... end` block; multiple commands sit inside and `end` closes it. Do not introduce `end loop`. A single-command form, if supported, should mirror the `if`/`while` single/block split; otherwise require `begin ... end` for loops. | `while ... begin ... end` | Open |
| 2026-10-19 | AllSpeak JS runtime pin | `on failure` should continue after its clause, as upstream does; the pinned build stops the thread. | `rest get ... or begin ... go to ... end`. | Open (not yet needed in the UI) |
| 2026-10-19 | AllSpeak JS runtime pin | Include the `scale` operator (upstream 2026-08-04) in the pinned bundle. The UI does not use it yet; the controller CLI has it. | Avoided in the UI. | Open (not yet needed) |
