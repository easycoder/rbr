!   unit-01-vocabulary.as — conformance of the AllSpeak testing vocabulary itself.
!
!   Part of the RBR validation of the new testing vocabulary (see
!   doc/PROPOSAL-allspeak-testing.md). Every check here passes, so the file
!   exercises the vocabulary without making the suite red.

    script Unit01Vocabulary

    variable A
    variable B
    variable Recovered

    put 1 into A
    put 2 into B
    put `no` into Recovered

!! Bare checks — these belong to the implicit default case. `that` may be omitted, and the condition grammar is exactly `if`'s: `is`, `is not`, `is greater than`, `is numeric`, `and` combinations, and the rest.

    check that A is 1
    check that B is 2 and A is 1
    check B is 2
    check that A is numeric
    check that B is greater than A

    test `comparisons`
        check that A is 1
        check that B is not 1
        check that A is less than B
        check that B is 2 and A is 1
    end test
!! @hash 1f9697db
!!!

!! The `on failure` clause is accepted on a check. Here the check passes, so the clause must stay dormant and the recovery must not run.

    test `failure clause stays dormant on a pass`
        check that A is 1 on failure gosub to FixUp
        check that Recovered is `no`
    end test

    exit
!! @hash 63c20ac4
!!!

!! Recovery for the `on failure` clause — would only run if a check above failed.

FixUp:
    put `yes` into Recovered
    return
!! @hash 19c69ebf
!!!
