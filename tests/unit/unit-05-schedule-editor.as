!   unit-05-schedule-editor.as — tests the desktop app's schedule-editor
!   logic, mirrored verbatim from desktop/rbr-desktop.as: ScheduleParseTime,
!   ScheduleToHHMM, StepSchedulePeriod, AddSchedulePeriod,
!   DeleteSchedulePeriod, SortSchedulePeriods and the SaveSchedule
!   storage-shape conversion ({start, off, target} -> {on, off, temp} plus
!   the splice into profiles[i].rooms[j].periods).
!
!   Part of the RBR validation of the new testing vocabulary. The GUI-only
!   steps (rendering the sheet, the messagebox confirm, the MQTT send) are
!   not mirrored — these tests cover the pure editing state machine.
!
!   NOTE: these mirror the subroutines as they stand today; they are not
!   linked to the live code. Keep in sync with desktop/rbr-desktop.as if
!   the logic changes.

    script Unit05ScheduleEditor

    list EditingPeriods
    list NewPeriodsList
    list StoragePeriods
    list EditingProfiles
    list EditedProfileRooms
    dictionary EditingPeriodRow
    dictionary ClonedPeriod
    dictionary EditedProfile
    dictionary EditedRoom
    dictionary SavedRoom
    variable EditingPeriodsCount
    variable ScheduleField
    variable ScheduleDelta
    variable ScheduleTime
    variable ScheduleMinutes
    variable ScheduleH
    variable ScheduleM
    variable PeriodIdx
    variable PeriodTempTenths
    variable LoopE
    variable SortI
    variable SortJ
    variable SortJplus1
    dictionary PeriodA
    dictionary PeriodB
    variable SortAMinutes    variable SortBMinutes
    variable DotIdx
    variable DecPart
    variable AvgInt
    variable AvgDec

    go to RunTests

!! Parse ScheduleTime ("HH:MM" or "H:MM") into minutes since midnight ->
!! ScheduleMinutes. Empty / malformed input yields 0.

ScheduleParseTime:
    put 0 into ScheduleMinutes
    if ScheduleTime is empty return
    put the index of `:` in ScheduleTime into DotIdx
    if DotIdx is less than 0 return
    put the value of left DotIdx of ScheduleTime into ScheduleMinutes
    multiply ScheduleMinutes by 60
    increment DotIdx
    put the value of from DotIdx of ScheduleTime into DecPart
    add DecPart to ScheduleMinutes
    return
!! @hash 2de6a490
!!!

!! Convert ScheduleM (0-1439 minutes since midnight) into "HH:MM" ->
!! ScheduleTime, zero-padded on both fields.

ScheduleToHHMM:
    put ScheduleM into ScheduleH
    divide ScheduleH by 60
    put ScheduleM modulo 60 into ScheduleM
    if ScheduleH is less than 10 put `0` cat ScheduleH into ScheduleTime
    else put ScheduleH cat empty into ScheduleTime
    put ScheduleTime cat `:` into ScheduleTime
    if ScheduleM is less than 10 put ScheduleTime cat `0` cat ScheduleM into ScheduleTime
    else put ScheduleTime cat ScheduleM into ScheduleTime
    return
!! @hash f571543d
!!!

!! Adjust EditingPeriods[PeriodIdx].ScheduleField by ScheduleDelta. Times
!! step in 15-minute increments wrapping at 24:00; targets step in 0.5°
!! tenths clamped to 5.0-30.0. (The app's copy re-renders the sheet after;
!! the render call is GUI-only and not mirrored here.)

