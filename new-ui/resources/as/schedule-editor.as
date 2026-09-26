!! Schedule-editor concurrent module. Owns the schedule-editor sheet's DOM, internal state, and event handlers. Hosts the per-room schedule editing flow that the parent (shell.as) opens via a single `send` and receives a Save / Cancel reply from.
!!
!! Loaded by shell.as inside BuildHomeScreen via `run ... as ScheduleEditorModule`, AFTER the sheet chrome has been rendered (so SheetContent exists to attach into). The module renders schedule-editor.json into SheetContent, attaches its DOM, wires its static click handlers (Save / Cancel / Add / profile-pill), then `release parent` and parks on `on message`.
!!
!! Lifecycle of one editing session: parent ships `{roomName, roomLegacyIdx, profileIdx, profiles}` and blocks on the reply. Module unpacks, clones the host room's periods into EditingPeriods (display shape {start, off, target}), renders period cards, shows its sheet, then waits in a poll loop (`while not DoneFlag wait 10 ticks`) for the Save or Cancel click handlers to fire. Save commits the edits back into the LiveProfiles snapshot the parent sent; Cancel discards. The handler hides the sheet, ships either `{cancelled:`no`, profiles}` or `{cancelled:`yes`}` back, and stops.
!!
!! Sheet-chrome ownership: the parent owns SheetRoot / SheetScrim / SheetContainer / SheetTitleEl. The module only owns ScheduleSheetEl and its children. The parent calls HideAllSheets + OpenSheet before send and CloseSheet after the reply, so the chrome animation brackets the whole editing session.

	script ScheduleEditor

	div SheetContent
	div ScheduleSheetEl
	button ScheduleProfilePillBtn
	div ScheduleProfileValue
	div ScheduleProfileChev
	div ScheduleProfilePicker
	button SchedProfilePill
	div SchedulePeriodList
	button ScheduleAddBtn
	button ScheduleSaveBtn
	button ScheduleCancelBtn
	div PeriodCardEl
	div PeriodTimeValue
	button PeriodTimeMinusBtn
	button PeriodTimePlusBtn
	div PeriodTempValue
	button PeriodTempMinusBtn
	button PeriodTempPlusBtn
	button PeriodDeleteBtn
	input PeriodEnableBox
	div PeriodTimeRow
	div PeriodOffRow
	div PeriodTempRow
	div PeriodOffValue
	button PeriodOffMinusBtn
	button PeriodOffPlusBtn

	variable ScheduleSheetWebson
	variable PeriodCardJson
	variable PeriodCardText
	variable SchedProfilePillJson
	variable SchedProfilePillText

	variable OpenMsg
	variable Result
	variable DoneFlag
	variable SavePending
	variable ConfirmFlag

	variable LiveProfiles
	variable Profiles
	variable ProfileN
	variable LegacyProfileCount
	variable LiveProfileForRoom
	variable LiveRoomsForRoom
	variable LiveRoomForSchedule

	variable EditingPeriods
	variable EditingPeriodsCount
	variable EditingRoomLegacyIdx
	variable EditingRoomName
	variable EditingProfileIdx
	variable EditingProfileName

	variable SourcePeriods
	variable SourcePeriodsCount
	variable SourcePeriod
	variable ClonedPeriod
	variable SortedPeriods

	variable PeriodIdx
	variable PeriodIdxStr
	variable PeriodRow
	variable PeriodTime
	variable PeriodTemp
	variable PeriodTempTenths
	variable PeriodOff
	variable PeriodEnabled
	variable PeriodDim
	variable PeriodBlock

	variable ScheduleDirty
	variable ScheduleProfilePickerOpen
	variable SchedProfilePillIdx
	variable SchedProfilePillIdxStr

	variable PeriodA
	variable PeriodB
	variable SortI
	variable SortJ
	variable SortJplus1
	variable SortAMinutes
	variable SortBMinutes

	variable ScheduleH
	variable ScheduleM
	variable NewProfilesArray
	variable NewIdx
	variable LoopE

	variable TempStr
	variable TempTenths
	variable DotIdx
	variable DecPart
	variable NegativeFlag
	variable AvgInt
	variable AvgDec

