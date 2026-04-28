!	Room By Room — new UI shell.
!	Slices 02 (TopBar) + 03 (RoomRow rest state) + 04 (SummaryCard)
!	+ 05 (Sheet chrome + MenuSheet) + 06 (ProfileSheet)
!	+ 07 (RoomRow expansion: mode / target / boost / edit-schedule)
!	+ 08 (Time-of-day background gradient).

	script Shell

	div AppRoot
	div TopBarHolder
	div MainHolder
	div SystemId
	div RoomName
	div HeatingTag
	div OfflineTag
	div Subline
	div TempEl
	div Setpoint
	div Chip
	div ChipIcon
	div Chevron
	div SummaryTitle
	div SummarySubtitle
	div SummaryChip
	div SummaryChipIcon
	div SummaryDot
	div SummaryAvg
	div SummaryOutside
	div SummaryToday
	div SummaryProfileName
	button MenuButton
	button ProfilePill
	div SheetRoot
	div SheetScrim
	div SheetContainer
	button SheetCloseBtn
	div SheetTitleEl
	div SheetContent
	div MenuSheetEl
	div ProfileSheetEl
	button MenuRowProfiles
	button MenuRowRooms
	button MenuRowHoliday
	button MenuRowSystem
	button MenuRowNotifications
	button MenuRowHelp
	button ProfileRowMF
	button ProfileRowWE
	button ProfileRowOff
	div ProfileDotMF
	div ProfileDotWE
	div ProfileDotOff
	div ProfileChipMF
	div ProfileChipWE
	div ProfileChipOff
	button ProfileManageBtn

!	Per-row interactive elements (indexed via `index X to RoomIndex` in the
!	render loop so each click handler can recover its row via `the index of X`).
	button RestRow
	div ChevronEl
	div ExpansionEl
	button ModeTimedBtn
	button ModeOnBtn
	button ModeOffBtn
	div TargetBlockEl
	div TargetValueEl
	button TargetMinusBtn
	button TargetPlusBtn
	div BoostBlockEl
	button BoostCancelBtn
	button Boost30Btn
	button Boost1hBtn
	button Boost2hBtn
	button EditScheduleBtn

	variable LayoutWebson
	variable TopBarWebson
	variable SummaryWebson
	variable SheetWebson
	variable MenuWebson
	variable ProfileWebson
	variable RoomRowText
	variable Seed
	variable RoomsList
	variable Room
	variable RoomIndex
	variable RoomCount
	variable RowText
	variable IndexStr
	variable Mode
	variable TempVal
	variable TargetTemp
	variable NextTime
	variable NextTarget
	variable Offline
	variable Sensor
	variable BoostVal
	variable NameText
	variable SublineText
	variable CallingForHeat
	variable ChipBg
	variable ChipFg
	variable ChipIconUrl
	variable MaskCss

!	Summary pass variables.
	variable LoopI
	variable CurRoom
	variable RName
	variable Ttemp
	variable Tsensor
	variable Toffline
	variable Tcalling
	variable HeatingCount
	variable HeatingNames
	variable SumTenths
	variable AvgCount
	variable TenthsOne
	variable DotIdx
	variable DecPart
	variable OutsideTemp
	variable AvgText
	variable AvgInt
	variable AvgDec
	variable OutsideText
	variable TitleText
	variable SubtitleText
	variable ProfileName

!	Expansion / interaction state.
	variable ExpandedIndex
	variable ClickIndex
	variable NewMode
	variable Tmode
	variable Ttarget
	variable LastTarget
	variable BoostDur
	variable TempStr
	variable TempTenths
	variable TempT
	variable TargetT
	variable Diff
	variable NewCalling

!	Time-of-day background.
	variable Hour
	variable LastHour
	variable GTop
	variable GMid
	variable GBot
	variable BgValue
	variable Glow

	attach AppRoot to `app` or begin
		alert `Missing #app container in index.html`
		stop
	end

	set style `min-height` of AppRoot to `100vh`
	gosub to ApplyBackground

!	Outer three-zone layout.
	rest get LayoutWebson from `resources/webson/layout.json?v=` cat now
		or go to LoadFailed
	render LayoutWebson in AppRoot

!	TopBar.
	attach TopBarHolder to `layout-topbar`
	rest get TopBarWebson from `resources/webson/top-bar.json?v=` cat now
		or go to LoadFailed
	render TopBarWebson in TopBarHolder

	attach SystemId to `top-bar-system-id`
	set the content of SystemId to `QED6 · 214`

!	Seed rooms.
	rest get Seed from `resources/json/seed-rooms.json?v=` cat now
		or go to LoadFailed
	put property `rooms` of Seed into RoomsList
	put the json count of RoomsList into RoomCount

