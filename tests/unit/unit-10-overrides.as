!   unit-10-overrides.as — tests the one-off room-override layer that sits on top of the
!   period logic, mirrored verbatim from controller.as: LoadRoomPeriods, GetRoomOverride,
!   GetEffectivePeriods and IdentifyMorningPeriod.
!
!   Part of the RBR validation of the new testing vocabulary.
!
!   GetRoomOverride decides "is this override for today?" against the real wall clock, so
!   every case stamps the override with today's own date (`datime today format %Y-%m-%d`).
!   That keeps the checks deterministic whatever day the suite runs on.
!
!   NOTE: these mirror the subroutines as they stand today; they are not linked to the
!   live code. Keep in sync with controller.as if the logic changes.

    script Unit10Overrides

    dictionary Room
    dictionary Map
    dictionary Period
    dictionary Message
    dictionary Overrides
    dictionary OverrideEntry
    list Periods
    list PeriodList
    list PeriodSource
    list OverrideKeys
    variable EventCount
    variable PI
    variable MI
    variable OB
    variable OI
    variable Time
    variable I
    variable T
    variable Temp
    variable OnTime
    variable OffTime
    variable TodayKey
    variable OverrideKind
    variable OverrideOn
    variable OverrideDate
    variable OverrideName
    variable OverrideWas
    variable MorningIdx
    variable MorningMin
    variable Value

    go to RunTests

!! Load the room's own `periods` into PeriodList as a copy, leaving EventCount set to the count (0 when the room has no schedule). Mirrors controller.as.

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
!! @hash b9f8b52c
!!!
!! Look up the one-off override armed for this room and today's date. Mirrors controller.as.

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
!! @hash f044737b
!!!
!! Build the effective, override-aware period list for today. Mirrors controller.as.

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
!! @hash dacbba8d
!!!
!! Identify the day's morning period — earliest `on`, ignoring zero-length and wrap-around periods. Mirrors controller.as.

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
!! @hash 02a2f082
!!!
!! Convert "HH:MM" to milliseconds since midnight, then add `today`. Shared helper, mirrored.

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
!! @hash ca05c0d7
!!!
!! Build the standard test room: a morning period (06:30-08:00) and an evening one (17:30-22:00), named Kitchen, with nothing armed.

BuildRoom:
    reset Room
    set entry `name` of Room to `Kitchen`
    set entry `advance` of Room to `-`
    reset Periods
    reset Period
    set entry `on` of Period to `06:30`
    set entry `off` of Period to `08:00`
    set entry `temp` of Period to `21.0`
    append Period to Periods
    reset Period
    set entry `on` of Period to `17:30`
    set entry `off` of Period to `22:00`
    set entry `temp` of Period to `21.0`
    append Period to Periods
    set entry `periods` of Room to Periods
    reset Map
    reset Overrides
    return
!! @hash 1a06869b
!!!
!! Arm the override described by OverrideKind / OverrideDate / OverrideOn on the Kitchen room.

ArmOverride:
    reset OverrideEntry
    set entry `kind` of OverrideEntry to OverrideKind
    set entry `date` of OverrideEntry to OverrideDate
    if OverrideKind is `start` set entry `on` of OverrideEntry to OverrideOn
    set entry `Kitchen` of Overrides to OverrideEntry
    set entry `overrides` of Map to Overrides
    return
!! @hash 8003bd03
!!!
!! Fetch entry `on` of the period at index 0 of PeriodList into Value, for an assertable read.

FirstOn:
    put item 0 of PeriodList into Period
    put entry `on` of Period into Value
    return
!! @hash 4096a92a
!!!
!! Resolve the calendar date a new override applies to. Mirrors controller.as (the log lines aside).

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
!! @hash 78a29f27
!!!
!! Arm a one-off override from the request in Message. Mirrors controller.as, minus the logging and the MapHasChanged flag (neither is observable here).

SetRoomOverride:
    put entry `name` of Room into OverrideName
    put `start` into OverrideKind
    put empty into OverrideOn
    if Message has entry `kind` put entry `kind` of Message into OverrideKind
    else if Message has entry `Kind` put entry `Kind` of Message into OverrideKind
    if OverrideKind is not `skip`
    begin
        if Message has entry `time` put entry `time` of Message into OverrideOn
        else if Message has entry `Time` put entry `Time` of Message into OverrideOn
        if OverrideOn is empty return
        put the index of `:` in OverrideOn into OI
        if OI is less than 1 return
        put `start` into OverrideKind
    end
    gosub to LoadRoomPeriods
    gosub to IdentifyMorningPeriod
    if MorningIdx is less than 0 return
    put item MorningIdx of PeriodList into Period
    put entry `on` of Period into OverrideWas
    gosub to ResolveOverrideDate
    if entry `advance` of Room is `A` set entry `advance` of Room to `-`
    reset OverrideEntry
    set entry `kind` of OverrideEntry to OverrideKind
    set entry `date` of OverrideEntry to OverrideDate
    set entry `was` of OverrideEntry to OverrideWas
    if OverrideKind is `start` set entry `on` of OverrideEntry to OverrideOn
    if Map has no entry `overrides`
    begin
        reset Overrides
    end
    else put entry `overrides` of Map into Overrides
    set entry OverrideName of Overrides to OverrideEntry
    set entry `overrides` of Map to Overrides
    return