!	Setup: load templates, render the sheet into the parent's sheet-content,
!	attach all DOM elements, wire static (non-per-row) click handlers, hide
!	the sheet, then park on `on message`.
	attach SheetContent to `sheet-content`
	rest get PeriodCardJson from `resources/webson/schedule-period.json?v=` cat now
		or stop
	rest get SchedProfilePillJson from `resources/webson/sched-profile-pill.json?v=` cat now
		or stop
	rest get ScheduleSheetWebson from `resources/webson/schedule-editor.json?v=` cat now
		or stop
	render ScheduleSheetWebson in SheetContent

	attach ScheduleSheetEl to `schedule-editor-sheet`
	set style `display` of ScheduleSheetEl to `none`
	attach ScheduleProfilePillBtn to `schedule-profile-pill`
	attach ScheduleProfileValue to `schedule-profile-value`
	attach ScheduleProfileChev to `schedule-profile-chev`
	attach ScheduleProfilePicker to `schedule-profile-picker`
	attach SchedulePeriodList to `schedule-period-list`
	attach ScheduleAddBtn to `schedule-add-btn`
	attach ScheduleSaveBtn to `schedule-save-btn`
	attach ScheduleCancelBtn to `schedule-cancel-btn`

	on click ScheduleProfilePillBtn gosub to ToggleSchedProfilePicker
	on click ScheduleAddBtn gosub to AddSchedulePeriod
	on click ScheduleSaveBtn gosub to OnSaveClick
	on click ScheduleCancelBtn gosub to OnCancelClick

	on message go to HandleOpen
	release parent
	log `ScheduleEditor module ready`
	stop
!! @hash b7b51849
!!!
!! Open-message handler. Parks until the user clicks Save or Cancel, then ships the reply and terminates.
!!
!! Resets per-session state (ScheduleDirty, picker-open), clones the target room's periods into EditingPeriods, paints the profile pill and the period cards, shows the sheet, then poll-waits on DoneFlag. The wait yields every 10 ticks so click handlers can fire on their own threads; the runtime guarantees other event handlers in this and the parent script keep running.
HandleOpen:
	put the message into OpenMsg
	put property `roomName` of OpenMsg into EditingRoomName
	put property `roomLegacyIdx` of OpenMsg into EditingRoomLegacyIdx
	put property `profileIdx` of OpenMsg into EditingProfileIdx
	put property `profiles` of OpenMsg into LiveProfiles
	put LiveProfiles into Profiles

	clear ScheduleDirty
	clear ScheduleProfilePickerOpen
	clear DoneFlag
	clear SavePending
	set style `display` of ScheduleProfilePicker to `none`
	set style `transform` of ScheduleProfileChev to `rotate(0deg)`

	gosub to ClonePeriodsForEditing
	gosub to RenderSchedulePeriods
	gosub to PaintSchedProfilePill
	set style `display` of ScheduleSheetEl to `block`

	while not DoneFlag wait 10 ticks

	set style `display` of ScheduleSheetEl to `none`
	put `{}` into Result
	if SavePending
	begin
		set property `cancelled` of Result to `no`
		set property `profiles` of Result to LiveProfiles
	end
	else
	begin
		set property `cancelled` of Result to `yes`
	end
	send Result to sender
	stop
