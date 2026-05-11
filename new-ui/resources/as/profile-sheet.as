!! Profile-sheet concurrent module. Owns the profile-sheet's DOM (profile list, calendar header, 7-day grid, per-day pickers) and the full edit-then-batch workflow.
!!
!! Loaded by shell.as inside BuildHomeScreen via `run ... as ProfileSheetModule`, AFTER the sheet chrome has been rendered. Renders profile-sheet.json into SheetContent, attaches its DOM, sets up the 7 day-row attaches with their click handlers, wires the static Save / Cancel / Add / calendar-expand / calendar-toggle click handlers, then `release parent` and parks on `on message`.
!!
!! Lifecycle of one editing session: parent ships `{profiles, activeProfileName, calendarOn, calendarData}` and blocks. Module clones the inputs into its Editing* working copies, renders the profile rows + day-grid, polls on DoneFlag. Edits (rename / delete / add / row-tap-to-select / calendar-toggle / day-pick) mutate the working copy in place. Save ships `{cancelled:`no`, profiles, activeIdx, calendarOn, calendarData}`; Cancel ships `{cancelled:`yes`}`.
!!
!! The active-idx is re-derived in OnSaveClick from EditingActiveName so renames of the active profile carry through. Save is disabled (validated) if the active name no longer exists in EditingProfiles (e.g. the user deleted it without picking a replacement).
!!
!! Sheet-chrome ownership: parent owns SheetRoot / SheetScrim / SheetContainer / SheetTitleEl. Module only owns ProfileSheetEl and its children.

	script ProfileSheet

	div SheetContent
	div ProfileSheetEl
	div ProfileTagline
	div ProfileListHolder
	div ProfileRow
	button ProfileBody
	div ProfileLabel
	button ProfileRenameBtn
	button ProfileDeleteBtn
	button ProfileAddBtn
	button ProfileSaveBtn
	button ProfileCancelBtn
	div CalendarHeaderEl
	button CalExpandBtn
	div CalendarHeaderTitle
	div CalendarChev
	div CalendarCardEl
	button CalendarToggleBtn
	div DayRow
	div DayProfileEl
	button DayEditBtn
	div DayPickerEl
	div DayPickerList
	button DayPickerCloseBtn
	button DayPill

	variable ProfileWebson
	variable ProfileRowJson
	variable ProfileRowText
	variable PillRowJson
	variable PillRowText

	variable OpenMsg
	variable Result
	variable DoneFlag
	variable SavePending
	variable ConfirmFlag

	variable Profiles
	variable EditingProfiles
	variable EditingProfilesCount
	variable EditingActiveName
	variable EditingActiveValid
	variable EditingCalendarOn
	variable EditingCalendarData
	variable CalendarCardExpanded

	variable ProfileN
	variable EditProfileN
	variable ProfileName
	variable NewProfileName
	variable ClonedProfile
	variable ClonedEntry
	variable NewProfilesArray
	variable NewIdx
	variable NewActiveIdx
	variable EditIdx
	variable EditClickIdx

	variable LegacyProfileCount
	variable LegacyCalData
	variable LegacyCalCount
	variable LegacyCalEntry
	variable PropName
	variable ProfName

	variable ProfileIdx
	variable ProfileIdxStr
	variable PillIdx
	variable PillIdxStr

	variable DayIds
	variable DayNamesShort
	variable DayIdStr
	variable DayEntry
	variable DayProfileName
	variable DayLoopI
	variable DayEditTargetIdx

	variable TempStr
	variable LoopE

!	Setup: render the profile sheet into the parent's sheet-content, attach DOM,
!	load the per-row templates, populate the day-id / day-name tables, attach the
!	seven day-row elements + wire their per-day click handlers, then wire the
!	static (non-per-row) click handlers and park on `on message`.
	attach SheetContent to `sheet-content`
	rest get ProfileWebson from `resources/webson/profile-sheet.json?v=` cat now
		or stop
	rest get ProfileRowJson from `resources/webson/profile-row.json?v=` cat now
		or stop
	rest get PillRowJson from `resources/webson/calendar-pill.json?v=` cat now
		or stop
	render ProfileWebson in SheetContent

	attach ProfileSheetEl to `profile-sheet`
	set style `display` of ProfileSheetEl to `none`
	attach ProfileListHolder to `profile-list`
	attach ProfileTagline to `profile-tagline`
	attach ProfileAddBtn to `profile-add-btn`
	attach ProfileSaveBtn to `profile-save-btn`
	attach ProfileCancelBtn to `profile-cancel-btn`
	attach CalendarHeaderEl to `profile-calendar-header`
	attach CalExpandBtn to `profile-calendar-expand`
	attach CalendarHeaderTitle to `profile-calendar-title`
	attach CalendarChev to `profile-calendar-chev`
	attach CalendarCardEl to `profile-calendar-card`
	attach CalendarToggleBtn to `profile-calendar-toggle`

