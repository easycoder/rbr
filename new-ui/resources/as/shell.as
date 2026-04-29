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
	div ProfileTagline
	div CalendarHeaderEl
	button CalExpandBtn
	div CalendarHeaderTitle
	div CalendarChev
	div CalendarCardEl
	button CalendarToggleBtn
	div DayRow
	div DayProfileEl
	button DayEditBtn
	button ProfileAddBtn
	button ProfileSaveBtn
	button ProfileCancelBtn
	button MenuRowProfiles
	button MenuRowRooms
	button MenuRowHoliday
	button MenuRowSystem
	button MenuRowNotifications
	button MenuRowHelp
	div ProfileListHolder
	div ProfileRow
	button ProfileBody
	div ProfileLabel
	button ProfileRenameBtn
	button ProfileDeleteBtn
	div DayPickerEl
	button DayPickerCloseBtn
	div DayPickerList
	button DayPill

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

!	MQTT connection state.
	variable Credentials
	variable Broker
	variable Port
	variable Username
	variable Password
	variable MAC
	variable MyID
	topic ServerTopic
	topic MyTopic
	variable ReceivedMessage
	variable Prompt
	variable FirstMapDone
	variable PollWait

!	Map ingestion / transformation state.
	variable Map
	variable Profiles
	variable CurrentProfile
	variable ActiveProfile
	variable ActiveProfileName
	variable SystemName
	variable CalendarData
	variable CalendarEntry
	variable DayN
	variable LoopJ
	variable ProfileN
	variable LegacyProfileCount

!	Date-formatting lookup tables and scratch.
	variable DayNames
	variable MonthNames
	variable DayName
	variable MonthName
	variable DateD
	variable DateDN
	variable DateM

!	Outbound (uirequest) payload state.
	variable Result
	variable SendOK
	variable ModeForServer
	variable BoostMinutes
	variable RoomNameForServer
	variable TargetForServer
	variable LoopP
	variable CalendarOn
	variable ProfileIdx
	variable ProfileRowText
	variable ProfileRowJson
	variable ProfileIdxStr

!	Combined ProfileSheet state (selection + editing batched through Save).
	variable EditingProfiles
	variable EditingProfilesCount
	variable EditingActiveName
	variable EditingCalendarOn
	variable EditingCalendarData
	variable EditingActiveValid
	variable CalendarCardExpanded
	variable EditIdx
	variable EditIdxStr
	variable EditClickIdx
	variable EditProfileN
	variable ClonedProfile
	variable NewProfileName
	variable NewProfilesArray
	variable NewIdx
	variable NewActiveIdx
	variable LoopE
	variable DayIds
	variable DayNamesShort
	variable DayIdStr
	variable DayPropName
	variable DayEntry
	variable DayProfileName
	variable DayLoopI
	variable DayEditTargetIdx
	variable PillIdx
	variable PillIdxStr
	variable PillRowText
	variable PillRowJson
	variable LegacyCalData
	variable LegacyCalCount
	variable LegacyCalEntry
	variable ClonedEntry
	variable PropName
	variable ProfName
	variable ConfirmFlag
	variable LegacyRooms
	variable LegacyRoomCount
	variable LegacyIdx
	variable LegacyRoom
	variable LegacyRelays
	variable LegacyRelayCount
	variable LegacyName
	variable LegacyMode
	variable LegacyTemp
	variable LegacyTarget
	variable LegacyStatus
	variable LegacyStatusMessage
	variable LegacyLinked
	variable OfflineReason
	variable LegacyBattery
	variable WarnMessage
	variable LegacyEvents
	variable LegacyEventCount
	variable LegacyEvent
	variable NewRoom
	variable RoomsListIdx
	variable Hundredths
	variable TempInt
	variable LoopK
	variable NowMinutes
	variable BoostUntil
	variable BoostRemaining
	variable BoostText
	variable NextTimeStr
	variable NextTempVal
	variable NextTempStr

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
	set the content of SystemId to `…`