!! @hash 37230515
!!!
!! Save click handler. Sorts EditingPeriods by start time, converts each row back to the storage shape `{on, off, temp, enabled}`, splices the result into LiveProfiles[EditingProfileIdx].rooms[EditingRoomLegacyIdx].periods, sets SavePending and DoneFlag so HandleOpen's wait loop exits and ships the reply.
OnSaveClick:
	gosub to SortPeriods
	put `[]` into SortedPeriods
	put 0 into LoopE
	while LoopE is less than EditingPeriodsCount
	begin
		put element LoopE of EditingPeriods into PeriodRow
		put `{}` into ClonedPeriod
		set property `on` of ClonedPeriod to property `start` of PeriodRow
		set property `off` of ClonedPeriod to property `off` of PeriodRow
		set property `temp` of ClonedPeriod to property `target` of PeriodRow
		set property `enabled` of ClonedPeriod to property `enabled` of PeriodRow
		set element LoopE of SortedPeriods to ClonedPeriod
		increment LoopE
	end

	put element EditingProfileIdx of LiveProfiles into LiveProfileForRoom
	put property `rooms` of LiveProfileForRoom into LiveRoomsForRoom
	put element EditingRoomLegacyIdx of LiveRoomsForRoom into LiveRoomForSchedule
	set property `periods` of LiveRoomForSchedule to SortedPeriods
	set element EditingRoomLegacyIdx of LiveRoomsForRoom to LiveRoomForSchedule
	set property `rooms` of LiveProfileForRoom to LiveRoomsForRoom
	set element EditingProfileIdx of LiveProfiles to LiveProfileForRoom

	set SavePending
	set DoneFlag
	return
!! @hash 7bf45d78
!!!
!! Cancel click handler. Sets DoneFlag (but not SavePending) so HandleOpen ships a `{cancelled: yes}` reply.
OnCancelClick:
	set DoneFlag
	return
!! @hash 070995d9
!!!
!! Update the profile-pill's value text from EditingProfileIdx.
PaintSchedProfilePill:
	put element EditingProfileIdx of Profiles into ProfileN
	put property `name` of ProfileN into EditingProfileName
	set the content of ScheduleProfileValue to EditingProfileName
	return
!! @hash 932ae161
!!!
!! Toggle the profile picker open / closed. Re-renders the pill list on each open so any profile renames or reorders are picked up.
ToggleSchedProfilePicker:
	if ScheduleProfilePickerOpen
	begin
		clear ScheduleProfilePickerOpen
		set style `display` of ScheduleProfilePicker to `none`
		set style `transform` of ScheduleProfileChev to `rotate(0deg)`
		return
	end
	gosub to RenderSchedProfilePicker
	set ScheduleProfilePickerOpen
	set style `display` of ScheduleProfilePicker to `flex`
	set style `transform` of ScheduleProfileChev to `rotate(180deg)`
	return
!! @hash 0cb4b4df
!!!
!! Render one pill per profile into the picker. Tapping a pill calls SwapEditingProfile to switch the editor to that profile's schedule. The currently-editing profile's pill is highlighted with the accent border.
RenderSchedProfilePicker:
	clear ScheduleProfilePicker
	put the json count of Profiles into LegacyProfileCount
	if LegacyProfileCount is 0 return
	set the elements of SchedProfilePill to LegacyProfileCount
	put 0 into SchedProfilePillIdx
	while SchedProfilePillIdx is less than LegacyProfileCount
	begin
		put SchedProfilePillJson into SchedProfilePillText
		put `` cat SchedProfilePillIdx into SchedProfilePillIdxStr
		replace `/I/` with SchedProfilePillIdxStr in SchedProfilePillText
		render SchedProfilePillText in ScheduleProfilePicker

		index SchedProfilePill to SchedProfilePillIdx
		attach SchedProfilePill to `sched-profile-pill-` cat SchedProfilePillIdxStr
		put element SchedProfilePillIdx of Profiles into ProfileN
		set the content of SchedProfilePill to property `name` of ProfileN
		if SchedProfilePillIdx is EditingProfileIdx
		begin
			set style `border-color` of SchedProfilePill to `var(--color-accent)`
			set style `color` of SchedProfilePill to `var(--color-accent)`
		end

		on click SchedProfilePill
		begin
			put the index of SchedProfilePill into SchedProfilePillIdx
			gosub to SwapEditingProfile
		end

		increment SchedProfilePillIdx
	end
	return