!	Day-id and short-name tables, indexed Monday-first to match the legacy
!	calendar-data array shape (day0=Mon ... day6=Sun).
	put `[]` into DayIds
	set element 0 of DayIds to `mon`
	set element 1 of DayIds to `tue`
	set element 2 of DayIds to `wed`
	set element 3 of DayIds to `thu`
	set element 4 of DayIds to `fri`
	set element 5 of DayIds to `sat`
	set element 6 of DayIds to `sun`

	put `[]` into DayNamesShort
	set element 0 of DayNamesShort to `Monday`
	set element 1 of DayNamesShort to `Tuesday`
	set element 2 of DayNamesShort to `Wednesday`
	set element 3 of DayNamesShort to `Thursday`
	set element 4 of DayNamesShort to `Friday`
	set element 5 of DayNamesShort to `Saturday`
	set element 6 of DayNamesShort to `Sunday`

	set the elements of DayRow to 7
	set the elements of DayProfileEl to 7
	set the elements of DayEditBtn to 7
	set the elements of DayPickerEl to 7
	set the elements of DayPickerList to 7
	set the elements of DayPickerCloseBtn to 7
	put 0 into DayLoopI
	while DayLoopI is less than 7
	begin
		put element DayLoopI of DayIds into DayIdStr
		index DayRow to DayLoopI
		attach DayRow to `calendar-` cat DayIdStr
		index DayProfileEl to DayLoopI
		attach DayProfileEl to `calendar-` cat DayIdStr cat `-profile`
		index DayEditBtn to DayLoopI
		attach DayEditBtn to `calendar-` cat DayIdStr cat `-edit`
		index DayPickerEl to DayLoopI
		attach DayPickerEl to `calendar-` cat DayIdStr cat `-picker`
		index DayPickerList to DayLoopI
		attach DayPickerList to `calendar-` cat DayIdStr cat `-picker-list`
		index DayPickerCloseBtn to DayLoopI
		attach DayPickerCloseBtn to `calendar-` cat DayIdStr cat `-picker-close`
		on click DayEditBtn
		begin
			put the index of DayEditBtn into DayEditTargetIdx
			gosub to OpenDayPicker
		end
		on click DayPickerCloseBtn
		begin
			put the index of DayPickerCloseBtn into DayEditTargetIdx
			gosub to CloseDayPicker
		end
		increment DayLoopI
	end

	clear CalendarCardExpanded
	on click CalExpandBtn gosub to ToggleCalendarCard
	on click CalendarToggleBtn
	begin
		if EditingCalendarOn clear EditingCalendarOn else set EditingCalendarOn
		gosub to ApplyCalendarHeaderState
		gosub to ApplyActiveProfile
	end
	on click ProfileAddBtn gosub to AddEditProfile
	on click ProfileSaveBtn gosub to OnSaveClick
	on click ProfileCancelBtn gosub to OnCancelClick

	on message go to HandleOpen
	release parent
	log `ProfileSheet module ready`
	stop