!	Day-of-week and month-name lookup tables for the SummaryCard date.
!	`the day` is JS getDay (0=Sun); `the month` is getMonth (0=Jan).
	put `[]` into DayNames
	set element 0 of DayNames to `Sun`
	set element 1 of DayNames to `Mon`
	set element 2 of DayNames to `Tue`
	set element 3 of DayNames to `Wed`
	set element 4 of DayNames to `Thu`
	set element 5 of DayNames to `Fri`
	set element 6 of DayNames to `Sat`

	put `[]` into MonthNames
	set element 0 of MonthNames to `Jan`
	set element 1 of MonthNames to `Feb`
	set element 2 of MonthNames to `Mar`
	set element 3 of MonthNames to `Apr`
	set element 4 of MonthNames to `May`
	set element 5 of MonthNames to `Jun`
	set element 6 of MonthNames to `Jul`
	set element 7 of MonthNames to `Aug`
	set element 8 of MonthNames to `Sep`
	set element 9 of MonthNames to `Oct`
	set element 10 of MonthNames to `Nov`
	set element 11 of MonthNames to `Dec`

!	MQTT credentials. Try a deploy-provided credentials.json, then fall back
!	to localStorage prompts (same keys as the legacy UI so a single first-run
!	prompt covers both).
	no cache
	rest get Credentials from `credentials.json`
		or go to NoCredentialsFile
	if Credentials is not empty
	begin
		put property `broker` of Credentials into Broker
		put property `port` of Credentials into Port
		put property `username` of Credentials into Username
		put property `password` of Credentials into Password
		put property `mac` of Credentials into MAC
		if Broker is `localhost`
		begin
			if the hostname is not `localhost` put the hostname into Broker
		end
	end
NoCredentialsFile:
	if Broker is empty
	begin
		get Broker from storage as `dev-broker`
		if Broker is `null` put empty into Broker
		if Broker is `undefined` put empty into Broker
		get Username from storage as `dev-username`
		if Username is `null` put empty into Username
		if Username is `undefined` put empty into Username
		get Password from storage as `dev-password`
		if Password is `null` put empty into Password
		if Password is `undefined` put empty into Password
		get MAC from storage as `dev-mac`
		if MAC is `null` put empty into MAC
		if MAC is `undefined` put empty into MAC
		if Broker is empty
		begin
			put prompt `Dev credentials:` cat newline cat `MQTT Broker URL:` into Broker
			put prompt `Dev credentials:` cat newline cat `Username:` into Username
			put prompt `Dev credentials:` cat newline cat `Password:` into Password
			put prompt `Dev credentials:` cat newline cat `Controller MAC address:` into MAC
			if Broker is empty go to LoadFailed
			put Broker into storage as `dev-broker`
			put Username into storage as `dev-username`
			put Password into storage as `dev-password`
			put MAC into storage as `dev-mac`
		end
	end

	if Port is empty put 443 into Port
	put `RBR-` cat random 999999 into MyID

	init ServerTopic
		name MAC
		qos 1
	init MyTopic
		name MyID
		qos 1

	dummy
	mqtt
		token `rbr` Password
		id MyID
		broker Broker
		port Port
		subscribe MyTopic

	on mqtt connect
	begin
		log `MQTT Connected`
		go to Connected
	end

	on mqtt message
	begin
		put the mqtt message into ReceivedMessage
		gosub to OnMapReceived
	end
	stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	First-render path: triggered when MQTT connects. Asks the controller
!	for a full map; the response handler (OnMapReceived) does the rest.
Connected:
	put `first` into Prompt
	clear FirstMapDone
	gosub to RequestMap
	stop

RequestMap:
	log `Requesting map: ` cat Prompt
	send to ServerTopic
		sender MyTopic
		action Prompt
	return

!	Fired by `on mqtt message`. First message → BuildHomeScreen (full render).
!	Subsequent messages → RefreshHomeScreen (in-place update).
OnMapReceived:
	if ReceivedMessage is empty return
	put ReceivedMessage into Map
	put empty into ReceivedMessage
	gosub to MapToRooms
	if not FirstMapDone
	begin
		set FirstMapDone
		gosub to BuildHomeScreen
		put `refresh` into Prompt
		fork to MapPollTask
	end
	else
	begin
		gosub to RefreshHomeScreen
	end
	return

!	10-second poll: re-request the map so the UI tracks live state.
MapPollTask:
	while true
	begin
		put 10 into PollWait
		while PollWait is not 0
		begin
			wait 1 second
			take 1 from PollWait
		end
		gosub to RequestMap
	end

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Build the home screen for the first time. Renders SummaryCard, room rows,
!	and sheet chrome. Calls ComputeSummaryStats once data is in place.
BuildHomeScreen:
!	First-pass summary stats from the freshly-built RoomsList.
	gosub to ComputeSummaryStats

