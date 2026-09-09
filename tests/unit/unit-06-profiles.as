!   unit-06-profiles.as — tests the desktop app's profile-manager logic,
!   mirrored verbatim from desktop/rbr-desktop.as: RenameProfileNow,
!   AddProfileNow, DeleteProfileNow (the rebuild + manual-selection
!   re-indexing) and the Update Profiles payload assembly.
!
!   Part of the RBR validation of the new testing vocabulary. GUI-only steps
!   (rendering the sheet, the messagebox confirms, the MQTT send) are not
!   mirrored — these cover the pure profile-list state machine. NOTE: these
!   mirror the subroutines as they stand today; they are not linked to the
!   live code. Keep in sync with desktop/rbr-desktop.as if the logic changes.

    script Unit06Profiles

    list ProfileList
    list NewProfiles
    list KeptProfiles
    list ProfileRooms
    dictionary ProfileSrc
    dictionary ClonedProfile
    dictionary SavedProfile
    dictionary Msg
    variable ProfileEditIdx
    variable ProfileIdx
    variable SwapIdx
    variable ProfileIndex
    variable ProfileListCount
    variable ProfileLoop
    variable SelectedProfile
    variable NewValue

    go to RunTests

!! Rename the profile at ProfileEditIdx in NewProfiles (a copy of
!! ProfileList) to NewValue; ProfileIndex = manual selection, unchanged.

RenameProfileNow:
    put ProfileList into NewProfiles
    put item ProfileEditIdx of NewProfiles into ProfileSrc
    set entry `name` of ProfileSrc to NewValue
    set item ProfileEditIdx of NewProfiles to ProfileSrc
    put 3 into ProfileIndex
    return
!! @hash d2f3c9e0
!!!

!! Append a profile named NewValue cloned from SelectedProfile's rooms.

AddProfileNow:
    put ProfileList into NewProfiles
    put item SelectedProfile of NewProfiles into ProfileSrc
    put `{}` into ClonedProfile
    set entry `name` of ClonedProfile to NewValue
    put entry `rooms` of ProfileSrc into ProfileRooms
    set entry `rooms` of ClonedProfile to ProfileRooms
    append ClonedProfile to NewProfiles
    return
!! @hash b9ee65f4
!!!

!! Rebuild NewProfiles without ProfileEditIdx and re-index the manual
!! selection: deleting an earlier profile shifts the rest up; deleting the
!! selected profile falls back to the entry that slid into its place
!! (clamped to the end). The last profile cannot be deleted.

DeleteProfileNow:
    put the count of ProfileList into ProfileListCount
    if ProfileListCount is less than 2 return
    put `[]` into KeptProfiles
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        if ProfileLoop is not ProfileEditIdx
        begin
            put item ProfileLoop of ProfileList into ProfileSrc
            append ProfileSrc to KeptProfiles
        end
        increment ProfileLoop
    end
    put KeptProfiles into NewProfiles
    put the count of KeptProfiles into ProfileListCount
    if ProfileEditIdx is less than ProfileIndex take 1 from ProfileIndex
    put ProfileListCount into ProfileLoop
    take 1 from ProfileLoop
    if ProfileIndex is greater than ProfileLoop put ProfileLoop into ProfileIndex
    return
!! @hash 2a9f7ce5
!!!

!! Build the Update Profiles payload (profiles + profile + calendar fields).

ShipProfilesUpdate:
    put `{}` into Msg
    set entry `Action` of Msg to `Update Profiles`
    set entry `profiles` of Msg to NewProfiles
    set entry `profile` of Msg to ProfileIndex
    return
!! @hash f2aebc31
!!!

!! Test helper: replace ProfileList with the three canonical profiles.

ResetProfiles:
    reset ProfileList
    ! Rooms shared by every profile (set entry deep-copies via JSON).
    reset ProfileRooms
    put `Kitchen` into NewValue
    append NewValue to ProfileRooms
    put `Bedroom` into NewValue
    append NewValue to ProfileRooms
    ! Profile 1
    put `{}` into ProfileSrc
    set entry `name` of ProfileSrc to `Monday-Friday`
    set entry `rooms` of ProfileSrc to ProfileRooms
    append ProfileSrc to ProfileList
    ! Profile 2 — a fresh dict (append stores a reference; never mutate a
    ! symbol after appending it)
    put `{}` into ProfileSrc
    set entry `name` of ProfileSrc to `All Off`
    set entry `rooms` of ProfileSrc to ProfileRooms
    append ProfileSrc to ProfileList
    ! Profile 3
    put `{}` into ProfileSrc
    set entry `name` of ProfileSrc to `Weekend`
    set entry `rooms` of ProfileSrc to ProfileRooms
    append ProfileSrc to ProfileList
    return
!! @hash c843dc7e
!!!

!! Swap the profile at ProfileIdx with the one at SwapIdx (adjacent reorder);
!! the manual `profile` selection follows the moved profile.

SwapAdjacentProfiles:
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    if SwapIdx is not less than ProfileListCount return
    put item ProfileIdx of NewProfiles into ProfileSrc
    put item SwapIdx of NewProfiles into ClonedProfile
    set item ProfileIdx of NewProfiles to ClonedProfile
    set item SwapIdx of NewProfiles to ProfileSrc
    if ProfileIndex is ProfileIdx put SwapIdx into ProfileIndex
    else if ProfileIndex is SwapIdx put ProfileIdx into ProfileIndex
    return
