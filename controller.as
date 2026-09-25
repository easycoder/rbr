!! RBR is a heating control system based on Zigbee relays and thermometers, with support for RBR-Now legacy devices.
!!
!! The script starts by declaring all the variables that it uses.
!   controller.as - the main program script

	info `This is the controller script for RBR`

    script Controller

    use mqtt
    use email

    dictionary Credentials
    dictionary CredDict
    dictionary Map
    dictionary Profile
    dictionary Room
    dictionary Period
    dictionary Sender
    dictionary Senders
    dictionary ReceivedMessage
    dictionary Message
    dictionary Thermometers
    dictionary Thermometer
    dictionary Temperatures
    dictionary RoomSpec
    dictionary CalendarDay
    dictionary WaitForConfirmation
    queue MessageQueue
    list Profiles
    list Rooms
    list SenderKeys
    list Replies
    list CalendarData
    topic ServerTopic
    topic SenderTopic
    variable RoomCount
    variable RoomName
    variable RoomIndex
    variable SelectedProfile
    variable TempNow
    variable TempWas
    variable Target
    variable TargetWas
    variable PeriodWas
    variable PeriodActive
    variable Sensor
    variable Relays
    variable RelayType
    variable RelayState
    variable RelayStateWas
    variable SensorFresh
    variable SensorFreshWas
    variable RequestState
    variable RequestStateWas
    variable RequestName
    variable EventCount
    variable LastMapSave
    variable MapHasChanged
    variable HeatingRequested
    variable Simulate
    variable Time
    variable Temp
    variable ImmediateUpdate
    variable UIRequestPending
    variable ConfirmationRequested
    variable StateChanged
    variable MessageText
    variable SenderName
    variable SenderQoS
    variable SenderKey
    variable Reply
    variable Broker
    variable Username
    variable Password
    variable MAC
    variable MailServer
    variable MailLogin
    variable MailPassword
    variable MailFrom
    variable Action
    variable Mode
    variable Value
    variable Value2
    variable ThermometerUpdate
    dictionary ZigbeeTemps
    dictionary ZigbeeTemp
    list ZigbeeTempKeys
    variable ZK
    variable LoopCount
    variable UpdateCount
    variable StartedVersion
    variable CurrentVersion
    variable VersionCheckCounter
    variable DashboardEnabled
    variable WaitCounter
    variable PriorityRoomIndex
    variable TodayWas
    variable RelayFails
    list OldRelayFails
    list NewRelayFails
    list RoomRelays
    list RoomRelayFails
    variable RelayFailsThis
    variable RelayFailsWorst
    variable RelayCount
    variable FailedRelays
    variable BadRelayName
    variable RelayMsg
    variable SensorAge
    variable RoomStatus
    variable PriorStatus
    variable BoostTemp
    variable BoostExpired
    variable BoostStartPeriod
    variable NaturalPeriod
    variable MapFilename
    variable OnTime
    variable OffTime
    variable InPeriod
    variable NaturalPeriodActive
    variable NextAdvanceIdx
    variable NextAdvanceMin
    variable PI
    list PeriodList
    list PeriodSource
    list OverrideKeys
    dictionary Overrides
    dictionary OverrideEntry
    variable TodayKey
    variable OverrideKind
    variable OverrideOn
    variable OverrideDate
    variable OverrideName
    variable OverrideWas
    variable MorningIdx
    variable MorningMin
    variable OB
    variable MI
    variable OI

    ! Reusable variables - but be careful!
    variable I
    variable L
    variable P
    variable R
    variable S
    variable T
    module DeviceModule
    dictionary DashboardData
    dictionary RoomDash
    list DashRooms
    dictionary RequestDash
    variable DashI
    dictionary HeatlogLast
    dictionary HeatlogRow
    variable HeatlogRoot
    variable HeatlogTs
    variable HeatlogTarget
    variable HeatlogActual
    variable HeatlogMode
    variable HeatlogName
    variable HeatlogDirty
!! @hash 09ea8221
!! @verified f7af243f
!!!
!! Basic initialisation.
!! The system can run either with real hardware or wth a simulator. The latter is chosen if a file 'sim' exists.
!    debug step

    if file `sim` exists
    begin
    	set Simulate
        run `simulator.as` as DeviceModule
    end
    else
    begin
    	clear Simulate
        run `deviceControl.as` as DeviceModule
    end

!	Some variables need to be inialised at the start
    set LastMapSave to now
    clear MapHasChanged
    clear ThermometerUpdate
    clear HeatingRequested
    clear UIRequestPending
    reset MessageQueue
    reset ReceivedMessage
    reset Temperatures
    set LoopCount to 0
    set UpdateCount to 0
    set PriorityRoomIndex to -1
    if file `.version` exists load StartedVersion from `.version`
    else set StartedVersion to `0`
    replace ` ` with `` in StartedVersion
    replace newline with `` in StartedVersion
    log `Controller version ` cat StartedVersion
    set VersionCheckCounter to 0
    ! Command-line flag: `allspeak controller.as --no-dashboard` runs without
    ! the terminal dashboard so log output stays visible in a foreground run
    ! (the dashboard repaints the console and hides runtime messages).
    ! Use set/clear (a boolean) rather than 'yes'/'no' strings: `if X` is true
    ! for ANY non-empty string, so `put 'no' into X` never disabled anything.
    set DashboardEnabled
    if argc is greater than 0
    begin
        if arg 0 is `--no-dashboard` clear DashboardEnabled
    end
!! @hash 5d76167c
!! @verified ccb83ebf
!!!
!! Load credentials and set up MQTT. Credentials come from the server unless a local 'credentials' file exists.
!!
!! The system is identified by its MAC address. This is found using the 'ip link' command (Linux only) but can be overridden by a file '.mac_override' if the controller needs to run on a different host but still access the same system data.
!   Load credentials
	if file `credentials` exists load Credentials from `credentials`
    else
    begin
	    get Credentials from url `https://rbrheating.com/credentials.php`
    	    or go to NoCredentials
    end
    put json Credentials into CredDict
    put entry `broker` of CredDict into Broker
    put entry `username` of CredDict into Username
    put entry `password` of CredDict into Password
    put entry `mail_server` of CredDict into MailServer
    put entry `mail_login` of CredDict into MailLogin
    put entry `mail_password` of CredDict into MailPassword
    put entry `mail_from` of CredDict into MailFrom

    if file `.mac_override` exists
    begin
        load MAC from `.mac_override`
        put trim MAC into MAC
        log `MAC address overridden to ` cat MAC
    end
    else
    begin
        put system `ip link show $(ip route show default | awk '{print $5}') | awk '/ether/ {print $2}'` into MAC
        if MAC is empty
        begin
            log `Unable to get my MAC address`
            exit
        end
        put trim MAC into MAC
        log `MAC address is ` cat MAC
    end

!    log `Broker is ` cat Broker
!    log `Username is ` cat Username
!    log `Password is ` cat Password
!    log `MAC is ` cat MAC

    ! Set up MQTT
    init ServerTopic
        name MAC
        qos 1

    mqtt
        token Username Password
        id uuid
        broker Broker
        port 1883
        subscribe ServerTopic
    
    on mqtt connect go to Start
    on mqtt message
    begin
        put the mqtt message into ReceivedMessage
        if entry `action` of ReceivedMessage is `uirequest` set UIRequestPending
        append ReceivedMessage to MessageQueue
    end
    stop
!! @hash dec90b28
!! @verified 39624871
!!!
!! Missing credentials signifies a non-recoverable error
!   The main start point.
NoCredentials:
    log `Error: Unable to load credentials from file or server`
    exit
!! @hash 13655ac1
!! @verified 13655ac1
!!!
!! Start by getting the thermometer data and the name of the request/demand relay if there is one.
!!
!! Check if a new version is available, then process the room list.
Start:
    gosub to LoadMap
    put entry `profiles` of Map into Profiles
    put entry `profile` of Map into SelectedProfile
    if file `thermometers.json` exists load Thermometers from `thermometers.json`
    else reset Thermometers

    ! Heat logging. Enabled when a `heatlog-root` file in the working
    ! directory names the data root (one line: an absolute path — on the
    ! controller a partition mount, on test machines a symlink to a local
    ! directory). heatlog-state.json holds each room's last logged
    ! target/actual/mode so a restart doesn't re-log the current state.
    set HeatlogRoot to empty
    if file `heatlog-root` exists
    begin
        load HeatlogRoot from `heatlog-root`
        replace newline with `` in HeatlogRoot
        ! The writer ships in the release tarball; if it has not reached
        ! this machine yet (e.g. an update that predates heatlog.py),
        ! disable logging with a clear warning rather than failing
        ! silently on every change.
        if file `heatlog.py` exists log `Heat logging enabled, root ` cat HeatlogRoot
        else
        begin
            log `Heat logging disabled: heatlog.py not found (release not fully applied?)`
            set HeatlogRoot to empty
        end
    end
    else log `Heat logging disabled (no heatlog-root file)`
    if file `heatlog-state.json` exists load HeatlogLast from `heatlog-state.json`
    else reset HeatlogLast
    clear HeatlogDirty

    if Map has entry `request` set RequestName to entry `request` of Map
    else set RequestName to empty
    set RequestState to `off`
    set RequestStateWas to `off`

!   Walk the list of rooms and process the needs of each one
    gosub to ProcessAllRooms
!! @hash 61f2c635
!! @verified 2e5e5cad
!!!
!! This is the head of each loop.
!! It waits 5 seconds between runs. This can be adjusted but 5 seconds seems optimal.
!!
!! Day-rollover check: ResolveCalendarProfile only runs inside ProcessAllRooms, so without an explicit midnight detection the controller keeps processing yesterday's profile until a UI action re-triggers it. A `today` comparison at the top of each cycle catches the rollover and refreshes the profile.
!!
!! If a room has priority (e.g. is waiting for an immediate response), process it before entering the main loop.
!!
!! Process each room, setting its radiator controller(s) ON or OFF according to the system logic.
!!
!! Process the request/demand relay. Note: the simulator does not have a request relay.
!!
!! Build and output a coloured terminal dashboard showing relay state, temperature, humidity, battery, and any warnings for each room — one `system background` call per cycle runs the Python dashboard renderer. Skipped entirely when run with `--no-dashboard` (a command-line flag added 2026-08-30 so foreground runs show log output instead of the repainting dashboard — see the flag handling in the initialisation block).
!!
!! Finally, if an immediate update was requested, notify the system that the map has changed, so the UIs will get updates without having to wait for the normal update cycle to complete.
MainLoop:
    ! log `MainLoop`
    ! Detect a day rollover. ResolveCalendarProfile only runs inside
    ! ProcessAllRooms, so without this the controller would keep
    ! processing yesterday's profile until a UI action re-triggered it.
    if today is not TodayWas
    begin
        log `Day rollover detected; refreshing profile selection`
        ! Retire any one-off override whose morning has now passed before
        ! the profile is re-resolved, so the UI learns the badge has gone.
        gosub to PruneOverrides
        gosub to ProcessAllRooms
    end

    ! If the updater (rbr-updater.py) has applied a new release, .version
    ! changes on disk. We are still running the old in-memory code, so log
    ! and exit — controller.service restarts us (or the operator restarts a
    ! manual run) and we come back with the new code.
    increment VersionCheckCounter
    if VersionCheckCounter is greater than 12
    begin
        set VersionCheckCounter to 0
        if file `.version` exists load CurrentVersion from `.version`
        replace ` ` with `` in CurrentVersion
        replace newline with `` in CurrentVersion
        if CurrentVersion is not StartedVersion
        begin
            log `Update applied: version ` cat StartedVersion cat ` -> ` cat CurrentVersion
            log `Restarting to load the new code`
            exit
        end
    end

    ! Wait for 5 seconds
    set WaitCounter to 50
    while WaitCounter is greater than 0
    begin
        wait 10 ticks
        decrement WaitCounter
        ! Short-circuit if a message arrives or an immediate update is requested
        if MessageQueue is not empty go to HandleMessages
        if ImmediateUpdate set WaitCounter to 0
        ! If the map has changed, update the UI now
        if Map is empty gosub to LoadMap
        if MapHasChanged
        begin