!! @hash 4cf53c6b
!!!
!! Open-message handler. Parks until the user clicks Save or Cancel, then ships the reply and terminates.
!!
!! Snapshots the open-message into the working copies (EditingProfiles, EditingCalendarOn, EditingCalendarData, EditingActiveName), renders the profile rows + active highlight + calendar header state + day grid, collapses the calendar card (predictable initial height), shows the sheet, polls on DoneFlag.
HandleOpen:
	put the message into OpenMsg
	put property `profiles` of OpenMsg into Profiles
	put property `activeProfileName` of OpenMsg into EditingActiveName

	gosub to CloneProfilesForEditing
	clear EditingCalendarOn
	if property `calendarOn` of OpenMsg is `on` set EditingCalendarOn
	put property `calendarData` of OpenMsg into LegacyCalData
	gosub to CloneCalendarData

	gosub to RenderProfileRows
	gosub to ApplyActiveProfile
	gosub to ApplyCalendarHeaderState
	gosub to ApplyDayProfiles
	gosub to ValidateEditingProfiles
	gosub to HideAllDayPickers
	clear CalendarCardExpanded
	set style `display` of CalendarCardEl to `none`
	set style `transform` of CalendarChev to `rotate(0deg)`

	clear DoneFlag
	clear SavePending
	set style `display` of ProfileSheetEl to `block`

	while not DoneFlag wait 10 ticks

	set style `display` of ProfileSheetEl to `none`
	put `{}` into Result
	if SavePending
	begin
		set property `cancelled` of Result to `no`
		set property `profiles` of Result to EditingProfiles
		set property `activeIdx` of Result to NewActiveIdx
		if EditingCalendarOn set property `calendarOn` of Result to `on`
		else set property `calendarOn` of Result to `off`
		set property `calendarData` of Result to EditingCalendarData
	end
	else
	begin
		set property `cancelled` of Result to `yes`
	end
	send Result to sender
	stop
!! @hash 41f935d7
!!!
!! Save click handler. Validates first (no-op if invalid), re-derives the new active-idx from EditingActiveName, sets SavePending and DoneFlag so HandleOpen ships the reply.
OnSaveClick:
	if not EditingActiveValid return
	put 0 into NewActiveIdx
	put 0 into LoopE
	while LoopE is less than EditingProfilesCount
	begin
		put element LoopE of EditingProfiles into EditProfileN
		if property `name` of EditProfileN is EditingActiveName put LoopE into NewActiveIdx
		increment LoopE
	end
	set SavePending
	set DoneFlag
	return
!! @hash 0d6139ec
!!!
!! Cancel click handler. Sets DoneFlag (but not SavePending) so HandleOpen ships a `{cancelled: yes}` reply.
OnCancelClick:
	set DoneFlag
	return
!! @hash 070995d9
!!!
!! Shallow-clone the input Profiles snapshot into EditingProfiles. Each profile is rebuilt as a fresh {} so name edits don't bleed back to the snapshot; the rooms array is aliased — per-room editing happens in the schedule and device editors which work on their own clones.
CloneProfilesForEditing:
	put `[]` into EditingProfiles
	put the json count of Profiles into LegacyProfileCount
	put 0 into LoopE
	while LoopE is less than LegacyProfileCount
	begin
		put element LoopE of Profiles into ProfileN
		put `{}` into ClonedProfile
		set property `name` of ClonedProfile to property `name` of ProfileN
		set property `rooms` of ClonedProfile to property `rooms` of ProfileN
		set element LoopE of EditingProfiles to ClonedProfile
		increment LoopE
	end
	put LegacyProfileCount into EditingProfilesCount
	return
!! @hash 46bddb56
!!!
!! Deep-clone the input calendar-data into EditingCalendarData. Each entry holds a single `day<i>-profile` string.
!!
!! Pads to 7 entries if the source was shorter (controllers can send a short array on first install before any per-day assignments). Source comes from LegacyCalData (set by HandleOpen from the open message).
CloneCalendarData:
	put `[]` into EditingCalendarData
	if LegacyCalData is empty put 0 into LegacyCalCount
	else put the json count of LegacyCalData into LegacyCalCount
	put 0 into LoopE
	while LoopE is less than LegacyCalCount
	begin
		put element LoopE of LegacyCalData into LegacyCalEntry
		put `{}` into ClonedEntry
		put `day` cat LoopE cat `-profile` into PropName
		put property PropName of LegacyCalEntry into ProfName
		if ProfName is not empty set property PropName of ClonedEntry to ProfName
		set element LoopE of EditingCalendarData to ClonedEntry
		increment LoopE
	end
	while LegacyCalCount is less than 7
	begin
		put `{}` into ClonedEntry
		set element LegacyCalCount of EditingCalendarData to ClonedEntry
		increment LegacyCalCount
	end
	return
