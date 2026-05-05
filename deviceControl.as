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
    variable Temp
    variable Time
    variable MasterIPAddr
    variable DeviceName
    variable DeviceMAC
    variable URL
    variable Path
    variable Message
    variable Reply
    variable I
    variable P
    variable N
    variable R
    variable T

!    debug step
    
    ! Comms between thi module and the controller is done with EasyCoder messaging (not MQTT)
    log `Set up the device controller`
    gosub to SetupDeviceController
    on message go to RunController
    release parent
    log `Device controller is ready`
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Set up the controller
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Deal with the heating in a single room
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Send a message to an ESP-Now device
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Send a message to a Zigbee device via the zigbee-bridge HTTP server
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Convert an HH:MM time into a number of seconds
ConvertTimeToInt:
    put `` cat Time into Time
    put the index of `:` in Time into I
    put the value of left I of Time into T
    multiply T by 60
    increment I
    put the value of from I of Time into Time
    add Time to T
    multiply T by 60000 giving Time
    add today to Time
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! Convert a temperature string into a number of hundredths
ConvertTempToInt:
    if Temp is empty put 0 into Temp
    put the index of `.` in Temp into I
    if I is less than 0 multiply Temp by 100
    else
    begin
        put the value of left I of Temp into T
        multiply T by 100
        increment I
        put the value of from I of Temp into Temp
        add T to Temp
    end
    return
