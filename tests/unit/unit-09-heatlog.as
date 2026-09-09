!   unit-09-heatlog.as — tests the heat-logging decision logic added to
!   controller.as's `HeatlogRecord`: hundredths->tenths rounding, the
!   mode->letter mapping (including off-mode target-tracks-actual), and the
!   change predicate that decides whether a row is appended.
!
!   NOTE: these subroutines mirror the logic inside HeatlogRecord as it
!   stands today; they are not linked to the live code. Keep in sync with
!   controller.as if HeatlogRecord changes. The CSV writer itself is
!   covered by tests/unit/heatlog_test.py (pure Python, no AllSpeak).

    script Unit09Heatlog

    variable Temp
    variable Mode
    variable HeatlogTarget
    variable HeatlogActual
    variable HeatlogMode
    variable RoomName
    variable LogChange
    dictionary HeatlogRow
    dictionary HeatlogLast

    go to RunTests

!! Round an internal integer-hundredths temperature (Temp) to integer-tenths, exactly as HeatlogRecord does (add 5, then integer divide by 10 — half-up for the positive temperatures heating deals in).

HundredthsToTenths:
    add 5 to Temp
    divide Temp by 10
    return
!! @hash 28b7c13b
!!!

!! Map the room's mode (Mode) and actual temperature in tenths (Temp) to the logged mode letter and target, mirroring HeatlogRecord's mode handling. Non-off modes keep the caller-supplied HeatlogTarget.

ModeToLog:
    if Mode is `off`
    begin
        put Temp into HeatlogTarget
        set HeatlogMode to `o`
    end
    else
    begin
        if Mode is `on` set HeatlogMode to `c`
        else if Mode is `timed` set HeatlogMode to `p`
        else if Mode is `boost` set HeatlogMode to `b`
    end
    return
!! @hash 2bd3b259
!!!

!! Set LogChange to `yes` when (HeatlogTarget, HeatlogActual, HeatlogMode) differ from the last logged row for RoomName in HeatlogLast — mirroring HeatlogRecord's append decision (missing last row = a change).

LogChanged:
    put `yes` into LogChange
    if HeatlogLast has entry RoomName
    begin
        put entry RoomName of HeatlogLast into HeatlogRow
        if HeatlogRow is not empty
        begin
            if entry `target` of HeatlogRow is HeatlogTarget
            begin
                if entry `actual` of HeatlogRow is HeatlogActual
                begin
                    if entry `mode` of HeatlogRow is HeatlogMode set LogChange to `no`
                end
            end
        end
    end
    return
!! @hash e469dfa6
!!!

RunTests:

!! Hundredths to tenths: exact tenths, half-up rounding, and truncation of smaller fractions.

    test `hundredths to tenths rounding`
        put 2070 into Temp
        gosub to HundredthsToTenths
        check that Temp is 207

        put 2075 into Temp
        gosub to HundredthsToTenths
        check that Temp is 208

        put 2064 into Temp
        gosub to HundredthsToTenths
        check that Temp is 206

        put 2000 into Temp
        gosub to HundredthsToTenths
        check that Temp is 200
    end test
!! @hash 811ed214
!!!

!! Mode letters and the off-mode rule: off logs target = actual with letter o; on/timed/boost keep their own target with c/p/b.

    test `mode letters and off-mode target`
        put 185 into Temp
        put `off` into Mode
        gosub to ModeToLog
        check that HeatlogMode is `o`
        check that HeatlogTarget is 185

        put 200 into HeatlogTarget
        put `on` into Mode
        gosub to ModeToLog
        check that HeatlogMode is `c`

        put `timed` into Mode
        gosub to ModeToLog
        check that HeatlogMode is `p`

        put `boost` into Mode
        gosub to ModeToLog
        check that HeatlogMode is `b`

        put `off` into Mode
        gosub to ModeToLog
        check that HeatlogMode is `o`
    end test
!! @hash 8774830c
!!!

!! Change predicate: no last row = change; identical row = no change; any of target/actual/mode differing = change (so a pure mode flip still logs).

    test `change predicate`
        reset HeatlogLast
        reset HeatlogRow
        set entry `Kitchen` of HeatlogLast to HeatlogRow

        put 207 into HeatlogTarget
        put 205 into HeatlogActual
        put `p` into HeatlogMode
        put `Kitchen` into RoomName
        gosub to LogChanged
        check that LogChange is `yes`

        reset HeatlogRow
        set entry `target` of HeatlogRow to HeatlogTarget
        set entry `actual` of HeatlogRow to HeatlogActual
        set entry `mode` of HeatlogRow to HeatlogMode
        set entry RoomName of HeatlogLast to HeatlogRow

        gosub to LogChanged
        check that LogChange is `no`

        put 206 into HeatlogActual
        gosub to LogChanged
        check that LogChange is `yes`

        put 205 into HeatlogActual
        put `o` into HeatlogMode
        gosub to LogChanged
        check that LogChange is `yes`

        put `Kitchen` into RoomName
        reset HeatlogLast
        gosub to LogChanged
        check that LogChange is `yes`
    end test
!! @hash 20d5285a
!!!

    exit
!! @hash 04e33077
!!!