!	First pass — collect summary stats.
	put 0 into HeatingCount
	put empty into HeatingNames
	put 0 into SumTenths
	put 0 into AvgCount
	put empty into OutsideTemp

	put 0 into LoopI
	while LoopI is less than RoomCount
	begin
		put element LoopI of RoomsList into CurRoom
		put property `name` of CurRoom into RName
		put property `temp` of CurRoom into Ttemp
		put property `sensor` of CurRoom into Tsensor
		put property `offline` of CurRoom into Toffline
		put property `calling` of CurRoom into Tcalling

		if Tcalling is `yes`
		begin
			increment HeatingCount
			if HeatingNames is empty put RName into HeatingNames
			else put HeatingNames cat `, ` cat RName into HeatingNames
		end

		if Tsensor is `no`
		begin
			if Toffline is `no`
			begin
				if Ttemp is not empty
				begin
					put the index of `.` in Ttemp into DotIdx
					if DotIdx is less than 0
					begin
						put the value of Ttemp into TenthsOne
						multiply TenthsOne by 10
					end
					else
					begin
						put the value of left DotIdx of Ttemp into TenthsOne
						multiply TenthsOne by 10
						increment DotIdx
						put the value of from DotIdx of Ttemp into DecPart
						add DecPart to TenthsOne
					end
					add TenthsOne to SumTenths
					increment AvgCount
				end
			end
		end

		if Tsensor is `yes`
		begin
			if OutsideTemp is empty put Ttemp into OutsideTemp
		end

		increment LoopI
	end

!	Average indoor as "XX.X°".
	put `—` into AvgText
	if AvgCount is greater than 0
	begin
		divide SumTenths by AvgCount
		put SumTenths modulo 10 into AvgDec
		put SumTenths into AvgInt
		divide AvgInt by 10
		put AvgInt cat `.` cat AvgDec cat `°` into AvgText
	end

!	Outside as "XX.X°" or em-dash.
	put `—` into OutsideText
	if OutsideTemp is not empty put OutsideTemp cat `°` into OutsideText

!	Title and subtitle copy.
	if HeatingCount is 0
	begin
		put `Nothing calling for heat` into TitleText
		put `Boiler idle` into SubtitleText
	end
	else if HeatingCount is 1
	begin
		put HeatingNames cat ` is calling for heat` into TitleText
		put `Boiler firing` into SubtitleText
	end
	else
	begin
		put HeatingCount cat ` rooms calling for heat` into TitleText
		put HeatingNames into SubtitleText
	end

!	Render SummaryCard into the main column (before the rooms so it sits on top).
	attach MainHolder to `layout-main`
	rest get SummaryWebson from `resources/webson/summary-card.json?v=` cat now
		or go to LoadFailed
	render SummaryWebson in MainHolder

	attach SummaryTitle to `summary-title`
	set the content of SummaryTitle to TitleText

	attach SummarySubtitle to `summary-subtitle`
	set the content of SummarySubtitle to SubtitleText

	attach SummaryAvg to `summary-avg`
	set the content of SummaryAvg to AvgText

	attach SummaryOutside to `summary-outside`
	set the content of SummaryOutside to OutsideText

	attach SummaryToday to `summary-today`
	set the content of SummaryToday to `Mon 23 Apr`

	put `Monday-Friday` into ProfileName
	attach SummaryProfileName to `summary-profile-name`
	set the content of SummaryProfileName to ProfileName

!	Chip appearance + pulse dot by heating state.
	attach SummaryChip to `summary-chip`
	attach SummaryChipIcon to `summary-chip-icon`
	attach SummaryDot to `summary-chip-dot`
	if HeatingCount is 0
	begin
		set style `background` of SummaryChip to `var(--color-chip-neutral-bg)`
		set style `background-color` of SummaryChipIcon to `var(--color-text-muted)`
		set style `display` of SummaryDot to `none`
	end
	else
	begin
		set style `background` of SummaryChip to `var(--color-chip-heat-bg)`
		set style `background-color` of SummaryChipIcon to `var(--color-chip-heat-fg)`
		set style `display` of SummaryDot to `block`
	end

!	Profile pill click — open ProfileSheet (wired below, after sheet chrome
!	is built; the attach here just binds the element so styling/listeners
!	hook into the right DOM node).
	attach ProfilePill to `summary-profile-pill`

!	Second pass — render each RoomRow.
	rest get RoomRowText from `resources/webson/room-row.json?v=` cat now
		or go to LoadFailed

	put -1 into ExpandedIndex

