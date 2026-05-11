!! Device-editor concurrent module. Owns the device-editor sheet's DOM, internal state, and event handlers. Hosts the room-and-device editing flow that the parent (shell.as) opens via a single `send` and receives a Save / Cancel reply from.
!!
!! Loaded by shell.as inside BuildHomeScreen via `run ... as DeviceEditorModule`, AFTER the sheet chrome has been rendered. Renders device-editor.json into SheetContent, attaches its DOM, wires its static click handlers (Save / Cancel / Add Room / room-pill / relay-type / linked), then `release parent` and parks on `on message`.
!!
!! Lifecycle of one editing session: parent ships `{profiles, currentProfile, requestRelay}` and blocks. Module clones the profiles tree (mutated in place by the room-list operations), picks the first non-outside room, populates the input fields, shows its sheet, polls on DoneFlag while the user clicks. Save commits the in-flight device-field edits across every profile and ships `{cancelled:`no`, profiles, requestRelay, requestRelayChanged}` back; Cancel ships `{cancelled:`yes`}`.
!!
!! Two outbound payloads from a save: the parent ships Update Profiles for the room-list/device-field changes, and a separate Request Relay only if requestRelay actually changed.
!!
!! Sheet-chrome ownership: parent owns SheetRoot / SheetScrim / SheetContainer / SheetTitleEl (HideAllSheets + OpenSheet before send, CloseSheet after reply). Module only owns DeviceEditorSheetEl and its children.

	script DeviceEditor

	div SheetContent
	div DeviceEditorSheetEl
	button DeviceEditorRoomPill
	div DeviceEditorRoomValue
	div DeviceEditorRoomChev
	div DeviceEditorRoomPicker
	div DeviceEditorRoomList
	button DeviceEditorAddRoomBtn
	button DeviceRoomEditName
	button DeviceRoomEditUp
	button DeviceRoomEditDown
	button DeviceRoomEditPencil
	button DeviceRoomEditDelete
	input DeviceEditorSensor
	button DeviceEditorRtRBRNow
	button DeviceEditorRtZigbee
	button DeviceEditorLinkedBtn
	textarea DeviceEditorRelays
	input DeviceEditorRequest
	button DeviceEditorSaveBtn
	button DeviceEditorCancelBtn

	variable DeviceEditorWebson
	variable DeviceRoomPillJson
	variable DeviceRoomPillText

	variable OpenMsg
	variable Result
	variable DoneFlag
	variable SavePending
	variable ConfirmFlag

	variable CurrentProfile
	variable OriginalRequestRelay

	variable EditingProfilesForDevices
	variable EditingProfilesCountForDevices
	variable EditingDevicesRoomLegacyIdx
	variable EditingDevicesRoomName
	variable EditingDevicesRelayType
	variable EditingDevicesLinked
	variable EditingDevicesSensor
	variable EditingDevicesRelaysText
	variable EditingRequestRelay

	variable LiveProfileForDevices
	variable LiveRoomsForDevices
	variable LiveRoomForDevices
	variable RoomEntry
	variable RoomEditCount
	variable RoomEditIdxForOp
	variable PrevLegacyIdx
	variable NextLegacyIdx
	variable NewRoomName
	variable SwapTarget
	variable RoomToInsert

	variable RelayLinesArray
	variable RelayLine
	variable RelayLineIdx

	variable DeviceProfileLoopI
	variable DeviceRoomPickerOpen
	variable DeviceRoomPillIdx
	variable DeviceRoomPillIdxStr

	variable TempStr
	variable NewIdx
	variable NewProfilesArray
	variable LoopE