!! @hash 4f8dbfa3
!!!
!! Swap the editor to the profile at SchedProfilePillIdx. If the current edit buffer is dirty, confirm before discarding.
!!
!! Re-clones the new profile's periods into EditingPeriods, re-renders the period cards, repaints the profile pill, closes the picker. The dirty flag is cleared because the new clone is by definition clean.
SwapEditingProfile:
	if SchedProfilePillIdx is EditingProfileIdx
	begin
		gosub to ToggleSchedProfilePicker
		return
	end
	if ScheduleDirty
	begin
		clear ConfirmFlag
		if confirm `Discard unsaved changes to this profile?` set ConfirmFlag
		if not ConfirmFlag return
	end
	put SchedProfilePillIdx into EditingProfileIdx
	clear ScheduleDirty
	gosub to ClonePeriodsForEditing
	gosub to RenderSchedulePeriods
	gosub to PaintSchedProfilePill
	clear ScheduleProfilePickerOpen
	set style `display` of ScheduleProfilePicker to `none`
	set style `transform` of ScheduleProfileChev to `rotate(0deg)`
	return
!! @hash 339be3e0
!!!
!! Clone the host room's `periods` (in the currently-editing profile) into EditingPeriods.
!!
!! Buffer shape is `{start, off, target, enabled}` rather than the storage shape `{on, off, temp, enabled}` — `start` is the ON time, renamed so PaintPeriodValues and StepPeriodTime work uniformly without per-field branches; the OFF stepper handles `off`. `enabled` is carried straight across: an absent flag reads as enabled, so an older map with no flags shows every period switched on. OnSaveClick maps everything back to the storage shape on commit.
!!
!! Each display row is a fresh `{}` so edits don't bleed back through the snapshot.
ClonePeriodsForEditing:
	put `[]` into EditingPeriods
	put element EditingProfileIdx of LiveProfiles into LiveProfileForRoom
	put property `rooms` of LiveProfileForRoom into LiveRoomsForRoom
	put element EditingRoomLegacyIdx of LiveRoomsForRoom into LiveRoomForSchedule

	put property `periods` of LiveRoomForSchedule into SourcePeriods
	if SourcePeriods is empty
	begin
		put 0 into EditingPeriodsCount
		return
	end
	put the json count of SourcePeriods into SourcePeriodsCount
	put 0 into LoopE
	while LoopE is less than SourcePeriodsCount
	begin
		put element LoopE of SourcePeriods into SourcePeriod
		put `{}` into ClonedPeriod
		set property `start` of ClonedPeriod to property `on` of SourcePeriod
		set property `off` of ClonedPeriod to property `off` of SourcePeriod
		set property `target` of ClonedPeriod to property `temp` of SourcePeriod
		set PeriodEnabled
		if SourcePeriod has entry `enabled`
		begin
			if property `enabled` of SourcePeriod set PeriodEnabled
			else clear PeriodEnabled
		end
		set property `enabled` of ClonedPeriod to PeriodEnabled
		set element LoopE of EditingPeriods to ClonedPeriod
		increment LoopE
	end
	put SourcePeriodsCount into EditingPeriodsCount
	return
