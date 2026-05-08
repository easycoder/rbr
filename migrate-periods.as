!   migrate-periods.as
!
!   One-shot migration: build a `periods` array alongside each room's existing
!   `events`, add a system-wide `background-temp`, and tag each room with a
!   `schedule-type` defaulting to "events" so behaviour is unchanged until the
!   user toggles a room over to the new model.
!
!   Reads:   map.json
!   Writes:  map-new.json   (inspect, diff, then mv to replace)
!
!   Run with:   allspeak migrate-periods.as
!
!   Algorithm (per room):
!     1. Build cyclic spans from events: span[i] runs from events[i-1].until
!        to events[i].until at events[i].temp (the temp held until that time).
!     2. Cyclic-merge adjacent spans that share a temp (handles wrap-around
!        cases where the last and first events are at the same temp).
!     3. Any span whose temp is at or below the OFF threshold (16.0 deg C)
!        is treated as OFF and dropped.
!     4. Each surviving span becomes a period {on, off, temp}.
!     5. If a room has no events, or all events are at or below the threshold,
!        periods is empty (controller will use background-temp 24h in periods
!        mode).

    script MigratePeriods

    dictionary Map
    list Profiles
    dictionary Profile
    list Rooms
    dictionary Room
    list Events
    dictionary Event
    dictionary Event2
    list Spans
    dictionary Span
    dictionary Span2
    list Rotated
    list Merged
    list NewPeriods
    dictionary NewPeriod

    variable MapFilename
    variable OutputFilename
    variable BackgroundTempDefault
    variable OffThreshold
    variable PIdx
    variable PCount
    variable RIdx
    variable RCount
    variable EIdx
    variable ECount
    variable SCount
    variable MCount
    variable RoomName
    variable ProfileName
    variable PeriodCount
    variable I
    variable J
    variable K
    variable L
    variable M
    variable Boundary
    variable BoundaryFound
    variable HasField
    variable TempStr
    variable TempInt

    set MapFilename to `map.json`
    set OutputFilename to `map-new.json`
    set BackgroundTempDefault to 12
    set OffThreshold to 1600

    log `migrate-periods: reading ` cat MapFilename
    if file MapFilename exists load Map from MapFilename
    else
    begin
        log `migrate-periods: ` cat MapFilename cat ` not found - aborting`
        exit
    end

    set HasField to 0
    if Map has entry `background-temp` set HasField to 1
    if HasField is 0
    begin
        set entry `background-temp` of Map to BackgroundTempDefault
        log `Added background-temp = ` cat BackgroundTempDefault
    end

    put entry `profiles` of Map into Profiles
    put the count of Profiles into PCount
    set PIdx to 0
    while PIdx is less than PCount
    begin
        put item PIdx of Profiles into Profile
        put entry `name` of Profile into ProfileName
        log `Profile: ` cat ProfileName
        put entry `rooms` of Profile into Rooms
        put the count of Rooms into RCount
        set RIdx to 0
        while RIdx is less than RCount
        begin
            put item RIdx of Rooms into Room
            put entry `name` of Room into RoomName

            set HasField to 0
            if Room has entry `schedule-type` set HasField to 1
            if HasField is 0 set entry `schedule-type` of Room to `events`

            gosub to BuildPeriodsFromEvents
            set entry `periods` of Room to NewPeriods
            put the count of NewPeriods into PeriodCount
            log `  ` cat RoomName cat `: ` cat PeriodCount cat ` period(s)`

            set item RIdx of Rooms to Room
            increment RIdx
        end
        set entry `rooms` of Profile to Rooms
        set item PIdx of Profiles to Profile
        increment PIdx
    end
    set entry `profiles` of Map to Profiles

    save prettify Map to OutputFilename
    log `migrate-periods: wrote ` cat OutputFilename
    log `Inspect with: diff ` cat MapFilename cat ` ` cat OutputFilename
    log `Replace with: mv ` cat OutputFilename cat ` ` cat MapFilename
    exit