!! @hash ea8e9b9c
!!!
!! Withdraw the room's override. Mirrors controller.as.

ClearRoomOverride:
    put entry `name` of Room into OverrideName
    if Map has no entry `overrides` return
    put entry `overrides` of Map into Overrides
    if Overrides has entry OverrideName delete entry OverrideName of Overrides
    return
!! @hash e15c8f3c
!!!
!! Drop overrides whose date has passed. Mirrors controller.as.

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
            delete entry OverrideName of Overrides
        increment OI
    end
    return
!! @hash 130a448a
!!!

RunTests:

!! Case 1: a start override replaces the morning `on`; the evening period is untouched.

    gosub to BuildRoom
    put datime today format `%Y-%m-%d` into TodayKey
    put `start` into OverrideKind
    put TodayKey into OverrideDate
    put `07:15` into OverrideOn
    gosub to ArmOverride

    test `a start override shifts the morning on time`
        gosub to GetEffectivePeriods
        check that EventCount is 2
        gosub to FirstOn
        check that Value is `07:15`
        put item 0 of PeriodList into Period
        put entry `off` of Period into Value
        check that Value is `08:00`
        put item 1 of PeriodList into Period
        put entry `on` of Period into Value
        check that Value is `17:30`
    end test
!! @hash bb420cd0
!!!
!! Case 2: an earlier start is honoured too.

    gosub to BuildRoom
    put `start` into OverrideKind
    put TodayKey into OverrideDate
    put `05:45` into OverrideOn
    gosub to ArmOverride

    test `an earlier start is honoured`
        gosub to GetEffectivePeriods
        check that EventCount is 2
        gosub to FirstOn
        check that Value is `05:45`
    end test
!! @hash 4c0af31c
!!!
!! Case 3: a start at or after the period's own off drops the period entirely — both strictly later (09:00 against an 08:00 off) and exactly equal (08:00).

    gosub to BuildRoom
    put `start` into OverrideKind
    put TodayKey into OverrideDate
    put `09:00` into OverrideOn
    gosub to ArmOverride

    test `a start later than the off time drops the period`
        gosub to GetEffectivePeriods
        check that EventCount is 1
        put item 0 of PeriodList into Period
        put entry `on` of Period into Value
        check that Value is `17:30`
    end test

    gosub to BuildRoom
    put `start` into OverrideKind
    put TodayKey into OverrideDate
    put `08:00` into OverrideOn
    gosub to ArmOverride

    test `a start equal to the off time drops the period`
        gosub to GetEffectivePeriods
        check that EventCount is 1
    end test
!! @hash b85c435a
!!!
!! Case 4: the explicit skip drops the morning period.

    gosub to BuildRoom
    put `skip` into OverrideKind
    put TodayKey into OverrideDate
    gosub to ArmOverride

    test `a skip drops the morning period`
        gosub to GetEffectivePeriods
        check that EventCount is 1
        put item 0 of PeriodList into Period
        put entry `on` of Period into Value
        check that Value is `17:30`
    end test
!! @hash 39e81ac2
!!!
!! Case 5: an override dated for another day leaves the schedule alone — the point of storing the date.

    gosub to BuildRoom
    put `start` into OverrideKind
    put `1900-01-01` into OverrideDate
    put `09:00` into OverrideOn
    gosub to ArmOverride

    test `an override for another day is ignored`
        gosub to GetEffectivePeriods
        check that EventCount is 2
        gosub to FirstOn
        check that Value is `06:30`
    end test
!! @hash 93dc3e92
!!!
!! Case 6: with no `overrides` entry at all (the map before any override is ever armed), the schedule passes through unchanged.

    gosub to BuildRoom

    test `no overrides leaves the schedule alone`
        gosub to GetEffectivePeriods
        check that EventCount is 2
        gosub to FirstOn
        check that Value is `06:30`
    end test
!! @hash 4187b0d8
!!!
!! Case 7: a wrap-around period (22:00-06:00) is not a morning period, so an override cannot bind to it and the schedule is untouched.

    reset Room
    set entry `name` of Room to `Kitchen`
    set entry `advance` of Room to `-`
    reset Periods
    reset Period
    set entry `on` of Period to `22:00`
    set entry `off` of Period to `06:00`
    set entry `temp` of Period to `21.0`
    append Period to Periods
    set entry `periods` of Room to Periods
    reset Map
    reset Overrides
    put `start` into OverrideKind
    put TodayKey into OverrideDate
    put `23:00` into OverrideOn
    gosub to ArmOverride

    test `a wrap-around period is not a morning period`
        gosub to GetEffectivePeriods
        check that EventCount is 1
        gosub to FirstOn
        check that Value is `22:00`
    end test