StepSchedulePeriod:
    put item PeriodIdx of EditingPeriods into EditingPeriodRow
    if ScheduleField is `start` put entry `start` of EditingPeriodRow into ScheduleTime
    else if ScheduleField is `off` put entry `off` of EditingPeriodRow into ScheduleTime
    else put entry `target` of EditingPeriodRow into ScheduleTime
    if ScheduleField is `target`
    begin
        put ScheduleTime scale 10 into PeriodTempTenths
        add ScheduleDelta to PeriodTempTenths
        if PeriodTempTenths is less than 50 put 50 into PeriodTempTenths
        if PeriodTempTenths is greater than 300 put 300 into PeriodTempTenths
        put PeriodTempTenths into AvgInt
        put PeriodTempTenths modulo 10 into AvgDec
        divide AvgInt by 10
        put AvgInt cat `.` cat AvgDec into ScheduleTime
        set entry `target` of EditingPeriodRow to ScheduleTime
    end
    else
    begin
        gosub to ScheduleParseTime
        add ScheduleMinutes to ScheduleDelta
        if ScheduleDelta is less than 0 add 1440 to ScheduleDelta
        put ScheduleDelta modulo 1440 into ScheduleDelta
        put ScheduleDelta into ScheduleM
        gosub to ScheduleToHHMM
        if ScheduleField is `start` set entry `start` of EditingPeriodRow to ScheduleTime
        else set entry `off` of EditingPeriodRow to ScheduleTime
    end
    set item PeriodIdx of EditingPeriods to EditingPeriodRow
    return
!! @hash 49aed685
!!!

!! Append a sensible default period (06:00-08:00 at 21.0) to the editor.

AddSchedulePeriod:
    put `{}` into ClonedPeriod
    set entry `start` of ClonedPeriod to `06:00`
    set entry `off` of ClonedPeriod to `08:00`
    set entry `target` of ClonedPeriod to `21.0`
    append ClonedPeriod to EditingPeriods
    increment EditingPeriodsCount
    return
!! @hash 2aabb663
!!!

!! Rebuild EditingPeriods without PeriodIdx.

DeleteSchedulePeriod:
    put `[]` into NewPeriodsList
    put 0 into LoopE
    while LoopE is less than EditingPeriodsCount
    begin
        if LoopE is not PeriodIdx
        begin
            put item LoopE of EditingPeriods into EditingPeriodRow
            append EditingPeriodRow to NewPeriodsList
        end
        increment LoopE
    end
    put NewPeriodsList into EditingPeriods
    put the count of NewPeriodsList into EditingPeriodsCount
    return
!! @hash f65e2eaf
!!!

!! Bubble-sort EditingPeriods in place by `start` (minutes since midnight).

SortSchedulePeriods:
    if EditingPeriodsCount is less than 2 return
    put 0 into SortI
    while SortI is less than EditingPeriodsCount
    begin
        put 0 into SortJ
        while SortJ is less than EditingPeriodsCount
        begin
            put SortJ into SortJplus1
            increment SortJplus1
            if SortJplus1 is less than EditingPeriodsCount
            begin
                put item SortJ of EditingPeriods into PeriodA
                put item SortJplus1 of EditingPeriods into PeriodB
                put entry `start` of PeriodA into ScheduleTime
                gosub to ScheduleParseTime
                put ScheduleMinutes into SortAMinutes
                put entry `start` of PeriodB into ScheduleTime
                gosub to ScheduleParseTime
                put ScheduleMinutes into SortBMinutes
                if SortAMinutes is greater than SortBMinutes
                begin
                    set item SortJ of EditingPeriods to PeriodB
                    set item SortJplus1 of EditingPeriods to PeriodA
                end
            end
            increment SortJ
        end
        increment SortI
    end
    return
!! @hash ac1e3cd9
!!!

!! SaveSchedule's storage conversion: sort, convert display shape
!! {start, off, target} to storage shape {on, off, temp}, splice into
!! EditingProfiles[0].rooms[0].periods. (The app's copy also ships the
!! Update Profiles message; the MQTT send is not mirrored.)

SaveSchedule:
    gosub to SortSchedulePeriods
    put `[]` into StoragePeriods
    put 0 into LoopE
    while LoopE is less than EditingPeriodsCount
    begin
        put item LoopE of EditingPeriods into EditingPeriodRow
        put `{}` into ClonedPeriod
        set entry `on` of ClonedPeriod to entry `start` of EditingPeriodRow
        set entry `off` of ClonedPeriod to entry `off` of EditingPeriodRow
        set entry `temp` of ClonedPeriod to entry `target` of EditingPeriodRow
        append ClonedPeriod to StoragePeriods
        increment LoopE
    end
    put item 0 of EditingProfiles into EditedProfile
    put entry `rooms` of EditedProfile into EditedProfileRooms
    put item 0 of EditedProfileRooms into EditedRoom
    set entry `periods` of EditedRoom to StoragePeriods
    set item 0 of EditedProfileRooms to EditedRoom
    set entry `rooms` of EditedProfile to EditedProfileRooms
    set item 0 of EditingProfiles to EditedProfile
    return