!	Render SummaryCard into the main column (before the rooms so it sits on top).
	attach MainHolder to `layout-main`
	rest get SummaryWebson from `resources/webson/summary-card.json?v=` cat now
		or go to LoadFailed
	render SummaryWebson in MainHolder

	attach SummaryTitle to `summary-title`
	attach SummarySubtitle to `summary-subtitle`
	attach SummaryAvg to `summary-avg`
	attach SummaryOutside to `summary-outside`
	attach SummaryToday to `summary-today`
	attach SummaryProfileName to `summary-profile-name`
	attach SummaryChip to `summary-chip`
	attach SummaryChipIcon to `summary-chip-icon`
	attach SummaryDot to `summary-chip-dot`

	gosub to PaintSummary

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
		gosub to OpenProfileSheet
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

!	Profile pill opens the combined ProfileSheet. Snapshot of state is taken
!	at open time; all changes batch through Save / discard via Cancel.
	on click ProfilePill gosub to OpenProfileSheet

!	Set up the static parts of the ProfileSheet: holder, tagline, calendar
!	header + content, day rows. Profile rows are rebuilt every open since
!	their count and contents come from the working copy.
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

	rest get ProfileRowJson from `resources/webson/profile-row.json?v=` cat now
		or go to LoadFailed
	rest get PillRowJson from `resources/webson/calendar-pill.json?v=` cat now
		or go to LoadFailed

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
	on click ProfileSaveBtn gosub to SaveEditingProfiles
	on click ProfileCancelBtn gosub to CloseProfileSheet

!	Background tick — re-pick the gradient at hour boundaries. Forked once
!	on first build; subsequent refreshes don't re-fork.
	fork to BackgroundTick

	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Refresh path: re-render every room in place + recompute the summary.
!	Assumes RoomCount is unchanged from the initial build. If a room's
!	expansion panel is open, repaint its inner controls so a controller-
!	side change (e.g. legacy UI changed mode) propagates immediately.
RefreshHomeScreen:
	put 0 into RoomIndex
	while RoomIndex is less than RoomCount
	begin
		put element RoomIndex of RoomsList into Room
		put `` cat RoomIndex into IndexStr
		gosub to RenderRoom
		increment RoomIndex
	end
	gosub to ComputeSummaryStats
	gosub to PaintSummary
	if ExpandedIndex is not -1
	begin
		put ExpandedIndex into ClickIndex
		gosub to PaintExpansion
	end
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Walk the controller's map, build the new-UI RoomsList from scratch.
!	Filters out the outdoor sensor entry (room with empty `relays`) and
!	feeds its temperature into OutsideTemp instead.
MapToRooms:
	put property `profiles` of Map into Profiles
	put property `profile` of Map into CurrentProfile
	if CurrentProfile is empty put 0 into CurrentProfile

!	Calendar lock state — when on, manual profile selection is masked.
	clear CalendarOn
	if property `calendar` of Map is `on` set CalendarOn

!	If the calendar is on, today's profile-name overrides Map.profile.
!	`the day` returns 0=Sunday (JS getDay), so shift +6 mod 7 to make
!	Monday=0 to match the Monday-first calendar-data array.
	if property `calendar` of Map is `on`
	begin
		put property `calendar-data` of Map into CalendarData
		if CalendarData is not empty
		begin
			put the day into DayN
			add 6 to DayN
			put DayN modulo 7 into DayN
			put element DayN of CalendarData into CalendarEntry
			if CalendarEntry is not empty
			begin
				put property `day` cat DayN cat `-profile` of CalendarEntry into DayProfileName
				if DayProfileName is not empty
				begin
					put the json count of Profiles into LegacyProfileCount
					put 0 into LoopJ
					while LoopJ is less than LegacyProfileCount
					begin
						put element LoopJ of Profiles into ProfileN
						if property `name` of ProfileN is DayProfileName put LoopJ into CurrentProfile
						increment LoopJ
					end
				end
			end
		end
	end

	put element CurrentProfile of Profiles into ActiveProfile
	put property `name` of ActiveProfile into ActiveProfileName
	put property `name` of Map into SystemName
	put property `rooms` of ActiveProfile into LegacyRooms
	put the json count of LegacyRooms into LegacyRoomCount

	put `[]` into RoomsList
	put 0 into RoomsListIdx
	put empty into OutsideTemp

	put 0 into LegacyIdx
	while LegacyIdx is less than LegacyRoomCount
	begin
		put element LegacyIdx of LegacyRooms into LegacyRoom
		put property `relays` of LegacyRoom into LegacyRelays
		put the json count of LegacyRelays into LegacyRelayCount
		if LegacyRelayCount is 0
		begin
