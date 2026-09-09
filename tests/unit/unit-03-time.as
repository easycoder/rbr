!   unit-03-time.as — tests `ConvertTimeToInt`, mirrored verbatim from
!   controller.as:1339.
!
!   Part of the RBR validation of the new testing vocabulary.
!
!   The subroutine returns milliseconds since midnight PLUS `today`, so an
!   absolute result is wall-clock dependent. Instead we assert differences
!   between two times of the same day, which are constant: 08:30 - 07:00 is
!   1.5 hours = 5400000 ms, whatever day the test runs on.
!
!   NOTE: this mirrors the subroutine as it stands today; it is not linked to
!   the live code. Keep in sync with controller.as if the conversion changes.

    script Unit03Time

    variable Time
    variable I
    variable T
    variable SevenAM
    variable Midnight
    variable EightThirty

    go to RunTests

!! Convert "HH:MM" to milliseconds since midnight, then add `today`. Both padded (`08:30`) and non-padded (`8:30`) hours parse.

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

RunTests:

!! 07:00 to 08:30 is exactly 90 minutes = 5400000 ms.

    test `90-minute span`
        put `07:00` into Time
        gosub to ConvertTimeToInt
        put Time into SevenAM
        put `08:30` into Time
        gosub to ConvertTimeToInt
        take SevenAM from Time
        check that Time is 5400000
    end test
!! @hash 5d19683b
!!!

!! 00:00 to 23:59 is 1439 minutes = 86340000 ms.

    test `full-day span`
        put `00:00` into Time
        gosub to ConvertTimeToInt
        put Time into Midnight
        put `23:59` into Time
        gosub to ConvertTimeToInt
        take Midnight from Time
        check that Time is 86340000
    end test
!! @hash 7a5a3fda
!!!

!! A non-padded hour (`8:30`) parses identically to `08:30` — their difference is zero.

    test `non-padded hour parses identically`
        put `08:30` into Time
        gosub to ConvertTimeToInt
        put Time into EightThirty
        put `8:30` into Time
        gosub to ConvertTimeToInt
        take EightThirty from Time
        check that Time is 0
    end test

    exit
!! @hash b43c908e
!!!