!	Pre-size every indexed per-row variable. Without this, `index X to N`
!	for N > 0 raises "out of range" — the array has to be allocated first.
	set the elements of RestRow to RoomCount
	set the elements of ChevronEl to RoomCount
	set the elements of ExpansionEl to RoomCount
	set the elements of TargetBlockEl to RoomCount
	set the elements of TargetValueEl to RoomCount
	set the elements of BoostBlockEl to RoomCount
	set the elements of ModeTimedBtn to RoomCount
	set the elements of ModeOnBtn to RoomCount
	set the elements of ModeOffBtn to RoomCount
	set the elements of TargetMinusBtn to RoomCount
	set the elements of TargetPlusBtn to RoomCount
	set the elements of Boost30Btn to RoomCount
	set the elements of Boost1hBtn to RoomCount
	set the elements of Boost2hBtn to RoomCount
	set the elements of BoostCancelBtn to RoomCount
	set the elements of EditScheduleBtn to RoomCount

	put 0 into RoomIndex
	while RoomIndex is less than RoomCount
	begin
		put RoomRowText into RowText
		put `` cat RoomIndex into IndexStr
		replace `/I/` with IndexStr in RowText
		render RowText in MainHolder

		put element RoomIndex of RoomsList into Room
		gosub to RenderRoom

!		Sensor rows have no chevron, no expansion, no interactions.
		put property `sensor` of Room into Sensor
		if Sensor is `no` gosub to WireRoomInteractions

		increment RoomIndex
	end

!	Sheet chrome — once, into AppRoot. Container is position:fixed so parent
!	doesn't matter visually, but keeping it under AppRoot keeps the DOM tidy.
	rest get SheetWebson from `resources/webson/sheet.json?v=` cat now
		or go to LoadFailed
	render SheetWebson in AppRoot

	attach SheetContent to `sheet-content`
	rest get MenuWebson from `resources/webson/menu-sheet.json?v=` cat now
		or go to LoadFailed
	render MenuWebson in SheetContent

	rest get ProfileWebson from `resources/webson/profile-sheet.json?v=` cat now
		or go to LoadFailed
	render ProfileWebson in SheetContent

	attach MenuSheetEl to `menu-sheet`
	attach ProfileSheetEl to `profile-sheet`
	set style `display` of ProfileSheetEl to `none`

	attach SheetRoot to `sheet-root`
	attach SheetScrim to `sheet-scrim`
	attach SheetContainer to `sheet-container`
	attach SheetCloseBtn to `sheet-close-btn`
	attach SheetTitleEl to `sheet-title`

	on click SheetCloseBtn gosub to CloseSheet
	on click SheetScrim gosub to CloseSheet

!	Menu row click stubs — each just logs until its target module lands.
	attach MenuRowProfiles to `menu-row-profiles`
	on click MenuRowProfiles
	begin
		log `Menu: Profiles & schedules (stub)`
	end
	attach MenuRowRooms to `menu-row-rooms`
	on click MenuRowRooms
	begin
		log `Menu: Rooms & thermostats (stub)`
	end
	attach MenuRowHoliday to `menu-row-holiday`
	on click MenuRowHoliday
	begin
		log `Menu: Holiday mode (stub)`
	end
	attach MenuRowSystem to `menu-row-system`
	on click MenuRowSystem
	begin
		log `Menu: Boiler & system (stub)`
	end
	attach MenuRowNotifications to `menu-row-notifications`
	on click MenuRowNotifications
	begin
		log `Menu: Notifications (stub)`
	end
	attach MenuRowHelp to `menu-row-help`
	on click MenuRowHelp
	begin
		log `Menu: Help & support (stub)`
	end

!	Hook up the top-bar menu button now that the sheet is ready.
	attach MenuButton to `top-bar-menu-btn`
	on click MenuButton
	begin
		set style `display` of MenuSheetEl to `block`
		set style `display` of ProfileSheetEl to `none`
		set the content of SheetTitleEl to `Menu`
		gosub to OpenSheet
	end

!	Profile pill opens ProfileSheet with the active profile highlighted.
	on click ProfilePill
	begin
		set style `display` of MenuSheetEl to `none`
		set style `display` of ProfileSheetEl to `block`
		set the content of SheetTitleEl to `Profile`
		gosub to ApplyActiveProfile
		gosub to OpenSheet
	end

!	ProfileSheet row clicks — set the active profile, update the home pill,
!	re-style the rows, and dismiss the sheet.
	attach ProfileRowMF to `profile-row-mf`
	on click ProfileRowMF
	begin
		put `Monday-Friday` into ProfileName
		set the content of SummaryProfileName to ProfileName
		gosub to ApplyActiveProfile
		gosub to CloseSheet
	end
	attach ProfileRowWE to `profile-row-we`
	on click ProfileRowWE
	begin
		put `Weekend` into ProfileName
		set the content of SummaryProfileName to ProfileName
		gosub to ApplyActiveProfile
		gosub to CloseSheet
	end
	attach ProfileRowOff to `profile-row-off`
	on click ProfileRowOff
	begin
		put `All off` into ProfileName
		set the content of SummaryProfileName to ProfileName
		gosub to ApplyActiveProfile
		gosub to CloseSheet
	end

	attach ProfileManageBtn to `profile-manage-btn`
	on click ProfileManageBtn
	begin
		log `Profile: Manage profiles… (stub)`
	end

	attach ProfileDotMF to `profile-row-mf-dot`
	attach ProfileDotWE to `profile-row-we-dot`
	attach ProfileDotOff to `profile-row-off-dot`
	attach ProfileChipMF to `profile-row-mf-active-chip`
	attach ProfileChipWE to `profile-row-we-active-chip`
	attach ProfileChipOff to `profile-row-off-active-chip`

