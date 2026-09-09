!   unit-07-rooms.as — tests the desktop app's room-manager logic, mirrored
!   verbatim from desktop/rbr-desktop.as: SwapRoomsInAllProfiles and
!   AddRoomToAllProfiles (each keeps the parallel room list consistent across
!   every profile, then builds the Update Profiles payload via
!   ShipProfilesUpdate).
!
!   Part of the RBR validation of the new testing vocabulary. GUI-only steps
!   (rendering the sheet, the MQTT send) are not mirrored. NOTE: these mirror
!   the subroutines as they stand today; they are not linked to the live
!   code. Keep in sync with desktop/rbr-desktop.as if the logic changes.

    script Unit07Rooms

    list ProfileList
    list Rooms
    list NewProfiles
    list KeptRooms
    list EditedProfileRooms
    list ProfileRooms
    list TestRoomNames
    dictionary EditedProfile
    dictionary NewSpec
    dictionary RoomA
    dictionary RoomB
    dictionary SavedProfile
    dictionary SavedRoom
    dictionary Msg
    variable ProfileListCount
    variable ProfileLoop
    variable ProfileIndex
    variable RoomIdx
    variable SwapIdx
    variable NewValue
    variable Value
    variable RoomName

    go to RunTests

!! Swap room entries RoomIdx / SwapIdx in every profile's rooms array.

SwapRoomsInAllProfiles:
    put the count of Rooms into Value
    if SwapIdx is not less than Value return
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put item RoomIdx of EditedProfileRooms into RoomA
        put item SwapIdx of EditedProfileRooms into RoomB
        set item RoomIdx of EditedProfileRooms to RoomB
        set item SwapIdx of EditedProfileRooms to RoomA
        set entry `rooms` of EditedProfile to EditedProfileRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    return
!! @hash 7b13f8e0
!!!

!! Append a fresh room (named NewValue) to every profile's rooms array.

AddRoomToAllProfiles:
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put `{}` into NewSpec
        set entry `name` of NewSpec to NewValue
        set entry `sensor` of NewSpec to empty
        set entry `relays` of NewSpec to `[]`
        set entry `mode` of NewSpec to `off`
        set entry `target` of NewSpec to 20
        set entry `events` of NewSpec to `[]`
        set entry `relayType` of NewSpec to `Zigbee`
        set entry `protect` of NewSpec to `no`
        set entry `linked` of NewSpec to `yes`
        set entry `advance` of NewSpec to `-`
        set entry `prevmode` of NewSpec to `off`
        set entry `relay` of NewSpec to `off`
        set entry `status` of NewSpec to `good`
        set entry `temperature` of NewSpec to -1
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        append NewSpec to EditedProfileRooms
        set entry `rooms` of EditedProfile to EditedProfileRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    return
!! @hash 2d1a2b5f
!!!

!! Rename room RoomIdx to NewValue in every profile's rooms array.

RenameRoomInAllProfiles:
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put item RoomIdx of EditedProfileRooms into NewSpec
        set entry `name` of NewSpec to NewValue
        set item RoomIdx of EditedProfileRooms to NewSpec
        set entry `rooms` of EditedProfile to EditedProfileRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    return
!! @hash 45de7a11
!!!

!! Remove room RoomIdx from every profile's rooms array. The last room is
!! protected (mirrors the app guard reading the live room count).

DeleteRoomFromAllProfiles:
    put the count of Rooms into Value
    if Value is less than 2 return
    put ProfileList into NewProfiles
    put the count of NewProfiles into ProfileListCount
    put 0 into ProfileLoop
    while ProfileLoop is less than ProfileListCount
    begin
        put item ProfileLoop of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put the count of EditedProfileRooms into Value
        put `[]` into KeptRooms
        put 0 into SwapIdx
        while SwapIdx is less than the count of EditedProfileRooms
        begin
            if SwapIdx is not RoomIdx
            begin
                put item SwapIdx of EditedProfileRooms into NewSpec
                append NewSpec to KeptRooms
            end
            increment SwapIdx
        end
        set entry `rooms` of EditedProfile to KeptRooms
        set item ProfileLoop of NewProfiles to EditedProfile
        increment ProfileLoop
    end
    return
!! @hash f26d01f2
!!!

ShipProfilesUpdate:
    put `{}` into Msg
    set entry `Action` of Msg to `Update Profiles`
    set entry `profiles` of Msg to NewProfiles
    set entry `profile` of Msg to ProfileIndex
    return
!! @hash f2aebc31
!!!

!! Test helper: two profiles with parallel rooms A B C (profile 1 carries a
!! distinguishing per-room mode so we can prove state travels with the room).