!! @hash b3419282
!!!
!! Tear down and rebuild the period cards from EditingPeriods.
!!
!! Each card carries its own indexed steppers (time -/+, temp -/+, off -/+) and a delete button. Click handlers recover the firing card via `the index of`. The OFF row is always shown (events-mode without OFF is no longer supported; the schedule model has been periods-only since 2026-05-08).
RenderSchedulePeriods:
	clear SchedulePeriodList
	if EditingPeriodsCount is 0 return
	set the elements of PeriodCardEl to EditingPeriodsCount
	set the elements of PeriodTimeValue to EditingPeriodsCount
	set the elements of PeriodTempValue to EditingPeriodsCount
	set the elements of PeriodTimeMinusBtn to EditingPeriodsCount
	set the elements of PeriodTimePlusBtn to EditingPeriodsCount
	set the elements of PeriodTempMinusBtn to EditingPeriodsCount
	set the elements of PeriodTempPlusBtn to EditingPeriodsCount
	set the elements of PeriodDeleteBtn to EditingPeriodsCount
	set the elements of PeriodEnableBox to EditingPeriodsCount
	set the elements of PeriodTimeRow to EditingPeriodsCount
	set the elements of PeriodOffRow to EditingPeriodsCount
	set the elements of PeriodTempRow to EditingPeriodsCount
	set the elements of PeriodOffValue to EditingPeriodsCount
	set the elements of PeriodOffMinusBtn to EditingPeriodsCount
	set the elements of PeriodOffPlusBtn to EditingPeriodsCount

	put 0 into PeriodIdx
	while PeriodIdx is less than EditingPeriodsCount
	begin
		put PeriodCardJson into PeriodCardText
		put `` cat PeriodIdx into PeriodIdxStr
		replace `/I/` with PeriodIdxStr in PeriodCardText
		render PeriodCardText in SchedulePeriodList

		index PeriodCardEl to PeriodIdx
		attach PeriodCardEl to `schedule-period-` cat PeriodIdxStr
		index PeriodTimeValue to PeriodIdx
		attach PeriodTimeValue to `schedule-period-` cat PeriodIdxStr cat `-time-value`
		index PeriodTempValue to PeriodIdx
		attach PeriodTempValue to `schedule-period-` cat PeriodIdxStr cat `-temp-value`
		index PeriodTimeMinusBtn to PeriodIdx
		attach PeriodTimeMinusBtn to `schedule-period-` cat PeriodIdxStr cat `-time-minus`
		index PeriodTimePlusBtn to PeriodIdx
		attach PeriodTimePlusBtn to `schedule-period-` cat PeriodIdxStr cat `-time-plus`
		index PeriodTempMinusBtn to PeriodIdx
		attach PeriodTempMinusBtn to `schedule-period-` cat PeriodIdxStr cat `-temp-minus`
		index PeriodTempPlusBtn to PeriodIdx
		attach PeriodTempPlusBtn to `schedule-period-` cat PeriodIdxStr cat `-temp-plus`
		index PeriodDeleteBtn to PeriodIdx
		attach PeriodDeleteBtn to `schedule-period-` cat PeriodIdxStr cat `-delete`
		index PeriodEnableBox to PeriodIdx
		attach PeriodEnableBox to `schedule-period-` cat PeriodIdxStr cat `-enable`

		index PeriodOffRow to PeriodIdx
		attach PeriodOffRow to `schedule-period-` cat PeriodIdxStr cat `-off-row`
		index PeriodTimeRow to PeriodIdx
		attach PeriodTimeRow to `schedule-period-` cat PeriodIdxStr cat `-time-row`
		index PeriodTempRow to PeriodIdx
		attach PeriodTempRow to `schedule-period-` cat PeriodIdxStr cat `-temp-row`
		index PeriodOffValue to PeriodIdx
		attach PeriodOffValue to `schedule-period-` cat PeriodIdxStr cat `-off-value`
		index PeriodOffMinusBtn to PeriodIdx
		attach PeriodOffMinusBtn to `schedule-period-` cat PeriodIdxStr cat `-off-minus`
		index PeriodOffPlusBtn to PeriodIdx
		attach PeriodOffPlusBtn to `schedule-period-` cat PeriodIdxStr cat `-off-plus`

		gosub to PaintPeriodValues
		gosub to PaintPeriodEnabled

		on click PeriodTimeMinusBtn
		begin
			put the index of PeriodTimeMinusBtn into PeriodIdx
			put -15 into ScheduleM
			gosub to StepPeriodTime
		end
		on click PeriodTimePlusBtn
		begin
			put the index of PeriodTimePlusBtn into PeriodIdx
			put 15 into ScheduleM
			gosub to StepPeriodTime
		end
		on click PeriodTempMinusBtn
		begin
			put the index of PeriodTempMinusBtn into PeriodIdx
			put -5 into PeriodTempTenths
			gosub to StepPeriodTemp
		end
		on click PeriodTempPlusBtn
		begin
			put the index of PeriodTempPlusBtn into PeriodIdx
			put 5 into PeriodTempTenths
			gosub to StepPeriodTemp
		end
		on click PeriodDeleteBtn
		begin
			put the index of PeriodDeleteBtn into PeriodIdx
			gosub to DeleteSchedulePeriod
		end

		on change PeriodEnableBox
		begin
			put the index of PeriodEnableBox into PeriodIdx
			gosub to TogglePeriodEnabled
		end

		on click PeriodOffMinusBtn
		begin
			put the index of PeriodOffMinusBtn into PeriodIdx
			put -15 into ScheduleM
			gosub to StepPeriodOff
		end
		on click PeriodOffPlusBtn
		begin
			put the index of PeriodOffPlusBtn into PeriodIdx
			put 15 into ScheduleM
			gosub to StepPeriodOff
		end

		increment PeriodIdx
	end
	return