!	Background tick — re-pick the gradient at hour boundaries. Forked so
!	the main flow can stop().
	fork to BackgroundTick

	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Pick the time-of-day gradient stops by hour bucket and apply both the
!	linear gradient + a soft white radial glow to AppRoot in one stacked
!	background. Cards/sheets sit in front via normal stacking.
ApplyBackground:
	put the hour into Hour
	put `#FDF6EC` into GTop
	put `#FBEEDD` into GMid
	put `#F5E2C9` into GBot
	if Hour is less than 6
	begin
		put `#1E2238` into GTop
		put `#2D2A3E` into GMid
		put `#433048` into GBot
	end
	else if Hour is less than 10
	begin
		put `#FFE8D4` into GTop
		put `#FFD3B0` into GMid
		put `#F5B994` into GBot
	end
	else if Hour is less than 15
	begin
		put `#FDF6EC` into GTop
		put `#FBEEDD` into GMid
		put `#F5E2C9` into GBot
	end
	else if Hour is less than 19
	begin
		put `#FFE1C2` into GTop
		put `#F7B88A` into GMid
		put `#E88A5B` into GBot
	end
	else if Hour is less than 22
	begin
		put `#F0A877` into GTop
		put `#B66B56` into GMid
		put `#5A3A52` into GBot
	end
	else
	begin
		put `#1E2238` into GTop
		put `#2D2A3E` into GMid
		put `#433048` into GBot
	end
	put `radial-gradient(ellipse at 50% -20%, rgba(255,255,255,0.5) 0%, transparent 70%)` into Glow
	put Glow cat `, linear-gradient(180deg, ` cat GTop cat ` 0%, ` cat GMid cat ` 45%, ` cat GBot cat ` 100%)` into BgValue
	set style `background` of AppRoot to BgValue
	set style `background-attachment` of AppRoot to `fixed`
	return

!	Hourly tick. Polls `the hour` once a minute and re-applies if it changed.
!	A minute is fine — boundaries don't need sub-minute precision.
BackgroundTick:
	put the hour into LastHour
	while true
	begin
		wait 60 seconds
		put the hour into Hour
		if Hour is not LastHour
		begin
			put Hour into LastHour
			gosub to ApplyBackground
		end
	end

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Open / close the bottom sheet. CSS transitions handle the motion; we
!	just flip opacity, transform and the root's pointer-events.
OpenSheet:
	set style `pointer-events` of SheetRoot to `auto`
	set style `opacity` of SheetScrim to `1`
	set style `transform` of SheetContainer to `translateY(0)`
	return

CloseSheet:
	set style `opacity` of SheetScrim to `0`
	set style `transform` of SheetContainer to `translateY(100%)`
	set style `pointer-events` of SheetRoot to `none`
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Re-paint the three profile rows so the one matching ProfileName looks
!	"active" (accent border, tinted bg, filled dot, ACTIVE chip) and the
!	others look "inactive".
ApplyActiveProfile:
	gosub to ResetProfileRows
	if ProfileName is `Monday-Friday` gosub to ActivateMF
	if ProfileName is `Weekend` gosub to ActivateWE
	if ProfileName is `All off` gosub to ActivateOff
	return

ResetProfileRows:
	set style `border` of ProfileRowMF to `1px solid var(--color-border-hairline)`
	set style `background` of ProfileRowMF to `var(--color-surface-card)`
	set style `border` of ProfileDotMF to `1.5px solid #CCC`
	set style `background` of ProfileDotMF to `transparent`
	set style `display` of ProfileChipMF to `none`
	set style `border` of ProfileRowWE to `1px solid var(--color-border-hairline)`
	set style `background` of ProfileRowWE to `var(--color-surface-card)`
	set style `border` of ProfileDotWE to `1.5px solid #CCC`
	set style `background` of ProfileDotWE to `transparent`
	set style `display` of ProfileChipWE to `none`
	set style `border` of ProfileRowOff to `1px solid var(--color-border-hairline)`
	set style `background` of ProfileRowOff to `var(--color-surface-card)`
	set style `border` of ProfileDotOff to `1.5px solid #CCC`
	set style `background` of ProfileDotOff to `transparent`
	set style `display` of ProfileChipOff to `none`
	return

