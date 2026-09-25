# Architecture Notes (for AI)

## Runtime layers

1. **AllSpeak runtime** — JavaScript (browser UI) or Python (controller, on a Linux mini-PC)
2. **AllSpeak scripts** (`.as`) — application logic in both environments
3. **Webson JSON** (`resources/webson/`, `new-ui/resources/webson/`) — UI structure
4. **MQTT** — controller↔UI communication

## Controller architecture

```
controller.as → load map.json (self-times 6×10s cycles)
                              │ re-launched every ~60s (cron or supervisor)
                              └─ 6×10s cycles:
                                 ProcessAllRooms()
                                 ├─ ResolveCalendarProfile()
                                 ├─ For each room:
                                 │  ├─ Read temperature (Zigbee / RBR-Now)
                                 │  ├─ Evaluate mode (timed/boost/advance/on/off)
                                 │  └─ Set relay on/off
                                 ├─ Publish status via MQTT
                                 └─ Handle incoming UI requests
```

## UI architecture (new PWA)

```
new-ui/index.html → load AllSpeak runtime
                  → load shell.as
                     → MQTT WebSocket connect
                     → first map download
                     → render home screen from Webson JSON
                     → 10-second polling refresh
                     → on user gesture:
                        mutate local map copy
                        send `uirequest` via MQTT
                        reconcile on next map push
```

## Data path

| Direction | Mechanism | Payload |
|-----------|-----------|---------|
| Controller → UI | MQTT publish (status topic) | Room temperatures, relay states, mode, target |
| UI → Controller | MQTT publish (request topic) | `uirequest` actions: Update Rooms, Select Profile, etc. |
| Controller → UI | MQTT publish (response topic) | Updated map or status |

## UI state lifecycle

- **Home screen**: rendered from local map copy, refreshed every 10s from controller
- **Sheets (Profile, Room, Schedule)**: snapshot live data into Editing\* variables on open, mutate locally, ship one `Update Profiles` (or `Update Rooms`) on Save, discard on Cancel
- **Demo mode**: when no credentials exist, renders a baked map + About sheet for marketing visits

## Known integration sensitivities

- If `render ... in Body` fails with "Webson engine is not loaded": ensure `Webson.js` is loaded by `index.html` and the render symbol name is correct
- MQTT WebSockets are silently torn down by mobile OSes when the tab is backgrounded — the UI handles this with a tab-resume freshness check and a poll-interval staleness watchdog

## Operational: checking the live controller

```bash
# 1. Is the controller running?
pgrep -fa controller.as

# 2. Recent log output
journalctl -u rbr-controller --no-pager -n 50 2>/dev/null \
  || find /tmp /var/log -name 'rbr*' -newer /tmp 2>/dev/null \
  || echo "No systemd unit or log file found — controller may run via cron only"

# 3. Re-launch mechanism (check if cron or a supervisor is used)
crontab -l 2>/dev/null | grep -i rbr

# 4. Runtime file freshness
ls -la map.json devices.json thermometers.json params.json

# 5. MQTT connectivity check
mosquitto_pub -h rbrheating.duckdns.org -p 8883 \
  -u rbr -P "$(cat ~/.mqtt_password)" \
  --capath /etc/ssl/certs \
  -t rbr/ping -m test -q 1 2>&1 | head -5

# Run the controller manually (exits if already running)
allspeak controller.as
```
