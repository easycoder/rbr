!! Device controller module for RBR. Sits between the main controller (controller.as) and the physical relay devices, translating per-room commands into HTTP calls on either the RBR-Now ESP-Now hub or the local Zigbee bridge.
!!
!! Run as a sub-module of controller.as (via `run ... as DeviceModule`) — communication with the parent is by EasyCoder messaging, not MQTT. The parent stops the module by terminating; there is no explicit shutdown handshake.
!!
!! The script starts by declaring all the variables it uses, then performs basic initialisation: loads config.json to find the master device's IP, registers the on-message handler that routes incoming RoomSpecs, and signals the parent it is ready.
!   deviceControl.as - a script to drive radiator relays and read temperatures

    script DeviceControl
    
    dictionary Config
    dictionary Devices
    dictionary Device
    dictionary RoomSpec
    dictionary Response
    dictionary Values
    list Relays
    list Replies
    list Keys
    variable RoomName
    variable RelayName
    variable RelayType
    variable RelayState
    variable MasterIPAddr
    variable DeviceName
    variable DeviceMAC
    variable URL
    variable Path
    variable Message
    variable Reply
    variable P
    variable N
    variable R

!    debug step
    
    ! Comms between this module and the controller is done with EasyCoder messaging (not MQTT)
    log `Set up the device controller`
    gosub to SetupDeviceController
    on message go to RunController
    release parent
    log `Device controller is ready`
    stop
!! @hash 38eefcfd
!! @verified 38eefcfd
!!!
!! Locate the IP address of the RBR-Now master device and stash it in MasterIPAddr for later HTTP calls by MessageESPDevice.
!!
!! Walks the `devices` dictionary in config.json and picks the one whose `master` flag is true. There is at most one master per system (the only RBR-Now node with a Wi-Fi interface; all others reach it via the private ESP-Now mesh).
!!
!! If no master is present — for example a pure-Zigbee install with no RBR-Now legacy devices — MasterIPAddr is left empty and MessageESPDevice short-circuits silently. Run-time errors only surface when a room is actually configured with `relayType: RBR-Now`.
SetupDeviceController:
    load Config from `config.json`
!    log `Config: ` cat prettify Config
    put entry `devices` of Config into Devices
    put the keys of Devices into Keys
    set N to 0
    while N is less than the count of Keys
    begin
        put item N of Keys into DeviceName
        put entry DeviceName of Devices into Device
        if entry `master` of Device is true
        begin
            put entry `ipaddr` of Device into MasterIPAddr
            ! Force a loop exit
            set N to the count of Keys
        end
        increment N
    end
    return