!	Setup: render the device-editor sheet, attach DOM, wire static click handlers,
!	hide the sheet, park on `on message`.
	attach SheetContent to `sheet-content`
	rest get DeviceRoomPillJson from `resources/webson/device-room-pill.json?v=` cat now
		or stop
	rest get DeviceEditorWebson from `resources/webson/device-editor.json?v=` cat now
		or stop
	render DeviceEditorWebson in SheetContent

	attach DeviceEditorSheetEl to `device-editor-sheet`
	set style `display` of DeviceEditorSheetEl to `none`
	attach DeviceEditorRoomPill to `device-editor-room-pill`
	attach DeviceEditorRoomValue to `device-editor-room-value`
	attach DeviceEditorRoomChev to `device-editor-room-chev`
	attach DeviceEditorRoomPicker to `device-editor-room-picker`
	attach DeviceEditorRoomList to `device-editor-room-list`
	attach DeviceEditorAddRoomBtn to `device-editor-add-room`
	attach DeviceEditorSensor to `device-editor-sensor`
	attach DeviceEditorRtRBRNow to `device-editor-rt-rbrnow`
	attach DeviceEditorRtZigbee to `device-editor-rt-zigbee`
	attach DeviceEditorLinkedBtn to `device-editor-linked-btn`
	attach DeviceEditorRelays to `device-editor-relays`
	attach DeviceEditorRequest to `device-editor-request`
	attach DeviceEditorSaveBtn to `device-editor-save-btn`
	attach DeviceEditorCancelBtn to `device-editor-cancel-btn`

	on click DeviceEditorRoomPill gosub to ToggleDeviceRoomPicker
	on click DeviceEditorAddRoomBtn gosub to AddRoomToEditingProfiles
	on click DeviceEditorRtRBRNow
	begin
		put `RBR-Now` into EditingDevicesRelayType
		gosub to PaintDeviceEditorRelayType
	end
	on click DeviceEditorRtZigbee
	begin
		put `Zigbee` into EditingDevicesRelayType
		gosub to PaintDeviceEditorRelayType
	end
	on click DeviceEditorLinkedBtn
	begin
		if EditingDevicesLinked is `yes` put `no` into EditingDevicesLinked
		else put `yes` into EditingDevicesLinked
		gosub to PaintDeviceEditorLinked
	end
	on click DeviceEditorSaveBtn gosub to OnSaveClick
	on click DeviceEditorCancelBtn gosub to OnCancelClick

	on message go to HandleOpen
	release parent
	log `DeviceEditor module ready`
	stop
!! @hash 822dd71e
!!!
!! Open-message handler. Parks until the user clicks Save or Cancel, then ships the reply and terminates.
!!
!! Snapshots the open-message's profiles + currentProfile + requestRelay into the working copies, picks the first non-outside room, populates the device-field inputs, shows the sheet, polls on DoneFlag. The demand-relay value is captured both as a baseline (OriginalRequestRelay) and as the editable EditingRequestRelay so the Save path can detect whether the user changed it.
HandleOpen:
	put the message into OpenMsg
	put property `profiles` of OpenMsg into EditingProfilesForDevices
	put the json count of EditingProfilesForDevices into EditingProfilesCountForDevices
	put property `currentProfile` of OpenMsg into CurrentProfile
	put property `requestRelay` of OpenMsg into OriginalRequestRelay
	put OriginalRequestRelay into EditingRequestRelay
	set the content of DeviceEditorRequest to EditingRequestRelay

	gosub to PickFirstRoomForDevices
	gosub to LoadDeviceEditorRoom

	clear DeviceRoomPickerOpen
	set style `display` of DeviceEditorRoomPicker to `none`
	set style `transform` of DeviceEditorRoomChev to `rotate(0deg)`

	clear DoneFlag
	clear SavePending
	set style `display` of DeviceEditorSheetEl to `block`

	while not DoneFlag wait 10 ticks

	set style `display` of DeviceEditorSheetEl to `none`
	put `{}` into Result
	if SavePending
	begin
		set property `cancelled` of Result to `no`
		set property `profiles` of Result to EditingProfilesForDevices
		set property `requestRelay` of Result to EditingRequestRelay
		if EditingRequestRelay is not OriginalRequestRelay
			set property `requestRelayChanged` of Result to `yes`
		else
			set property `requestRelayChanged` of Result to `no`
	end
	else
	begin
		set property `cancelled` of Result to `yes`
	end
	send Result to sender
	stop
!! @hash fd23e8b0
!!!
!! Save click handler. Reads the input fields, splits the relays textarea on newlines (strips empties) into an array, commits the device-field edits for the currently-selected room across every profile in the working copy, captures the demand-relay value, sets SavePending and DoneFlag so HandleOpen ships the reply.
OnSaveClick:
	if EditingProfilesForDevices is empty
	begin
		log `OnSaveClick: editing copy empty — aborting`
		alert `Map data not loaded — please reload the page.`
		return
	end
	put the content of DeviceEditorSensor into EditingDevicesSensor
	put the content of DeviceEditorRelays into EditingDevicesRelaysText

