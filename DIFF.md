# What to do

- **Deploy the fix now, with `--release`.** Release `2610261152` does not compile — `ProcessTrvState`'s new list reused the name `RoomRelays`, which already exists — so every controller that took it stops at `Compile error … Duplicate symbol name` and never reconnects (the page's "first map didn't arrive in 30s"). `./deploy.sh --release` publishes the corrected controller and a new stamp; controllers recover on their next hourly check.
- **To recover one immediately:** copy this `controller.allspeak` to the controller and restart it (`sudo systemctl restart controller`), or restart `rbr-updater` to force the check now. The service's own 60-second restart brings it up once the file is good.
- The release also carries the calendar-name and valve/no-actuator changes from earlier today. The calendar repair (Mon–Fri → `Weekday`) is already live in the map.

# What changed

The controller had a duplicate `list RoomRelays` declaration: the actuator test in `SetRelay` used that name instead of its own, and the AllSpeak compiler refuses a duplicate symbol in a single pass. The whole controller therefore failed to compile, which is why MQTT never connected. It now uses `ActuatorRelays`, and `tests/unit/controller-compile-check.sh` compiles the whole controller in a throwaway directory (fake MAC, local credentials, `--no-dashboard`) on every unit run. The routine tests extract functions and could never see this class of fault; the compile check can.

Everything else from today's release stands: no-actuator rooms no longer call for heat, and the valve's own `running_state` is published as `trvrunning` for the room card.
