!! Thermal simulator for RBR. Stands in for deviceControl.as when the controller is started against a `sim` flag, modelling how a room's temperature responds to the relay being on or off, biased by an outdoor-conditions envelope read from environment.csv.
!!
!! Run as a sub-module of controller.as (via `run ... as DeviceModule`) — communication with the parent is by EasyCoder messaging, not MQTT. Each RoomSpec carries the room name, current temperature, and relay state; we apply one step of the thermal model and reply with the new temperature so the controller treats us interchangeably with the real device controller.
!!
!! The script starts by declaring all the variables it uses, then performs basic initialisation: loads environment.csv to populate the time-of-day weather envelope (SetupSimulator), registers the on-message handler that runs each per-room simulation step, and signals the parent it is ready.
!   simulator.as

    script Simulator
    
    dictionary AllParams
    dictionary Params
    dictionary Rooms
    dictionary Data
    dictionary Values
    dictionary Item
    list Times
    list Replies
    variable RoomName
    variable RelayState
    variable LastRelayState
    variable AmbientNow
    variable OnOffTime
    variable OnOffTemp
    variable SolarBoost
    variable Temp
    variable TempNow
    variable Time
    variable Value
    variable Elapsed
    variable Delta
    variable Ceiling
    variable Rows
    variable I
    variable N
    variable T

!    debug step
    
    log `Set up the simulator`
    gosub to SetupSimulator
    reset AllParams
    reset Rooms
    on message go to RunSimulation
    release parent
    stop
