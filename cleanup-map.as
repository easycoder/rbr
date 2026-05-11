!   cleanup-map.as
!
!   One-shot cleanup: now that periods is the only schedule model, strip
!   the dead `events` and `schedule-type` fields from every room. Run
!   after the controller has switched to the periods-only build.
!
!   Reads:   map.json
!   Writes:  map-clean.json   (inspect, diff, then mv to replace)
!
!   Run with:   allspeak cleanup-map.as

    script CleanupMap

    dictionary Map
    list Profiles
    dictionary Profile
    list Rooms
    dictionary Room

    variable MapFilename
    variable OutputFilename
    variable PIdx
    variable PCount
    variable RIdx
    variable RCount
    variable RoomName
    variable ProfileName
    variable Removed

    set MapFilename to `map.json`
    set OutputFilename to `map-clean.json`

    log `cleanup-map: reading ` cat MapFilename
    if file MapFilename exists load Map from MapFilename
    else
    begin
        log `cleanup-map: ` cat MapFilename cat ` not found - aborting`
        exit
    end

    set Removed to 0
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
            if Room has entry `events`
            begin
                delete entry `events` of Room
                increment Removed
            end
            if Room has entry `schedule-type`
            begin
                delete entry `schedule-type` of Room
                increment Removed
            end
            log `  ` cat RoomName cat ` cleaned`
            set item RIdx of Rooms to Room
            increment RIdx
        end
        set entry `rooms` of Profile to Rooms
        set item PIdx of Profiles to Profile
        increment PIdx
    end
    set entry `profiles` of Map to Profiles

    save prettify Map to OutputFilename
    log `cleanup-map: removed ` cat Removed cat ` field(s); wrote ` cat OutputFilename
    log `Inspect with: diff ` cat MapFilename cat ` ` cat OutputFilename
    log `Replace with: mv ` cat OutputFilename cat ` ` cat MapFilename
    exit