!	Split the textarea content on newlines, strip empties, into an array.
	put `[]` into RelayLinesArray
	put 0 into RelayLineIdx
	put 0 into LoopE
	if EditingDevicesRelaysText is not empty
	begin
		split EditingDevicesRelaysText on newline giving RelayLine
		while LoopE is less than the elements of RelayLine
		begin
			index RelayLine to LoopE
			if RelayLine is not empty
			begin
				set element RelayLineIdx of RelayLinesArray to RelayLine
				increment RelayLineIdx
			end
			increment LoopE
		end
	end

!	Apply the device-field edits for the currently-selected room across every
!	profile. The room-list edits (move / add / rename / delete) have already
!	been applied to EditingProfilesForDevices by their handlers.
	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than EditingProfilesCountForDevices
	begin
		put element DeviceProfileLoopI of EditingProfilesForDevices into LiveProfileForDevices
		put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
		put element EditingDevicesRoomLegacyIdx of LiveRoomsForDevices into LiveRoomForDevices
		set property `sensor` of LiveRoomForDevices to EditingDevicesSensor
		set property `relayType` of LiveRoomForDevices to EditingDevicesRelayType
		set property `linked` of LiveRoomForDevices to EditingDevicesLinked
		set property `relays` of LiveRoomForDevices to RelayLinesArray
		set element EditingDevicesRoomLegacyIdx of LiveRoomsForDevices to LiveRoomForDevices
		set property `rooms` of LiveProfileForDevices to LiveRoomsForDevices
		set element DeviceProfileLoopI of EditingProfilesForDevices to LiveProfileForDevices
		increment DeviceProfileLoopI
	end

	put the content of DeviceEditorRequest into EditingRequestRelay
	set SavePending
	set DoneFlag
	return
!! @hash 659742b9
!!!
!! Cancel click handler. Sets DoneFlag (but not SavePending) so HandleOpen ships a `{cancelled: yes}` reply.
OnCancelClick:
	set DoneFlag
	return
!! @hash 070995d9
!!!
!! Set EditingDevicesRoomLegacyIdx to the first non-outside room (rooms with a non-empty `relays` array) in the current profile's rooms. Used on initial open and again after a delete that wiped the previously-selected room.
!!
!! Uses the same counter (RoomEditCount) as both loop index and early-exit sentinel — sets it past the array length once a match is found.
PickFirstRoomForDevices:
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put 0 into EditingDevicesRoomLegacyIdx
	put 0 into RoomEditCount
	while RoomEditCount is less than the json count of LiveRoomsForDevices
	begin
		put element RoomEditCount of LiveRoomsForDevices into RoomEntry
		if property `relays` of RoomEntry is not empty
		begin
			put RoomEditCount into EditingDevicesRoomLegacyIdx
			put the json count of LiveRoomsForDevices into RoomEditCount
		end
		increment RoomEditCount
	end
	return
!! @hash 9f06947d
!!!
!! Pull device fields for the currently-selected room out of EditingProfilesForDevices into the input controls.
!!
!! Reads sensor, relayType, linked, relays. Defaults relayType to "RBR-Now" and linked to "yes" on empty/missing fields. Joins the relays array onto separate textarea lines.
!!
!! The demand-relay value is NOT touched here — it's system-wide and was loaded in HandleOpen.
LoadDeviceEditorRoom:
	if EditingProfilesForDevices is empty
	begin
		log `LoadDeviceEditorRoom: editing copy empty — aborting`
		alert `Map data not loaded — please reload the page.`
		return
	end
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put element EditingDevicesRoomLegacyIdx of LiveRoomsForDevices into LiveRoomForDevices
	put property `name` of LiveRoomForDevices into EditingDevicesRoomName

	put property `sensor` of LiveRoomForDevices into EditingDevicesSensor
	put property `relayType` of LiveRoomForDevices into EditingDevicesRelayType
	if EditingDevicesRelayType is empty put `RBR-Now` into EditingDevicesRelayType
	put property `linked` of LiveRoomForDevices into EditingDevicesLinked
	if EditingDevicesLinked is empty put `yes` into EditingDevicesLinked

	put property `relays` of LiveRoomForDevices into RelayLinesArray
	put empty into EditingDevicesRelaysText
	if RelayLinesArray is not empty
	begin
		put 0 into RelayLineIdx
		while RelayLineIdx is less than the json count of RelayLinesArray
		begin
			put element RelayLineIdx of RelayLinesArray into RelayLine
			if EditingDevicesRelaysText is empty put RelayLine into EditingDevicesRelaysText
			else put EditingDevicesRelaysText cat newline cat RelayLine into EditingDevicesRelaysText
			increment RelayLineIdx
		end
	end

	set the content of DeviceEditorRoomValue to EditingDevicesRoomName
	set the content of DeviceEditorSensor to EditingDevicesSensor
	set the content of DeviceEditorRelays to EditingDevicesRelaysText
	gosub to PaintDeviceEditorRelayType
	gosub to PaintDeviceEditorLinked
	return