!! @hash abf9bbb5
!! @verified abf9bbb5
!!!
!! Run one thermal-model step for a single room. Called by the runtime each time controller.as sends us a RoomSpec — typically every five to ten seconds per room while the simulator is active.
!!
!! Per-room parameters live in params.json, keyed by room name. The fields are: `rate-up` (heating rate when the relay is on), `rate-down` (cooling rate toward ambient when off), `ceiling` (maximum reachable temperature — stored as whole degrees, converted to hundredths at use), and `boost` (percentage of the environment's solar-boost contribution applied to this room: 100 means a fully sun-exposed room, 0 means a room with no solar gain at all). Sensible defaults (10/10/23/50) are seeded on first sight of an unseen room and written straight back to disk so they can be tuned by hand.
!!
!! Per-room dynamic state lives in the in-memory Rooms dictionary: `OnOffTime` (timestamp anchor for the elapsed-time calculation), `OnOffTemp` (the temperature snapshot at the last relay state change), `OnOffState` (the relay state from the previous cycle, used to detect transitions).
!!
!! Step semantics:
!!
!! Compute Elapsed = now − OnOffTime, then Delta = rate × Elapsed ÷ 3600 (rate from params, Elapsed in milliseconds — the divisor 3600 is the magic-number conversion that links the params' rate units to the simulator's time/temperature units).
!!
!! Relay on: add Delta to the current temperature, clamped at the room's ceiling.
!!
!! Relay off: subtract Delta from the current temperature, clamped at the current ambient temperature (FindAmbientTemp). Ambient is the latest matching entry in environment.csv plus a per-room-scaled share of its solar-boost column.
!!
!! When the relay state has changed since last cycle, latch the new (OnOffTemp, OnOffState) into Rooms so the next cycle's calculation has the correct reference temperature for the new state.
!!
!! Reply with the new temperature in a single-element Replies list so controller.as can fold it back into the Room exactly the way it folds a real device's reply. Ends with `stop` rather than `return` because we are the registered on-message handler — `stop` returns control to the runtime to await the next message without re-entering the script body.
RunSimulation:
    put the message into Values
    put entry `room name` of Values into RoomName
    put entry `temperature` of Values into TempNow
    put entry `relay state` of Values into RelayState
!    if RoomName is `Sunroom` log TempNow

    ! Get the parameters for this room
    if AllParams is empty
    begin
        if file `params.json` exists load AllParams from `params.json` else reset AllParams
    end
    if AllParams has entry RoomName put entry RoomName of AllParams into Params
    else
    begin
        log `Init params for ` cat RoomName
        reset Params
        set entry `rate-up` of Params to 10
        set entry `rate-down` of Params to 10
        set entry `ceiling` of Params to 23
        set entry `boost` of Params to 50
        set entry RoomName of AllParams to Params
        save prettify AllParams to `params.json`
    end
    put entry `ceiling` of Params into Temp
    gosub to ConvertTempToInt
    put Temp into Ceiling

    ! Check we have an entry for this named room
!    put entry RoomName of AllParams into Params
    if Rooms does not have entry RoomName
    begin
        reset Data
        set entry `OnOffTime` of Data to now
        set entry `OnOffTemp` of Data to TempNow
        set entry `OnOffState` of Data to empty
        set entry RoomName of Rooms to Data
    end
    put entry RoomName of Rooms into Data
    put entry `OnOffTime` of Data into OnOffTime
    put entry `OnOffTemp` of Data into OnOffTemp
    put entry `OnOffState` of Data into LastRelayState
    if OnOffTemp is not numeric set OnOffTemp to 0

    take OnOffTime from now giving Elapsed

    if RelayState is `on` put entry `rate-up` of Params into Delta
    else put entry `rate-down` of Params into Delta
    multiply Delta by Elapsed
    divide Delta by 3600
!    if RoomName is `Sunroom` log Elapsed cat `:` cat Delta
    if RelayState is `on`
    begin
        add Delta to TempNow
        if TempNow is greater than Ceiling set TempNow to Ceiling
    end
    else
    begin
        gosub to FindAmbientTemp
        take Delta from TempNow
        if TempNow is less than AmbientNow set TempNow to AmbientNow
    end
    set entry `OnOffTime` of Data to now
    if RelayState is not LastRelayState
    begin
        put entry RoomName of Rooms into Data
        set entry `OnOffTemp` of Data to TempNow
        set entry `OnOffState` of Data to RelayState
        set entry RoomName of Rooms to Data
    end
!    if RoomName is `Sunroom` log TempNow cat `: Relay is ` cat RelayState
    reset Replies
    append TempNow to Replies
        send Replies to sender
    stop
!! @hash e8efb1df
!! @verified e8efb1df
!!!
!! Load the time-of-day outdoor-conditions envelope from environment.csv into the in-memory Times list.
!!
!! Each row of environment.csv is `HH:MM,temperature,boost` — the outdoor temperature and a solar-boost magnitude at that time of day. Rows are expected to be in chronological order and to cover a full 24-hour cycle. Temperature is the base ambient; boost models direct-sun contribution which is later scaled per-room by params.boost% inside FindAmbientTemp (so a north-facing room with boost=0 sees only the base ambient, a conservatory with boost=120 sees an exaggerated swing).
!!
!! Called once at startup. The envelope is never reloaded — to pick up edits to environment.csv, restart the controller. Malformed rows (anything that doesn't split into three fields) are silently skipped so a trailing blank line or stray comment doesn't break the simulation.
SetupSimulator:
    load Rows from `environment.csv`
    split Rows
    reset Times
    put 0 into N
    while N is less than the elements of Rows
    begin
        index Rows to N
        if Rows is not empty
        begin
            put Rows into Value
            split Value on `,`
            if the elements of Value is 3
            begin
                reset Item
                index Value to 0
                set entry `time` of Item to Value
                index Value to 1
                set entry `temperature` of Item to Value
                index Value to 2
                set entry `boost` of Item to Value
                append Item to Times
            end
        end
        increment N
    end
    return
!! @hash e4ba9415
!! @verified e4ba9415
!!!
!! Find the current ambient temperature for the room being simulated and return it in AmbientNow (units: hundredths-of-a-degree, matching everything else in the simulator and the controller's map).
!!
!! Walks the Times list to find the latest entry whose time-of-day has already passed. The loop increments N while `now > entry.time`, so on exit N is one past the active entry — decrement-then-index gives us the right row. If `now` precedes the first entry of the day, N stops at 0 and is wrapped to count-1 so the day's final entry is used (i.e. last night's conditions carry over until the first morning row).
!!
!! Once the row is selected we add a scaled share of its `boost` column to the base ambient. The per-room scaling is params.boost (a percentage), so a value of 50 contributes half the boost magnitude; 100 contributes all of it; 0 effectively disables solar gain for that room. Both base and contribution come through ConvertTempToInt so AmbientNow lands in hundredths.
!!
!! Note the explicit FAT2 inner label — `go to` rather than a `while` loop, because the loop body needs to call ConvertTimeToInt which clobbers I and T (PI is not declared here, so a vanilla `while` with a numeric index works fine, but the goto-style was already in place).
FindAmbientTemp:
    set N to 0
FAT2:
    if N is less than the count of Times
    begin
        put item N of Times into Item
        put entry `time` of Item into Time
        gosub to ConvertTimeToInt
        if now is greater than Time
        begin
            increment N
            go to FAT2
        end
    end
    if N is 0 set N to the count of Times
    decrement N
    set Time to item N of Times
    set Temp to entry `temperature` of Item
    gosub to ConvertTempToInt
    put Temp into AmbientNow
    set Temp to entry `boost` of Item
    gosub to ConvertTempToInt
    set SolarBoost to entry `boost` of Params
    multiply Temp by SolarBoost
    divide Temp by 100
    add Temp to AmbientNow
    return
!! @hash 60a4d5d4
!! @verified 60a4d5d4
!!!
!! Convert an HH:MM time string into an integer milliseconds-since-epoch value for today (Time variable in/out).
!!
!! Mirror of the same routine in controller.as — each AllSpeak module has its own label namespace and a sub-module can't gosub into its parent. Clobbers I and T as scratch.
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
!! Mirror of the same routine in controller.as. Empty input becomes 0. The `scale` operator makes this copy and the controller's identical — and incidentally fixes the old divergence here, where "20.5" used to yield 2005 instead of 2050 because this copy lacked the controller's single-digit-fraction compensation.
ConvertTempToInt:
    if Temp is empty put 0 into Temp
    put Temp scale 100 into Temp
    return
!! @hash 3c92fcd2
!! @verified 49748387
!!!