!! @hash d6a48172
!!!
!! Walk every profile row; highlight the row matching EditingActiveName, dim the row bodies when EditingCalendarOn (admin actions stay enabled).
ApplyActiveProfile:
	put 0 into ProfileIdx
	while ProfileIdx is less than EditingProfilesCount
	begin
		index ProfileRow to ProfileIdx
		index ProfileBody to ProfileIdx
		put element ProfileIdx of EditingProfiles into EditProfileN
		if property `name` of EditProfileN is EditingActiveName
		begin
			set style `border` of ProfileRow to `1.5px solid var(--color-accent)`
			set style `background` of ProfileRow to `var(--color-accent-10)`
		end
		else
		begin
			set style `border` of ProfileRow to `1px solid var(--color-border-hairline)`
			set style `background` of ProfileRow to `var(--color-surface-card)`
		end
		if EditingCalendarOn
		begin
			set style `opacity` of ProfileBody to `0.45`
			set style `cursor` of ProfileBody to `default`
		end
		else
		begin
			set style `opacity` of ProfileBody to `1`
			set style `cursor` of ProfileBody to `pointer`
		end
		increment ProfileIdx
	end
	return
!! @hash 0afd1454
!!!
!! Paint the calendar header pill + toggle button based on EditingCalendarOn.
ApplyCalendarHeaderState:
	if EditingCalendarOn
	begin
		set the content of CalendarHeaderTitle to `Calendar active`
		set style `background` of CalendarHeaderEl to `var(--color-accent-10)`
		set style `border-color` of CalendarHeaderEl to `var(--color-accent)`
		set the content of CalendarToggleBtn to `ON`
		set style `color` of CalendarToggleBtn to `var(--color-accent)`
	end
	else
	begin
		set the content of CalendarHeaderTitle to `Calendar inactive`
		set style `background` of CalendarHeaderEl to `transparent`
		set style `border-color` of CalendarHeaderEl to `var(--color-border-hairline)`
		set the content of CalendarToggleBtn to `OFF`
		set style `color` of CalendarToggleBtn to `var(--color-text-disabled)`
	end
	return
!! @hash 3f215a37
!!!
!! Toggle the calendar card's expansion (the day-grid below the header pill). UI-only; chevron rotates 180° to indicate open state.
ToggleCalendarCard:
	if CalendarCardExpanded
	begin
		clear CalendarCardExpanded
		set style `display` of CalendarCardEl to `none`
		set style `transform` of CalendarChev to `rotate(0deg)`
	end
	else
	begin
		set CalendarCardExpanded
		set style `display` of CalendarCardEl to `block`
		set style `transform` of CalendarChev to `rotate(180deg)`
	end
	return
!! @hash 245021d9
!!!
!! Paint the 7 day-of-week rows from EditingCalendarData. Each entry's `day<i>-profile`; empty / missing shows as em-dash.
ApplyDayProfiles:
	put 0 into DayLoopI
	while DayLoopI is less than 7
	begin
		index DayProfileEl to DayLoopI
		if EditingCalendarData is empty
		begin
			set the content of DayProfileEl to `—`
		end
		else
		begin
			put element DayLoopI of EditingCalendarData into DayEntry
			if DayEntry is empty
			begin
				set the content of DayProfileEl to `—`
			end
			else
			begin
				put property `day` cat DayLoopI cat `-profile` of DayEntry into DayProfileName
				if DayProfileName is empty set the content of DayProfileEl to `—`
				else set the content of DayProfileEl to DayProfileName
			end
		end
		increment DayLoopI
	end
	return
!! @hash 4a6d09c3
!!!
!! Open the day-picker embedded directly under day DayEditTargetIdx (0–6).
!!
!! Hides any other open picker first, then renders one pill per profile in EditingProfiles into this day's picker-list. Pill-click writes the chosen profile name back into EditingCalendarData[DayEditTargetIdx].day<i>-profile and closes the picker.
!!
!! Pill IDs use a single template (`calendar-day-pill-<i>`) across all seven days' pickers, so HideAllDayPickers clears every list first to avoid stale-DOM duplicate-id collisions.
OpenDayPicker:
	gosub to HideAllDayPickers
	index DayPickerList to DayEditTargetIdx
	clear DayPickerList
	if EditingProfilesCount is greater than 0
	begin
		set the elements of DayPill to EditingProfilesCount
		put 0 into PillIdx
		while PillIdx is less than EditingProfilesCount
		begin
			put PillRowJson into PillRowText
			put `` cat PillIdx into PillIdxStr
			replace `/I/` with PillIdxStr in PillRowText
			render PillRowText in DayPickerList

			index DayPill to PillIdx
			attach DayPill to `calendar-day-pill-` cat PillIdxStr
			put element PillIdx of EditingProfiles into EditProfileN
			set the content of DayPill to property `name` of EditProfileN

			on click DayPill
			begin
				put the index of DayPill into PillIdx
				put element PillIdx of EditingProfiles into EditProfileN
				put property `name` of EditProfileN into ProfileName
				put `day` cat DayEditTargetIdx cat `-profile` into PropName
				put element DayEditTargetIdx of EditingCalendarData into DayEntry
				if DayEntry is empty put `{}` into DayEntry
				set property PropName of DayEntry to ProfileName
				set element DayEditTargetIdx of EditingCalendarData to DayEntry
				gosub to ApplyDayProfiles
				gosub to HideAllDayPickers
			end

			increment PillIdx
		end
	end
	index DayPickerEl to DayEditTargetIdx
	set style `display` of DayPickerEl to `block`
	return