!! @hash 0e9279cb
!!!
!! Toggle the room picker open / closed. Rebuilds the list each open so adds, moves, deletes, and the current selection highlight all reflect the latest editing state.
ToggleDeviceRoomPicker:
	if DeviceRoomPickerOpen
	begin
		clear DeviceRoomPickerOpen
		set style `display` of DeviceEditorRoomPicker to `none`
		set style `transform` of DeviceEditorRoomChev to `rotate(0deg)`
		return
	end
	gosub to RenderDeviceRoomPicker
	set DeviceRoomPickerOpen
	set style `display` of DeviceEditorRoomPicker to `flex`
	set style `transform` of DeviceEditorRoomChev to `rotate(180deg)`
	return
!! @hash c7e869d2
!!!
!! Render one row per non-outside room in the current profile's rooms array. All profiles share the same rooms (device wiring is physical) — CurrentProfile is just the convenient picker.
!!
!! Each row carries its own legacy index in the indexed-button slots (DeviceRoomEditName / Up / Down / Pencil / Delete). The outside-sensor entry (empty relays) is rendered nowhere and never moved / deleted / renamed.
!!
!! Up arrow hidden on the first non-outside row; Down arrow on the last. Selected row's name gets the accent colour.
RenderDeviceRoomPicker:
	clear DeviceEditorRoomList
	if EditingProfilesForDevices is empty return
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put the json count of LiveRoomsForDevices into RoomEditCount
	if RoomEditCount is 0 return
	set the elements of DeviceRoomEditName to RoomEditCount
	set the elements of DeviceRoomEditUp to RoomEditCount
	set the elements of DeviceRoomEditDown to RoomEditCount
	set the elements of DeviceRoomEditPencil to RoomEditCount
	set the elements of DeviceRoomEditDelete to RoomEditCount

	gosub to FindRoomListEnds

	put 0 into DeviceRoomPillIdx
	while DeviceRoomPillIdx is less than RoomEditCount
	begin
		put element DeviceRoomPillIdx of LiveRoomsForDevices into RoomEntry
		if property `relays` of RoomEntry is empty
		begin