!! @hash 9415b520
!!!
!! Paint the on / off / target values for PeriodIdx into the existing card without a full re-render. Reads EditingPeriods[PeriodIdx] and writes the three text spans. Temperature gets a "°" suffix; times are already "HH:MM" strings.
PaintPeriodValues:
	index PeriodTimeValue to PeriodIdx
	index PeriodTempValue to PeriodIdx
	index PeriodOffValue to PeriodIdx
	put element PeriodIdx of EditingPeriods into PeriodRow
	put property `start` of PeriodRow into PeriodTime
	set the content of PeriodTimeValue to PeriodTime
	put property `off` of PeriodRow into PeriodOff
	set the content of PeriodOffValue to PeriodOff
	put `` cat property `target` of PeriodRow into PeriodTemp
	put the index of `.` in PeriodTemp into DotIdx
	if DotIdx is less than 0 put PeriodTemp cat `.0` into PeriodTemp
	set the content of PeriodTempValue to PeriodTemp cat `°`
	return
!! @hash 8ee57fd7
!!!
!! Paint the Enabled state of the card at PeriodIdx: the checkbox, plus the three editable rows. Sets the DOM `checked` attribute for an enabled period and removes it for a disabled one (a boolean HTML attribute is on when present, so a false value must be removed, not set to "false"); a disabled period's rows are dimmed to 45% and given `pointer-events: none`, so its steppers are inert and it reads as switched off. Called once per card right after it is rendered — the elements are then fresh, so the attribute still governs the live checkedness — and again from TogglePeriodEnabled so the dimming tracks the checkbox.
PaintPeriodEnabled:
	index PeriodEnableBox to PeriodIdx
	index PeriodTimeRow to PeriodIdx
	index PeriodOffRow to PeriodIdx
	index PeriodTempRow to PeriodIdx
	put element PeriodIdx of EditingPeriods into PeriodRow
	put `1` into PeriodDim
	put `auto` into PeriodBlock
	if property `enabled` of PeriodRow
		set attribute `checked` of PeriodEnableBox to `checked`
	else
	begin
		remove attribute `checked` of PeriodEnableBox
		put `0.45` into PeriodDim
		put `none` into PeriodBlock
	end
	set style `opacity` of PeriodTimeRow to PeriodDim
	set style `opacity` of PeriodOffRow to PeriodDim
	set style `opacity` of PeriodTempRow to PeriodDim
	set style `pointer-events` of PeriodTimeRow to PeriodBlock
	set style `pointer-events` of PeriodOffRow to PeriodBlock
	set style `pointer-events` of PeriodTempRow to PeriodBlock
	return