!			Outdoor sensor entry: take its temperature, skip the room.
			put property `temperature` of LegacyRoom into LegacyTemp
			if LegacyTemp is not empty
			begin
				if LegacyTemp is not 0
				begin
					put LegacyTemp into TempStr
					gosub to FormatHundredths
					put TempStr into OutsideTemp
				end
			end
		end
		else
		begin
			gosub to BuildRoomEntry
			set element RoomsListIdx of RoomsList to NewRoom
			increment RoomsListIdx
		end
		increment LegacyIdx
	end
	put RoomsListIdx into RoomCount
	return

!	Build a single new-UI room entry from a legacy controller-map room.
!	Inputs: LegacyRoom, RoomsListIdx. Output: NewRoom (a fresh JSON object).
BuildRoomEntry:
	put `{}` into NewRoom
	put property `name` of LegacyRoom into LegacyName
	set property `name` of NewRoom to LegacyName
	set property `id` of NewRoom to `room-` cat RoomsListIdx
	set property `sensor` of NewRoom to `no`

!	Mode: legacy lowercase → new-UI title-case. Anything unrecognised → Off.
	put property `mode` of LegacyRoom into LegacyMode
	put `Off` into Mode
	if LegacyMode is `timed` put `Timed` into Mode
	else if LegacyMode is `on` put `On` into Mode
	else if LegacyMode is `boost` put `Boost` into Mode
	set property `mode` of NewRoom to Mode

!	Temperature: legacy hundredths integer → "X.Y" string. 0 / empty → empty.
	put property `temperature` of LegacyRoom into LegacyTemp
	if LegacyTemp is empty set property `temp` of NewRoom to empty
	else if LegacyTemp is 0 set property `temp` of NewRoom to empty
	else
	begin
		put LegacyTemp into TempStr
		gosub to FormatHundredths
		set property `temp` of NewRoom to TempStr
	end

!	Target: number → "X.Y" string. Off mode clears the target. Default 20.0.
	if Mode is `Off` set property `target` of NewRoom to empty
	else
	begin
		put property `target` of LegacyRoom into LegacyTarget
		if LegacyTarget is empty set property `target` of NewRoom to `20.0`
		else
		begin
			put `` cat LegacyTarget into TempStr
			put the index of `.` in TempStr into DotIdx
			if DotIdx is less than 0 put TempStr cat `.0` into TempStr
			set property `target` of NewRoom to TempStr
		end
	end

!	Offline: controller verdict via `status` (`fail` → offline). Also treat
!	a linked room with no temperature as offline (the thermometer hasn't
!	reported yet — common for Zigbee sensors after a restart). Categorise
!	the reason from statusMessage so the sub-line tells the user *what*
!	is wrong, not just "No signal".
	set property `offline` of NewRoom to `no`
	put `No signal` into OfflineReason
	put property `status` of LegacyRoom into LegacyStatus
	put property `statusMessage` of LegacyRoom into LegacyStatusMessage
	put property `linked` of LegacyRoom into LegacyLinked

	if LegacyLinked is `yes`
	begin
		put property `temperature` of LegacyRoom into LegacyTemp
		if LegacyTemp is empty
		begin
			set property `offline` of NewRoom to `yes`
			put `Thermometer not reporting` into OfflineReason
		end
	end

	if LegacyStatus is `fail`
	begin
		set property `offline` of NewRoom to `yes`
		if the index of `Sensor` in LegacyStatusMessage is greater than -1
			put `Thermometer not reporting` into OfflineReason
		else if the index of `Relay` in LegacyStatusMessage is greater than -1
			put `Relay not responding` into OfflineReason
	end

	set property `offlineReason` of NewRoom to OfflineReason

!	Warn-state message: surface the controller's diagnostic for online rooms
!	whose status is "warn" (e.g. "Sensor: no report for 12 min"). For failed
!	rooms the same message has already shaped offlineReason.
	set property `warnMessage` of NewRoom to empty
	if property `offline` of NewRoom is `no`
	begin
		if LegacyStatus is `warn`
		begin
			if LegacyStatusMessage is not empty set property `warnMessage` of NewRoom to LegacyStatusMessage
		end
	end