ActivateMF:
	set style `border` of ProfileRowMF to `1.5px solid var(--color-accent)`
	set style `background` of ProfileRowMF to `var(--color-accent-10)`
	set style `border` of ProfileDotMF to `5px solid var(--color-accent)`
	set style `background` of ProfileDotMF to `var(--color-surface-card)`
	set style `display` of ProfileChipMF to `inline`
	return

ActivateWE:
	set style `border` of ProfileRowWE to `1.5px solid var(--color-accent)`
	set style `background` of ProfileRowWE to `var(--color-accent-10)`
	set style `border` of ProfileDotWE to `5px solid var(--color-accent)`
	set style `background` of ProfileDotWE to `var(--color-surface-card)`
	set style `display` of ProfileChipWE to `inline`
	return

ActivateOff:
	set style `border` of ProfileRowOff to `1.5px solid var(--color-accent)`
	set style `background` of ProfileRowOff to `var(--color-accent-10)`
	set style `border` of ProfileDotOff to `5px solid var(--color-accent)`
	set style `background` of ProfileDotOff to `var(--color-surface-card)`
	set style `display` of ProfileChipOff to `inline`
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Per-row wiring. Indexes each interactive element to RoomIndex so the
!	click handlers can recover the firing row via `the index of X`. Called
!	once per non-sensor row from the render loop.
WireRoomInteractions:
	index RestRow to RoomIndex
	attach RestRow to `room-` cat RoomIndex cat `-rest`
	on click RestRow
	begin
		put the index of RestRow into ClickIndex
		gosub to ToggleExpansion
	end

	index ChevronEl to RoomIndex
	attach ChevronEl to `room-` cat RoomIndex cat `-chevron`
	index ExpansionEl to RoomIndex
	attach ExpansionEl to `room-` cat RoomIndex cat `-expansion`
	index TargetBlockEl to RoomIndex
	attach TargetBlockEl to `room-` cat RoomIndex cat `-target-block`
	index BoostBlockEl to RoomIndex
	attach BoostBlockEl to `room-` cat RoomIndex cat `-boost-block`
	index TargetValueEl to RoomIndex
	attach TargetValueEl to `room-` cat RoomIndex cat `-target-value`

	index ModeTimedBtn to RoomIndex
	attach ModeTimedBtn to `room-` cat RoomIndex cat `-mode-timed`
	on click ModeTimedBtn
	begin
		put the index of ModeTimedBtn into ClickIndex
		put `Timed` into NewMode
		gosub to ChangeMode
	end
	index ModeOnBtn to RoomIndex
	attach ModeOnBtn to `room-` cat RoomIndex cat `-mode-on`
	on click ModeOnBtn
	begin
		put the index of ModeOnBtn into ClickIndex
		put `On` into NewMode
		gosub to ChangeMode
	end
	index ModeOffBtn to RoomIndex
	attach ModeOffBtn to `room-` cat RoomIndex cat `-mode-off`
	on click ModeOffBtn
	begin
		put the index of ModeOffBtn into ClickIndex
		put `Off` into NewMode
		gosub to ChangeMode
	end

	index TargetMinusBtn to RoomIndex
	attach TargetMinusBtn to `room-` cat RoomIndex cat `-target-minus`
	on click TargetMinusBtn
	begin
		put the index of TargetMinusBtn into ClickIndex
		gosub to StepTargetDown
	end
	index TargetPlusBtn to RoomIndex
	attach TargetPlusBtn to `room-` cat RoomIndex cat `-target-plus`
	on click TargetPlusBtn
	begin
		put the index of TargetPlusBtn into ClickIndex
		gosub to StepTargetUp
	end

	index Boost30Btn to RoomIndex
	attach Boost30Btn to `room-` cat RoomIndex cat `-boost-30`
	on click Boost30Btn
	begin
		put the index of Boost30Btn into ClickIndex
		put `30 min` into BoostDur
		gosub to ApplyBoost
	end
	index Boost1hBtn to RoomIndex
	attach Boost1hBtn to `room-` cat RoomIndex cat `-boost-1h`
	on click Boost1hBtn
	begin
		put the index of Boost1hBtn into ClickIndex
		put `1 hr` into BoostDur
		gosub to ApplyBoost
	end
	index Boost2hBtn to RoomIndex
	attach Boost2hBtn to `room-` cat RoomIndex cat `-boost-2h`
	on click Boost2hBtn
	begin
		put the index of Boost2hBtn into ClickIndex
		put `2 hr` into BoostDur
		gosub to ApplyBoost
	end

	index BoostCancelBtn to RoomIndex
	attach BoostCancelBtn to `room-` cat RoomIndex cat `-boost-cancel`
	on click BoostCancelBtn
	begin
		put the index of BoostCancelBtn into ClickIndex
		gosub to CancelBoost
	end

	index EditScheduleBtn to RoomIndex
	attach EditScheduleBtn to `room-` cat RoomIndex cat `-edit-schedule`
	on click EditScheduleBtn
	begin
		put the index of EditScheduleBtn into ClickIndex
		log `Edit schedule (stub) for room ` cat ClickIndex
	end
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Toggle expansion for ClickIndex. Closes any other open expansion first.
ToggleExpansion:
	if ExpandedIndex is not -1
	begin
		index ExpansionEl to ExpandedIndex
		set style `display` of ExpansionEl to `none`
		index ChevronEl to ExpandedIndex
		set style `transform` of ChevronEl to `rotate(0deg)`
		if ExpandedIndex is ClickIndex
		begin
			put -1 into ExpandedIndex
			return
		end
	end
	index ExpansionEl to ClickIndex
	set style `display` of ExpansionEl to `flex`
	index ChevronEl to ClickIndex
	set style `transform` of ChevronEl to `rotate(180deg)`
	put ClickIndex into ExpandedIndex
	gosub to PaintExpansion
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Paint the expansion controls for room ClickIndex (mode pill highlight,
!	target value, boost chip highlight, section visibility).
PaintExpansion:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	put property `target` of Room into Ttarget
	put property `boost` of Room into BoostDur