!! @hash d31a7fd5
!!!

RunTests:

!! Case 1: ScheduleParseTime handles padded, non-padded, empty and malformed.

    test `parse HH:MM to minutes`
        put `06:00` into ScheduleTime
        gosub to ScheduleParseTime
        check that ScheduleMinutes is 360
        put `18:30` into ScheduleTime
        gosub to ScheduleParseTime
        check that ScheduleMinutes is 1110
        put `0:05` into ScheduleTime
        gosub to ScheduleParseTime
        check that ScheduleMinutes is 5
    end test

    test `parse empty or malformed yields 0`
        put empty into ScheduleTime
        gosub to ScheduleParseTime
        check that ScheduleMinutes is 0
        put `bad` into ScheduleTime
        gosub to ScheduleParseTime
        check that ScheduleMinutes is 0
    end test

!! Case 2: ScheduleToHHMM zero-pads both fields and wraps within the day.

    test `format minutes to HH:MM`
        put 0 into ScheduleM
        gosub to ScheduleToHHMM
        check that ScheduleTime is `00:00`
        put 360 into ScheduleM
        gosub to ScheduleToHHMM
        check that ScheduleTime is `06:00`
        put 1439 into ScheduleM
        gosub to ScheduleToHHMM
        check that ScheduleTime is `23:59`
    end test

!! Case 3: time stepping wraps at midnight (23:45 + 15 = 00:00, 00:00 - 15
!! = 23:45).

    test `time stepper wraps at midnight`
        reset EditingPeriods
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `23:45`
        set entry `off` of ClonedPeriod to `08:00`
        set entry `target` of ClonedPeriod to `21.0`
        append ClonedPeriod to EditingPeriods
        put 1 into EditingPeriodsCount
        put 0 into PeriodIdx
        put `start` into ScheduleField
        put 15 into ScheduleDelta
        gosub to StepSchedulePeriod
        put item 0 of EditingPeriods into EditingPeriodRow
        check that entry `start` of EditingPeriodRow is `00:00`
        put -15 into ScheduleDelta
        gosub to StepSchedulePeriod
        put item 0 of EditingPeriods into EditingPeriodRow
        check that entry `start` of EditingPeriodRow is `23:45`
    end test

!! Case 4: target stepping uses 0.5° tenths and clamps at 5.0 and 30.0.

    test `target stepper clamps at 5.0 and 30.0`
        reset EditingPeriods
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `06:00`
        set entry `off` of ClonedPeriod to `08:00`
        set entry `target` of ClonedPeriod to `21.0`
        append ClonedPeriod to EditingPeriods
        put 1 into EditingPeriodsCount
        put 0 into PeriodIdx
        put `target` into ScheduleField
        put 5 into ScheduleDelta
        gosub to StepSchedulePeriod
        put item 0 of EditingPeriods into EditingPeriodRow
        put entry `target` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `21.5`
        put 200 into ScheduleDelta
        gosub to StepSchedulePeriod
        put item 0 of EditingPeriods into EditingPeriodRow
        put entry `target` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `30.0`
        put -400 into ScheduleDelta
        gosub to StepSchedulePeriod
        put item 0 of EditingPeriods into EditingPeriodRow
        put entry `target` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `5.0`
    end test

!! Case 5: AddSchedulePeriod appends the default and bumps the count.

    test `add period appends default`
        reset EditingPeriods
        put 0 into EditingPeriodsCount
        gosub to AddSchedulePeriod
        check that EditingPeriodsCount is 1
        put item 0 of EditingPeriods into EditingPeriodRow
        put entry `start` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `06:00`
        put entry `off` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `08:00`
        put entry `target` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `21.0`
    end test