!	Battery: flag low (≤20%) so the sub-line can warn during normal operation.
!	0 / empty means "no reading" — don't flag those.
	set property `batteryLow` of NewRoom to `no`
	put property `battery` of LegacyRoom into LegacyBattery
	if LegacyBattery is not empty
	begin
		if LegacyBattery is greater than 0
		begin
			if LegacyBattery is less than 21 set property `batteryLow` of NewRoom to `yes`
		end
	end

!	Boost: when mode is `boost`, compute remaining time from the room's
!	`until` field (a ms end-timestamp the controller sets when boost is
!	applied). Round up to the next minute, format as "N min(s)". Mirrors
!	the legacy formula in rbr.as:910-920.
	set property `boost` of NewRoom to empty
	if LegacyMode is `boost`
	begin
		put property `until` of LegacyRoom into BoostUntil
		if BoostUntil is not empty
		begin
			put BoostUntil into BoostRemaining
			take the timestamp from BoostRemaining
			if BoostRemaining is greater than 0
			begin
				divide BoostRemaining by 60000
				add 1 to BoostRemaining
				if BoostRemaining is 1 put `1 min` into BoostText
				else put BoostRemaining cat ` mins` into BoostText
				set property `boost` of NewRoom to BoostText
			end
		end
	end

!	Current schedule period: walk events in order, pick the first whose
!	`until` time is still in the future. nextTime = end of current period;
!	nextTarget = current period's target. Both empty if no events or all
!	have already passed.
	set property `nextTime` of NewRoom to empty
	set property `nextTarget` of NewRoom to empty
	put property `events` of LegacyRoom into LegacyEvents
	if LegacyEvents is not empty
	begin
		put the json count of LegacyEvents into LegacyEventCount
		put the hour into NowMinutes
		multiply NowMinutes by 60
		add the minute to NowMinutes
		put 0 into LoopK
		while LoopK is less than LegacyEventCount
		begin
			put element LoopK of LegacyEvents into LegacyEvent
			put property `until` of LegacyEvent into NextTimeStr
			put NextTimeStr into TempStr
			gosub to ParseTimeMinutes
			if TempTenths is greater than NowMinutes
			begin
				put property `temp` of LegacyEvent into NextTempVal
				set property `nextTime` of NewRoom to NextTimeStr
				put `` cat NextTempVal into NextTempStr
				put the index of `.` in NextTempStr into DotIdx
				if DotIdx is less than 0 put NextTempStr cat `.0` into NextTempStr
				set property `nextTarget` of NewRoom to NextTempStr
				put LegacyEventCount into LoopK
			end
			increment LoopK
		end
	end

!	Calling: derived. Re-use the existing RecalcCalling logic on the new room.
!	Write Room back to NewRoom defensively in case `put A into B` snapshots
!	the JSON value rather than aliasing the reference.
	put NewRoom into Room
	gosub to RecalcCalling
	put Room into NewRoom
	return

!	Convert TempStr (legacy hundredths integer, e.g. 1980) to "X.Y" string
!	with a single decimal digit (19.8). In-place via TempStr.
FormatHundredths:
	put TempStr modulo 100 into Hundredths
	put TempStr into TempInt
	divide TempInt by 100
	divide Hundredths by 10
	put `` cat TempInt cat `.` cat Hundredths into TempStr
	return

!	Parse TempStr ("HH:MM" or "H:MM") into minutes-since-midnight; output
!	via TempTenths. Empty / malformed input yields 0.
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
!	Walk all profile rows; the one matching EditingActiveName gets shaded
!	background + accent border. When EditingCalendarOn, the row body (the
!	select target) is dimmed to signal that selection is locked, while the
!	pencil + ✕ buttons stay at full opacity (admin actions still allowed).
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Calendar header painting based on EditingCalendarOn. The outer pill
!	gets bg/border colour-coding so state is visible at a glance even when
!	the day-grid is collapsed; the right-side toggle button shows ON/OFF.
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Toggle the calendar card's expansion. UI-only; no state mutation.
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Paint the 7 day rows from EditingCalendarData. Each entry's property is
!	`day<i>-profile`. Empty / missing → em-dash placeholder.
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
!	from Off restores last target (default 20.0). Sends an "Operating Mode"
!	uirequest to the controller after the local mutation.
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

	put NewMode into Mode
	gosub to LowercaseModeForServer
	put property `name` of Room into RoomNameForServer
	put property `target` of Room into TargetForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to ModeForServer
	if NewMode is `Timed` set property `Boost` of Result to 0
	else if NewMode is `On`
	begin
		set property `advance` of Result to `none`
		set property `target` of Result to TargetForServer
	end
	gosub to PostUiRequest
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

