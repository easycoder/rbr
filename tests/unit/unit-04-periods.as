!   unit-04-periods.as — tests the period-selection logic, mirrored verbatim
!   from controller.as: GetNaturalPeriod (1256), FindCurrentPeriod (1058),
!   FindNextPeriodFromNow (1192), ApplyPeriodsAdvance (1123) and
!   PeriodsBackgroundTarget (1243).
!
!   Part of the RBR validation of the new testing vocabulary.
!
!   The subroutines read the real wall clock via `now`, so the test data is
!   chosen to be time-independent: a zero-length period (on = off) is always
!   "in period", and a room with no periods (or an empty list) is always
!   background. This keeps every check deterministic at any time of day.
!
!   NOTE: these mirror the subroutines as they stand today; they are not
!   linked to the live code. Keep in sync with controller.as if the logic
!   changes.

    script Unit04Periods

    dictionary Room
    dictionary Map
    dictionary Period
    list Periods
    list PeriodList
    variable EventCount
    variable PI
    variable Time
    variable I
    variable T
    variable Temp
    variable OnTime
    variable OffTime
    variable InPeriod
    variable NaturalPeriod
    variable NaturalPeriodActive
    variable PeriodActive
    variable PeriodWas
    variable Target
    variable NextAdvanceIdx
    variable NextAdvanceMin

    go to RunTests

!! Set Target to the system background temperature (default 12C when the map has no `background-temp`). Leaves PeriodActive untouched.

PeriodsBackgroundTarget:
    if Map has entry `background-temp` put entry `background-temp` of Map into Temp
    else put 12 into Temp
    put `` cat Temp into Temp
    gosub to ConvertTempToInt
    put Temp into Target
    return
!! @hash deed3093
!!!

!! Side-effect-free natural-period lookup used as the boost reference latch. Returns the index of the period containing `now` in NaturalPeriod (-1 if none).

GetNaturalPeriod:
    put -1 into NaturalPeriod
    if Room has entry `periods` put entry `periods` of Room into PeriodList
    else return
    put the count of PeriodList into EventCount
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
!! @hash 3e0b5e99
!!!

!! Find the next period chronologically: smallest `on` strictly after `now`, else wrap to the smallest `on` overall (tomorrow's first). Returns the index in NextAdvanceIdx (-1 if PeriodList is empty).

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
!! @hash 15672e67
!!!

!! Decide PeriodActive and Target from the natural state and the room's `advance` flag. Advance is only exercised in its "off" (`-`) state here, so the UI-push branch (ForceUpdate in the live controller) is omitted — it is unreachable for the data in this suite.

ApplyPeriodsAdvance:
    if entry `advance` of Room is `A`
    begin
        if NaturalPeriodActive is not PeriodWas
        begin
            set entry `advance` of Room to `-`
            set entry `period` of Room to NaturalPeriodActive
        end
        else
        begin
            if NaturalPeriodActive is less than 0
            begin
                gosub to FindNextPeriodFromNow
                if NextAdvanceIdx is less than 0
                begin
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
                set PeriodActive to -1
                gosub to PeriodsBackgroundTarget
            end
            set entry `period` of Room to PeriodActive
            return
        end
    end
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
!! @hash d8653487
!!!

!! The natural-period phase of FindCurrentPeriod: scans the room's periods against `now` (phase 1) then resolves PeriodActive/Target via ApplyPeriodsAdvance (phase 2).

FindCurrentPeriod:
    set PeriodActive to -1
    set NaturalPeriodActive to -1
    if Room has entry `periods` put entry `periods` of Room into PeriodList
    else
    begin
        gosub to ApplyPeriodsAdvance
        set PeriodWas to NaturalPeriodActive
        return
    end
    put the count of PeriodList into EventCount
    if EventCount is 0
    begin
        gosub to ApplyPeriodsAdvance
        set PeriodWas to NaturalPeriodActive
        return
    end
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
            set NaturalPeriodActive to PI
            put EventCount into PI
        end
        else increment PI
    end
    gosub to ApplyPeriodsAdvance
    set PeriodWas to NaturalPeriodActive
    return
!! @hash db528d19
!!!

!! Convert "HH:MM" to milliseconds since midnight, then add `today` (shared helper).

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

!! Convert a temperature string (e.g. "20.5") into integer-hundredths (2050), via `scale` (shared helper).

ConvertTempToInt:
    if Temp is empty put 0 into Temp
    put Temp scale 100 into Temp
    return
!! @hash 1ee8520e
!!!

RunTests:

!! Case 1: a zero-length period (12:00-12:00, 21.0) is always "in period", so the natural index is 0 and the target is 2100.

    reset Room
    set entry `advance` of Room to `-`
    reset Period
    set entry `on` of Period to `12:00`
    set entry `off` of Period to `12:00`
    set entry `temp` of Period to `21.0`
    reset Periods
    append Period to Periods
    set entry `periods` of Room to Periods

    test `zero-length period is always in period`
        gosub to GetNaturalPeriod
        check that NaturalPeriod is 0
        gosub to FindCurrentPeriod
        check that PeriodActive is 0
        check that Target is 2100
    end test
!! @hash dd88fcdf
!!!

!! Case 2: no periods entry at all — always background at the configured background temperature (18.0 here).

    reset Room
    set entry `advance` of Room to `-`
    reset Map
    set entry `background-temp` of Map to `18`

    test `no periods means background`
        gosub to GetNaturalPeriod
        check that NaturalPeriod is -1
        gosub to FindCurrentPeriod
        check that PeriodActive is -1
        check that Target is 1800
    end test
!! @hash a4451774
!!!

!! Case 3: an empty periods list behaves like no periods.

    reset Room
    set entry `advance` of Room to `-`
    reset Periods
    set entry `periods` of Room to Periods

    test `empty periods list means background`
        gosub to FindCurrentPeriod
        check that PeriodActive is -1
        check that Target is 1800
    end test
!! @hash 0abce553
!!!

!! Case 4: FindNextPeriodFromNow with a single 00:00 period always resolves to index 0 (strictly-after-now fails, the wrap picks the smallest `on`), and with no periods returns -1.

    reset PeriodList
    reset Period
    set entry `on` of Period to `00:00`
    append Period to PeriodList
    put the count of PeriodList into EventCount

    test `single period always resolves to index 0`
        gosub to FindNextPeriodFromNow
        check that NextAdvanceIdx is 0
    end test

    reset PeriodList
    put 0 into EventCount

    test `no periods gives -1`
        gosub to FindNextPeriodFromNow
        check that NextAdvanceIdx is -1
    end test

    exit
!! @hash 64e08b17
!!!