!! @hash ff6ffcb6
!!!
!! StepPeriodTime / StepPeriodOff adjust the on/off time by ScheduleM (±15) minutes, wrapping at 24:00. StepPeriodTemp adjusts the target by PeriodTempTenths (±5 = ±0.5°), clamped to [5.0°, 30.0°].
!!
!! Updates the displayed value in place; the sort happens on Save rather than per-edit so the user can drift one period through midnight without rows jumping under their finger. Sets ScheduleDirty so SwapEditingProfile can confirm before discarding.
StepPeriodTime:
	put element PeriodIdx of EditingPeriods into PeriodRow
	put property `start` of PeriodRow into TempStr
	gosub to ParseTimeMinutes
	add TempTenths to ScheduleM
	if ScheduleM is less than 0 add 1440 to ScheduleM
	put ScheduleM modulo 1440 into ScheduleM
	gosub to MinutesToHHMM
	set property `start` of PeriodRow to TempStr
	set element PeriodIdx of EditingPeriods to PeriodRow
	set ScheduleDirty
	gosub to PaintPeriodValues
	return

StepPeriodOff:
	put element PeriodIdx of EditingPeriods into PeriodRow
	put property `off` of PeriodRow into TempStr
	gosub to ParseTimeMinutes
	add TempTenths to ScheduleM
	if ScheduleM is less than 0 add 1440 to ScheduleM
	put ScheduleM modulo 1440 into ScheduleM
	gosub to MinutesToHHMM
	set property `off` of PeriodRow to TempStr
	set element PeriodIdx of EditingPeriods to PeriodRow
	set ScheduleDirty
	gosub to PaintPeriodValues
	return

StepPeriodTemp:
	put element PeriodIdx of EditingPeriods into PeriodRow
	put `` cat property `target` of PeriodRow into TempStr
	gosub to ToTenths
	add PeriodTempTenths to TempTenths
	if TempTenths is less than 50 put 50 into TempTenths
	if TempTenths is greater than 300 put 300 into TempTenths
	gosub to TenthsToString
	set property `target` of PeriodRow to TempStr
	set element PeriodIdx of EditingPeriods to PeriodRow
	set ScheduleDirty
	gosub to PaintPeriodValues
	return
!! @hash 49aed685
!!!
!! Add a new period to the editor with sensible defaults: 06:00–08:00 at 21.0°. Sort happens on Save.
AddSchedulePeriod:
	put `{}` into ClonedPeriod
	set property `start` of ClonedPeriod to `06:00`
	set property `off` of ClonedPeriod to `08:00`
	set property `target` of ClonedPeriod to `21.0`
	set property `enabled` of ClonedPeriod to true
	set element EditingPeriodsCount of EditingPeriods to ClonedPeriod
	increment EditingPeriodsCount
	set ScheduleDirty
	gosub to RenderSchedulePeriods
	return
!! @hash ac100a7a
!!!
!! Record a tap on PeriodIdx's Enabled checkbox. Reads the box's own checked state (the checkbox already holds the new value) and writes it onto the editing row, then marks the schedule dirty so a Cancel or profile switch still confirms. No full re-render: the DOM already shows the new state, and PaintPeriodEnabled dims or undims the row's controls to match.
TogglePeriodEnabled:
	put element PeriodIdx of EditingPeriods into PeriodRow
	put PeriodEnableBox into PeriodEnabled
	set property `enabled` of PeriodRow to PeriodEnabled
	set element PeriodIdx of EditingPeriods to PeriodRow
	set ScheduleDirty
	gosub to PaintPeriodEnabled
	return