!	Target step persisted: write the new target, then ship "Operating Mode"
!	with the unchanged mode + new target. Controller decides whether to
!	override the schedule (Timed) or just update the setpoint (On/Boost).
WriteTargetTenths:
	put TargetT into TempTenths
	gosub to TenthsToString
	set property `target` of Room to TempStr
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange

	put property `mode` of Room into Mode
	gosub to LowercaseModeForServer
	put property `name` of Room into RoomNameForServer
	put property `target` of Room into TargetForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to ModeForServer
	set property `target` of Result to TargetForServer
	gosub to PostUiRequest
	return

!	Apply boost duration BoostDur ("30 min" / "1 hr" / "2 hr"). Per spec:
!	also forces mode = Boost. Sends "Operating Mode" with boost=B<minutes>.
ApplyBoost:
	put element ClickIndex of RoomsList into Room
	set property `mode` of Room to `Boost`
	set property `boost` of Room to BoostDur
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange

	put 0 into BoostMinutes
	if BoostDur is `30 min` put 30 into BoostMinutes
	else if BoostDur is `1 hr` put 60 into BoostMinutes
	else if BoostDur is `2 hr` put 120 into BoostMinutes
	put property `name` of Room into RoomNameForServer
	put property `target` of Room into TargetForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to `boost`
	set property `advance` of Result to `none`
	set property `boost` of Result to `B` cat BoostMinutes
	set property `target` of Result to TargetForServer
	gosub to PostUiRequest
	return

!	Cancel boost. Per spec: revert to Timed and clear boost.
CancelBoost:
	put element ClickIndex of RoomsList into Room
	set property `mode` of Room to `Timed`
	set property `boost` of Room to empty
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange

	put property `name` of Room into RoomNameForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to `timed`
	set property `Boost` of Result to 0
	gosub to PostUiRequest
	return

!	Lowercase the title-case Mode (Timed/On/Off/Boost) into ModeForServer
!	(timed/on/off/boost) for the controller's payload format.
LowercaseModeForServer:
	put `off` into ModeForServer
	if Mode is `Timed` put `timed` into ModeForServer
	else if Mode is `On` put `on` into ModeForServer
	else if Mode is `Boost` put `boost` into ModeForServer
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Combined ProfileSheet — selection (active row) + edits (rename, delete,
!	add) + calendar toggle + day-profile mappings all batch through Save.
!	Cancel just closes; the editing snapshot is rebuilt fresh on next open.

!	Open: snapshot Map state into the Editing* working copies, render rows,
!	apply highlights, collapse the calendar card, swap the visible sheet.
OpenProfileSheet:
	gosub to CloneProfilesForEditing
	clear EditingCalendarOn
	if CalendarOn set EditingCalendarOn
	gosub to CloneCalendarData
	put ActiveProfileName into EditingActiveName
	gosub to RenderProfileRows
	gosub to ApplyActiveProfile
	gosub to ApplyCalendarHeaderState
	gosub to ApplyDayProfiles
	gosub to ValidateEditingProfiles
	gosub to HideAllDayPickers
	clear CalendarCardExpanded
	set style `display` of CalendarCardEl to `none`
	set style `transform` of CalendarChev to `rotate(0deg)`
	set style `display` of MenuSheetEl to `none`
	set style `display` of ProfileSheetEl to `block`
	set the content of SheetTitleEl to `Profile`
	gosub to OpenSheet
	return

!	Cancel: just close. Editing snapshot is left to rot; next open rebuilds.
CloseProfileSheet:
	gosub to CloseSheet
	return

!	Shallow-clone Profiles → EditingProfiles. Each profile is a fresh {} so
!	name edits don't bleed back. The rooms array is aliased; per-room data
!	editing is a future slice (schedule editor).
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

!	Deep-clone Map.calendar-data → EditingCalendarData. Each entry holds a
!	single `day<i>-profile` string. Pads to 7 entries if the controller
!	sent fewer, so the day-picker can always write into a defined slot.
CloneCalendarData:
	put `[]` into EditingCalendarData
	put property `calendar-data` of Map into LegacyCalData
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