!! Case 6: DeleteSchedulePeriod removes the selected index and renumbers.

    test `delete period removes index 1`
        reset EditingPeriods
        put 0 into EditingPeriodsCount
        gosub to AddSchedulePeriod
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `10:00`
        set entry `off` of ClonedPeriod to `11:00`
        set entry `target` of ClonedPeriod to `22.0`
        append ClonedPeriod to EditingPeriods
        increment EditingPeriodsCount
        put 1 into PeriodIdx
        gosub to DeleteSchedulePeriod
        check that EditingPeriodsCount is 1
        put item 0 of EditingPeriods into EditingPeriodRow
        put entry `start` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `06:00`
    end test

    test `delete last remaining period leaves an empty list`
        reset EditingPeriods
        put 0 into EditingPeriodsCount
        gosub to AddSchedulePeriod
        put 0 into PeriodIdx
        gosub to DeleteSchedulePeriod
        check that EditingPeriodsCount is 0
    end test

!! Case 7: SortSchedulePeriods orders by start time regardless of input order.

    test `sort orders periods by start`
        reset EditingPeriods
        put 0 into EditingPeriodsCount
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `18:00`
        set entry `off` of ClonedPeriod to `20:00`
        set entry `target` of ClonedPeriod to `22.0`
        append ClonedPeriod to EditingPeriods
        increment EditingPeriodsCount
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `06:00`
        set entry `off` of ClonedPeriod to `08:00`
        set entry `target` of ClonedPeriod to `21.0`
        append ClonedPeriod to EditingPeriods
        increment EditingPeriodsCount
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `00:30`
        set entry `off` of ClonedPeriod to `01:30`
        set entry `target` of ClonedPeriod to `20.0`
        append ClonedPeriod to EditingPeriods
        increment EditingPeriodsCount
        gosub to SortSchedulePeriods
        put item 0 of EditingPeriods into EditingPeriodRow
        put entry `start` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `00:30`
        put item 1 of EditingPeriods into EditingPeriodRow
        put entry `start` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `06:00`
        put item 2 of EditingPeriods into EditingPeriodRow
        put entry `start` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `18:00`
    end test

!! Case 8: SaveSchedule converts display shape to storage shape and splices
!! it into profiles[i].rooms[j].periods.

    test `save converts and splices periods into the profile`
        reset EditingProfiles
        reset EditingPeriods
        put 0 into EditingPeriodsCount
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `18:00`
        set entry `off` of ClonedPeriod to `20:00`
        set entry `target` of ClonedPeriod to `22.0`
        append ClonedPeriod to EditingPeriods
        increment EditingPeriodsCount
        put `{}` into ClonedPeriod
        set entry `start` of ClonedPeriod to `06:00`
        set entry `off` of ClonedPeriod to `08:00`
        set entry `target` of ClonedPeriod to `21.0`
        append ClonedPeriod to EditingPeriods
        increment EditingPeriodsCount
        reset EditedRoom
        set entry `name` of EditedRoom to `Kitchen`
        reset EditedProfileRooms
        append EditedRoom to EditedProfileRooms
        reset EditedProfile
        set entry `name` of EditedProfile to `Monday-Friday`
        set entry `rooms` of EditedProfile to EditedProfileRooms
        append EditedProfile to EditingProfiles
        gosub to SaveSchedule
        put item 0 of EditingProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put item 0 of EditedProfileRooms into SavedRoom
        put entry `periods` of SavedRoom into StoragePeriods
        check that the count of StoragePeriods is 2
        put item 0 of StoragePeriods into EditingPeriodRow
        put entry `on` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `06:00`
        put entry `off` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `08:00`
        put entry `temp` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `21.0`
        put item 1 of StoragePeriods into EditingPeriodRow
        put entry `on` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `18:00`
        put entry `temp` of EditingPeriodRow into ScheduleTime
        check that ScheduleTime is `22.0`
    end test

    exit
!! @hash 4a12b2e9
!!!