!	Mode segmented control — re-attach per click then style.
	index ModeTimedBtn to ClickIndex
	index ModeOnBtn to ClickIndex
	index ModeOffBtn to ClickIndex
	gosub to ResetModeBtn
	if Tmode is `Timed` gosub to ActivateModeTimed
	if Tmode is `On` gosub to ActivateModeOn
	if Tmode is `Off` gosub to ActivateModeOff
	if Tmode is `Boost` gosub to ActivateModeTimed

!	Target tile — hide whole block when mode = Off, otherwise show + set value.
	index TargetBlockEl to ClickIndex
	if Tmode is `Off` set style `display` of TargetBlockEl to `none`
	else
	begin
		set style `display` of TargetBlockEl to `block`
		index TargetValueEl to ClickIndex
		if Ttarget is empty set the content of TargetValueEl to `20.0`
		else set the content of TargetValueEl to Ttarget
	end

!	Boost — hide whole block when mode = Off, otherwise show + style chips.
	index BoostBlockEl to ClickIndex
	if Tmode is `Off` set style `display` of BoostBlockEl to `none`
	else
	begin
		set style `display` of BoostBlockEl to `block`
		index Boost30Btn to ClickIndex
		index Boost1hBtn to ClickIndex
		index Boost2hBtn to ClickIndex
		gosub to ResetBoostBtn
		if BoostDur is `30 min` gosub to ActivateBoost30
		if BoostDur is `1 hr` gosub to ActivateBoost1h
		if BoostDur is `2 hr` gosub to ActivateBoost2h
		index BoostCancelBtn to ClickIndex
		if BoostDur is empty set style `display` of BoostCancelBtn to `none`
		else set style `display` of BoostCancelBtn to `inline-block`
	end
	return

!	Mode-button styling helpers. The buttons are already at the right slot
!	via the `index` calls in PaintExpansion.
ResetModeBtn:
	set style `background` of ModeTimedBtn to `transparent`
	set style `color` of ModeTimedBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeTimedBtn to `500`
	set style `box-shadow` of ModeTimedBtn to `none`
	set style `background` of ModeOnBtn to `transparent`
	set style `color` of ModeOnBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeOnBtn to `500`
	set style `box-shadow` of ModeOnBtn to `none`
	set style `background` of ModeOffBtn to `transparent`
	set style `color` of ModeOffBtn to `var(--color-text-muted)`
	set style `font-weight` of ModeOffBtn to `500`
	set style `box-shadow` of ModeOffBtn to `none`
	return

ActivateModeTimed:
	set style `background` of ModeTimedBtn to `var(--color-surface-card)`
	set style `color` of ModeTimedBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeTimedBtn to `600`
	set style `box-shadow` of ModeTimedBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateModeOn:
	set style `background` of ModeOnBtn to `var(--color-surface-card)`
	set style `color` of ModeOnBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeOnBtn to `600`
	set style `box-shadow` of ModeOnBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateModeOff:
	set style `background` of ModeOffBtn to `var(--color-surface-card)`
	set style `color` of ModeOffBtn to `var(--color-text-primary)`
	set style `font-weight` of ModeOffBtn to `600`
	set style `box-shadow` of ModeOffBtn to `0 1px 3px rgba(0,0,0,0.08)`
	return

ResetBoostBtn:
	set style `background` of Boost30Btn to `var(--color-surface-card)`
	set style `border` of Boost30Btn to `1px solid var(--color-border-hairline)`
	set style `color` of Boost30Btn to `var(--color-text-primary)`
	set style `font-weight` of Boost30Btn to `500`
	set style `background` of Boost1hBtn to `var(--color-surface-card)`
	set style `border` of Boost1hBtn to `1px solid var(--color-border-hairline)`
	set style `color` of Boost1hBtn to `var(--color-text-primary)`
	set style `font-weight` of Boost1hBtn to `500`
	set style `background` of Boost2hBtn to `var(--color-surface-card)`
	set style `border` of Boost2hBtn to `1px solid var(--color-border-hairline)`
	set style `color` of Boost2hBtn to `var(--color-text-primary)`
	set style `font-weight` of Boost2hBtn to `500`
	return

