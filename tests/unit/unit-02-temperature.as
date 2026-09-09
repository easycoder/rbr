!   unit-02-temperature.as — tests `ConvertTempToInt`, mirrored verbatim from
!   controller.as:1356 (the `scale`-based form).
!
!   Part of the RBR validation of the new testing vocabulary: exercises
!   `check that` against the controller's real temperature-conversion logic.
!
!   NOTE: this mirrors the subroutine as it stands today; it is not linked to
!   the live code (that would need the logic extracted into a shared module).
!   Keep in sync with controller.as if the conversion changes.

    script Unit02Temperature

    variable Temp
    variable I
    variable T

    go to RunTests

!! Convert a temperature string (e.g. "20.5") into integer-hundredths (2050). Empty input becomes 0; negatives are handled natively by `scale`.

ConvertTempToInt:
    if Temp is empty put 0 into Temp
    put Temp scale 100 into Temp
    return
!! @hash 1ee8520e
!!!

RunTests:

!! Whole degrees and one/two fractional digits.

    test `whole degrees and one/two fractional digits`
        put `21.5` into Temp
        gosub to ConvertTempToInt
        check that Temp is 2150

        put `18.25` into Temp
        gosub to ConvertTempToInt
        check that Temp is 1825
    end test
!! @hash 79cdcc74
!!!

!! Integer input, zero, empty input, and negatives — the `scale` operator's reason for existing.

    test `integer, zero, empty and negative input`
        put `10` into Temp
        gosub to ConvertTempToInt
        check that Temp is 1000

        put `0` into Temp
        gosub to ConvertTempToInt
        check that Temp is 0

        put `` into Temp
        gosub to ConvertTempToInt
        check that Temp is 0

        put `-5` into Temp
        gosub to ConvertTempToInt
        check that Temp is -500
    end test

    exit
!! @hash dc2e4d3e
!!!