!! @hash e5d8e1eb
!!!
!! Case 8: IdentifyMorningPeriod finds the earliest `on` regardless of the stored order.

    gosub to BuildRoom
    ! Put the evening period first in the stored list.
    reset Periods
    reset Period
    set entry `on` of Period to `17:30`
    set entry `off` of Period to `22:00`
    set entry `temp` of Period to `21.0`
    append Period to Periods
    reset Period
    set entry `on` of Period to `06:30`
    set entry `off` of Period to `08:00`
    set entry `temp` of Period to `21.0`
    append Period to Periods
    set entry `periods` of Room to Periods

    test `the morning period is the earliest on, whatever the stored order`
        gosub to LoadRoomPeriods
        gosub to IdentifyMorningPeriod
        check that MorningIdx is 1
    end test
!! @hash 34f30922
!!!
!! Case 9: the effective list is a copy — editing it must never rewrite the room's stored schedule. This is the guard against a skipped or shifted period quietly persisting.

    gosub to BuildRoom
    put `start` into OverrideKind
    put TodayKey into OverrideDate
    put `07:15` into OverrideOn
    gosub to ArmOverride

    test `editing the effective list leaves the stored schedule intact`
        gosub to GetEffectivePeriods
        put item 0 of PeriodList into Period
        set entry `on` of Period to `00:01`
        delete item 0 of PeriodList
        put entry `periods` of Room into PeriodSource
        put the count of PeriodSource into EventCount
        check that EventCount is 2
        put item 0 of PeriodSource into Period
        put entry `on` of Period into Value
        check that Value is `06:30`
    end test
!! @hash ed4d7867
!!!
!! Case 10: the arm path. A well-formed request stores the override — with the scheduled
!! start recorded as `was` — and resolves a date; a request with no time, a malformed time,
!! or no morning period to act on stores nothing.

    gosub to BuildRoom
    reset Message
    set entry `time` of Message to `08:30`
    gosub to SetRoomOverride
    put entry `overrides` of Map into Overrides
    put entry `Kitchen` of Overrides into OverrideEntry

    test `a well-formed request arms a start override`
        check that entry `kind` of OverrideEntry is `start`
        check that entry `on` of OverrideEntry is `08:30`
        check that entry `was` of OverrideEntry is `06:30`
        check that entry `date` of OverrideEntry is not empty
    end test

    gosub to BuildRoom
    reset Message
    set entry `kind` of Message to `start`
    gosub to SetRoomOverride

    test `a start with no time is rejected`
        check that Map has no entry `overrides`
    end test

    gosub to BuildRoom
    reset Message
    set entry `time` of Message to `later`
    gosub to SetRoomOverride

    test `a malformed time is rejected`
        check that Map has no entry `overrides`
    end test
!! @hash f3b38b91
!!!
!! Case 11: a request also survives a previous arm's leftover time — the guard that a
!! missing `time` is never satisfied by the value of an earlier request.

    gosub to BuildRoom
    reset Message
    set entry `time` of Message to `08:30`
    gosub to SetRoomOverride
    gosub to BuildRoom
    reset Message
    gosub to SetRoomOverride

    test `a later request without a time is still rejected`
        check that Map has no entry `overrides`
    end test
!! @hash d2870f1e
!!!
!! Case 12: skip needs no time; arming cancels an engaged Advance; Clear withdraws it.

    gosub to BuildRoom
    set entry `advance` of Room to `A`
    reset Message
    set entry `kind` of Message to `skip`
    gosub to SetRoomOverride
    put entry `overrides` of Map into Overrides
    put entry `Kitchen` of Overrides into OverrideEntry

    test `skip arms without a time and cancels Advance`
        check that entry `kind` of OverrideEntry is `skip`
        check that OverrideEntry has no entry `on`
        check that entry `advance` of Room is `-`
    end test

    gosub to ClearRoomOverride
    put entry `overrides` of Map into Overrides

    test `clear withdraws the override`
        check that Overrides has no entry `Kitchen`
    end test
!! @hash 7ed690d2
!!!
!! Case 13: pruning drops a stale date and keeps a live one.

    gosub to BuildRoom
    reset Overrides
    reset OverrideEntry
    set entry `date` of OverrideEntry to `1900-01-01`
    set entry `Old` of Overrides to OverrideEntry
    reset OverrideEntry
    set entry `date` of OverrideEntry to TodayKey
    set entry `Fresh` of Overrides to OverrideEntry
    set entry `overrides` of Map to Overrides
    gosub to PruneOverrides
    put entry `overrides` of Map into Overrides

    test `pruning drops the past and keeps today`
        check that Overrides has no entry `Old`
        check that Overrides has entry `Fresh`
    end test

    exit
!! @hash 7cd7ac68
!!!
