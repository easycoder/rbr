# Proposal: one shared room list, with per-profile state keyed by name

## The decision

Room *identity* moves above profiles. A system has one list of rooms; each profile carries only that room's schedule and per-profile state, keyed by room name. The controller is to match what the PWA already presents, rather than the PWA bending around the controller.

Decided 2026-10-17 by Graham: "A system, once running, rarely if ever needs special profiles with their own room sets. The PWA presents things logically, so the controller should be set to match that."

## Why, in one paragraph

The two halves already disagree, and the join between them is an array index. The controller is genuinely per-profile: `ProcessAllRooms` takes the selected profile and sizes every parallel array from *that* profile's room count. The PWA assumes the opposite — it never sends `Update Rooms`, always ships the whole `profiles` array, and edits rooms by index across every profile (`SwapRoomsAcrossProfiles` is even commented "in every profile"). Nothing checks that index 3 means the same room in each profile. So the moment a profile has a shorter or differently ordered room list, renaming or reordering a device writes into whatever occupies that index elsewhere — silently. It is safe today only because all three profiles on the live map happen to agree: 8 rooms, same names, same order.

The deeper fault is that a room record conflates two unlike things. Identity is a property of the installation: which relays the room has and how reliably they answer, which thermometer serves it, how the relay is driven, and whether it is protected against frost. Schedule state is a property of a plan: what the room is asked to do, and when. Joined by index, divergence is a corruption; joined by name, it cannot happen.

## The model

```
map.json
  name, request, calendar, calendar-data, profile
  rooms: [                        # identity, shared by every profile
    { name, relays[], sensor, linked, relayfails[], protect, ptemp,
      temperature, humidity, battery, status, statusMessage,
      relayMessage, relaysFailed, relaysTotal, timestamp, sensorAge, relay }
  ]
  profiles: [
    { name,
      rooms: { "Kitchen": { mode, target, periods[], events[], period,
                            advance, prevmode, until, boostperiod },
               "Sunroom": { ... } } }
  ]
```

### Which field goes where

| Field | Belongs to | Why |
| --- | --- | --- |
| `name` | identity | The shared key. |
| `relays` | identity | Which relays the room has — wiring, not schedule. |
| `sensor` | identity | Which thermometer serves the room. |
| `linked` | identity | Whether the relay is driven by target/temperature or directly by mode — a property of the equipment, which is why it appears in `SetRelay` rather than in any schedule code. |
| `relayfails` | identity | Per-relay failure counts, parallel to `relays`. About the relays, not the plan. |
| `temperature`, `humidity`, `battery`, `sensorAge`, `timestamp` | identity | Readings from one physical sensor; identical in every profile. Storing them per profile triples them for no reason. |
| `status`, `statusMessage`, `relayMessage`, `relaysFailed`, `relaysTotal`, `relay` | identity | Derived from the readings and the relays, so likewise identical per profile. |
| `mode`, `target`, `prevmode`, `until`, `boostperiod` | per profile | What the room is being asked to do under *that* profile — deliberately, not merely as the old shape. `Select Profile` re-materialises the room's operating state from the profile it selects, which is what makes a profile such as `All Off` actually turn everything off; and the operating-mode code clears `until`, `prevmode` and `boostperiod` on a mode change specifically "so the map doesn't carry zombie state across profile views". |
| `periods`, `events`, `period`, `advance` | per profile | The schedule itself, which is the whole point of a profile. |
| `protect`, `ptemp` | identity | Frost protection protects the room's fabric and pipework whatever the plan says: a property of the installation, not of a schedule. It also means the frost sheet writes one record instead of looping every profile — another per-profile loop gone. (The controller reads neither field today, which is recorded separately in DIFF.md.) |

The readings moving to identity also shrinks the file: today every reading is written three times, once per profile.

## Implementation shape

The controller's per-room logic does not change. It continues to work on one flat `Room` per iteration, exactly as now, because that is what `SetRelay`, `ApplyPeriods`, `GetNaturalPeriod` and the rest already understand. Only three boundaries change:

1. **`LoadMap`** reads the new shape and *materialises* the working array for the selected profile: for each entry in `Map.rooms`, merge the identity with `profiles[selected].rooms[name]`. A room present in identity but absent from that profile is skipped for control, which is the existing intent of per-profile sets made explicit and safe.
2. **`CommitRooms`** (new) splits the working array back: identity fields to the matching entry in `Map.rooms` (matched by name, not index), state fields into `profiles[selected].rooms[name]`. Called before `PrepareMapForDisk` and before `SendMapToUI`, so both see committed state.
3. **`Update Profiles`** stores the incoming shape and re-materialises. Because the PWA edits identity once and state per profile, an incoming profile carrying a state entry for an unknown room name is a rename or a stale copy — it must be matched by name against identity, and a state entry with no identity must be reported rather than silently dropped.

`ProcessAllRooms` gains one lookup (identity by name) and otherwise shrinks: the arrays it sizes are the shared room list's, and `RoomCount` no longer varies with the profile.

### Two hazards to handle explicitly

- **Materialised rooms must not alias stored ones.** AllSpeak aliases json variables on assignment; the merged working `Room` has to be built fresh (`put prettify` then `put json`), and committed back by copy, or deleting a field in one place will delete it in the other. This is the trap that cost an afternoon during the volatile-storage work.
- **The disk copy and the UI copy are the same `Map`.** `PrepareMapForDisk` deep-copies today for this reason. That does not change, but the strip list does: the readings are no longer inside a profile, so the strip loop moves from `profiles[].rooms[]` to the top-level `rooms[]`.

## Migration

**No migration script is needed, and none was written.** The controller converts an old-shape map in memory when it loads it (`EnsureSharedRooms`: names unioned across profiles, selected profile first, identity fields lifted out of each profile's copies) and the converted shape is what `PrepareMapForDisk` writes back on the next save. A machine with no map never sees the old format at all — `LoadMap`'s default branch builds the new shape directly.

That replaces the `propose-shared-rooms.allspeak` this section originally called for: a script would have had to be run, validated and undone by hand, where the controller already carries the conversion, running it twice is a no-op, and a map written by an old controller is converted again on the next load. The one thing the script would have added — refusing to continue when profiles disagree, rather than quietly choosing one — the conversion keeps in a weaker form: it unions the names, so no room is lost, and a profile that never had a room simply has no state for it.

## Staging

Both halves must land together; a controller expecting the new shape with a PWA writing the old one is worse than either.

1. Controller: `LoadMap`, `MaterialiseRooms`, `CommitRooms`, `Update Profiles`, `PrepareMapForDisk`, the default map. Verify with the local harness (broker + controller + stub bridge) against a migrated copy of the live map: rooms control, readings land, the disk file is the new shape and is written once rather than every tick.
2. PWA: `map-to-rooms` (translate identity once, state per profile), `device-editor` (edit identity only — the per-profile loops disappear, which is the simplification this change buys), `profile-sheet`, `schedule-editor`, `shell`'s sync-current-room path. Verify in a headless browser against the same map.
3. Docs and one deploy. `AI/MAP_FORMAT.md` is updated; the product docs under `docs/` are not yet, and the desktop app and the legacy UI in `tests/` still speak the old format — see DIFF.md for what that breaks.

Stages 1 and 2 are both written, verified locally, and **running on the live controller as of 2026-10-17** — the controller was replaced first, then the page, so that the mismatch window failed safely. The version stamp was deliberately left alone, so no other controller self-updates. See DIFF.md for what was found on the way (`CommitRooms` was not copying the derived status fields, which no local fixture could have caught) and for the rollback files on the box.