!! @hash 43e6be75
!!!
!! Close one specific day's picker (used by its ✕ button). DayEditTargetIdx identifies which day.
CloseDayPicker:
	index DayPickerEl to DayEditTargetIdx
	set style `display` of DayPickerEl to `none`
	return
!! @hash 46868367
!!!
!! Hide every day-picker AND empty every picker-list. Clearing the lists prevents stale pill DOM elements (which all share the id pattern `calendar-day-pill-<i>`) from blocking the next render's attach-by-id.
HideAllDayPickers:
	put 0 into DayLoopI
	while DayLoopI is less than 7
	begin
		index DayPickerEl to DayLoopI
		set style `display` of DayPickerEl to `none`
		index DayPickerList to DayLoopI
		clear DayPickerList
		increment DayLoopI
	end
	return
!! @hash 6c521ef6
!!!
!! Tear down and rebuild the profile list from EditingProfiles. Called on open and after every edit (rename / delete / add).
!!
!! Each row carries three indexed click targets: body (select as active), pencil (rename), ✕ (delete). Tapping body when the calendar is on shows an alert rather than changing selection.
RenderProfileRows:
	clear ProfileListHolder
	if EditingProfilesCount is 0 return
	set the elements of ProfileRow to EditingProfilesCount
	set the elements of ProfileBody to EditingProfilesCount
	set the elements of ProfileLabel to EditingProfilesCount
	set the elements of ProfileRenameBtn to EditingProfilesCount
	set the elements of ProfileDeleteBtn to EditingProfilesCount

	put 0 into ProfileIdx
	while ProfileIdx is less than EditingProfilesCount
	begin
		put ProfileRowJson into ProfileRowText
		put `` cat ProfileIdx into ProfileIdxStr
		replace `/I/` with ProfileIdxStr in ProfileRowText
		render ProfileRowText in ProfileListHolder

		index ProfileRow to ProfileIdx
		attach ProfileRow to `profile-row-` cat ProfileIdxStr
		index ProfileBody to ProfileIdx
		attach ProfileBody to `profile-row-` cat ProfileIdxStr cat `-body`
		index ProfileLabel to ProfileIdx
		attach ProfileLabel to `profile-row-` cat ProfileIdxStr cat `-label`
		index ProfileRenameBtn to ProfileIdx
		attach ProfileRenameBtn to `profile-row-` cat ProfileIdxStr cat `-rename`
		index ProfileDeleteBtn to ProfileIdx
		attach ProfileDeleteBtn to `profile-row-` cat ProfileIdxStr cat `-delete`

		put element ProfileIdx of EditingProfiles into EditProfileN
		set the content of ProfileLabel to property `name` of EditProfileN

		on click ProfileBody
		begin
			if EditingCalendarOn
			begin
				alert `Profiles cannot be accessed while the Calendar is on.`
				return
			end
			put the index of ProfileBody into EditClickIdx
			put element EditClickIdx of EditingProfiles into EditProfileN
			put property `name` of EditProfileN into EditingActiveName
			gosub to ApplyActiveProfile
			gosub to ValidateEditingProfiles
		end
		on click ProfileRenameBtn
		begin
			put the index of ProfileRenameBtn into EditClickIdx
			gosub to RenameEditProfile
		end
		on click ProfileDeleteBtn
		begin
			put the index of ProfileDeleteBtn into EditClickIdx
			gosub to DeleteEditProfile
		end

		increment ProfileIdx
	end
	return