!			Skip the outside-sensor entry — not edited from this list.
			increment DeviceRoomPillIdx
		end
		else
		begin
			put DeviceRoomPillJson into DeviceRoomPillText
			put `` cat DeviceRoomPillIdx into DeviceRoomPillIdxStr
			replace `/I/` with DeviceRoomPillIdxStr in DeviceRoomPillText
			render DeviceRoomPillText in DeviceEditorRoomList

			index DeviceRoomEditName to DeviceRoomPillIdx
			attach DeviceRoomEditName to `device-room-edit-` cat DeviceRoomPillIdxStr cat `-name`
			set the content of DeviceRoomEditName to property `name` of RoomEntry
			if DeviceRoomPillIdx is EditingDevicesRoomLegacyIdx
				set style `color` of DeviceRoomEditName to `var(--color-accent)`

			index DeviceRoomEditUp to DeviceRoomPillIdx
			attach DeviceRoomEditUp to `device-room-edit-` cat DeviceRoomPillIdxStr cat `-up`
			if DeviceRoomPillIdx is PrevLegacyIdx set style `visibility` of DeviceRoomEditUp to `hidden`

			index DeviceRoomEditDown to DeviceRoomPillIdx
			attach DeviceRoomEditDown to `device-room-edit-` cat DeviceRoomPillIdxStr cat `-down`
			if DeviceRoomPillIdx is NextLegacyIdx set style `visibility` of DeviceRoomEditDown to `hidden`

			index DeviceRoomEditPencil to DeviceRoomPillIdx
			attach DeviceRoomEditPencil to `device-room-edit-` cat DeviceRoomPillIdxStr cat `-edit`

			index DeviceRoomEditDelete to DeviceRoomPillIdx
			attach DeviceRoomEditDelete to `device-room-edit-` cat DeviceRoomPillIdxStr cat `-delete`

			on click DeviceRoomEditName
			begin
				put the index of DeviceRoomEditName into EditingDevicesRoomLegacyIdx
				gosub to LoadDeviceEditorRoom
				clear DeviceRoomPickerOpen
				set style `display` of DeviceEditorRoomPicker to `none`
				set style `transform` of DeviceEditorRoomChev to `rotate(0deg)`
			end
			on click DeviceRoomEditUp
			begin
				put the index of DeviceRoomEditUp into RoomEditIdxForOp
				gosub to MoveRoomUpInEditingProfiles
			end
			on click DeviceRoomEditDown
			begin
				put the index of DeviceRoomEditDown into RoomEditIdxForOp
				gosub to MoveRoomDownInEditingProfiles
			end
			on click DeviceRoomEditPencil
			begin
				put the index of DeviceRoomEditPencil into RoomEditIdxForOp
				gosub to RenameRoomInEditingProfiles
			end
			on click DeviceRoomEditDelete
			begin
				put the index of DeviceRoomEditDelete into RoomEditIdxForOp
				gosub to DeleteRoomInEditingProfiles
			end

			increment DeviceRoomPillIdx
		end
	end
	return
!! @hash 3e9d2b4a
!!!
!! Walk the current profile's rooms; capture the lowest and highest legacy indices that hold non-outside rooms into PrevLegacyIdx and NextLegacyIdx. Used by the render loop to hide the up arrow on the first non-outside row and the down arrow on the last.
FindRoomListEnds:
	put -1 into PrevLegacyIdx
	put -1 into NextLegacyIdx
	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than RoomEditCount
	begin
		put element DeviceProfileLoopI of LiveRoomsForDevices into RoomEntry
		if property `relays` of RoomEntry is not empty
		begin
			if PrevLegacyIdx is -1 put DeviceProfileLoopI into PrevLegacyIdx
			put DeviceProfileLoopI into NextLegacyIdx
		end
		increment DeviceProfileLoopI
	end
	return
!! @hash 8743bc31
!!!
!! Room-list mutation routines for the editing working copy. Each operates on EditingProfilesForDevices, applies the same change across every profile, and re-renders the room picker.
!!
!! MoveRoomUp / MoveRoomDown find the previous / next non-outside room (skipping the outside-sensor slot if it sits between the two rooms being swapped) and call SwapRoomsAcrossProfiles. SwapRoomsAcrossProfiles also updates EditingDevicesRoomLegacyIdx so the currently-displayed room follows the swap.
MoveRoomUpInEditingProfiles:
	put RoomEditIdxForOp into SwapTarget
	decrement SwapTarget
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	while SwapTarget is not less than 0
	begin
		put element SwapTarget of LiveRoomsForDevices into RoomEntry
		if property `relays` of RoomEntry is not empty
		begin
			gosub to SwapRoomsAcrossProfiles
			gosub to RenderDeviceRoomPicker
			return
		end
		decrement SwapTarget
	end
	return

MoveRoomDownInEditingProfiles:
	put RoomEditIdxForOp into SwapTarget
	increment SwapTarget
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put the json count of LiveRoomsForDevices into RoomEditCount
	while SwapTarget is less than RoomEditCount
	begin
		put element SwapTarget of LiveRoomsForDevices into RoomEntry
		if property `relays` of RoomEntry is not empty
		begin
			gosub to SwapRoomsAcrossProfiles
			gosub to RenderDeviceRoomPicker
			return
		end
		increment SwapTarget
	end
	return

