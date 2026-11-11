# What to do

- Restart RBR Studio. It starts again with the 2026-11-09 Sunroom scenario selected.

# What changed

- **Startup crash fixed.** The new plan-snapshot steps are controller steps with no `room` (`controller: {raw, adopt}`). `DescribeStep` read `controller.room` unconditionally, so loading a scenario that contains one raised `Key 'room' not found in Controller` at startup. It now defaults the Target to `—` when a controller step has no room.
- An adopt step is labelled **Plan snapshot** / **full map push** instead of dumping the whole map into the Action column; the raw payload stays in the step detail and the wire log.
- The plan-snapshot/base-map work from the previous change remains in the tree: a scenario starts from the map in force at its window start, and `plan.snapshot` events are replayed as full-map pushes that become the new base.

# Try it

- `./run-studio.sh`: the Sunroom scenario loads 203 rows; `s132` reads `Controller  —  Plan snapshot  full map push` and the Step tab shows its detail.
- `s92` still shows the Sunroom subline `22.0°→19:00 (A)` and the Step tab's `target at the time: 22.0 °C`; `s132` flips the subline to 22.5.