ActivateBoost30:
	set style `background` of Boost30Btn to `var(--color-accent-10)`
	set style `border` of Boost30Btn to `1.5px solid var(--color-accent)`
	set style `color` of Boost30Btn to `var(--color-accent)`
	set style `font-weight` of Boost30Btn to `600`
	return

ActivateBoost1h:
	set style `background` of Boost1hBtn to `var(--color-accent-10)`
	set style `border` of Boost1hBtn to `1.5px solid var(--color-accent)`
	set style `color` of Boost1hBtn to `var(--color-accent)`
	set style `font-weight` of Boost1hBtn to `600`
	return

ActivateBoost2h:
	set style `background` of Boost2hBtn to `var(--color-accent-10)`
	set style `border` of Boost2hBtn to `1.5px solid var(--color-accent)`
	set style `color` of Boost2hBtn to `var(--color-accent)`
	set style `font-weight` of Boost2hBtn to `600`
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Mode change. Per spec: clear boost; mode→Off clears target; mode away
!	from Off restores last target (default 20.0).
ChangeMode:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	put property `target` of Room into Ttarget
	if Tmode is NewMode return
	set property `mode` of Room to NewMode
	set property `boost` of Room to empty
	if NewMode is `Off`
	begin
		if Ttarget is not empty set property `lastTarget` of Room to Ttarget
		set property `target` of Room to empty
	end
	else
	begin
		if Ttarget is empty
		begin
			put property `lastTarget` of Room into LastTarget
			if LastTarget is empty set property `target` of Room to `20.0`
			else set property `target` of Room to LastTarget
		end
	end
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange
	return

!	Step the target up or down by 0.5 (5 tenths) with clamp [50, 300].
StepTargetUp:
	gosub to LoadTargetTenths
	add 5 to TargetT
	if TargetT is greater than 300 return
	gosub to WriteTargetTenths
	return

StepTargetDown:
	gosub to LoadTargetTenths
	take 5 from TargetT
	if TargetT is less than 50 return
	gosub to WriteTargetTenths
	return

LoadTargetTenths:
	put element ClickIndex of RoomsList into Room
	put property `target` of Room into Ttarget
	if Ttarget is empty put `20.0` into Ttarget
	put Ttarget into TempStr
	gosub to ToTenths
	put TempTenths into TargetT
	return

WriteTargetTenths:
	put TargetT into TempTenths
	gosub to TenthsToString
	set property `target` of Room to TempStr
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange
	return

!	Apply boost duration BoostDur. Per spec: also forces mode = Boost.
ApplyBoost:
	put element ClickIndex of RoomsList into Room
	set property `mode` of Room to `Boost`
	set property `boost` of Room to BoostDur
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange
	return

!	Cancel boost. Per spec: revert to Timed and clear boost.
CancelBoost:
	put element ClickIndex of RoomsList into Room
	set property `mode` of Room to `Timed`
	set property `boost` of Room to empty
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange
	return

!	After any state change: recompute `calling`, re-render the rest row,
!	and repaint the expansion. Room and ClickIndex must be set.
AfterStateChange:
	gosub to RecalcCalling
	set element ClickIndex of RoomsList to Room
	put ClickIndex into RoomIndex
	put `` cat RoomIndex into IndexStr
	gosub to RenderRoom
	gosub to PaintExpansion
	return

!	Recompute `calling` for the current Room.
RecalcCalling:
	put `no` into NewCalling
	put property `sensor` of Room into Tsensor
	put property `offline` of Room into Toffline
	put property `mode` of Room into Tmode
	put property `temp` of Room into Ttemp
	put property `target` of Room into Ttarget
	if Tsensor is `no`
	begin
		if Toffline is `no`
		begin
			if Tmode is not `Off`
			begin
				if Ttemp is not empty
				begin
					if Ttarget is not empty
					begin
						put Ttemp into TempStr
						gosub to ToTenths
						put TempTenths into TempT
						put Ttarget into TempStr
						gosub to ToTenths
						put TempTenths into TargetT
						take TempT from TargetT giving Diff
						if Diff is greater than 2 put `yes` into NewCalling
					end
				end
			end
		end
	end
	set property `calling` of Room to NewCalling
	return