ResetRooms:
    reset ProfileList
    reset TestRoomNames
    put `A` into RoomName
    append RoomName to TestRoomNames
    put `B` into RoomName
    append RoomName to TestRoomNames
    put `C` into RoomName
    append RoomName to TestRoomNames
    ! profile 0: plain rooms
    put `{}` into EditedProfile
    set entry `name` of EditedProfile to `Weekdays`
    reset EditedProfileRooms
    reset ProfileRooms
    reset RoomA
    set entry `name` of RoomA to `A`
    append RoomA to EditedProfileRooms
    set entry `name` of RoomA to `B`
    append RoomA to EditedProfileRooms
    set entry `name` of RoomA to `C`
    append RoomA to EditedProfileRooms
    set entry `rooms` of EditedProfile to EditedProfileRooms
    append EditedProfile to ProfileList
    ! Profile 1: same rooms, room B has mode `on` (state must follow the room)
    put `{}` into EditedProfile
    set entry `name` of EditedProfile to `Weekend`
    reset EditedProfileRooms
    put `{}` into RoomA
    set entry `name` of RoomA to `A`
    set entry `mode` of RoomA to `off`
    append RoomA to EditedProfileRooms
    put `{}` into RoomA
    set entry `name` of RoomA to `B`
    set entry `mode` of RoomA to `on`
    append RoomA to EditedProfileRooms
    put `{}` into RoomA
    set entry `name` of RoomA to `C`
    set entry `mode` of RoomA to `off`
    append RoomA to EditedProfileRooms
    set entry `rooms` of EditedProfile to EditedProfileRooms
    append EditedProfile to ProfileList
    put 3 into Value
    ! Rooms = profile-0's rooms (the swap guard's live list in the app).
    put item 0 of ProfileList into EditedProfile
    put entry `rooms` of EditedProfile into Rooms
    return
!! @hash 45af1cd5
!!!

RunTests:

!! Case 1: swapping rooms reorders every profile the same way.

    test `swap reorders all profiles`
        gosub to ResetRooms
        ! Move room C (index 2) up to index 1 across both profiles.
        put 2 into RoomIdx
        put 1 into SwapIdx
        gosub to SwapRoomsInAllProfiles
        put 1 into ProfileIndex
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        put item 0 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put item 1 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `C`
        put item 1 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put item 1 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `C`
        put entry `mode` of SavedRoom into RoomName
        check that RoomName is `off`
        put item 0 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `A`
        put item 2 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `B`
    end test

!! Case 2: the room's live state (mode) travels with the swapped entry.

    test `swap carries room state`
        gosub to ResetRooms
        put 0 into RoomIdx
        put 1 into SwapIdx
        gosub to SwapRoomsInAllProfiles
        put item 1 of NewProfiles into EditedProfile
        put entry `rooms` of EditedProfile into EditedProfileRooms
        put item 0 of EditedProfileRooms into SavedRoom
        put entry `mode` of SavedRoom into RoomName
        check that RoomName is `on`
    end test

!! Case 3: adding a room appends the same default room to every profile.

    test `add appends to all profiles`
        gosub to ResetRooms
        put `Garage` into NewValue
        gosub to AddRoomToAllProfiles
        put 0 into ProfileIndex
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        check that the count of NewProfiles is 2
        put item 0 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put the count of EditedProfileRooms into Value
        check that Value is 4
        put item 3 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `Garage`
        put entry `relays` of SavedRoom into ProfileRooms
        check that the count of ProfileRooms is 0
        put item 1 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put item 3 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `Garage`
        put entry `mode` of SavedRoom into RoomName
        check that RoomName is `off`
    end test

!! Case 4: rename applies to every profile's room at RoomIdx.

    test `rename room across all profiles`
        gosub to ResetRooms
        put 1 into RoomIdx
        put `Dining` into NewValue
        gosub to RenameRoomInAllProfiles
        put 0 into ProfileIndex
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        put item 0 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put item 1 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `Dining`
        put item 1 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put item 1 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `Dining`
        put entry `mode` of SavedRoom into RoomName
        check that RoomName is `on`
    end test

!! Case 5: deleting a room removes it from every profile; state of the
!! remaining rooms is untouched.

    test `delete room across all profiles`
        gosub to ResetRooms
        put 1 into RoomIdx
        gosub to DeleteRoomFromAllProfiles
        put 0 into ProfileIndex
        gosub to ShipProfilesUpdate
        put entry `profiles` of Msg into NewProfiles
        put item 0 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put the count of EditedProfileRooms into Value
        check that Value is 2
        put item 0 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `A`
        put item 1 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `C`
        put item 1 of NewProfiles into SavedProfile
        put entry `rooms` of SavedProfile into EditedProfileRooms
        put the count of EditedProfileRooms into Value
        check that Value is 2
        put item 1 of EditedProfileRooms into SavedRoom
        put entry `name` of SavedRoom into RoomName
        check that RoomName is `C`
    end test

    exit
!! @hash 6c6be4c7
!!!
