!! Standalone console diagnostics for the RBR controller. Copy this file to the controller and run `allspeak diagnose.as` from the directory that holds map.json — every line of output goes to the console via `ulog`, so you can read it directly or redirect it to a file (`allspeak diagnose.as > diag.txt`) and send it back.
!!
!! It is deliberately read-only: it queries the zigbee bridge (health, device list, per-device state) and reports the map's room configuration and the thermometers file, but never commands a relay unless you opt in by setting TestRelay at the bottom.
!!
!! What each section answers: the bridge sections show whether zigbee2mqtt knows a device under the name the map uses (name mismatch shows up as an error or a missing device), the room section shows what the controller believes (mode, target, temperature, status, relay decision), and the optional TestRelay section sends one `state=on` command so you can watch whether the radiator actually switches.
!   diagnose.as

    script Diagnose

    dictionary Map
    list Profiles
    dictionary Profile
    list Rooms
    dictionary Room
    dictionary Thermometers
    dictionary Thermometer
    dictionary Response
    dictionary DeviceMap
    dictionary Device
    dictionary StateMap
    dictionary StateData
    list Keys
    list Relays
    variable SelectedProfile
    variable RoomCount
    variable RoomName
    variable Sensor
    variable RelayName
    variable BridgeUp
    variable R
    variable J
    variable N
    variable KeyName
    variable TestRelay
    dictionary TestResponse

    ! Entry point — top-level statements run first; dispatch to Main then exit.
    gosub to Main
    exit
!! @hash 6eb00917
!!!
!! Main routine — run the diagnostic sections in order.
!!
!! Each section is independent: Context reads map.json, Bridge talks to the zigbee bridge, RoomsSection prints the controller's view of the rooms, RelayQuery asks the bridge for each mapped relay's state, and RelayTest optionally sends one ON command (see RelayTest).
Main:
    gosub to Context
    gosub to Bridge
    gosub to RoomsSection
    gosub to RelayQuery
    gosub to RelayTest
    gosub to Section
    ulog `Diagnostic complete`
    return
!! @hash d3c1dc6b
!!!
!! Print a banner line so each section is easy to spot in the console.
!!
!! Nothing here depends on controller state, so it runs unchanged whether the controller is running or not — it reads the same files the controller uses and talks to the same bridge.
Section:
    ulog `============================================================`
    return
!! @hash f530580e
!!!
!! Section 1 — context: current time, whether the map file is present, the configured request relay name, and which profile the controller would select.
!!
!! The map's `profile` field is an index into `profiles`; we mirror the controller's selection (`put item SelectedProfile of Profiles into Profile`) so the room list below matches what the controller is actually processing.
Context:
    gosub to Section
    ulog `RBR diagnostic — ` cat now
    if file `map.json` exists
    begin
        load Map from `map.json`
        ulog `map.json present`
    end
    else ulog `map.json MISSING (run from the controller directory)`
    if Map has entry `request` ulog `request relay: ` cat entry `request` of Map
    else ulog `request relay: <not configured>`
    put entry `profiles` of Map into Profiles
    if Map has entry `profile` put entry `profile` of Map into SelectedProfile
    else set SelectedProfile to 0
    if Profiles is not empty
    begin
        put item SelectedProfile of Profiles into Profile
        if Profile has entry `name` ulog `active profile: ` cat entry `name` of Profile cat ` (index ` cat SelectedProfile cat `)`
        else ulog `active profile: index ` cat SelectedProfile
        put entry `rooms` of Profile into Rooms
        put the count of Rooms into RoomCount
        ulog `rooms in profile: ` cat RoomCount
    end
    else ulog `no profiles found in map.json`
    return
!! @hash 1fb18d32
!!!
!! Section 2 — bridge health and the full device list from zigbee2mqtt, as seen by the bridge.
!!
!! This is the decisive check for a name mismatch: every device zigbee2mqtt knows appears here under its friendly name. Compare the map's relay names (printed in Section 3) against this list — if `Lounge-radiators` is absent, or is present but with a type/model that is not a switchable plug, that is the diagnosis.
Bridge:
    gosub to Section
    ulog `Zigbee bridge at http://127.0.0.1:8889`
    set BridgeUp
    get Response from url `http://127.0.0.1:8889/health`
    or begin
        clear BridgeUp
        ulog `  bridge NOT reachable (is rbr-zigbee-bridge.service running?)`
    end
    if BridgeUp
    begin
        if Response has entry `devices` ulog `  health: ok, ` cat entry `devices` of Response cat ` known device(s)`
        else ulog `  health: ` cat Response
        get Response from url `http://127.0.0.1:8889/devices`
        or begin
            clear BridgeUp
            ulog `  /devices call failed`
        end
    end
    if BridgeUp
    begin
        if Response has entry `devices` put entry `devices` of Response into DeviceMap
        else reset DeviceMap
        if Response has entry `states` put entry `states` of Response into StateMap
        else reset StateMap
        put the keys of DeviceMap into Keys
        set N to 0
        while N is less than the count of Keys
        begin
            put item N of Keys into KeyName
            put entry KeyName of DeviceMap into Device
            ulog `  ` cat KeyName cat `  type=` cat entry `type` of Device cat `  model=` cat entry `model` of Device
            if StateMap has entry KeyName
            begin
                put entry KeyName of StateMap into StateData
                if StateData has entry `state` ulog `      state=` cat entry `state` of StateData
                else ulog `      state=<never reported>`
                if StateData has entry `available` ulog `      available=` cat entry `available` of StateData
                if StateData has entry `last_seen` ulog `      last_seen(s)=` cat entry `last_seen` of StateData
            end
            else ulog `      no cached state (never seen by this bridge process)`
            increment N
        end
    end
    return