!! @hash 68f3c2d1
!!!

RunTests:

!! Case 1: rename replaces the name in place and keeps the array order.

    test `rename replaces the name in place`
        gosub to ResetProfiles
        put 1 into ProfileEditIdx
        put `Work Days` into NewValue
        put 3 into ProfileIndex
        gosub to RenameProfileNow
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        check that the count of NewProfiles is 3
        put item 0 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Monday-Friday`
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Work Days`
        put item 2 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Weekend`
    end test

!! Case 2: deleting an earlier profile shifts the manual selection up.

    test `delete before selection shifts manual index`
        gosub to ResetProfiles
        put 0 into ProfileEditIdx
        put 2 into ProfileIndex
        gosub to DeleteProfileNow
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        check that the count of NewProfiles is 2
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 1
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Weekend`
    end test

!! Case 3: deleting the selected middle profile — the next profile slides
!! into its index, so the manual index keeps pointing at a valid entry.

    test `delete selected profile falls back to next`
        gosub to ResetProfiles
        put 1 into ProfileEditIdx
        put 1 into ProfileIndex
        gosub to DeleteProfileNow
        gosub to ShipProfilesUpdate
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 1
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Weekend`
    end test

!! Case 4: deleting the LAST profile while it is selected clamps the manual
!! index to the new end.

    test `delete last selected profile clamps to end`
        gosub to ResetProfiles
        put 2 into ProfileEditIdx
        put 2 into ProfileIndex
        gosub to DeleteProfileNow
        gosub to ShipProfilesUpdate
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 1
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `All Off`
    end test

!! Case 5: deleting the selected FIRST profile keeps index 0 on the next
!! profile.

    test `delete first selected profile stays at 0`
        gosub to ResetProfiles
        put 0 into ProfileEditIdx
        put 0 into ProfileIndex
        gosub to DeleteProfileNow
        gosub to ShipProfilesUpdate
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 0
        put item 0 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `All Off`
    end test

!! Case 6: the last remaining profile is protected from deletion.

    test `last profile cannot be deleted`
        gosub to ResetProfiles
        ! Delete twice, chaining the result back into ProfileList (the
        ! mirrored DeleteProfileNow reads ProfileList and writes NewProfiles).
        put 1 into ProfileEditIdx
        put 0 into ProfileIndex
        gosub to DeleteProfileNow
        put NewProfiles into ProfileList
        put 1 into ProfileEditIdx
        put 0 into ProfileIndex
        gosub to DeleteProfileNow
        put NewProfiles into ProfileList
        put the count of ProfileList into ProfileListCount
        check that ProfileListCount is 1
        ! The final profile is protected: deleting it is a no-op.
        put 0 into ProfileEditIdx
        put 0 into ProfileIndex
        gosub to DeleteProfileNow
        put the count of ProfileList into ProfileListCount
        check that ProfileListCount is 1
        put the count of NewProfiles into ProfileListCount
        check that ProfileListCount is 1
    end test

!! Case 7: Add clones the selected profile's rooms (same count + names) and
!! appends under the new name.

    test `add clones the active profile rooms`
        gosub to ResetProfiles
        put 1 into SelectedProfile
        put `Weekend` into NewValue
        gosub to AddProfileNow
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        check that the count of NewProfiles is 4
        put item 3 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Weekend`
        put entry `rooms` of SavedProfile into ProfileRooms
        check that the count of ProfileRooms is 2
        put item 0 of ProfileRooms into NewValue
        check that NewValue is `Kitchen`
        put item 1 of ProfileRooms into NewValue
        check that NewValue is `Bedroom`
    end test

!! Case 8: reordering swaps adjacent profiles; the manual selection follows
!! the moved profile.

    test `swap up moves profile and follows selection`
        gosub to ResetProfiles
        ! Move Weekend (index 2) up to index 1; manual selection is 2.
        put 2 into ProfileIdx
        put 1 into SwapIdx
        put 2 into ProfileIndex
        gosub to SwapAdjacentProfiles
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Weekend`
        put item 2 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `All Off`
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 1
    end test

    test `swap down moves profile and follows selection`
        gosub to ResetProfiles
        ! Move Monday-Friday (index 0) down to index 1; manual selection is 0.
        put 0 into ProfileIdx
        put 1 into SwapIdx
        put 0 into ProfileIndex
        gosub to SwapAdjacentProfiles
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        put item 0 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `All Off`
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Monday-Friday`
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 1
    end test

    test `swap of non-selected profiles leaves selection put`
        gosub to ResetProfiles
        put 1 into ProfileIdx
        put 2 into SwapIdx
        put 0 into ProfileIndex
        gosub to SwapAdjacentProfiles
        gosub to ShipProfilesUpdate
        put entry `profile` of Msg into ProfileIndex
        check that ProfileIndex is 0
        put item 1 of NewProfiles into SavedProfile
        put entry `name` of SavedProfile into NewValue
        check that NewValue is `Weekend`
    end test

    exit
!! @hash 59acda36
!!!
