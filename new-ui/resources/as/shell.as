!	Room By Room — new UI shell.
!	Slices 02 (TopBar) + 03 (RoomRow rest state) + 04 (SummaryCard) + 05 (Sheet chrome + MenuSheet).

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
	button MenuRowProfiles
	button MenuRowRooms
	button MenuRowHoliday
	button MenuRowSystem
	button MenuRowNotifications
	button MenuRowHelp

	variable LayoutWebson
	variable TopBarWebson
	variable SummaryWebson
	variable SheetWebson
	variable MenuWebson
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

	attach AppRoot to `app` or begin
		alert `Missing #app container in index.html`
		stop
	end

	set style `background` of AppRoot to `#F6F4F0`
	set style `min-height` of AppRoot to `100vh`

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

!	Profile pill click — stub for now.
	attach ProfilePill to `summary-profile-pill`
	on click ProfilePill
	begin
		log `Profile pill tapped (ProfileSheet not built yet)`
	end

!	Second pass — render each RoomRow.
	rest get RoomRowText from `resources/webson/room-row.json?v=` cat now
		or go to LoadFailed

	put 0 into RoomIndex
	while RoomIndex is less than RoomCount
	begin
		put RoomRowText into RowText
		put `` cat RoomIndex into IndexStr
		replace `/I/` with IndexStr in RowText
		render RowText in MainHolder

		put element RoomIndex of RoomsList into Room
		gosub to RenderRoom

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
		set the content of SheetTitleEl to `Menu`
		gosub to OpenSheet
	end

	stop

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