!	String "X.Y" → integer tenths (e.g. "20.5" → 205). Uses TempStr in,
!	TempTenths out. Mirrors the inline logic in the summary pass.
ToTenths:
	put 0 into TempTenths
	if TempStr is empty return
	put the index of `.` in TempStr into DotIdx
	if DotIdx is less than 0
	begin
		put the value of TempStr into TempTenths
		multiply TempTenths by 10
		return
	end
	put the value of left DotIdx of TempStr into TempTenths
	multiply TempTenths by 10
	increment DotIdx
	put the value of from DotIdx of TempStr into DecPart
	add DecPart to TempTenths
	return

!	Integer tenths → "X.Y" string. Uses TempTenths in, TempStr out.
TenthsToString:
	put TempTenths into AvgInt
	put TempTenths modulo 10 into AvgDec
	divide AvgInt by 10
	put AvgInt cat `.` cat AvgDec into TempStr
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Render one room into the already-built row matching IndexStr / Room.
RenderRoom:
	put property `mode` of Room into Mode
	put property `temp` of Room into TempVal
	put property `target` of Room into TargetTemp
	put property `offline` of Room into Offline
	put property `sensor` of Room into Sensor
	put property `boost` of Room into BoostVal
	put property `nextTime` of Room into NextTime
	put property `nextTarget` of Room into NextTarget
	put property `name` of Room into NameText

	clear CallingForHeat
	if property `calling` of Room is `yes` set CallingForHeat

	attach RoomName to `room-` cat IndexStr cat `-name`
	set the content of RoomName to NameText

	attach HeatingTag to `room-` cat IndexStr cat `-heating-tag`
	if CallingForHeat set style `display` of HeatingTag to `inline-flex`
	else set style `display` of HeatingTag to `none`

	attach OfflineTag to `room-` cat IndexStr cat `-offline-tag`
	if Offline is `yes` set style `display` of OfflineTag to `inline-flex`
	else set style `display` of OfflineTag to `none`

	attach Chevron to `room-` cat IndexStr cat `-chevron`
	if Sensor is `yes` set style `display` of Chevron to `none`
	else set style `display` of Chevron to `block`

	put empty into SublineText
	if Sensor is `yes` put `Outdoor sensor` into SublineText
	else if Offline is `yes` put `No signal` into SublineText
	else if Mode is `Off` put `Off — no schedule` into SublineText
	else if BoostVal is not empty
	begin
		put `Boost · ` cat BoostVal cat ` left` into SublineText
	end
	else if NextTime is not empty
	begin
		put `→ ` cat NextTarget cat `° at ` cat NextTime into SublineText
	end
	attach Subline to `room-` cat IndexStr cat `-subline`
	set the content of Subline to SublineText

	attach TempEl to `room-` cat IndexStr cat `-temp`
	if TempVal is empty set the content of TempEl to `—`
	else set the content of TempEl to TempVal
	if Offline is `yes` set style `color` of TempEl to `var(--color-text-disabled)`
	else set style `color` of TempEl to `var(--color-text-primary)`

	attach Setpoint to `room-` cat IndexStr cat `-setpoint`
	if Sensor is `yes` set the content of Setpoint to empty
	else if TargetTemp is empty set the content of Setpoint to empty
	else set the content of Setpoint to `set ` cat TargetTemp cat `°`

	gosub to ApplyChipStyle
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Decide chip bg / fg / icon-url and apply. Priority: sensor > offline > Off
!	> Boost > calling-for-heat > default (Timed, not heating).
ApplyChipStyle:
	put `var(--color-chip-ok-bg)` into ChipBg
	put `var(--color-chip-ok-fg)` into ChipFg
	put `resources/icon/clock.svg` into ChipIconUrl

	if Sensor is `yes`
	begin
		put `var(--color-chip-neutral-bg)` into ChipBg
		put `var(--color-chip-neutral-fg)` into ChipFg
		put `resources/icon/sensor.svg` into ChipIconUrl
	end
	else if Offline is `yes`
	begin
		put `var(--color-chip-warn-bg)` into ChipBg
		put `var(--color-chip-warn-fg)` into ChipFg
		put `resources/icon/clock.svg` into ChipIconUrl
	end
	else if Mode is `Off`
	begin
		put `var(--color-chip-neutral-bg)` into ChipBg
		put `var(--color-chip-neutral-fg)` into ChipFg
		put `resources/icon/off.svg` into ChipIconUrl
	end
	else if Mode is `Boost`
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
		put `resources/icon/boost.svg` into ChipIconUrl
	end
	else if CallingForHeat
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
	end

	attach Chip to `room-` cat IndexStr cat `-chip`
	set style `background` of Chip to ChipBg

	attach ChipIcon to `room-` cat IndexStr cat `-chip-icon`
	set style `background-color` of ChipIcon to ChipFg
	put `url(` cat ChipIconUrl cat `) center/contain no-repeat` into MaskCss
	set style `mask` of ChipIcon to MaskCss
	set style `-webkit-mask` of ChipIcon to MaskCss
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
LoadFailed:
	alert `Failed to load UI template`
	stop