!            log `Update map from MainLoop`
            gosub SendMapToUI
        end
    end

    ! log `Repeat ` cat LoopCount
    increment LoopCount
    put PriorityRoomIndex into P
    if P is not less than 0
    begin
        if P is less than RoomCount
        begin
            if UIRequestPending go to HandleMessages
            index Room to P
            index TargetWas to P
            index PeriodWas to P
            index PeriodActive to P
            index RelayStateWas to P
            index SensorFreshWas to P
            set RoomIndex to P
            gosub to ProcessRoom
        end
    end
    ! Examine the state of each room
    put 0 into R
    while R is less than RoomCount
    begin
        if UIRequestPending go to HandleMessages
        if R is not P
        begin
            index Room to R
            index TargetWas to R
            index PeriodWas to R
            index PeriodActive to R
            index RelayStateWas to R
            index SensorFreshWas to R
            set RoomIndex to R
            gosub to ProcessRoom
        end
        increment R
    end
    set PriorityRoomIndex to -1
    ! Do the 'request' relay
    if not Simulate gosub to ProcessRequestRelay

    ! Build and refresh the terminal dashboard with current room states.
    ! Skipped in simulation mode since the simulator has its own display.
    if not Simulate
    begin
        reset DashRooms
        put 0 into DashI
        while DashI is less than RoomCount
        begin
            index Room to DashI
            reset RoomDash
            set entry `name` of RoomDash to entry `name` of Room
            if Room has entry `relay` set entry `relay` of RoomDash to entry `relay` of Room
            if Room has entry `temperature` set entry `temperature` of RoomDash to entry `temperature` of Room
            if Room has entry `humidity` set entry `humidity` of RoomDash to entry `humidity` of Room
            if Room has entry `battery` set entry `battery` of RoomDash to entry `battery` of Room
            if Room has entry `status` set entry `status` of RoomDash to entry `status` of Room
            if Room has entry `sensorAge` set entry `sensorAge` of RoomDash to entry `sensorAge` of Room
            if Room has entry `statusMessage` set entry `statusMessage` of RoomDash to entry `statusMessage` of Room
            append RoomDash to DashRooms
            increment DashI
        end
        set entry `rooms` of DashboardData to DashRooms
        reset RequestDash
        if RequestName is not empty
        begin
            set entry `name` of RequestDash to RequestName
            set entry `relay` of RequestDash to RequestState
            set entry `status` of RequestDash to `good`
            set entry `request` of DashboardData to RequestDash
        end
        set entry `timestamp` of DashboardData to now
        if DashboardEnabled
        begin
            save prettify DashboardData to `/tmp/rbr-dashboard.json`
            ! Relative on purpose: the renderer ships next to this script and the
            ! controller is always started from the install directory (the
            ! systemd unit sets WorkingDirectory; manual runs are 'cd ~/rbr &&
            ! allspeak controller.as'). An absolute path here only ever worked
            ! on the one machine whose home directory it named, so every other
            ! install logged 'can't open file' on each dashboard refresh. The
            ! service unit passes --no-dashboard: a headless service has no
            ! terminal to paint, so the JSON is all that matters there.
            system background `python3 rbr-dashboard.py`
        end
    end

    ! Signal the map has changed
    if ImmediateUpdate
    begin
        set MapHasChanged
        clear ImmediateUpdate
    end
!! @hash fbaf46c7
!! @verified ce47a848
!!!
!! Drain the queue of messages received from the UI between MainLoop ticks.
!!
!! Four action types: `first` (one-shot at UI startup, triggers a full map push), `refresh` (10-second heartbeat from each connected UI — any reply doubles as a round-trip alive signal feeding the UI's heartbeat dot and stall-detection watchdog), `uirequest` (a user action handed off to ProcessUIRequest), and `sendemail` (registration/recovery email relay).
!!
!! Once a minute we also pull the latest Zigbee thermometer readings from the bridge's zigbee-temperatures.json before flushing Thermometers back to disk. The merge lives here rather than in MainLoop's body so it isn't starved when a busy UI keeps short-circuiting the 5-second wait via `go to HandleMessages`. Without RBR-Now devices in play, this is the only path that updates Thermometers — RBR-Now installs get a parallel update from RecordThermometer during room processing.
!!
!! Map and thermometer files are flushed to disk at most once a minute. Senders silent for more than 100 seconds are dropped from the recipient list so we stop pushing updates to disconnected UIs.
HandleMessages:
    ! Check for incoming messages from the UI
    ! There are 3 Action types; `first`, `refresh` and `uirequest`
    ! The first of these is sent just once by the UI
    ! The second are sent every 10 seconds by the UI
    ! The third is send by the UI to inform the backend about a user action in the UI
    while MessageQueue is not empty
    begin
        pop ReceivedMessage from MessageQueue
!        log ReceivedMessage
        put entry `sender` of ReceivedMessage into Sender
        ! Senders arrive in three shapes: a real object (JS UI), a JSON
        ! string of the topic object (Python runtime / desktop app — e.g.
        ! '{"name": "RBR-desktop-123", "qos": 1}'), or a bare string
        ! (raw probes). Normalise them all to a dictionary so the
        ! `set entry ... of Sender` calls below can't crash on a str.
        ! (2026-08-30: the controller crashed on the string forms. Note:
        ! `put json` is lenient — a bare string passes through unchanged —
        ! and `is object` can't be used to test for a dict, so the check
        ! is `has entry 'name'` after the parse.)
        put json Sender into Sender
        if Sender has no entry `name`
        begin
            put entry `sender` of ReceivedMessage into SenderName
            put `{}` into Sender
            set entry `name` of Sender to SenderName
            set entry `qos` of Sender to 1
        end
        put entry `name` of Sender into SenderName
        set entry `last` of Sender to now
        ! Build a dictionary of senders
        set entry SenderName of Senders to Sender
        put entry `action` of ReceivedMessage into Action
        put entry `message` of ReceivedMessage into Message
        if Action is `first`
        begin
            set MapHasChanged
            set StateChanged
!            log `Update map from 'first'`
            gosub to SendMapToUI
        end
        else if Action is `refresh`
        begin
            ! Refresh acts as a heartbeat. If the map changed, push the
            ! full map to all senders. Otherwise reply with an empty
            ! message to just the requester — the UI uses any reply as
            ! a "round-trip is alive" signal driving its heartbeat dot
            ! and stall-detection watchdog.
            if MapHasChanged
            begin
                gosub to SendMapToUI
            end
            else
            begin
                set MessageText to empty
                gosub to SendMessage
            end
        end
        else if Action is `uirequest` gosub to ProcessUIRequest
        else if Action is `sendemail` gosub to SendEmail
    end
    clear UIRequestPending

    ! Refresh Zigbee thermometers and save files, once a minute.
    add 60000 to LastMapSave giving T
    if T is less than now
    begin
        ! Merge Zigbee thermometer data if available. Pairing this with
        ! the save tick (rather than running it every MainLoop cycle)
        ! guarantees Thermometers is refreshed at the same cadence as
        ! thermometers.json is flushed, even when the wait loop in
        ! MainLoop keeps short-circuiting before reaching its body.
        if file `zigbee-temperatures.json` exists
        begin
            load ZigbeeTemps from `zigbee-temperatures.json`
            put the keys of ZigbeeTemps into ZigbeeTempKeys
            set ZK to 0
            while ZK is less than the count of ZigbeeTempKeys
            begin
                put item ZK of ZigbeeTempKeys into Value
                put entry Value of ZigbeeTemps into ZigbeeTemp
                set entry Value of Thermometers to ZigbeeTemp
                increment ZK
            end
            set ThermometerUpdate
        end
!        log `Save the map`
        if Simulate save prettify Map to `map-sim.json` else save prettify Map to `map.json`
        put now into LastMapSave
        if ThermometerUpdate save prettify Thermometers to `thermometers.json`
        ! Persist heat-log change state once a minute (single writer) so a
        ! restart resumes change detection without re-logging current state.
        if HeatlogDirty
        begin
            save prettify HeatlogLast to `heatlog-state.json`
            clear HeatlogDirty
        end
    end

    ! If no messages have beeen received for 60 seconds, remove the sender from the list
    put the keys of Senders into SenderKeys
    set S to 0
    while S is less than the count of SenderKeys
    begin
        put item S of SenderKeys into SenderKey
        put entry SenderKey of Senders into Sender
        put entry `last` of Sender into T
        add 100000 to T
        if now is greater than T
        begin
            put entry `name` of Sender into SenderName
            if Senders has entry SenderName delete entry SenderName of Senders
        end
        increment S
    end
    go to MainLoop
!! @hash c3d77012
!! @verified b8cec348
!!!
!! Load the system map from disk, or build a fresh default map if the file is absent.
!!
!! Honours the simulate flag by reading map-sim.json instead of map.json. The default map has a single empty `Default` profile so the UI has something coherent to render at first launch.
LoadMap:
    log `Load the system map`
    if Simulate set MapFilename to `map-sim.json` else set MapFilename to `map.json`
    if file MapFilename exists load Map from MapFilename
    else
    begin
        reset Map
        reset Profiles
        reset Profile
        set entry `name` of Profile to `Default`
        reset Rooms
        set entry `rooms` of Profile to Rooms
        append Profile to Profiles
        set entry `profiles` of Map to Profiles
        set entry `profile` of Map to 0
        set entry `calendar` of Map to `off`
        set entry `calendar-data` of Map to `[]`
        set entry `name` of Map to `New System`
    end
    set MapHasChanged
    return
!! @hash e3869999
!! @verified e3869999
!!!
!! When the calendar feature is on, override SelectedProfile with the profile assigned to today's weekday.
!!
!! Uses Monday=0 weekday numbering to match how calendar-data is indexed in the map. A no-op when the calendar is off, when calendar-data is missing, or when the day's profile name doesn't resolve to any profile in the list.
!!
!! After testing that the calendar has an entry for the current day, the code looks up the profile held for that day, and checks it against the list of profiles. If one matches it is returned in SelectedProfile as the profile to use. 
ResolveCalendarProfile:
    if entry `calendar` of Map is not `on` return
    if Map has entry `calendar-data`
    begin
        put weekday into Value
        put entry `calendar-data` of Map into CalendarData
        put item Value of CalendarData into CalendarDay
        if CalendarDay is not empty
        begin
            put entry `day` cat Value cat `-profile` of CalendarDay into Value2
            if Value2 is not empty
            begin
                put the count of Profiles into L
                put 0 into I
                while I is less than L
                begin
                    put item I of Profiles into CalendarDay
                    if entry `name` of CalendarDay is Value2 put I into SelectedProfile
                    increment I
                end
            end
        end
    end
    return
!! @hash fd56a9bc
!! @verified fd56a9bc
!!!
!! Re-bind the per-room state arrays to the currently-selected profile and reset transient flags before a full processing cycle.
!!
!! Called once at startup and after any UI action that changes the active profile or rooms list (Update Rooms, Select Profile, Update Profiles).
!!
!! Sizes the parallel TargetWas/PeriodWas/PeriodActive/RelayStateWas/SensorFreshWas arrays to match the new room count, clears stale advance-rq/boost/responses entries, and seeds PeriodWas from each room's current natural period (via GetNaturalPeriod) so ApplyPeriodsAdvance's roll-over check works on the very next cycle — including the case where Advance was engaged in background time (where the previous -1 sentinel would have blocked auto-cancel). Also stamps TodayWas so MainLoop's day-rollover detector has a baseline.
ProcessAllRooms:
    gosub to ResolveCalendarProfile
    put item SelectedProfile of Profiles into Profile
    put entry `rooms` of Profile into Rooms
    put the count of Rooms into RoomCount
    set the elements of Room to RoomCount
    set the elements of TargetWas to RoomCount
    set the elements of PeriodWas to RoomCount
    set the elements of PeriodActive to RoomCount
    set the elements of RelayStateWas to RoomCount
    set the elements of SensorFreshWas to RoomCount

    set R to 0
    while R is less than RoomCount
    begin
        index Room to R
        put item R of Rooms into Room

        ! Housekeeping
        delete entry `advance-rq` of Room
        delete entry `boost` of Room
        delete entry `responses` of Room

        ! Initialisation

        index PeriodWas to R
        ! Seed PeriodWas with the room's *current* natural period instead
        ! of the -1 sentinel, so ApplyPeriodsAdvance's roll-over check
        ! works on the very next cycle. (A -1 sentinel collides with the
        ! legitimate "in background" value and blocks the auto-cancel for
        ! Advance engaged outside any period.)
        gosub to GetNaturalPeriod
        set PeriodWas to NaturalPeriod
        index PeriodActive to R
        set PeriodActive to 0
        index RelayStateWas to R
        set RelayStateWas to empty
        ! SensorFreshWas starts unknown so each room's first processed cycle
        ! counts as a transition and pushes one map to any UI already
        ! connected. Harmless — the UI receives a map on `first` regardless —
        ! and it means a room that is already stale at startup is reported as
        ! such rather than silently appearing healthy.
        index SensorFreshWas to R
        set SensorFreshWas to empty
        index TargetWas to R
        set TargetWas to 0
        increment R
    end
    set TodayWas to today
    return
!! @hash 83aef399
!! @verified 09455c73
!!!
!! Run one control cycle for a single room: read its current temperature, apply the active mode to derive a target, send a relay command to the device controller, and store the outcome on the Room dictionary for the UI.
!!
!! Mode handling:
!! `timed` consults the room's schedule via FindCurrentPeriod and ApplyPeriodsAdvance.
!!
!! `on` uses the room's stored target.
!!
!! `boost` runs at the boost target until either the `until` timestamp expires or the natural period rolls over (then auto-reverts to prevmode).
!!
!! `off` forces the relay off.
!!
!! A boost engaged mid-period latches `boostperiod` so it doesn't self-cancel on its own first cycle.
!!
!! Sensor staleness: if the configured thermometer hasn't reported within 45 minutes the current reading is treated as missing, the relay is forced off (which in most cases will soon trigger a temperature change to be posted), and the last known temperature is preserved on the Room so the UI can show it greyed out rather than blank. Boost mode bypasses this gate (the `until` timestamp is the safety bound). A flip in freshness also marks the map changed, so connected UIs learn that the status moved without waiting for the temperature itself to differ.
!!
!! Falls through to ProcessReply, which folds the device's reply back into the Room.
ProcessRoom:
    put entry `name` of Room into RoomName
    put entry `sensor` of Room into Sensor
    reset RoomSpec
!    log `Process ` cat RoomName

    ! Get the current temperature
    if Simulate
    begin
        put entry `temperature` of Room into TempNow
        if TempNow is not numeric
        begin
            put TempNow into Temp
            gosub to ConvertTempToInt
            put Temp into TempNow
        end
    end
    else
    begin
        set TempNow to empty
        ! Check all the thermometers that have registered
        if Thermometers has entry Sensor
        begin
            put entry Sensor of Thermometers into Thermometer
            put entry `ts` of Thermometer into T
            ! Staleness gate: if last report is older than 45 min (the warn
            ! threshold) we treat the room as having no current reading,
            ! which leaves TempNow empty and hence forces the relay off in
            ! SetRelay. Mirrors RoomStatus's `warn` threshold below.
            add 2700000 to T
            if T is greater than now
            begin
                set TempNow to entry `temp` of Thermometer
                set entry `battery` of RoomSpec to entry `batt` of Thermometer
                ! Surface battery and humidity on the Room itself so the
                ! map sent to the UI carries the latest reading. Humidity
                ! is optional (only some thermometers report it).
                set entry `battery` of Room to entry `batt` of Thermometer
                if Thermometer has entry `hum`
                    set entry `humidity` of Room to entry `hum` of Thermometer
            end
            ! else log RoomName cat ` sensor ` cat Sensor cat ` has not reported recently`
        end
        ! else log RoomName cat ` sensor ` cat Sensor cat ` has not yet reported`
    end
    ! A flip in FRESHNESS is itself a UI-visible change. MapHasChanged used to
    ! be set only when the temperature VALUE changed (see below), so a sensor
    ! resuming after a long gap with the same reading left every open UI still
    ! showing the soft "No recent change" warning until something else moved —
    ! the warning outlived the condition it describes. Tracking the flip lets
    ! the next UI heartbeat (10s) carry a fresh map and clear the warning.
    set SensorFresh to 1
    if TempNow is empty set SensorFresh to 0
    if SensorFresh is not SensorFreshWas
    begin
        set MapHasChanged
        put SensorFresh into SensorFreshWas
    end

    put entry `temperature` of Room into TempWas
    ! Preserve the last known reading when TempNow is empty (sensor stale).
    ! Status moves to `warn` on its own which both forces the relay off in
    ! SetRelay and lets the UI show a soft "no recent change" warning over
    ! the last known value, instead of blanking the temperature display.
    if TempNow is not empty
    begin
        set entry `temperature` of Room to TempNow
        if TempNow is not TempWas
        begin
            ! log RoomName cat `: temp changed ` cat TempWas cat ` -> ` cat TempNow
            set MapHasChanged
        end
    end
    put entry `relays` of Room into Relays
    put entry `relayType` of Room into RelayType
    put entry `relay` of Room into RelayState
    put entry `mode` of Room into Mode

    ! Deal with the various operating modes
    if Mode is `timed` gosub to FindCurrentPeriod
    else if Mode is `on`
    begin
        put entry `target` of Room into Temp
        gosub to ConvertTempToInt
        put Temp into Target
    end
    else if Mode is `boost`
    begin
        clear BoostExpired

        ! Time-based expiry (the controller-side `until` timestamp).
        put entry `until` of Room into T
        if T is not empty
        begin
            if T is not greater than now set BoostExpired
        end

        ! Period-boundary expiry — mirror the existing Advance auto-cancel
        ! at schedule boundaries. We latch the natural period at boost-
        ! start (`boostperiod`) on the first cycle so a boost engaged
        ! mid-period doesn't immediately self-cancel; subsequent cycles
        ! cancel as soon as the natural period rolls. Rooms with no
        ! `periods` skip this check.
        if not BoostExpired
        begin
            if Room has entry `periods`
            begin
                gosub to GetNaturalPeriod
                if Room has entry `boostperiod`
                begin
                    put entry `boostperiod` of Room into BoostStartPeriod
                    if NaturalPeriod is not BoostStartPeriod set BoostExpired
                end
                else set entry `boostperiod` of Room to NaturalPeriod
            end
        end

        if BoostExpired
        begin
            ! Revert to previous mode.
            if Room has entry `prevmode`
                set entry `mode` of Room to entry `prevmode` of Room
            else set entry `mode` of Room to `timed`
            delete entry `until` of Room
            delete entry `prevmode` of Room
            delete entry `boostperiod` of Room
            ! log RoomName cat `: Boost expired, reverting to ` cat entry `mode` of Room
            gosub to ForceUpdate
            put entry `mode` of Room into Mode
            if Mode is `timed` gosub to FindCurrentPeriod
            else if Mode is `on`
            begin
                put entry `target` of Room into Temp
                gosub to ConvertTempToInt
                put Temp into Target
            end
            else
            begin
                set Mode to `off`
                set RelayState to `off`
            end
            go to BoostDone
        end
        put entry `target` of Room into Temp
        gosub to ConvertTempToInt
        put Temp into Target
    end
    else
    begin
        set Mode to `off`
        set RelayState to `off`
    end
BoostDone:
    if TempNow is empty set RelayState to `off`

    ! Compute the desired relay state now so the device command
    ! in this cycle carries the latest ON/OFF/timed decision.
    gosub to SetRelay

    ! Record heating data on any change to target, actual, or mode.
    if HeatlogRoot is not empty gosub to HeatlogRecord

    ! Build a pack of data and send it to the device controller or the simulator
    ! It will open/close the relay and return the current temperature of the room
    set entry `room name` of RoomSpec to RoomName
    set entry `temperature` of RoomSpec to TempNow
    set entry `relays` of RoomSpec to Relays
    set entry `relay type` of RoomSpec to RelayType
    set entry `relay state` of RoomSpec
    to RelayState
!    log RoomName cat ` ` cat RelayState
    ! Send the RoomSpec packet to the device controller using EasyCoder messaging (not MQTT)
    put TempNow into TempWas
    send RoomSpec to DeviceModule and assign reply to Replies
!! @hash a6c6d222
!! @verified 5b7749f8
!!!
!! Fold the device controller's reply back into the Room state and re-decide the relay.
!!
!! The reply is a list with one entry per slot: an integer is a fresh temperature reading from the relay's own sensor, an empty value indicates a relay failure, and any other string is a BLE thermometer announcement we hand to RecordThermometer. Failures are counted per relay into `relayfails` (a list parallel to the room's `relays`); each relay's count is reset only by that relay answering, so a dead relay cannot be masked by a healthy sibling in the same room. RoomStatus turns the counts into warn/fail (all relays down) or `partial` (some down).
!!
!! After folding, SetRelay runs again so any updated temperature is reflected in the relay decision.
!!
!! Reused: also called via gosub from ProcessRequestRelay so the request relay's reply gets the same treatment.
ProcessReply:
    if Replies is not empty
    begin
!       Track relay response quality PER RELAY. `relayfails` is a list
!       parallel to the room's `relays`, holding each relay's consecutive
!       failure count. A relay that answers resets only its OWN count, so a
!       dead relay can no longer be masked by a healthy sibling (a single
!       room-wide counter was zeroed by any healthy reply, which is why a
!       dead relay in a multi-relay room never surfaced).
        reset OldRelayFails
        if Room has entry `relayfails`
        begin
            put entry `relayfails` of Room into RelayFails
!           Legacy maps stored one room-wide number for the whole room; it
!           is discarded rather than copied, so a big stale count cannot
!           flag every relay on the first cycle after this change.
            if RelayFails is not numeric put RelayFails into OldRelayFails
        end
        reset NewRelayFails
        put 0 into I
        while I is less than the count of Replies
        begin
            put 0 into RelayFailsThis
            if I is less than the count of OldRelayFails put item I of OldRelayFails into RelayFailsThis
            put item I of Replies into Value
            if Value is empty
            begin
                increment RelayFailsThis
            end
            else
            begin
                set RelayFailsThis to 0
                if Value is numeric put Value into TempNow
                else
                begin
                    put Value into Reply
                    if Reply is not empty gosub to RecordThermometer
                end
            end
            append RelayFailsThis to NewRelayFails
            increment I
        end
        set entry `relayfails` of Room to NewRelayFails
        if TempNow is not empty set entry `temperature` of Room to TempNow
        gosub to SetRelay
    end
    go to RoomStatus
!! @hash 931c8b52
!! @verified 63064a79
!!!
!! Drive the optional boiler request relay that turns the central heat source on whenever any room is demanding heat.
!!
!! HeatingRequested is set during SetRelay for any room whose relay went on this cycle; we read it here and reset it for the next cycle.
!!
!! The decided state is captured into RequestState so the terminal dashboard's RequestDash row shows the real request-relay state. It must be captured here, before the send: the final SetRelay run inside ProcessReply re-decides the last processed room and overwrites RelayState, and RequestState is read by the dashboard build later in the same cycle.
!!
!! Skipped entirely in simulation mode and on systems with no request relay configured.
ProcessRequestRelay:
    if RequestName is empty log `No request relay`
    else
    begin
        if HeatingRequested put `on` into RelayState else put `off` into RelayState
        ! Capture the decision for the dashboard — RequestState is read
        ! when the RequestDash row is built in MainLoop, and RelayState is
        ! clobbered by the final SetRelay run in ProcessReply below.
        put RelayState into RequestState
        clear HeatingRequested
!        log RequestName cat `: ` cat RelayState
        reset RoomSpec
        set entry `request` of RoomSpec to RequestName
        set entry `relay state` of RoomSpec to RelayState
        send RoomSpec to DeviceModule and assign reply to Replies
        gosub to ProcessReply
    end
    return
!! @hash fe034a6a
!! @verified ea51e1af
!!!
!! Decide whether this room's relay should be on or off this cycle, based on mode, target, current temperature, and prior status.
!!
!! Read the previous cycle's status as a safety override. If the room was already classified as `warn` (stale sensor or repeated relay failures) or `fail`, we leave the relay off regardless of mode or current temperature reading. This belt-and-braces protects against paths that could keep TempNow populated past the staleness gate (e.g. an RBR-Now relay reporting its own temperature when the configured thermometer is dead).
!!
!! Boost is the one mode that bypasses the staleness lockout: it's a user-initiated, time-bounded override (the `until` timestamp is the safety bound). For linked boost rooms we still honour the target where we have any temperature data — last known reading on the room itself if TempNow has been emptied by the staleness gate. With no temperature data at all, default the relay to ON so a boost on a never-reported sensor still produces heat for its bounded duration.
!!
!! Safety overrides come first: a prior `warn`/`fail` status (from staleness or repeated relay failures) forces relay off regardless of mode, so a dead sensor cannot leave heat permanently on. Boost mode is the one exception — it's a user-initiated, time-bounded override (the `until` timestamp is the safety bound) and runs even when no temperature data is available at all.
!!
!! Unlinked relays (`linked: no`) are driven directly by mode rather than by target/temperature. For a linked room in `on` or `timed` mode, the relay turns on if the current temperature is below the target. SetRelay also signals the boiler request via HeatingRequested.
!!
!! Falls through to RoomStatus.
SetRelay:
    put RelayState into RelayStateWas
    put empty into PriorStatus
    if Room has entry `status` put entry `status` of Room into PriorStatus
    if Mode is `off` set RelayState to `off`
    else if Mode is `boost`
    begin
        if entry `linked` of Room is `no` set RelayState to `on`
        else
        begin
            put TempNow into BoostTemp
            if BoostTemp is empty put entry `temperature` of Room into BoostTemp
            ! Normalise to integer hundredths if the source provided
            ! a "X.Y" string (the simulator path can leave Room.temperature
            ! in that form).
            if BoostTemp is not empty
            begin
                if BoostTemp is not numeric
                begin
                    put BoostTemp into Temp
                    gosub to ConvertTempToInt
                    put Temp into BoostTemp
                end
            end
            if BoostTemp is empty set RelayState to `on`
            else if BoostTemp is less than Target set RelayState to `on`
            else set RelayState to `off`
        end
    end
    else if PriorStatus is `warn` set RelayState to `off`
    else if PriorStatus is `fail` set RelayState to `off`
    else if entry `linked` of Room is `no`
    begin
        ! Unlinked relays are driven directly by mode, not by target/temperature.
        if Mode is `on` set RelayState to `on`
        else set RelayState to `off`
    end
    else
    begin
!        log RoomName cat ` ` cat TempNow cat `/` cat Target
        set RelayState to `off`
        if TempNow is not empty
        begin
            if TempNow is less than Target set RelayState to `on`
        end
    end
    set entry `relay` of Room to RelayState
    if RelayState is `on` set HeatingRequested

    ! Update the room record. Temperature is left alone when TempNow is
    ! empty so the UI can keep showing the last known reading.
    if TempNow is not empty set entry `temperature` of Room to TempNow
    set entry `relay` of Room to RelayState
    set entry `period` of Room to PeriodActive
!! @hash d2926dac
!! @verified d2926dac
!!!
!! Compute the room's health status (`good` / `warn` / `fail` / `partial`) and a human-readable status message for the UI.
!!
!! Forces an immediate UI update on either a period change (advance off) or a relay-state change so the UI sees these promptly rather than waiting for the next 5-second tick.
!!
!! Relay health comes from the per-relay failure counts in `relayfails` (a list parallel to the room's `relays`). ALL relays failing > 5 cycles is `warn`, > 20 is `fail` — SetRelay forces the relays off for those, as before. Only SOME relays failing is `partial`: the room can still heat from the working relay(s), so it is flagged for the UI without the force-off, and the message names the relay that is not answering.
!!
!! Sensor staleness > 45 min -> warn, > 60 min -> fail. The 45-minute warn threshold matches the staleness gate in ProcessRoom that empties TempNow, so a stale sensor and a `warn` status both force the relay off at the same point. SensorAge is surfaced on Room so the UI can show "N min ago".
!!
!! Falls through to UpdateRooms.
RoomStatus:
    if Mode is `timed`
    begin
        if PeriodActive is not PeriodWas and entry `advance` of Room is not `A`
        begin
!            log RoomName cat `: Period ` cat PeriodWas cat `->` cat PeriodNow
!                 cat ` ` cat entry `advance` of Room
            ! log `Force an update (period change)`
            gosub to ForceUpdate
        end
    end
    if RelayState is not RelayStateWas
    begin
!        log RoomName cat `: RelayState ` cat RelayStateWas cat `->` cat RelayState
        put RelayState into RelayStateWas
        gosub to ForceUpdate
    end

!   Compute room status based on relay failures and thermometer staleness
    put `good` into RoomStatus

!   Check relay health. `relayfails` is a list parallel to the room's
!   `relays`, one consecutive-failure count per relay. A room whose relays
!   are ALL failing is a full failure (warn, then fail — SetRelay forces the
!   relays off, as before). When only SOME relays fail, the room is
!   `partial`: it can still heat from the working radiator(s), so the status
!   is surfaced to the UI but does NOT trigger SetRelay's force-off.
    put 0 into RelayFailsWorst
    put 0 into FailedRelays
    put 0 into RelayCount
    put empty into BadRelayName
    if Room has entry `relays`
    begin
        put entry `relays` of Room into RoomRelays
        put the count of RoomRelays into RelayCount
    end
    if Room has entry `relayfails`
    begin
        put entry `relayfails` of Room into RelayFails
!       numeric = legacy room-wide count, which is discarded
        if RelayFails is not numeric put RelayFails into RoomRelayFails
    end
    if RoomRelayFails is not empty
    begin
        put 0 into I
        while I is less than the count of RoomRelayFails
        begin
            put item I of RoomRelayFails into RelayFailsThis
            if RelayFailsThis is greater than RelayFailsWorst put RelayFailsThis into RelayFailsWorst
            if RelayFailsThis is greater than 5
            begin
                increment FailedRelays
!               Remember the first failing relay's name for the message
                if FailedRelays is 1 and I is less than RelayCount
                    put item I of RoomRelays into BadRelayName
            end
            increment I
        end
    end
    if FailedRelays is greater than 0
    begin
        if RelayCount is greater than 1 and FailedRelays is less than RelayCount
            put `partial` into RoomStatus
        else
        begin
            if RelayFailsWorst is greater than 20 put `fail` into RoomStatus
            else put `warn` into RoomStatus
        end
    end

!   Check thermometer staleness (skip in simulation mode)
    if Sensor is not empty and not Simulate
    begin
        if Thermometers has entry Sensor
        begin
            put entry Sensor of Thermometers into Thermometer
            put entry `ts` of Thermometer into T
            put now into SensorAge
            take T from SensorAge
!           SensorAge is now milliseconds since last report. Surface it
!           on Room so the UI's info sheet can show "N min ago".
            set entry `sensorAge` of Room to SensorAge
!           Warn at 45 min (2700000ms), fail at 60 min (3600000ms). The
!           45-min warn threshold matches the staleness gate above that
!           empties TempNow, so a stale sensor and a `warn` status both
!           force the relay off at the same point.
            if SensorAge is greater than 3600000 put `fail` into RoomStatus
            else if SensorAge is greater than 2700000
            begin
                if RoomStatus is not `fail` put `warn` into RoomStatus
            end
        end
        else put `fail` into RoomStatus
    end

    set entry `status` of Room to RoomStatus
    set entry `timestamp` of Room to now

!   Relay health is also surfaced explicitly (counts + a message naming the
!   faulty relay) so the UI can show a partial-failure indicator even when the
!   room status is masked by something else — a stale sensor pushes the status
!   to `warn`, which would otherwise hide the relay fault entirely.
    set entry `relaysFailed` of Room to FailedRelays
    set entry `relaysTotal` of Room to RelayCount

!   Build a status message for the UI
    put empty into Value
    put empty into RelayMsg
    if FailedRelays is greater than 0
    begin
!       Partial failure: name the relay that is not answering so the room
!       card's amber warning says which radiator is dead.
        if RelayCount is greater than 1 and FailedRelays is less than RelayCount
        begin
            put `Relay: ` cat BadRelayName cat ` not responding` into Value
            put BadRelayName cat ` not responding` into RelayMsg
        end
        else put `Relay: ` cat RelayFailsWorst cat ` failures` into Value
    end
    if Sensor is not empty and not Simulate
    begin
        if Thermometers has entry Sensor
        begin
            put entry Sensor of Thermometers into Thermometer
            put entry `ts` of Thermometer into T
            put now into SensorAge
            take T from SensorAge
            if SensorAge is greater than 600000
            begin
                divide SensorAge by 60000 giving SensorAge
                if Value is not empty put Value cat `. ` into Value
                put Value cat `Sensor: no report for ` cat SensorAge cat ` min` into Value
            end
        end
        else
        begin
            if Value is not empty put Value cat `. ` into Value
            put Value cat `Sensor: not registered` into Value
        end
    end
    set entry `statusMessage` of Room to Value
    set entry `relayMessage` of Room to RelayMsg
!! @hash 07a1a758
!! @verified e101ab9c
!!!
!! Cascading writers for the system map: callers gosub to whichever level they need, then control falls through up to UpdateMap and returns.
!!
!! UpdateRooms writes a single Room back into the Rooms list; UpdateProfile rewrites the profile's rooms list; UpdateProfiles writes the profile back into the profiles list; UpdateMap puts the profiles list back on the Map. Each level is a valid entry point.
UpdateRooms:
!    log `Update ` cat RoomName cat ` (` cat RoomIndex cat ` )`
    set item RoomIndex of Rooms to Room
UpdateProfile:
    set entry `rooms` of Profile to Rooms
UpdateProfiles:
    set item SelectedProfile of Profiles to Profile
UpdateMap:
    set entry `profiles` of Map to Profiles
    return
!! @hash b14a1967
!! @verified 19bec5d0
!!!
!! Trigger an immediate UI update by setting both ImmediateUpdate (which short-circuits MainLoop's 5-second wait) and MapHasChanged (which makes SendMapToUI actually push). 
!!
!! Used by paths that want the UI to see a state change without waiting for the next tick: period rolls, relay state changes, mode changes, etc.
ForceUpdate:
!    log `Force an immediate update`
    set ImmediateUpdate
    set MapHasChanged
    return
!! @hash 58722563
!! @verified 58722563
!!!
!! Determine which scheduled period applies right now and set Target accordingly.
!!
!! Two phases.
!! (1) Walk the room's `periods` list to identify NaturalPeriodActive — the index of the period containing `now` (wrap-aware via on > off), or -1 if `now` falls between every period. The list walked is the *effective* one for today, built by GetEffectivePeriods, so a one-off override armed for the morning is already reflected in the period times (or in the period's absence).
!!
!! (2) Apply the room's `advance` flag via ApplyPeriodsAdvance, then save NaturalPeriodActive into PeriodWas for the next cycle's roll-over comparison.
!!
!! Sets PeriodActive (-1 = background-targeted, >= 0 = period index) and Target. Iterates with PI rather than I because ConvertTimeToInt and ConvertTempToInt both clobber I.
FindCurrentPeriod:
    set PeriodActive to -1
    set NaturalPeriodActive to -1
    gosub to GetEffectivePeriods
    if EventCount is 0
    begin
        gosub to ApplyPeriodsAdvance
        set PeriodWas to NaturalPeriodActive
        return
    end

    ! Phase 1: determine the natural period (if any). Use PI (not I) as
    ! the iterator — ConvertTimeToInt and ConvertTempToInt both clobber I.
    put 0 into PI
    while PI is less than EventCount
    begin
        put item PI of PeriodList into Period
        put entry `on` of Period into Time
        gosub to ConvertTimeToInt
        set OnTime to Time
        put entry `off` of Period into Time
        gosub to ConvertTimeToInt
        set OffTime to Time
        set InPeriod to 0
        if OnTime is OffTime set InPeriod to 1
        else if OnTime is less than OffTime
        begin
            if now is not less than OnTime
                if now is less than OffTime set InPeriod to 1
        end
        else
        begin
            ! Wraps midnight: in-period when at-or-after `on`, OR before `off`.
            if now is not less than OnTime set InPeriod to 1
            else if now is less than OffTime set InPeriod to 1
        end
        if InPeriod is 1
        begin
            set NaturalPeriodActive to PI
            put EventCount into PI
        end
        else increment PI
    end

    ! Phase 2: apply advance, then save natural for next cycle.
    gosub to ApplyPeriodsAdvance
    set PeriodWas to NaturalPeriodActive
    return
!! @hash 99c2b5b5
!! @verified bd73d6d4
!!!
!! Decide PeriodActive and Target from NaturalPeriodActive and the room's `advance` flag.
!!
!! PeriodList must be loaded by the caller (or left absent/empty for the no-periods edge case).
!!
!! Without advance, both simply mirror the natural state. With advance on (and no roll-over since it was engaged): from a natural period -> Target = background-temp (heat goes off until next natural on); from natural background -> Target = next period's temp (heat skips ahead and turns on now).
!!
!! Auto-cancels the moment the natural state would have rolled, so the user never has to remember to undo it.
ApplyPeriodsAdvance:
    if entry `advance` of Room is `A`
    begin
        ! Auto-cancel the advance once the natural state has rolled.
        ! PeriodWas is seeded from the room's current natural period in
        ! ProcessAllRooms, so any value here is a real period index
        ! (>= 0) or -1 for background — both legitimate engagement
        ! anchors. A simple inequality is enough; no sentinel guard.
        if NaturalPeriodActive is not PeriodWas
        begin
            ! log RoomName cat `: Cancelling the advance (periods)`
            set entry `advance` of Room to `-`
            set entry `period` of Room to NaturalPeriodActive
            gosub to ForceUpdate
            ! Fall through: use natural state.
        end
        else
        begin
            ! Apply the advance shift.
            if NaturalPeriodActive is less than 0
            begin
                ! From background: skip ahead to the next period.
                gosub to FindNextPeriodFromNow
                if NextAdvanceIdx is less than 0
                begin
                    ! No periods at all — Target stays at background.
                    set PeriodActive to -1
                    gosub to PeriodsBackgroundTarget
                end
                else
                begin
                    set PeriodActive to NextAdvanceIdx
                    put item NextAdvanceIdx of PeriodList into Period
                    put entry `temp` of Period into Temp
                    gosub to ConvertTempToInt
                    put Temp into Target
                end
            end
            else
            begin
                ! From a period: heat goes OFF (background-temp) until
                ! the natural period would have ended.
                set PeriodActive to -1
                gosub to PeriodsBackgroundTarget
            end
            set entry `period` of Room to PeriodActive
            return
        end
    end

    ! Natural state (advance not set, or just cancelled).
    set PeriodActive to NaturalPeriodActive
    if NaturalPeriodActive is less than 0 gosub to PeriodsBackgroundTarget
    else
    begin
        put item NaturalPeriodActive of PeriodList into Period
        put entry `temp` of Period into Temp
        gosub to ConvertTempToInt
        put Temp into Target
    end
    return
!! @hash a311f7af
!! @verified 46a58892
!!!
!! Find the next period chronologically: smallest `on` strictly after `now`, else (no on later today) wrap to the smallest `on` overall = tomorrow's first.
!!
!! Returns the period index in NextAdvanceIdx (-1 if PeriodList is empty).
!!
!! Used by ApplyPeriodsAdvance when an advance is engaged from background-time and we need to skip ahead to the next scheduled on-period.
FindNextPeriodFromNow:
    set NextAdvanceIdx to -1
    if EventCount is 0 return
    put 0 into PI
    while PI is less than EventCount
    begin
        put item PI of PeriodList into Period
        put entry `on` of Period into Time
        gosub to ConvertTimeToInt
        if Time is greater than now
        begin
            if NextAdvanceIdx is less than 0
            begin
                set NextAdvanceMin to Time
                set NextAdvanceIdx to PI
            end
            else if Time is less than NextAdvanceMin
            begin
                set NextAdvanceMin to Time
                set NextAdvanceIdx to PI
            end
        end
        increment PI
    end
    if NextAdvanceIdx is not less than 0 return
    ! No on > now today — wrap to the smallest on overall.
    put 0 into PI
    while PI is less than EventCount
    begin
        put item PI of PeriodList into Period
        put entry `on` of Period into Time
        gosub to ConvertTimeToInt
        if NextAdvanceIdx is less than 0
        begin
            set NextAdvanceMin to Time
            set NextAdvanceIdx to PI
        end
        else if Time is less than NextAdvanceMin
        begin
            set NextAdvanceMin to Time
            set NextAdvanceIdx to PI
        end
        increment PI
    end
    return
!! @hash b43dc6dd
!! @verified b43dc6dd
!!!
!! Set Target to the system's background temperature, used in periods mode whenever `now` falls outside every period (or the room has none).
!!
!! Defaults to 12C when no background-temp is configured. Leaves PeriodActive untouched — the caller has already decided which period (or -1 = background) is active.
PeriodsBackgroundTarget:
    if Map has entry `background-temp` put entry `background-temp` of Map into Temp
    else put 12 into Temp
    put `` cat Temp into Temp
    gosub to ConvertTempToInt
    put Temp into Target
    return
!! @hash 86cbeddf
!! @verified 86cbeddf
!!!
!! Side-effect-free version of FindCurrentPeriod's first phase, used solely by the boost period-boundary check.
!!
!! Returns the index of the period containing `now` in NaturalPeriod (-1 if none). Does not touch PeriodActive / Period / Target / advance — this is a reference value for ProcessRoom to compare against the boost-start latch (`boostperiod`) so a boost can auto-cancel when the natural period rolls. Uses the effective (override-aware) period list, so a boost latched on an overridden morning still cancels when that period rolls.
GetNaturalPeriod:
    put -1 into NaturalPeriod
    gosub to GetEffectivePeriods
    if EventCount is 0 return
    put 0 into PI
    while PI is less than EventCount
    begin
        put item PI of PeriodList into Period
        put entry `on` of Period into Time
        gosub to ConvertTimeToInt
        set OnTime to Time
        put entry `off` of Period into Time
        gosub to ConvertTimeToInt
        set OffTime to Time
        set InPeriod to 0
        if OnTime is OffTime set InPeriod to 1
        else if OnTime is less than OffTime
        begin
            if now is not less than OnTime
                if now is less than OffTime set InPeriod to 1
        end
        else
        begin
            if now is not less than OnTime set InPeriod to 1
            else if now is less than OffTime set InPeriod to 1
        end
        if InPeriod is 1
        begin
            set NaturalPeriod to PI
            put EventCount into PI
        end
        else increment PI
    end
    return
!! @hash 1d458c3a
!! @verified b55848a3
!!!
!! Load the room's own `periods` into PeriodList as a *copy*, leaving EventCount set to the count (0 when the room has no schedule).
!!
!! The copy matters: AllSpeak collections are held by reference, so handing the room's list straight to PeriodList lets an edit — applying an override, or dropping a skipped period — silently rewrite the stored schedule. `append` copies the entry, which is all the isolation a period (`on`/`off`/`temp`) needs.
LoadRoomPeriods:
    reset PeriodList
    put 0 into EventCount
    if Room has no entry `periods` return
    put entry `periods` of Room into PeriodSource
    put the count of PeriodSource into EventCount
    if EventCount is 0 return
    put 0 into OB
    while OB is less than EventCount
    begin
        put item OB of PeriodSource into Period
        append Period to PeriodList
        increment OB
    end
    return
!! @hash 6b264584
!!!
!! Look up the one-off override armed for this room and *today's* date.
!!
!! Overrides live at the top level of the map keyed by room name, so they apply whichever profile the calendar picks for the day, and they survive a wholesale `Update Profiles` (which replaces `profiles` only). Leaves OverrideKind (`start`/`skip`) and OverrideOn set, or both empty when nothing is armed for today.
GetRoomOverride:
    put empty into OverrideKind
    put empty into OverrideOn
    if Map has no entry `overrides` return
    put entry `overrides` of Map into Overrides
    put entry `name` of Room into OverrideName
    if Overrides has no entry OverrideName return
    put entry OverrideName of Overrides into OverrideEntry
    put datime today format `%Y-%m-%d` into TodayKey
    if entry `date` of OverrideEntry is not TodayKey return
    put entry `kind` of OverrideEntry into OverrideKind
    if OverrideKind is `start` put entry `on` of OverrideEntry into OverrideOn
    return
!! @hash 8e2a8fd4
!!!
!! Build PeriodList as the set of periods that apply to this room *today*, honouring any one-off override armed for it.
!!
!! Always a copy of the room's `periods` (see LoadRoomPeriods). The override either replaces the morning period's `on`, or drops that period altogether — a `skip`, or a requested start at or after the period's own `off`, which is the "entire period skipped" case. Sets PeriodList and EventCount; an empty list means no periods apply.
GetEffectivePeriods:
    gosub to LoadRoomPeriods
    if EventCount is 0 return
    gosub to GetRoomOverride
    if OverrideKind is empty return
    gosub to IdentifyMorningPeriod
    if MorningIdx is less than 0 return
    if OverrideKind is `start`
    begin
        put item MorningIdx of PeriodList into Period
        put entry `off` of Period into Time
        gosub to ConvertTimeToInt
        put Time into OffTime
        put OverrideOn into Time
        gosub to ConvertTimeToInt
        put Time into OnTime
        if OnTime is less than OffTime
        begin
            put item MorningIdx of PeriodList into Period
            set entry `on` of Period to OverrideOn
            return
        end
    end
    delete item MorningIdx of PeriodList
    put the count of PeriodList into EventCount
    return
!! @hash 601273e8
!!!
!! Identify the day's morning period — the entry with the earliest `on` time — as the target of a one-off start-time override.
!!
!! Zero-length and wrap-around periods (`on` at or after `off`) are excluded: neither is a morning warm-up the user could sensibly shift, and for a wrap-around period "later than the off time" has no useful meaning. Leaves the index in MorningIdx (-1 if none). Reads PeriodList/EventCount, which the caller must have loaded.
IdentifyMorningPeriod:
    set MorningIdx to -1
    put 999999999999999 into MorningMin
    put 0 into MI
    while MI is less than EventCount
    begin
        put item MI of PeriodList into Period
        put entry `on` of Period into Time
        gosub to ConvertTimeToInt
        put Time into OnTime
        put entry `off` of Period into Time
        gosub to ConvertTimeToInt
        put Time into OffTime
        if OnTime is less than OffTime
        begin
            if OnTime is less than MorningMin
            begin
                put OnTime into MorningMin
                set MorningIdx to MI
            end
        end
        increment MI
    end
    return
!! @hash 31783f0e
!!!
!! Resolve which calendar date a newly-armed override applies to: "the next occurrence of the day's first period" — today if that period has not started yet, otherwise tomorrow.
!!
!! The date is frozen at arm time so the meaning cannot drift during the day. The period's `on` is compared against `now` through ConvertTimeToInt (today-anchored), and tomorrow is reached with a 36-hour offset so a daylight-saving step on the way cannot land on the wrong calendar day. Expects PeriodList/EventCount loaded and MorningIdx set by IdentifyMorningPeriod.
ResolveOverrideDate:
    put datime today format `%Y-%m-%d` into TodayKey
    put item MorningIdx of PeriodList into Period
    put entry `on` of Period into Time
    gosub to ConvertTimeToInt
    if now is less than Time
    begin
        put TodayKey into OverrideDate
        return
    end
    put today into T
    add 129600000 to T
    put datime T format `%Y-%m-%d` into OverrideDate
    return
!! @hash 13f45682
!!!
!! Arm a one-off override on the room named in the current UI request.
!!
!! `kind` is `start` (with a `time` of HH:MM) or `skip`; anything else is rejected. The room must have a morning period to act on. Arming cancels any engaged Advance — one morning, one intent — and replaces whatever override the room already held.
SetRoomOverride:
    put entry `name` of Room into OverrideName
    put `start` into OverrideKind
    ! Clear the request time here: these are script-level globals, so a stale
    ! value from a previous request would otherwise satisfy the "time
    ! required" check below.
    put empty into OverrideOn
    if Message has entry `kind` put entry `kind` of Message into OverrideKind
    else if Message has entry `Kind` put entry `Kind` of Message into OverrideKind
    if OverrideKind is not `skip`
    begin
        if Message has entry `time` put entry `time` of Message into OverrideOn
        else if Message has entry `Time` put entry `Time` of Message into OverrideOn
        if OverrideOn is empty
        begin
            log `UIRequest rejected: Room Override needs a time`
            return
        end
        put the index of `:` in OverrideOn into OI
        if OI is less than 1
        begin
            log `UIRequest rejected: Room Override time must be HH:MM`
            return
        end
        put `start` into OverrideKind
    end
    gosub to LoadRoomPeriods
    gosub to IdentifyMorningPeriod
    if MorningIdx is less than 0
    begin
        log `UIRequest rejected: Room Override needs a morning period`
        return
    end
    put item MorningIdx of PeriodList into Period
    put entry `on` of Period into OverrideWas
    gosub to ResolveOverrideDate
    if entry `advance` of Room is `A` set entry `advance` of Room to `-`
    reset OverrideEntry
    set entry `kind` of OverrideEntry to OverrideKind
    set entry `date` of OverrideEntry to OverrideDate
    set entry `was` of OverrideEntry to OverrideWas
    set entry `at` of OverrideEntry to now
    if OverrideKind is `start` set entry `on` of OverrideEntry to OverrideOn
    if Map has no entry `overrides`
    begin
        reset Overrides
    end
    else put entry `overrides` of Map into Overrides
    set entry OverrideName of Overrides to OverrideEntry
    set entry `overrides` of Map to Overrides
    log `Room override armed: ` cat OverrideName cat ` ` cat OverrideKind cat ` for ` cat OverrideDate
    set MapHasChanged
    return
!! @hash 463ba962
!!!
!! Cancel any override held for the room named in the current UI request.
ClearRoomOverride:
    put entry `name` of Room into OverrideName
    if Map has no entry `overrides` return
    put entry `overrides` of Map into Overrides
    if Overrides has entry OverrideName
    begin
        delete entry OverrideName of Overrides
        log `Room override cleared: ` cat OverrideName
        set MapHasChanged
    end
    return
!! @hash b8bbeba7
!!!
!! Drop one-off overrides whose target date has passed; called on the midnight roll-over.
!!
!! An expired override is already inert — it only matches on its own date — so this is tidiness rather than correctness. It is also what clears the armed badge from every connected UI, since it marks the map changed.
PruneOverrides:
    if Map has no entry `overrides` return
    put entry `overrides` of Map into Overrides
    put the keys of Overrides into OverrideKeys
    put datime today format `%Y-%m-%d` into TodayKey
    put 0 into OI
    while OI is less than the count of OverrideKeys
    begin
        put item OI of OverrideKeys into OverrideName
        put entry OverrideName of Overrides into OverrideEntry
        if entry `date` of OverrideEntry is less than TodayKey
        begin
            delete entry OverrideName of Overrides
            log `Room override expired: ` cat OverrideName
            set MapHasChanged
        end
        increment OI
    end
    return
!! @hash 72da8206
!!!
!! Record temperature/humidity/battery readings for Mijia BLE thermometers seen by RBR-Now relays.
!!
!! RBR-Now devices forward BLE announcements as a string in their reply payload; we parse the trailing `+`-delimited segment, split its semicolon fields (rssi;temp;hum;batt;mac-suffix), and stash a Thermometer record under `a4:c1:38:<suffix>` in the Thermometers dictionary. ThermometerUpdate is set so HandleMessages flushes thermometers.json on the next minute.
RecordThermometer:
    if Reply is empty return
!    log Reply
    put Reply into Value
    split Value on ` `
    if the elements of Value is 1 return
    index Value to 2
    put Value into Value2
    split Value2 on `+`
    if the elements of Value2 is 1 return
    index Value2 to 1
    if Value2 is not empty
    begin
        split Value2 on `;`
        if the elements of Value2 is not less than 5
        begin
            reset Thermometer
            set entry `ts` of Thermometer to now
            index Value2 to 1
            set entry `rssi` of Thermometer to Value2
            index Value2 to 2
            multiply Value2 by 10
            set entry `temp` of Thermometer to Value2
            index Value2 to 3
            set entry `hum` of Thermometer to Value2
            index Value2 to 4
            set entry `batt` of Thermometer to Value2
            index Value2 to 0
            set entry `a4:c1:38:` cat Value2 of Thermometers to Thermometer
            set ThermometerUpdate
!            log RoomName cat ` thermometer: ` cat Thermometer
        end
        set the elements of Value to 1
    end
    return
!! @hash 533978e4
!! @verified 533978e4
!!!
!! Convert an HH:MM time string into an integer milliseconds-since-epoch value for today (Time variable in/out).
!!
!! Used throughout period scheduling to compare schedule times against `now`. Clobbers I and T as scratch — callers iterating over a list must use a different counter (PI is the project's convention).
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
!! @hash 2893761b
!! @verified 2893761b
!!!
!! Convert a temperature string (e.g. "20.5") into an integer-hundredths value (2050). Temp variable in/out.
!!
!! The map stores temperatures as integer hundredths to avoid floating-point arithmetic at runtime; user-supplied values arrive as strings and need this conversion. Empty input becomes 0. The `scale` operator does the conversion with exact integer arithmetic (rounding half away from zero when the string carries more than two fractional digits) and handles negative values natively — no more split-on-the-dot dance, and no scratch vars clobbered (callers' "use PI not I" warnings are now moot but harmless).
ConvertTempToInt:
    if Temp is empty put 0 into Temp
    put Temp scale 100 into Temp
    return
!! @hash 3c92fcd2
!! @verified 38e6b2c1
!!!
!! Find a room by name and leave RoomIndex pointing at it (-1 if no match).
!!
!! Sets the Room dictionary as a side-effect by virtue of the index walk. Used by ResolveRoomFromMessage to translate UI room references into a usable index.
GetRoomByName:
    set RoomIndex to 0
    while RoomIndex is less than RoomCount
    begin
        index Room to RoomIndex
        if entry `name` of Room is RoomName return
        increment RoomIndex
    end
    ! Not found
    set RoomIndex to -1
    return
!! @hash 7ac36668
!! @verified 7ac36668
!!!
!! Resolve the room referenced by an incoming UI request.
!!
!! Accepts three field names for backward compatibility (`Room` and `room name` carry the room name; `roomnumber` carries the index); the first match wins.
!!
!! On success: RoomIndex >= 0 and the Room dictionary is indexed. On failure: RoomIndex = -1.
!!
!! Used at the top of every UIRequest action that operates on a specific room.
ResolveRoomFromMessage:
    if Message has entry `Room`
    begin
        put entry `Room` of Message into RoomName
        gosub to GetRoomByName
        return
    end
    if Message has entry `room name`
    begin
        put entry `room name` of Message into RoomName
        gosub to GetRoomByName
        return
    end
    if Message has entry `roomnumber`
    begin
        put entry `roomnumber` of Message into RoomIndex
        if RoomIndex is less than 0
        begin
            set RoomIndex to -1
            return
        end
        if RoomIndex is not less than RoomCount
        begin
            set RoomIndex to -1
            return
        end
        index Room to RoomIndex
        if Room is empty
        begin
            set RoomIndex to -1
            return
        end
        put entry `name` of Room into RoomName
        return
    end
    set RoomIndex to -1
    return
!! @hash 4e68554c
!! @verified 4e68554c
!!!
!! Dispatch a `uirequest` MQTT message to the appropriate map mutation.
!!
!! Envelope: { sender, action:`uirequest`, message:<payload> }. Payload is either a canonical object ({ Action|action, ... }) or a legacy module wrapper ({ request:`Update`, data:{ ... } }) which we unwrap. 
!!
!! Action names are normalised so the UI can be upgraded incrementally — `request`, `addroom`, `rooms`, `system name`, etc. all map to their canonical forms.
!!
!! Supported actions: `System Name` (renames the system), `Request Relay` (sets the boiler-request relay name), `Add Room` (appends a room spec), `Update Rooms` (full replacement array, used by delete/reorder), `Select Profile` (switches active profile), `Update Profiles` (rewrites profiles list and optional calendar), `Operating Mode` (per-room mode change), `Room Override` (arms or clears a one-off schedule tweak for a room), and `Test`.
!!
!! Operating Mode handles all four modes plus the `Advance` toggle and boost duration parsing (accepts a raw integer minutes, or `B<n>` form like `B30`). Switching out of boost (boost -> off/timed/on) clears the boost-tracking fields (`until`, `prevmode`, `boostperiod`) so the map doesn't carry zombie state across profile views. After mutating the map most actions call ForceUpdate so the change is visible to all UIs immediately.
!!
!! Room Override carries `op` (`set`, the default, or `clear`) plus, for a set, `kind` (`start` with a `time` of HH:MM, or `skip`). It is a one-day schedule tweak stored outside `profiles` — see SetRoomOverride — and is not a mode change, so a room in `on`/`off`/`boost` keeps that mode and the override applies when the room returns to `timed`.
ProcessUIRequest:
    ! Legacy UI modules may still send {request:`Update`, data:{...}}.
    ! Unwrap only when there is no direct Action/action field.
    if Message does not have entry `Action`
    begin
        if Message does not have entry `action`
        begin
            if Message has entry `request`
            begin
                put entry `request` of Message into Value
                if Value is `Update`
                begin
                    if Message has entry `data` put entry `data` of Message into Message
                    else
                    begin
                        log `UIRequest rejected: wrapper has no data`
                        return
                    end
                end
                else return
            end
            else
            begin
                log `UIRequest rejected: missing Action/action`
                return
            end
        end
    end

!    log Action cat ` from ` cat SenderName cat `: ` cat Message
    if Message has entry `Action` put entry `Action` of Message into Action
    else if Message has entry `action` put entry `action` of Message into Action
    else
    begin
        log `UIRequest rejected: missing Action/action`
        return
    end
    log `UI Request: ` cat Action

    ! Normalise action names so the UI can be upgraded incrementally.
    put lowercase Action into Value
    if Value is `test` put `Test` into Action
    else if Value is `system name` put `System Name` into Action
    else if Value is `name` put `System Name` into Action
    else if Value is `request relay` put `Request Relay` into Action
    else if Value is `request` put `Request Relay` into Action
    else if Value is `add room` put `Add Room` into Action
    else if Value is `addroom` put `Add Room` into Action
    else if Value is `rooms` put `Update Rooms` into Action
    else if Value is `update rooms` put `Update Rooms` into Action
    else if Value is `select profile` put `Select Profile` into Action
    else if Value is `update profiles` put `Update Profiles` into Action
    else if Value is `operating mode` put `Operating Mode` into Action
    else if Value is `room override` put `Room Override` into Action
    else if Value is `special action` put `Room Override` into Action

    if Action is `Test`
    begin
        log `Test message received`
    end
    else if Action is `System Name`
    begin
        if Message has entry `System Name` put entry `System Name` of Message into Value
        else if Message has entry `name` put entry `name` of Message into Value
        else
        begin
            log `UIRequest rejected: System Name needs System Name/name`
            return
        end
        set entry `name` of Map to Value
        log `Set the system name to ` cat entry `name` of Map
        gosub to ForceUpdate
    end
    else if Action is `Request Relay`
    begin
        if Message has entry `Request Relay` put entry `Request Relay` of Message into Value
        else if Message has entry `request` put entry `request` of Message into Value
        else
        begin
            log `UIRequest rejected: Request Relay needs Request Relay/request`
            return
        end
        set entry `request` of Map to Value
        set RequestName to Value
        log `Set the request relay to ` cat entry `request` of Map
        gosub to ForceUpdate
    end
    else if Action is `Add Room`
    begin
        if Message has entry `Request Relay` put entry `Request Relay` of Message into Value
        else if Message has entry `request` put entry `request` of Message into Value
        else clear Value
        if Value is not empty
        begin
            set entry `request` of Map to Value
            log `Set the request relay to ` cat entry `request` of Map
        end
        if Message has entry `Add Room` put entry `Add Room` of Message into RoomSpec
        else if Message has entry `spec` put entry `spec` of Message into RoomSpec
        else
        begin
            log `UIRequest rejected: Add Room needs Add Room/spec`
            return
        end
        log `Add room ` cat entry `name` of RoomSpec
        append RoomSpec to Rooms
        gosub to UpdateProfile
        gosub to ForceUpdate
    end
    else if Action is `Update Rooms`
    begin
        if Message has entry `rooms` put entry `rooms` of Message into Rooms
        else
        begin
            log `UIRequest rejected: Update Rooms needs rooms`
            return
        end
        log `Update rooms list (` cat the count of Rooms cat ` rooms)`
        gosub to UpdateProfile
        log `Force an update (Update Rooms)`
        gosub to ForceUpdate
        gosub to ProcessAllRooms
    end
    else if Action is `Select Profile`
    begin
        if Message has entry `Profile` put entry `Profile` of Message into SelectedProfile
        else if Message has entry `Select Profile` put entry `Select Profile` of Message into SelectedProfile
        else
        begin
            log `UIRequest rejected: Select Profile needs Profile`
            return
        end
        log `Select profile ` cat SelectedProfile
        set entry `profile` of Map to SelectedProfile
        log `Force an update (select profile)`
        gosub to ForceUpdate
        ! This recursive call is needed to ensure the UI updates immediately
        gosub to ProcessAllRooms
    end
    else if Action is `Update Profiles`
    begin
        if Message has entry `profiles`
        begin
            set entry `profiles` of Map to entry `profiles` of Message
            put entry `profiles` of Map into Profiles
            log `Updated profiles list`
        end
        if Message has entry `profile`
        begin
            put entry `profile` of Message into SelectedProfile
            set entry `profile` of Map to SelectedProfile
            log `Select profile ` cat SelectedProfile
        end
        if Message has entry `calendar`
            set entry `calendar` of Map to entry `calendar` of Message
        if Message has entry `calendar-data`
            set entry `calendar-data` of Map to entry `calendar-data` of Message
        log `Force an update (profile change)`
        gosub to ForceUpdate
        gosub to ProcessAllRooms
    end
    else if Action is `Operating Mode`
    begin
        gosub to ResolveRoomFromMessage
        if RoomIndex is less than 0
        begin
            log `UIRequest rejected: Operating Mode needs valid room reference`
            return
        end
        set PriorityRoomIndex to RoomIndex
        if Message has entry `Mode` put entry `Mode` of Message into Mode
        else if Message has entry `mode` put entry `mode` of Message into Mode
        else
        begin
            log `UIRequest rejected: Operating Mode needs Mode/mode`
            return
        end
        put entry `mode` of Room into Value2
        if Mode is `boost`
        begin
            if Value2 is not `boost`
                set entry `prevmode` of Room to Value2
            ! Drop any stale period-latch from a prior boost so the next
            ! ProcessRoom cycle records the current natural period fresh.
            if Room has entry `boostperiod` delete entry `boostperiod` of Room
        end
        else if Value2 is `boost`
        begin
            ! Leaving boost without letting it expire naturally — clear
            ! all boost-tracking fields so the map doesn't carry zombie
            ! state into the next mode (and into future profile views).
            delete entry `until` of Room
            delete entry `prevmode` of Room
            delete entry `boostperiod` of Room
        end
        set entry `mode` of Room to Mode
        if Message has entry `target` set entry `target` of Room to entry `target` of Message
        else if Message has entry `Target` set entry `target` of Room to entry `Target` of Message
        if Mode is `on`
        begin
            put entry `target` of Room into Temp
            gosub to ConvertTempToInt
            put Temp into Value
            if Value is less than 1
            begin
                gosub to FindCurrentPeriod
                if PeriodActive is less than 0
                begin
                    if Map has entry `background-temp`
                        set entry `target` of Room to entry `background-temp` of Map
                    else set entry `target` of Room to 12
                end
                else
                begin
                    put entry `periods` of Room into PeriodList
                    put item PeriodActive of PeriodList into Period
                    set entry `target` of Room to entry `temp` of Period
                end
            end
        end
        if Mode is `timed`
        begin
            if Message has entry `Advance` put `Advance` into Value
            else if Message has entry `advance` put `advance` into Value
            else put empty into Value
            if Value is not empty
            begin
                ! Toggle the advance
                if entry `advance` of Room is `-`
                begin
                    ! Not already advanced, so set it up
                    ! log RoomName cat ` set Advance`
                    set entry `advance` of Room to `A`
                end
                else
                begin
                    ! Already advanced so cancel it
                    ! log RoomName cat ` cancel Advance`
                    set entry `advance` of Room to `-`
                end
                ! log `Force an update (timed mode)`
                gosub to ForceUpdate
            end
        end
        else if Mode is `boost`
        begin
            if Message has entry `duration` set T to entry `duration` of Message
            else if Message has entry `boost`
            begin
                put entry `boost` of Message into Temp
                if Temp is empty put 0 into T
                else
                begin
                    if left 1 of Temp is `B` put from 1 of Temp into T
                    else put Temp into T
                end
            end
            else if Message has entry `Boost`
            begin
                put entry `Boost` of Message into Temp
                if Temp is empty put 0 into T
                else
                begin
                    if left 1 of Temp is `B` put from 1 of Temp into T
                    else put Temp into T
                end
            end
            else put 0 into T
            multiply T by 60000
            add now to T
            set entry `until` of Room to T
            if Message has entry `target` set entry `target` of Room to entry `target` of Message
            else if Message has entry `Target` set entry `target` of Room to entry `Target` of Message
        end
        gosub to UpdateRooms
        put item SelectedProfile of Profiles into Profile
        put entry `rooms` of Profile into Rooms
        put item RoomIndex of Rooms into RoomSpec
        if Mode is not `timed` or Value is empty gosub to ForceUpdate
    end
    else if Action is `Room Override`
    begin
        gosub to ResolveRoomFromMessage
        if RoomIndex is less than 0
        begin
            log `UIRequest rejected: Room Override needs valid room reference`
            return
        end
        if Message has entry `op` put entry `op` of Message into Value
        else if Message has entry `Op` put entry `Op` of Message into Value
        else put `set` into Value
        if Value is `clear`
        begin
            gosub to ClearRoomOverride
        end
        else gosub to SetRoomOverride
        gosub to ForceUpdate
    end
    else log `UIRequest rejected: unsupported action ` cat Action
!! @hash eddda5ae
!! @verified 4dd81a04
!!!
!! Push to every connected UI. If MapHasChanged the full map is sent; otherwise an empty payload goes out as a heartbeat reply (the UI uses any reply to keep its alive indicator green and its stall watchdog quiet).
!!
!! Iterates the Senders dictionary, which HandleMessages prunes of any sender silent for over 100 seconds. Clears MapHasChanged after the push so subsequent calls in the same tick cycle don't re-send the same map.
SendMapToUI:
    if MapHasChanged set MessageText to Map else set MessageText to empty
    clear MapHasChanged
    put the keys of Senders into SenderKeys
    put the count of SenderKeys into L
!    log `SendMapToUI recipients=` cat L
    set S to 0
    while S is less than the count of SenderKeys
    begin
        put item S of SenderKeys into SenderKey
!        log `SendMapToUI -> ` cat SenderKey
        put entry SenderKey of Senders into Sender
        gosub to SendMessage
        increment S
    end
    increment UpdateCount
    return
!! @hash a4fc17e8
!! @verified a4fc17e8
!!!
!! Send a single MessageText payload to one Sender over MQTT.
!!
!! Wraps the message with action `confirm` (when ConfirmationRequested is set, used for actions that need an ack) or `reply` otherwise. Topic name and QoS come from the Sender record so each UI receives messages on its own MQTT topic.
SendMessage:
    if Sender is empty return
    put entry `name` of Sender into SenderName
    put entry `qos` of Sender into SenderQoS
    init SenderTopic
        name SenderName
        qos SenderQoS
    if ConfirmationRequested
    begin
        set entry SenderName of WaitForConfirmation
        set Action to `confirm`
    end
    else set Action to `reply`
!    log left 20 of MessageText
    send to SenderTopic
        action Action
        message MessageText
    clear ConfirmationRequested
    return
!! @hash 958a0b69
!! @verified 958a0b69
!!!
!! Send an outbound email on behalf of the UI for registration or password recovery.
!!
!! Message contains `{ to, code, type:"register"|"recover" }`. Mail credentials (server/login/password/from) were loaded from credentials.php at startup. A failure is logged but otherwise silent — the UI gets no negative ack, since the user can't know whether their attempt reached the server anyway.
SendEmail:
    put entry `to` of Message into Value
    put entry `code` of Message into Value2
    put entry `type` of Message into Action
    if Action is `register`
    begin
        put `Your RBR Heating verification code is: ` cat Value2 cat newline cat newline cat `Enter this code in the RBR app to complete registration.` into T
        send email to Value from MailFrom subject `Your RBR Heating verification code` body T via MailServer user MailLogin password MailPassword
            or begin
                log `SendEmail: failed to send registration email to ` cat Value
                return
            end
        log `SendEmail: sent registration email to ` cat Value
    end
    else if Action is `recover`
    begin
        put `Your new RBR Heating password is: ` cat Value2 cat newline cat newline cat `Use this to log in to the RBR app.` into T
        send email to Value from MailFrom subject `Your new RBR Heating password` body T via MailServer user MailLogin password MailPassword
            or begin
                log `SendEmail: failed to send recovery email to ` cat Value
                return
            end
        log `SendEmail: sent recovery email to ` cat Value
    end
    return
!! @hash b957d949
!! @verified b957d949
!!!
!!
!! Record one heating-data row for the current room when its target, actual, or
!! mode has changed since the last logged row, then spawn the CSV writer.
!!
!! Called from ProcessRoom after the relay decision, so Room is indexed and
!! TempNow holds the fresh reading (or is empty — a gap in the log means no
!! valid reading, not "no change"). Skipped when heat logging is disabled (no
!! heatlog-root file), when the room has no thermometer, when the relay is
!! unlinked (mode-driven rather than target/temperature), or when Target is
!! missing. In off mode the logged target tracks the actual so no demand is
!! implied; relay-on inference for analysis is mode c/p/b AND target > actual.
!!
!! Temperatures are logged in tenths of a degree (internal hundredths rounded
!! by add 5 then divide by 10) and the timestamp in minutes since the epoch.
!! Last-logged state lives in HeatlogLast keyed by room name and is persisted
!! to heatlog-state.json once a minute by HandleMessages.
HeatlogRecord:
    if HeatlogRoot is empty return
    put entry `sensor` of Room into Sensor
    if Sensor is empty return
    if entry `linked` of Room is `no` return
    if TempNow is empty return
    ! Actual temperature, hundredths -> tenths.
    put TempNow into Temp
    if Temp is not numeric gosub to ConvertTempToInt
    add 5 to Temp
    divide Temp by 10
    put Temp into HeatlogActual
    put entry `mode` of Room into Mode
    if Mode is `off`
    begin
        ! Off mode: target tracks actual so the row never implies demand.
        put HeatlogActual into HeatlogTarget
        set HeatlogMode to `o`
    end
    else
    begin
        if Mode is `on` set HeatlogMode to `c`
        else if Mode is `timed` set HeatlogMode to `p`
        else if Mode is `boost` set HeatlogMode to `b`
        else return
        if Target is empty return
        ! Target (hundredths) -> tenths.
        put Target into Temp
        if Temp is not numeric gosub to ConvertTempToInt
        add 5 to Temp
        divide Temp by 10
        put Temp into HeatlogTarget
    end
    ! Append only when something changed since the last logged row.
    ! A room key appears in HeatlogLast only once a row has been logged,
    ! so a missing key always counts as a change (startup baseline).
    if HeatlogLast has entry RoomName
    begin
        put entry RoomName of HeatlogLast into HeatlogRow
        if HeatlogRow is not empty
        begin
            if entry `target` of HeatlogRow is HeatlogTarget
            begin
                if entry `actual` of HeatlogRow is HeatlogActual
                begin
                    if entry `mode` of HeatlogRow is HeatlogMode return
                end
            end
        end
    end
    put now into HeatlogTs
    divide HeatlogTs by 60000
    ! The room name passes through the shell inside double quotes, so
    ! neutralise anything that could break out of them; the writer
    ! sanitises the folder name independently.
    put RoomName into HeatlogName
    replace `"` with `'` in HeatlogName
    replace `$` with `-` in HeatlogName
    system background `python3 heatlog.py --root "` cat HeatlogRoot cat `" --room "` cat HeatlogName cat `" --ts ` cat HeatlogTs cat ` --target ` cat HeatlogTarget cat ` --actual ` cat HeatlogActual cat ` --mode ` cat HeatlogMode
    reset HeatlogRow
    set entry `target` of HeatlogRow to HeatlogTarget
    set entry `actual` of HeatlogRow to HeatlogActual
    set entry `mode` of HeatlogRow to HeatlogMode
    set entry RoomName of HeatlogLast to HeatlogRow
    set HeatlogDirty
    return
!! @hash 73266ce3
!!!