!	Open the day-picker embedded directly under day DayEditTargetIdx (0–6).
!	Hides any other open picker first, then renders one pill per profile in
!	EditingProfiles into THIS day's picker-list. Pill-click writes the
!	profile name back into EditingCalendarData and closes the picker.
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
				gosub to CloseAllDayPickers
			end

			increment PillIdx
		end
	end
	index DayPickerEl to DayEditTargetIdx
	set style `display` of DayPickerEl to `block`
	return

!	Close one specific day's picker (used by its ✕ button). DayEditTargetIdx
!	identifies which.
CloseDayPicker:
	index DayPickerEl to DayEditTargetIdx
	set style `display` of DayPickerEl to `none`
	return

!	Hide every day-picker AND empty every picker-list. Clearing the lists
!	prevents stale pill DOM elements (which all share the id pattern
!	`calendar-day-pill-N`) from blocking the next render's attach by id.
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

CloseAllDayPickers:
	gosub to HideAllDayPickers
	return

!	Tear down + rebuild the profile list from EditingProfiles. Called on
!	open and after every edit (rename / delete / add). Each row wires three
!	click targets: body (select), pencil (rename), ✕ (delete).
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

!	Rename: prompt for a new name, write it back. If the renamed profile
!	WAS the active one, update EditingActiveName to track. Re-render rows.
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

!	Delete: confirm, rebuild EditingProfiles without the entry, re-render.
!	If the active profile was deleted, Save will be disabled by validate.
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

!	Add: clone the active profile (so the new one inherits room schedules),
!	prompt for a name, append.
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

!	Validate: Save is disabled if EditingActiveName isn't present in
!	EditingProfiles (user deleted the active one without picking another).
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

!	Save: ship Update Profiles with the full editing snapshot — profiles,
!	active index, calendar on/off, calendar-data — committing all batched
!	changes in one round trip. Closes the sheet on success.
SaveEditingProfiles:
	if not EditingActiveValid return
	put 0 into NewActiveIdx
	put 0 into LoopE
	while LoopE is less than EditingProfilesCount
	begin
		put element LoopE of EditingProfiles into EditProfileN
		if property `name` of EditProfileN is EditingActiveName put LoopE into NewActiveIdx
		increment LoopE
	end

	put `{}` into Result
	set property `Action` of Result to `Update Profiles`
	set property `profiles` of Result to EditingProfiles
	set property `profile` of Result to NewActiveIdx
	if EditingCalendarOn set property `calendar` of Result to `on`
	else set property `calendar` of Result to `off`
	if EditingCalendarData is not empty set property `calendar-data` of Result to EditingCalendarData
	gosub to PostUiRequest
	gosub to CloseProfileSheet
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Ship the Result JSON object to the controller as a uirequest. Optimistic
!	pattern: local state has already been mutated; on send failure we just
!	alert and let the user retry. The next refresh will reconcile.
PostUiRequest:
	log `Sending uirequest: ` cat Result
	send to ServerTopic
		sender MyTopic
		action `uirequest`
		message Result
		giving SendOK
	if not SendOK
	begin
		log `WARNING: MQTT send failed (no broker acknowledgment)`
		alert `Request failed - please retry`
	end
	return

!	After any state change: recompute `calling`, re-render the rest row,
!	repaint the expansion, and refresh the summary card. Room and ClickIndex
!	must be set.
AfterStateChange:
	gosub to RecalcCalling
	set element ClickIndex of RoomsList to Room
	put ClickIndex into RoomIndex
	put `` cat RoomIndex into IndexStr
	gosub to RenderRoom
	gosub to PaintExpansion
	gosub to ComputeSummaryStats
	gosub to PaintSummary
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

!	Walk RoomsList and recompute the summary aggregates: HeatingCount,
!	HeatingNames, AvgText, OutsideText, TitleText, SubtitleText. Read by
!	PaintSummary. Called once at startup and again from AfterStateChange.
ComputeSummaryStats:
	put 0 into HeatingCount
	put empty into HeatingNames
	put 0 into SumTenths
	put 0 into AvgCount