!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Build NewPeriods for the current Room from its `events` array.
BuildPeriodsFromEvents:
    reset NewPeriods
    if Room has entry `events` put entry `events` of Room into Events
    else return
    put the count of Events into ECount
    if ECount is 0 return

    ! Step 1: Build cyclic spans
    reset Spans
    set EIdx to 0
    while EIdx is less than ECount
    begin
        if EIdx is 0 set I to ECount
        else set I to EIdx
        decrement I
        put item I of Events into Event2
        put item EIdx of Events into Event

        reset Span
        set entry `start` of Span to entry `until` of Event2
        set entry `end` of Span to entry `until` of Event
        put entry `temp` of Event into TempStr
        set entry `temp` of Span to `` cat TempStr
        gosub to TempStrToInt
        set entry `tempint` of Span to TempInt

        append Span to Spans
        increment EIdx
    end

    ! Step 2: Cyclic merge of adjacent same-temp spans.
    !   - If all spans share a temp, leave Spans as-is (will be dropped in step 3).
    !   - Otherwise rotate so index 0 sits at a temp boundary, then linear-merge.
    put the count of Spans into SCount
    if SCount is greater than 1
    begin
        ! Find a boundary (first index whose temp differs from its predecessor)
        set Boundary to 0
        set BoundaryFound to 0
        set I to 0
        while I is less than SCount
        begin
            if BoundaryFound is 0
            begin
                if I is 0 set J to SCount
                else set J to I
                decrement J
                put item I of Spans into Span
                put item J of Spans into Span2
                if entry `tempint` of Span is not entry `tempint` of Span2
                begin
                    set Boundary to I
                    set BoundaryFound to 1
                end
            end
            increment I
        end

        if BoundaryFound is 1
        begin
            ! Rotate so Boundary becomes index 0
            if Boundary is greater than 0
            begin
                reset Rotated
                set K to 0
                while K is less than SCount
                begin
                    set L to Boundary
                    add K to L
                    if L is not less than SCount take SCount from L
                    put item L of Spans into Span
                    append Span to Rotated
                    increment K
                end
                set Spans to Rotated
            end

            ! Linear merge of adjacent same-temp spans
            reset Merged
            set I to 0
            while I is less than SCount
            begin
                put item I of Spans into Span
                if I is 0 append Span to Merged
                else
                begin
                    put the count of Merged into MCount
                    set M to MCount
                    decrement M
                    put item M of Merged into Span2
                    if entry `tempint` of Span2 is entry `tempint` of Span
                    begin
                        set entry `end` of Span2 to entry `end` of Span
                        set item M of Merged to Span2
                    end
                    else append Span to Merged
                end
                increment I
            end
            set Spans to Merged
        end
    end

    ! Step 3: Drop spans at or below the OFF threshold; emit the rest.
    put the count of Spans into SCount
    set I to 0
    while I is less than SCount
    begin
        put item I of Spans into Span
        if entry `tempint` of Span is greater than OffThreshold
        begin
            reset NewPeriod
            set entry `on` of NewPeriod to entry `start` of Span
            set entry `off` of NewPeriod to entry `end` of Span
            set entry `temp` of NewPeriod to entry `temp` of Span
            append NewPeriod to NewPeriods
        end
        increment I
    end
    return


!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Convert TempStr (e.g. "15.0", 15, "21.5", "") into an integer in hundredths.
!   Mirrors controller.as ConvertTempToInt.
TempStrToInt:
    put `` cat TempStr into TempStr
    if TempStr is empty
    begin
        set TempInt to 0
        return
    end
    put the index of `.` in TempStr into I
    if I is less than 0 multiply TempStr by 100 giving TempInt
    else
    begin
        put the value of left I of TempStr into TempInt
        multiply TempInt by 100
        increment I
        put the value of from I of TempStr into J
        if J is less than 10 multiply J by 10
        add J to TempInt
    end
    return