!! @hash 29131be6
!! @verified 29131be6
!!!
!! Top-level message handler. Invoked by the EasyCoder runtime whenever controller.as sends us a RoomSpec via `send ... to DeviceModule`.
!!
!! Two message shapes are accepted:
!!
!! Request relay (boiler demand): RoomSpec has a `request` entry naming the relay and a `relay state` (`on`/`off`). The request/demand relay is Zigbee — it drives the boiler and lives on the same bridge as the room relays (it was ESP-Now in the original RBR-Now setup, hence the cross-references). We send the requested state to that single Zigbee device and reply with a single-element list.
!!
!! Room relay batch: RoomSpec carries `room name`, `relays` (one or more relay names — most rooms have one but some rooms control multiple radiators in parallel), `relay type` (`RBR-Now` or `Zigbee`), and `relay state`. The loop dispatches each named relay via the appropriate transport (MessageESPDevice for RBR-Now, MessageZigbeeDevice for Zigbee) and collects each device's response into Replies before sending the whole list back.
!!
!! The reply list lets controller.as track each relay individually — empty entries count as failures (incremented into the room's `relayfails`), numeric entries are temperature readings from the relay's own sensor, and string entries are BLE thermometer announcements forwarded by RBR-Now devices.
!!
!! MessageZigbeeDevice reads RelayState (not Message) to build its URL, so for the request-relay path we populate both to match the room-relay path. Each branch ends with `stop` rather than `return` because we are the registered on-message handler — `stop` returns control to the runtime to await the next message without re-entering the script body.
RunController:
!    log `RunController:` cat the message
    put the message into RoomSpec

    ! See if this room is the request relay. The request/demand relay is
    ! Zigbee — it drives the boiler and so lives on the same bridge as the
    ! room relays (was ESP-Now in the original ESP32 + RBR-Now setup).
    ! MessageZigbeeDevice reads RelayState (not Message) to build its URL,
    ! so populate both to match the room-relay path below.
    if RoomSpec has entry `request`
    begin
        put entry `request` of RoomSpec into RelayName
        put entry `relay state` of RoomSpec into RelayState
        put RelayState into Message
        gosub to MessageZigbeeDevice
        reset Replies
        append Reply to Replies
        send Replies to sender
        stop
    end

    ! No, so do a regular room
    put entry `room name` of RoomSpec into RoomName
    put entry `relays` of RoomSpec into Relays
    put entry `relay type` of RoomSpec into RelayType
    put entry `relay state` of RoomSpec into RelayState
    put RelayState into Message
    if RelayState is empty set RelayState to `off`

    reset Replies
    set R to 0
    while R is less than the count of Relays
    begin
        put item R of Relays into RelayName
!        log `Do relay ` cat RelayName cat `type ` cat RelayType cat ` in ` cat RoomName
        if RelayType is `RBR-Now` gosub to MessageESPDevice
        else if RelayType is `Zigbee` gosub to MessageZigbeeDevice
        append Reply to Replies
        increment R
    end
    send Replies to sender
    stop
!! @hash d7af03a5
!! @verified d7af03a5
!!!
!! Send a relay command to an RBR-Now (ESP32) device through the master hub via HTTP, and capture the device's response in Reply.
!!
!! RBR-Now devices live on a private ESP-Now mesh and aren't directly reachable from the LAN — the master is the only node with a Wi-Fi interface, so all traffic is tunnelled through it. The default URL form is `http://<master>/?mac=<short-mac>&msg=<state>`; the master strips its own header and forwards the `msg` payload over ESP-Now to the device identified by `mac`.
!!
!! A device record may carry a `path` entry that overrides the default endpoint, useful for devices running custom firmware that exposes a different URL shape. A comma inside the path acts as a placeholder for the MAC/message insertion point: text left of the comma is appended directly to the master URL, text right of it forms the `&msg=!` payload with the MAC and message comma-joined after it. A path with no comma is appended whole, with the MAC and message tacked on as `!<mac>,<msg>`.
!!
!! Short-circuits silently when MasterIPAddr is empty (no RBR-Now master configured) or when the named relay isn't in the devices dictionary (typo or stale config). Both leave Reply unset, so the caller treats it as a failure.
!!
!! On success the reply's leading `OK` is the master's per-message ack — anything past it carries the device's payload (its own temperature reading, or a BLE thermometer announcement) which controller.as's ProcessReply parses. A non-`OK` response is logged and Reply is cleared so the caller counts it as a failure.
MessageESPDevice:
    if MasterIPAddr is empty return
    if Devices does not have entry RelayName return
    put entry RelayName of Devices into Device
!    log `Send ` cat Message cat ` to ` cat RelayName cat ` at ` cat RoomName
    put entry `ssid` of Device into DeviceMAC
    put right 12 of DeviceMAC into DeviceMAC
    put `http://` cat MasterIPAddr cat `/?mac=` into URL
    if Device has entry `path` put entry `path` of Device into Path else put empty into Path
    if Path is empty put URL cat DeviceMAC cat `&msg=` cat Message into URL
    else
    begin
        put the position of `,` in Path into P
        if P is greater than 0
        begin
            put URL cat left P of Path into URL
            increment P
            put URL cat `&msg=!` cat from P of Path into URL
            put URL cat DeviceMAC cat `,` cat Message into URL
        end
        else put URL cat Path cat `&msg=!` cat DeviceMAC cat `,` cat Message into URL
    end

!    log URL
    ! Send a command by HTTP to the hub device
    get Reply from url URL
    or begin
        log `Message to '` cat RelayName cat `' failed`
        set Reply to empty
        return
    end
    put from 6 of DeviceMAC into DeviceMAC
!    log `?mac=` cat DeviceMAC cat `&msg=` cat Message cat ` -> ` cat Reply
!    log RelayName cat `: msg=` cat Message cat ` -> ` cat Reply
    if left 2 of Reply is not `OK`
    begin
        log `Bad response from ` cat RelayName cat `: ` cat Reply
        set Reply to empty
    end
    return
!! @hash 24fc12ac
!! @verified 24fc12ac
!!!
!! Send a relay command to a Zigbee device via the local zigbee-bridge HTTP server on 127.0.0.1:8889.
!!
!! The bridge translates HTTP to MQTT for zigbee2mqtt and returns the device's reported state as JSON. URL form is `http://127.0.0.1:8889/device/<name>?state=<on|off>`. The device name is the friendly name registered with zigbee2mqtt and must match the relay name in map.json.
!!
!! On success we build a small Values dictionary carrying the device's reported `state` (so the controller can confirm the relay actually flipped) and a placeholder `uptime` of 0, then return that as Reply. On bridge failure (network error, bridge not running) or a response with no `state` field, Reply is left empty so the caller counts it as a relay failure — same as a failed RBR-Now call.
!!
!! No master/IP setup is required here because the Zigbee bridge always runs on localhost. There is currently no equivalent of MessageESPDevice's path/custom-endpoint mechanism; a device is identified solely by its zigbee2mqtt friendly name.
MessageZigbeeDevice:
    put `http://127.0.0.1:8889/device/` cat RelayName cat `?state=` cat RelayState into URL
!    log URL
    get Response from url URL
    or begin
        log `Zigbee bridge call failed for ` cat RelayName
        set Reply to empty
        return
    end
!    log RelayName cat ` ` cat Response
    reset Values
    set entry `uptime` of Values to 0
    if Response has entry `state`
    begin
        set entry `state` of Values to entry `state` of Response
        put Values into Reply
    end
    else set Reply to empty
    return
!! @hash 1f26f342
!! @verified 1f26f342
!!!