!	OutsideTemp is owned by MapToRooms (extracted from the outdoor sensor
!	entry, which is filtered out of RoomsList). Don't reset it here.

	put 0 into LoopI
	while LoopI is less than RoomCount
	begin
		put element LoopI of RoomsList into CurRoom
		put property `name` of CurRoom into RName
		put property `temp` of CurRoom into Ttemp
		put property `offline` of CurRoom into Toffline
		put property `calling` of CurRoom into Tcalling

		if Tcalling is `yes`
		begin
			increment HeatingCount
			if HeatingNames is empty put RName into HeatingNames
			else put HeatingNames cat `, ` cat RName into HeatingNames
		end

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

		increment LoopI
	end

	put `—` into AvgText
	if AvgCount is greater than 0
	begin
		divide SumTenths by AvgCount
		put SumTenths modulo 10 into AvgDec
		put SumTenths into AvgInt
		divide AvgInt by 10
		put AvgInt cat `.` cat AvgDec cat `°` into AvgText
	end

	put `—` into OutsideText
	if OutsideTemp is not empty put OutsideTemp cat `°` into OutsideText

	if HeatingCount is 0
	begin
		put `Nothing calling for heat` into TitleText
		put `System idle` into SubtitleText
	end
	else if HeatingCount is 1
	begin
		put HeatingNames cat ` is calling for heat` into TitleText
		put `System firing` into SubtitleText
	end
	else
	begin
		put HeatingCount cat ` rooms calling for heat` into TitleText
		put HeatingNames into SubtitleText
	end
	return

!	Push the aggregates from ComputeSummaryStats into the SummaryCard DOM.
!	Element vars must already be attached. Also refreshes today's date,
!	the active profile name, and the system ID — all of which depend on
!	live data and so can't be set during synchronous startup.
PaintSummary:
	set the content of SummaryTitle to TitleText
	set the content of SummarySubtitle to SubtitleText
	set the content of SummaryAvg to AvgText
	set the content of SummaryOutside to OutsideText

	gosub to FormatTodayString
	set the content of SummaryToday to TempStr

	if ActiveProfileName is not empty
	begin
		put ActiveProfileName into ProfileName
		set the content of SummaryProfileName to ActiveProfileName
	end
	if SystemName is not empty set the content of SystemId to SystemName

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
	return

!	Build today's date as "Mon 23 Apr" into TempStr. Uses DayNames /
!	MonthNames lookups built once during synchronous startup.
FormatTodayString:
	put the day into DateD
	put the day number into DateDN
	put the month into DateM
	put element DateD of DayNames into DayName
	put element DateM of MonthNames into MonthName
	put DayName cat ` ` cat DateDN cat ` ` cat MonthName into TempStr
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
	else if Offline is `yes` put property `offlineReason` of Room into SublineText
	else if Mode is `Off` put empty into SublineText
	else if Mode is `Boost`
	begin
		if BoostVal is empty put `Boost active` into SublineText
		else put `Boost · ` cat BoostVal cat ` left` into SublineText
	end
	else if Mode is `On`
	begin
		if TargetTemp is not empty put TargetTemp cat `°` into SublineText
	end
	else if Mode is `Timed`
	begin
		if NextTime is not empty put NextTarget cat `°→` cat NextTime into SublineText
	end

!	Battery-low + warn-state messages, appended for online rooms (offline
!	rooms already carry a more important status message).
	if Sensor is `no`
	begin
		if Offline is `no`
		begin
			if property `batteryLow` of Room is `yes`
			begin
				if SublineText is empty put `Battery low` into SublineText
				else put SublineText cat ` · Battery low` into SublineText
			end
			put property `warnMessage` of Room into WarnMessage
			if WarnMessage is not empty
			begin
				if SublineText is empty put WarnMessage into SublineText
				else put SublineText cat ` · ` cat WarnMessage into SublineText
			end
		end
	end

	attach Subline to `room-` cat IndexStr cat `-subline`
	set the content of Subline to SublineText

	attach TempEl to `room-` cat IndexStr cat `-temp`
	if TempVal is empty set the content of TempEl to `—`
	else set the content of TempEl to TempVal
	if Offline is `yes` set style `color` of TempEl to `var(--color-text-disabled)`
	else set style `color` of TempEl to `var(--color-text-primary)`

!	Setpoint slot left empty pending a more useful per-room secondary value.
!	Element kept attached so the layout slot is reserved.
	attach Setpoint to `room-` cat IndexStr cat `-setpoint`
	set the content of Setpoint to empty

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
		put `resources/icon/offline.svg` into ChipIconUrl
	end
	else if Mode is `Off`
	begin
		put `var(--color-chip-neutral-bg)` into ChipBg
		put `var(--color-chip-neutral-fg)` into ChipFg
		put `resources/icon/off.svg` into ChipIconUrl
	end
	else if Mode is `On`
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
		put `resources/icon/on.svg` into ChipIconUrl
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