!	Swap rooms[RoomEditIdxForOp] and rooms[SwapTarget] in every profile.
!	If the swap involves the currently-selected room, follow it so the
!	device-fields panel keeps showing the same room.
SwapRoomsAcrossProfiles:
	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than EditingProfilesCountForDevices
	begin
		put element DeviceProfileLoopI of EditingProfilesForDevices into LiveProfileForDevices
		put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
		put element RoomEditIdxForOp of LiveRoomsForDevices into LiveRoomForDevices
		put element SwapTarget of LiveRoomsForDevices into RoomEntry
		set element RoomEditIdxForOp of LiveRoomsForDevices to RoomEntry
		set element SwapTarget of LiveRoomsForDevices to LiveRoomForDevices
		set property `rooms` of LiveProfileForDevices to LiveRoomsForDevices
		set element DeviceProfileLoopI of EditingProfilesForDevices to LiveProfileForDevices
		increment DeviceProfileLoopI
	end
	if EditingDevicesRoomLegacyIdx is RoomEditIdxForOp put SwapTarget into EditingDevicesRoomLegacyIdx
	else if EditingDevicesRoomLegacyIdx is SwapTarget put RoomEditIdxForOp into EditingDevicesRoomLegacyIdx
	return
!! @hash 2118d67c
!!!
!! Prompt for a new name and apply to rooms[RoomEditIdxForOp].name in every profile. Cancel / blank input = no-op. If the renamed room is the currently-selected one, update the panel's displayed name too.
RenameRoomInEditingProfiles:
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put element RoomEditIdxForOp of LiveRoomsForDevices into RoomEntry
	put property `name` of RoomEntry into TempStr
	put prompt `Rename room:` cat newline cat TempStr into NewRoomName
	if NewRoomName is empty return
	if NewRoomName is `null` return
	if NewRoomName is `undefined` return
	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than EditingProfilesCountForDevices
	begin
		put element DeviceProfileLoopI of EditingProfilesForDevices into LiveProfileForDevices
		put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
		put element RoomEditIdxForOp of LiveRoomsForDevices into LiveRoomForDevices
		set property `name` of LiveRoomForDevices to NewRoomName
		set element RoomEditIdxForOp of LiveRoomsForDevices to LiveRoomForDevices
		set property `rooms` of LiveProfileForDevices to LiveRoomsForDevices
		set element DeviceProfileLoopI of EditingProfilesForDevices to LiveProfileForDevices
		increment DeviceProfileLoopI
	end
	if RoomEditIdxForOp is EditingDevicesRoomLegacyIdx
	begin
		put NewRoomName into EditingDevicesRoomName
		set the content of DeviceEditorRoomValue to EditingDevicesRoomName
	end
	gosub to RenderDeviceRoomPicker
	return
!! @hash 49ba6836
!!!
!! Confirm and remove rooms[RoomEditIdxForOp] from every profile. If the deleted room was the currently-selected one, re-pick the first non-outside room and reload the device fields. Adjusts EditingDevicesRoomLegacyIdx for the shift when the deleted index was earlier than the selected.
DeleteRoomInEditingProfiles:
	put element CurrentProfile of EditingProfilesForDevices into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put element RoomEditIdxForOp of LiveRoomsForDevices into RoomEntry
	put property `name` of RoomEntry into TempStr
	clear ConfirmFlag
	if confirm `Delete room "` cat TempStr cat `"?` set ConfirmFlag
	if not ConfirmFlag return

	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than EditingProfilesCountForDevices
	begin
		put element DeviceProfileLoopI of EditingProfilesForDevices into LiveProfileForDevices
		put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
		json delete element RoomEditIdxForOp of LiveRoomsForDevices
		set property `rooms` of LiveProfileForDevices to LiveRoomsForDevices
		set element DeviceProfileLoopI of EditingProfilesForDevices to LiveProfileForDevices
		increment DeviceProfileLoopI
	end

	if RoomEditIdxForOp is EditingDevicesRoomLegacyIdx
	begin
		gosub to PickFirstRoomForDevices
		gosub to LoadDeviceEditorRoom
	end
	else if RoomEditIdxForOp is less than EditingDevicesRoomLegacyIdx
	begin
		decrement EditingDevicesRoomLegacyIdx
	end
	gosub to RenderDeviceRoomPicker
	return