!! @hash 0e4a4d50
!!!
!! Section 3 — what the controller believes about each room in the selected profile: mode, target, temperature, status, and the relay name(s) it commands.
!!
!! Temperature is stored in centi-degrees (2420 = 24.2°C). `status` warn/fail with a statusMessage is the relay-failure path the bridge feeds; a room showing `relay: on` with a warn/fail status has been forced off by the safety override in SetRelay.
RoomsSection:
    gosub to Section
    ulog `Rooms from map.json (selected profile)`
    if file `thermometers.json` exists load Thermometers from `thermometers.json`
    else reset Thermometers
    set R to 0
    while R is less than RoomCount
    begin
        put item R of Rooms into Room
        put entry `name` of Room into RoomName
        ulog `--- ` cat RoomName cat ` ---`
        if Room has entry `mode` ulog `  mode=` cat entry `mode` of Room
        if Room has entry `target` ulog `  target=` cat entry `target` of Room
        if Room has entry `relayType` ulog `  relayType=` cat entry `relayType` of Room
        if Room has entry `relay` ulog `  relay (controller decision)=` cat entry `relay` of Room
        if Room has entry `status` ulog `  status=` cat entry `status` of Room
        if Room has entry `statusMessage` ulog `  statusMessage=` cat entry `statusMessage` of Room
        if Room has entry `temperature` ulog `  temperature(centi)=` cat entry `temperature` of Room
        if Room has entry `sensor` ulog `  sensor=` cat entry `sensor` of Room
        if Room has entry `relays`
        begin
            put entry `relays` of Room into Relays
            set J to 0
            while J is less than the count of Relays
            begin
                put item J of Relays into RelayName
                ulog `  relay name #` cat J cat ` = ` cat RelayName
                increment J
            end
        end
        put entry `sensor` of Room into Sensor
        if Thermometers has entry Sensor
        begin
            put entry Sensor of Thermometers into Thermometer
            if Thermometer has entry `temp` ulog `  sensor reading(centi)=` cat entry `temp` of Thermometer cat `  reported(ms)=` cat entry `ts` of Thermometer
            else ulog `  sensor has no reading yet`
        end
        else ulog `  sensor has not registered (thermometers.json has no entry)`
        increment R
    end
    return
!! @hash 4081637d
!!!
!! Section 4 — read-only state query for every relay the map names, straight from the bridge.
!!
!! The bridge's answer here is exactly what the controller's failure detection sees: a body WITH a `state` field is treated as a healthy reply, a body with `error` or no state at all is counted as a relay failure. `{"state":"unknown"}` under the old bridge code means the name matches nothing zigbee2mqtt knows.
RelayQuery:
    gosub to Section
    ulog `Bridge state query for each mapped relay (read-only)`
    set R to 0
    while R is less than RoomCount
    begin
        put item R of Rooms into Room
        put entry `name` of Room into RoomName
        put entry `relays` of Room into Relays
        set J to 0
        while J is less than the count of Relays
        begin
            put item J of Relays into RelayName
            set BridgeUp
            get Response from url `http://127.0.0.1:8889/device/` cat RelayName
            or begin
                clear BridgeUp
                ulog `  ` cat RelayName cat ` -> bridge call failed`
            end
            if BridgeUp
            begin
                if Response has entry `error` ulog `  ` cat RelayName cat ` -> ERROR: ` cat entry `error` of Response
                else if Response has entry `state` ulog `  ` cat RelayName cat ` -> state=` cat entry `state` of Response
                else ulog `  ` cat RelayName cat ` -> no state (treated as relay failure)`
            end
            increment J
        end
        increment R
    end
    return
!! @hash 582d8736
!!!
!! Section 5 — optional single ON command. Leave TestRelay empty (default) to skip; set it to a device name (e.g. `Lounge-radiators`) to send one `state=on` and watch the radiator for a few seconds.
!!
!! This is the same command the controller sends every ~5s, so it cannot make things worse than the controller already does; the response body tells you whether the bridge believes the device switched. The bridge waits up to 2s (new code) for the device to confirm the state change before answering.
RelayTest:
    set TestRelay to empty
    if TestRelay is not empty
    begin
        gosub to Section
        ulog `Sending state=on test command to ` cat TestRelay
        set BridgeUp
        get TestResponse from url `http://127.0.0.1:8889/device/` cat TestRelay cat `?state=on`
        or begin
            clear BridgeUp
            ulog `  bridge call failed`
        end
        if BridgeUp
        begin
            if TestResponse has entry `error` ulog `  response: ERROR ` cat entry `error` of TestResponse
            else if TestResponse has entry `state` ulog `  response: state=` cat entry `state` of TestResponse
            else ulog `  response: no state field (counted as a relay failure)`
        end
        ulog `  now check whether the radiator actually heated up`
    end
    return
!! @hash bba42154
!!!