!! @hash 6af4f489
!!!
!! Rename the profile at EditClickIdx. Prompt for a new name, write it back. If the renamed profile was the active one, update EditingActiveName to track the new name.
RenameEditProfile:
	put element EditClickIdx of EditingProfiles into EditProfileN
	put property `name` of EditProfileN into ProfileName
	put prompt `Rename profile:` cat newline cat ProfileName into NewProfileName
	if NewProfileName is empty return
	if NewProfileName is `null` return
	if NewProfileName is `undefined` return
	set property `name` of EditProfileN to NewProfileName
	set element EditClickIdx of EditingProfiles to EditProfileN
	if ProfileName is EditingActiveName put NewProfileName into EditingActiveName
	gosub to RenderProfileRows
	gosub to ApplyActiveProfile
	gosub to ValidateEditingProfiles
	return
!! @hash 8ba58de6
!!!
!! Delete the profile at EditClickIdx after a confirm. Rebuilds EditingProfiles without the entry, re-renders rows. If the active was deleted, ValidateEditingProfiles disables Save until the user picks another.
DeleteEditProfile:
	put element EditClickIdx of EditingProfiles into EditProfileN
	put property `name` of EditProfileN into ProfileName
	put `Delete profile "` cat ProfileName cat `"?` into TempStr
	clear ConfirmFlag
	if confirm TempStr set ConfirmFlag
	if not ConfirmFlag return
	put `[]` into NewProfilesArray
	put 0 into NewIdx
	put 0 into LoopE
	while LoopE is less than EditingProfilesCount
	begin
		if LoopE is not EditClickIdx
		begin
			put element LoopE of EditingProfiles into EditProfileN
			set element NewIdx of NewProfilesArray to EditProfileN
			increment NewIdx
		end
		increment LoopE
	end
	put NewProfilesArray into EditingProfiles
	put NewIdx into EditingProfilesCount
	gosub to RenderProfileRows
	gosub to ApplyActiveProfile
	gosub to ValidateEditingProfiles
	return
!! @hash ec66653d
!!!
!! Add a new profile by cloning the active one (so the new profile inherits the same rooms + schedules — much easier than starting from scratch). Prompt for a name and append.
!!
!! Falls back to profile 0 if the active profile can't be found (shouldn't happen, defensive).
AddEditProfile:
	put -1 into EditIdx
	put 0 into LoopE
	while LoopE is less than EditingProfilesCount
	begin
		put element LoopE of EditingProfiles into EditProfileN
		if property `name` of EditProfileN is EditingActiveName put LoopE into EditIdx
		increment LoopE
	end
	if EditIdx is -1 put 0 into EditIdx

	put prompt `Name for new profile (duplicating current):` into NewProfileName
	if NewProfileName is empty return
	if NewProfileName is `null` return
	if NewProfileName is `undefined` return

	put element EditIdx of EditingProfiles into EditProfileN
	put `{}` into ClonedProfile
	set property `name` of ClonedProfile to NewProfileName
	set property `rooms` of ClonedProfile to property `rooms` of EditProfileN
	set element EditingProfilesCount of EditingProfiles to ClonedProfile
	increment EditingProfilesCount
	gosub to RenderProfileRows
	gosub to ApplyActiveProfile
	gosub to ValidateEditingProfiles
	return
!! @hash 3228305a
!!!
!! Validate the editing state. Save is disabled if EditingActiveName isn't present in EditingProfiles (the user has deleted the previously-active profile without picking another).
!!
!! The Save button is dimmed and uncursored when invalid; full opacity and pointer cursor when valid.
ValidateEditingProfiles:
	clear EditingActiveValid
	put 0 into LoopE
	while LoopE is less than EditingProfilesCount
	begin
		put element LoopE of EditingProfiles into EditProfileN
		if property `name` of EditProfileN is EditingActiveName set EditingActiveValid
		increment LoopE
	end
	if EditingActiveValid
	begin
		set style `opacity` of ProfileSaveBtn to `1`
		set style `cursor` of ProfileSaveBtn to `pointer`
	end
	else
	begin
		set style `opacity` of ProfileSaveBtn to `0.5`
		set style `cursor` of ProfileSaveBtn to `not-allowed`
	end
	return
!! @hash cf58b737
!!!
