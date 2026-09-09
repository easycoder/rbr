!   unit-08-calendar.as — tests the desktop app's calendar-editor logic,
!   mirrored verbatim from desktop/rbr-desktop.as: CloneCalendarDataForEdit
!   (pad to 7), AssignCalendarDay (day -> profile name) and
!   PaintCalendarDayNames (display list). GUI-only steps (rendering the
!   sheet, the MQTT send) are not mirrored. NOTE: these mirror the
!   subroutines as they stand today; they are not linked to the live code.

    script Unit08Calendar

    list CalendarData
    list DayNames
    list ProfileList
    dictionary Map
    dictionary CalendarDay
    dictionary SavedDay
    dictionary ProfileSrc
    variable CalendarState
    variable CalendarDayIdx
    variable CalendarProfileIdx
    variable DayLoop
    variable PropName
    variable Value
    variable ProfileName

    go to RunTests

!! Snapshot the map's calendar-data into CalendarData, padding to 7 entries.

CloneCalendarDataForEdit:
    if Map has entry `calendar-data` put entry `calendar-data` of Map into CalendarData
    else put `[]` into CalendarData
    put the count of CalendarData into Value
    while Value is less than 7
    begin
        put `{}` into CalendarDay
        append CalendarDay to CalendarData
        increment Value
    end
    return
!! @hash 101ceb78
!!!

!! Assign day CalendarDayIdx to the profile at CalendarProfileIdx (by name).

AssignCalendarDay:
    if CalendarDayIdx is less than 0 return
    if CalendarDayIdx is greater than 6 return
    put the count of ProfileList into Value
    if CalendarProfileIdx is not less than Value return
    gosub to CloneCalendarDataForEdit
    put item CalendarProfileIdx of ProfileList into ProfileSrc
    put entry `name` of ProfileSrc into ProfileName
    put item CalendarDayIdx of CalendarData into CalendarDay
    if CalendarDay is empty put `{}` into CalendarDay
    set entry `day` cat CalendarDayIdx cat `-profile` of CalendarDay to ProfileName
    set item CalendarDayIdx of CalendarData to CalendarDay
    return
!! @hash e09d5c3b
!!!

!! Rebuild DayNames (7 display names, '' = none) from the map's
!! calendar-data.

PaintCalendarDayNames:
    put `[]` into DayNames
    if Map has entry `calendar-data` put entry `calendar-data` of Map into CalendarData
    else put `[]` into CalendarData
    put 0 into DayLoop
    while DayLoop is less than 7
    begin
        put empty into PropName
        put the count of CalendarData into Value
        if DayLoop is less than Value
        begin
            put item DayLoop of CalendarData into CalendarDay
            put `day` cat DayLoop cat `-profile` into Value
            if CalendarDay is not empty
            begin
                if CalendarDay has entry Value put entry Value of CalendarDay into PropName
            end
        end
        append PropName to DayNames
        increment DayLoop
    end
    return
!! @hash 77dc9c60
!!!

!! Test helper: a canonical 7-entry calendar-data (Mon-Fri, Weekend weekend)
!! and three profiles.

ResetCalendar:
    reset ProfileList
    reset Map
    ! profiles
    put `{}` into ProfileSrc
    set entry `name` of ProfileSrc to `Monday-Friday`
    append ProfileSrc to ProfileList
    put `{}` into ProfileSrc
    set entry `name` of ProfileSrc to `All Off`
    append ProfileSrc to ProfileList
    put `{}` into ProfileSrc
    set entry `name` of ProfileSrc to `Weekend`
    append ProfileSrc to ProfileList
    ! calendar-data, 7 days
    put `[]` into CalendarData
    put 0 into DayLoop
    while DayLoop is less than 7
    begin
        put `{}` into CalendarDay
        if DayLoop is less than 5 put `Monday-Friday` into ProfileName
        else put `Weekend` into ProfileName
        set entry `day` cat DayLoop cat `-profile` of CalendarDay to ProfileName
        append CalendarDay to CalendarData
        increment DayLoop
    end
    set entry `calendar-data` of Map to CalendarData
    return
!! @hash 9d26e99f
!!!

RunTests:

!! Case 1: padding a short array grows it to 7 empty day entries.

    test `calendar data pads to 7`
        gosub to ResetCalendar
        put `[]` into CalendarData
        set entry `calendar-data` of Map to CalendarData
        gosub to CloneCalendarDataForEdit
        put the count of CalendarData into Value
        check that Value is 7
    end test

!! Case 2: assigning a day writes the profile name at day<i>-profile.

    test `assign day writes profile name`
        gosub to ResetCalendar
        put 2 into CalendarDayIdx
        put 2 into CalendarProfileIdx
        gosub to AssignCalendarDay
        put item 2 of CalendarData into SavedDay
        put entry `day2-profile` of SavedDay into PropName
        check that PropName is `Weekend`
        ! other days untouched
        put item 0 of CalendarData into SavedDay
        put entry `day0-profile` of SavedDay into PropName
        check that PropName is `Monday-Friday`
    end test

!! Case 3: assigning a missing day / out-of-range profile is a no-op.

    test `assign guards against bad indices`
        gosub to ResetCalendar
        put 9 into CalendarDayIdx
        put 0 into CalendarProfileIdx
        gosub to AssignCalendarDay
        put 3 into CalendarDayIdx
        put 9 into CalendarProfileIdx
        gosub to AssignCalendarDay
        put item 3 of CalendarData into SavedDay
        put entry `day3-profile` of SavedDay into PropName
        check that PropName is `Monday-Friday`
    end test

!! Case 4: paint yields display names, '' for empty days.

    test `paint builds day display names`
        gosub to ResetCalendar
        put 5 into DayLoop
        while DayLoop is less than 7
        begin
            put item DayLoop of CalendarData into SavedDay
            delete entry `day` cat DayLoop cat `-profile` of SavedDay
            set item DayLoop of CalendarData to SavedDay
            increment DayLoop
        end
        set entry `calendar-data` of Map to CalendarData
        gosub to PaintCalendarDayNames
        put item 0 of DayNames into PropName
        check that PropName is `Monday-Friday`
        put item 4 of DayNames into PropName
        check that PropName is `Monday-Friday`
        put item 5 of DayNames into PropName
        check that PropName is empty
        put the count of DayNames into Value
        check that Value is 7
    end test

    exit
!! @hash 9abca3c5
!!!