!! @hash 1f88de45
!!!
!! Remove the period at PeriodIdx by rebuilding the array without it, then re-rendering the card list. Sets ScheduleDirty.
DeleteSchedulePeriod:
	put `[]` into NewProfilesArray
	put 0 into NewIdx
	put 0 into LoopE
	while LoopE is less than EditingPeriodsCount
	begin
		if LoopE is not PeriodIdx
		begin
			put element LoopE of EditingPeriods into PeriodRow
			set element NewIdx of NewProfilesArray to PeriodRow
			increment NewIdx
		end
		increment LoopE
	end
	put NewProfilesArray into EditingPeriods
	put NewIdx into EditingPeriodsCount
	set ScheduleDirty
	gosub to RenderSchedulePeriods
	return
!! @hash f65e2eaf
!!!
!! Bubble-sort EditingPeriods in place by `start` time (minutes-since-midnight). N is small (typical schedules are ≤6 periods) so simple O(n²) is fine. Called once from OnSaveClick before writing back.
SortPeriods:
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
				put element SortJ of EditingPeriods into PeriodA
				put element SortJplus1 of EditingPeriods into PeriodB
				put property `start` of PeriodA into TempStr
				gosub to ParseTimeMinutes
				put TempTenths into SortAMinutes
				put property `start` of PeriodB into TempStr
				gosub to ParseTimeMinutes
				put TempTenths into SortBMinutes
				if SortAMinutes is greater than SortBMinutes
				begin
					set element SortJ of EditingPeriods to PeriodB
					set element SortJplus1 of EditingPeriods to PeriodA
				end
			end
			increment SortJ
		end
		increment SortI
	end
	return
!! @hash ac1e3cd9
!!!
!! Convert ScheduleM (0–1439 minutes-since-midnight) into TempStr "HH:MM" with zero-pad on both fields. Used by StepPeriodTime / StepPeriodOff after the modulo-1440 wrap.
MinutesToHHMM:
	put ScheduleM into ScheduleH
	divide ScheduleH by 60
	put ScheduleM modulo 60 into ScheduleM
	if ScheduleH is less than 10 put `0` cat ScheduleH into TempStr
	else put `` cat ScheduleH into TempStr
	put TempStr cat `:` into TempStr
	if ScheduleM is less than 10 put TempStr cat `0` cat ScheduleM into TempStr
	else put TempStr cat ScheduleM into TempStr
	return
!! @hash f571543d
!!!
!! Parse TempStr ("HH:MM" or "H:MM") into minutes-since-midnight; output via TempTenths (the variable name is historic — it carries minutes here, not tenths). Empty / malformed input yields 0.
!!
!! Local copy: each AllSpeak module has its own label namespace and the parent's ParseTimeMinutes can't be called from here.
ParseTimeMinutes:
	put 0 into TempTenths
	if TempStr is empty return
	put the index of `:` in TempStr into DotIdx
	if DotIdx is less than 0 return
	put the value of left DotIdx of TempStr into TempTenths
	multiply TempTenths by 60
	increment DotIdx
	put the value of from DotIdx of TempStr into DecPart
	add DecPart to TempTenths
	return
!! @hash 3a38eab5
!!!
!! Convert "X.Y" string → integer tenths (e.g. "20.5" → 205). TempStr in, TempTenths out. Handles negative values natively via `scale`. Local copy of shell.as's ToTenths.
ToTenths:
	put 0 into TempTenths
	if TempStr is empty return
	put TempStr scale 10 into TempTenths
	return
!! @hash 294c7e6e
!!!
!! Reverse of ToTenths: integer tenths → "X.Y" string. TempTenths in, TempStr out. Local copy of shell.as's TenthsToString.
TenthsToString:
	put TempTenths into AvgInt
	put TempTenths modulo 10 into AvgDec
	divide AvgInt by 10
	put AvgInt cat `.` cat AvgDec into TempStr
	return
!! @hash 3855d409
!!!