!! @hash 4a571eb9
!!!
!! Append a fresh "Unnamed" room to every profile's rooms array. Each profile's new room starts with an empty periods array (no schedule yet) and default device fields the user will fill in via the inputs below. prevmode is omitted — the controller writes it on first boost.
AddRoomToEditingProfiles:
	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than EditingProfilesCountForDevices
	begin
		put `{}` into RoomToInsert
		set property `name` of RoomToInsert to `Unnamed`
		set property `sensor` of RoomToInsert to empty
		set property `relays` of RoomToInsert to `[]`
		set property `relayType` of RoomToInsert to `Zigbee`
		set property `linked` of RoomToInsert to `yes`
		set property `mode` of RoomToInsert to `off`
		set property `target` of RoomToInsert to 0
		set property `periods` of RoomToInsert to `[]`
		set property `relay` of RoomToInsert to `off`
		set property `advance` of RoomToInsert to `-`
		set property `protect` of RoomToInsert to `no`

		put element DeviceProfileLoopI of EditingProfilesForDevices into LiveProfileForDevices
		put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
		put the json count of LiveRoomsForDevices into RoomEditCount
		set element RoomEditCount of LiveRoomsForDevices to RoomToInsert
		set property `rooms` of LiveProfileForDevices to LiveRoomsForDevices
		set element DeviceProfileLoopI of EditingProfilesForDevices to LiveProfileForDevices
		increment DeviceProfileLoopI
	end
	gosub to RenderDeviceRoomPicker
	return
!! @hash d8ff5ecf
!!!
!! Style the RBR-Now / Zigbee relay-type pill. Reset blanks both pills; Activate<X> applies the lit look to the matching one.
PaintDeviceEditorRelayType:
	gosub to ResetDeviceEditorRtBtns
	if EditingDevicesRelayType is `RBR-Now` gosub to ActivateRtRBRNow
	else if EditingDevicesRelayType is `Zigbee` gosub to ActivateRtZigbee
	return

ResetDeviceEditorRtBtns:
	set style `background` of DeviceEditorRtRBRNow to `transparent`
	set style `color` of DeviceEditorRtRBRNow to `var(--color-text-muted)`
	set style `font-weight` of DeviceEditorRtRBRNow to `500`
	set style `box-shadow` of DeviceEditorRtRBRNow to `none`
	set style `background` of DeviceEditorRtZigbee to `transparent`
	set style `color` of DeviceEditorRtZigbee to `var(--color-text-muted)`
	set style `font-weight` of DeviceEditorRtZigbee to `500`
	set style `box-shadow` of DeviceEditorRtZigbee to `none`
	return

ActivateRtRBRNow:
	set style `background` of DeviceEditorRtRBRNow to `var(--color-surface-card)`
	set style `color` of DeviceEditorRtRBRNow to `var(--color-text-primary)`
	set style `font-weight` of DeviceEditorRtRBRNow to `600`
	set style `box-shadow` of DeviceEditorRtRBRNow to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateRtZigbee:
	set style `background` of DeviceEditorRtZigbee to `var(--color-surface-card)`
	set style `color` of DeviceEditorRtZigbee to `var(--color-text-primary)`
	set style `font-weight` of DeviceEditorRtZigbee to `600`
	set style `box-shadow` of DeviceEditorRtZigbee to `0 1px 3px rgba(0,0,0,0.08)`
	return
!! @hash 19f3d6c2
!!!
!! Style the linked toggle button — On (accent border + accent text + bold) when EditingDevicesLinked is `yes`, Off (plain card background + hairline border) otherwise.
PaintDeviceEditorLinked:
	if EditingDevicesLinked is `yes`
	begin
		set the content of DeviceEditorLinkedBtn to `On`
		set style `background` of DeviceEditorLinkedBtn to `var(--color-accent-10)`
		set style `border` of DeviceEditorLinkedBtn to `1.5px solid var(--color-accent)`
		set style `color` of DeviceEditorLinkedBtn to `var(--color-accent)`
		set style `font-weight` of DeviceEditorLinkedBtn to `600`
	end
	else
	begin
		set the content of DeviceEditorLinkedBtn to `Off`
		set style `background` of DeviceEditorLinkedBtn to `var(--color-surface-card)`
		set style `border` of DeviceEditorLinkedBtn to `1px solid var(--color-border-hairline)`
		set style `color` of DeviceEditorLinkedBtn to `var(--color-text-primary)`
		set style `font-weight` of DeviceEditorLinkedBtn to `500`
	end
	return
!! @hash ebe7dda5
!!!
