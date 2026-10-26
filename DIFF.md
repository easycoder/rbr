# What to do

- **Deploy the controller and the PWA** (`./deploy.sh --release`), then reload the page once. No map or broker change. This release also carries the calendar-name fix from yesterday.
- **On the New System, bind `DR-Rad`, `KW-Rad` and `OB-Rad`** in Rooms and Devices. This change stops the app claiming heat for rooms with nothing to open; it cannot heat an unbound room.

# What changed

**No-actuator rooms no longer call for heat.** A room with no relays and no TRV has nothing to open, so `SetRelay` now leaves it off and does not set `HeatingRequested` — it could previously fire the demand relay for a room it could not heat. The page suppresses its heating tag and marks it "No radiator assigned". `On` and `Boost` cannot override the rule; both are tested.

**The valve's own state is on the card.** `zigbee-trv.json` already carried `running_state` (`heat` = valve open, `idle` = closed) and `last_seen`; the controller now publishes it as `trvrunning` on the room's identity record, freshness-gated at 45 minutes like the sensor gate. The page shows "heating" while the valve is open and "valve idle" in amber when RBR is calling but the valve is closed; with no report it falls back to the demand as before. A change in valve state marks the map changed, so the card updates within a cycle instead of waiting for some other change.

**Tests.** `tests/unit/setrelay_test.py` runs ten cases against the shipped `SetRelay`; `commit_roundtrip_test.py` now carries `trvrunning` through materialise into the identity record; `tests/pwa-valve-state-check.js` drives the whole shell with a fake MQTT client and reads the rendered tags and warn rows; and the Devices-sheet check now includes `trv` in the identity it compares, so a rename cannot quietly drop a valve binding.
