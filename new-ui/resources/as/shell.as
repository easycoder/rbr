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
	button HeartbeatBtn
	div HeartbeatDot
	button HouseMark
	div AboutSheetEl
	button AboutTabAbout
	button AboutTabManual
	div AboutBodyAbout
	div AboutBodyManual
	button AboutCtaSetup
	div RoomName
	div HeatingTag
	div OfflineTag
	div Subline
	div TempEl
	div Setpoint
	div Chip
	div ChipIcon
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
	button MenuRowSystem
	button MenuRowDevices
	button MenuRowOutside
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
	div DeviceEditorSheetEl
	button DeviceEditorRoomPill
	div DeviceEditorRoomValue
	div DeviceEditorRoomChev
	div DeviceEditorRoomPicker
	button DeviceRoomPill
	input DeviceEditorSensor
	button DeviceEditorRtRBRNow
	button DeviceEditorRtZigbee
	button DeviceEditorLinkedBtn
	textarea DeviceEditorRelays
	input DeviceEditorRequest
	button DeviceEditorSaveBtn
	button DeviceEditorCancelBtn
	div SystemSheetEl
	input SystemSheetName
	button SystemSheetTypeBoiler
	button SystemSheetTypeHeatPump
	button SystemSheetSaveBtn
	button SystemSheetCancelBtn
	div OutsideSheetEl
	input OutsideSheetSensor
	input OutsideSheetFrost
	button OutsideSheetSaveBtn
	button OutsideSheetCancelBtn
	div SummaryOutsideFrost
	div InfoSheetEl
	div InfoRelayValue
	div InfoTempValue
	div InfoHumidityValue
	div InfoBatteryValue
	div InfoAgeValue

!	Per-row interactive elements (indexed via `index X to RoomIndex` in the
!	render loop so each click handler can recover its row via `the index of X`).
	button RestRow
	button InfoBtn
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
	div AdvanceBlockEl
	button AdvanceBtn
	button EditScheduleBtn

	variable LayoutWebson
	variable TopBarWebson
	variable SummaryWebson
	variable SheetWebson
	variable MenuWebson
	variable ProfileWebson
	variable RoomRowText
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
	variable BoostDur
	variable Advance
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
	variable LastReceivedAt
	variable ResumeAge
	variable ConsecutiveSendFailures

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
	variable CalendarOn
	variable DemoMode
	variable AboutSheetWebson
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

!	Schedule editor state.
	variable ScheduleSheetWebson
	variable PeriodCardJson
	variable PeriodCardText
	variable EditingEvents
	variable EditingEventsCount
	variable EditingRoomLegacyIdx
	variable EditingRoomName
	variable PeriodIdx
	variable PeriodIdxStr
	variable PeriodEvent
	variable PeriodTime
	variable PeriodTemp
	variable PeriodTempTenths
	variable EventA
	variable EventB
	variable SortI
	variable SortJ
	variable SortAMinutes
	variable SortBMinutes
	variable SortedEvents
	variable ClonedEvent
	variable SortJplus1
	variable ScheduleH
	variable ScheduleM
	variable LiveProfiles
	variable LiveProfileForRoom
	variable LiveRoomsForRoom
	variable LiveRoomForSchedule
	variable EditingProfileIdx
	variable EditingProfileName
	variable ScheduleDirty
	variable ScheduleProfilePickerOpen
	variable SchedProfilePillIdx
	variable SchedProfilePillIdxStr
	variable SchedProfilePillJson
	variable SchedProfilePillText
	variable LegacyRooms
	variable LegacyRoomCount
	variable LegacyIdx
	variable LegacyRoom
	variable LegacyRelays
	variable LegacyRelayCount
	variable LegacyName
	variable LegacyMode
	variable LegacyPrevMode
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
	variable Tboost

!	Info sheet state.
	variable InfoSheetWebson
	variable InfoSheetOpen
	variable InfoSheetRoomIdx
	variable InfoAgeMs
	variable InfoAgeMin
	variable InfoBatteryVal
	variable InfoHumidityVal
	variable InfoRelayVal

!	System sheet state. SystemType is "Boiler" or "Heat Pump"; stored on
!	the map root so the controller can fan it out to fuel-aware logic.
	variable SystemSheetWebson
	variable EditingSystemName
	variable EditingSystemType
	variable SystemType

!	Demand-relay state. RequestRelay holds the current map.request value;
!	EditingRequestRelay is the in-flight value while the Devices sheet is
!	open. Save ships a `Request Relay` uirequest only when the value has
!	actually changed, so opening Devices, switching rooms, and clicking
!	Save without touching the demand-relay field doesn't gratuitously
!	republish it.
	variable RequestRelay
	variable EditingRequestRelay

!	Outside sheet state. The outside thermometer lives in the legacy "room
!	with empty relays" slot of every profile; sensor name and frost-trigger
!	(ptemp) are fanned out to all profiles on save. FrostActive is derived
!	per refresh from the controller's `frostActive` flag if present, else
!	computed locally (outside temp ≤ trigger and no rooms calling).
	variable OutsideSheetWebson
	variable OutsideSensor
	variable FrostTrigger
	variable EditingOutsideSensor
	variable EditingFrostTrigger
	variable FrostActive
	variable OutsideTempTenths
	variable FrostTriggerTenths
	variable NegativeFlag
	variable OutsideRoomLegacyIdx
	variable OutsideRoomFound
	variable LiveProfileForOutside
	variable LiveRoomsForOutside
	variable LiveRoomForOutside
	variable OutsideProfileLoopI

!	Device editor state. EditingDevicesRoomLegacyIdx pins the legacy-room
!	slot we're editing across all live profiles (the same physical room
!	exists in every profile, so device fields are written to all slots).
!	EditingDevicesRoomIdx is the index into RoomsList (filters out outdoor
!	sensor rooms); the room picker lets the user swap rooms within the
!	editor without leaving the sheet.
	variable DeviceEditorWebson
	variable DeviceRoomPillJson
	variable DeviceRoomPillText
	variable DeviceRoomPillIdx
	variable DeviceRoomPillIdxStr
	variable DeviceRoomPickerOpen
	variable EditingDevicesRoomIdx
	variable EditingDevicesRoomLegacyIdx
	variable EditingDevicesRoomName
	variable EditingDevicesRelayType
	variable EditingDevicesLinked
	variable EditingDevicesSensor
	variable EditingDevicesRelaysText
	variable LiveProfileForDevices
	variable LiveRoomsForDevices
	variable LiveRoomForDevices
	variable RelayLinesArray
	variable RelayLine
	variable RelayLineIdx
	variable DeviceProfileLoopI
	variable DeviceProfileCount
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

	attach HeartbeatBtn to `top-bar-heartbeat`
	attach HeartbeatDot to `top-bar-heartbeat-dot`
	on click HeartbeatBtn gosub to RequestMap

!	Tab resume — when the OS un-throttles a backgrounded tab, the MQTT
!	WebSocket may have been silently torn down by the OS or network.
!	The MQTT client doesn't always notice, so a `send` succeeds into a
!	dead socket and no reply ever comes back. If the last message we
!	received is older than 5 minutes, force a full page reload to rebuild
!	MQTT from scratch. For shorter resumes (briefly switched apps), just
!	trigger an immediate refresh.
	on resume
	begin
		log `Tab resumed`
!		Don't try to RequestMap before MQTT has connected and the first
!		map cycle has run — the topic objects and Prompt aren't reliably
!		set yet, and the next normal poll will catch up on its own.
		if not FirstMapDone return
		if LastReceivedAt is not empty
		begin
			put now into ResumeAge
			take LastReceivedAt from ResumeAge
			if ResumeAge is greater than 300000
			begin
				log `Stale data on resume (` cat ResumeAge cat ` ms); reloading`
				location the location
				return
			end
		end
		gosub to RequestMap
	end

!	Panic-button for stranded credentials. The hamburger button is the only
!	always-visible UI element, so wire it now (synchronously, before MQTT)
!	to a credentials-reset action. BuildHomeScreen re-binds it later for
!	the full menu sheet, so this handler only fires when BuildHomeScreen
!	never ran (i.e. MQTT hasn't connected and no map has arrived).
	attach MenuButton to `top-bar-menu-btn`
	on click MenuButton gosub to ResetCredentialsAndReload

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

!	MQTT credentials. The broker / port / username / password are shared
!	across all customers and served by credentials.php (which reads from
!	`../<HTTP_HOST>.txt` — see credentials.example.json for the schema).
!	The per-system MAC is the only thing the user has to enter, and we
!	cache it in localStorage so the prompt fires only on first run.
!
!	A site-local credentials.json (deploy-provided) takes priority over
!	the shared endpoint — useful for offline / on-IXHUB testing where
!	credentials.php isn't reachable.
	no cache
	rest get Credentials from `credentials.json`
		or go to TryServerCredentials
	if Credentials is not empty go to ApplyCredentials
TryServerCredentials:
!	credentials.php lives at the site root, one level above new-ui/.
	rest get Credentials from `../credentials.php`
		or go to NoCredentialsFile
ApplyCredentials:
	if Credentials is not empty
	begin
		put property `broker` of Credentials into Broker
		put property `port` of Credentials into Port
		put property `username` of Credentials into Username
		put property `password` of Credentials into Password
		if Broker is `localhost`
		begin
			if the hostname is not `localhost` put the hostname into Broker
		end
	end
NoCredentialsFile:
!	MAC is per-system and never lives on the server. Read it from
!	localStorage so the user only has to enter it once.
	get MAC from storage as `dev-mac`
	if MAC is `null` put empty into MAC
	if MAC is `undefined` put empty into MAC

!	No usable credentials → demo / marketing mode. We need a broker (either
!	from credentials.json / credentials.php) and a MAC (from localStorage).
!	Either missing → render the home from a baked demo map and open the
!	About sheet so first-time visitors see what RBR does. Skip MQTT.
	clear DemoMode
	if Broker is empty set DemoMode
	if MAC is empty set DemoMode
	if DemoMode
	begin
		rest get ReceivedMessage from `demo-map.json?v=` cat now
			or go to LoadFailed
		gosub to OnMapReceived
		gosub to OpenAboutSheet
		stop
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
		token Username Password
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
!	Default Prompt so a spurious early call (e.g. on resume firing during
!	a window where the page backgrounded mid-load) can't trigger the
!	runtime's "missing action field" check.
	if Prompt is empty put `refresh` into Prompt
	log `Requesting map: ` cat Prompt
	if not DemoMode
	begin
		send to ServerTopic
			sender MyTopic
			action Prompt
			giving SendOK
		if not SendOK log `MQTT poll send failed; will retry next cycle`
	end
	return

!	Briefly tint the topbar heartbeat dot to confirm fresh data arrived.
!	Pulsing on RECEIVE rather than send means a dead-but-not-yet-detected
!	WebSocket (common after a phone wake-up) shows up as the dot going
!	quiet — an honest signal — instead of false-positive pulses from a
!	send that "succeeded" into a closed socket.
PulseHeartbeat:
	set style `background-color` of HeartbeatDot to `var(--color-accent)`
	wait 50 ticks
	set style `background-color` of HeartbeatDot to `rgba(0,0,0,0.18)`
	return

!	Fired by `on mqtt message`. First message → BuildHomeScreen (full render).
!	Subsequent messages → RefreshHomeScreen (in-place update).
OnMapReceived:
	if ReceivedMessage is empty return
	put ReceivedMessage into Map
	put empty into ReceivedMessage
	put now into LastReceivedAt
	gosub to MapToRooms
	if not FirstMapDone
	begin
		set FirstMapDone
		gosub to BuildHomeScreen
		put `refresh` into Prompt
		if not DemoMode fork to MapPollTask
	end
	else
	begin
		gosub to RefreshHomeScreen
	end
	gosub to PulseHeartbeat
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
	attach SummaryOutsideFrost to `summary-outside-frost`
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
	set the elements of InfoBtn to RoomCount
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
	set the elements of AdvanceBlockEl to RoomCount
	set the elements of AdvanceBtn to RoomCount
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

!	Menu row click handlers. System / Devices / Outside open their own
!	sheets; Help is wired but inactive (no target sheet yet — placeholder
!	for a future help/about flow).
	attach MenuRowSystem to `menu-row-system`
	on click MenuRowSystem gosub to OpenSystemSheet
	attach MenuRowDevices to `menu-row-devices`
	on click MenuRowDevices gosub to OpenDeviceEditor
	attach MenuRowOutside to `menu-row-outside`
	on click MenuRowOutside gosub to OpenOutsideSheet
	attach MenuRowHelp to `menu-row-help`
	on click MenuRowHelp
	begin
		log `Menu: Help & support (stub)`
	end

!	Hook up the top-bar menu button now that the sheet is ready.
	attach MenuButton to `top-bar-menu-btn`
	on click MenuButton
	begin
		gosub to HideAllSheets
		set style `display` of MenuSheetEl to `block`
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

!	Schedule editor sheet — sibling sheet inside sheet-content. Rendered
!	once; opened on demand via the per-room "Edit schedule" button.
	rest get PeriodCardJson from `resources/webson/schedule-period.json?v=` cat now
		or go to LoadFailed
	rest get SchedProfilePillJson from `resources/webson/sched-profile-pill.json?v=` cat now
		or go to LoadFailed
	rest get ScheduleSheetWebson from `resources/webson/schedule-editor.json?v=` cat now
		or go to LoadFailed
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
	on click ScheduleSaveBtn gosub to SaveScheduleEditor
	on click ScheduleCancelBtn gosub to CloseScheduleEditor

!	Device editor sheet — sibling sheet inside sheet-content. Opened from
!	the menu's "Devices" row. The room picker at the top swaps which room
!	is being edited without leaving the sheet.
	rest get DeviceRoomPillJson from `resources/webson/device-room-pill.json?v=` cat now
		or go to LoadFailed
	rest get DeviceEditorWebson from `resources/webson/device-editor.json?v=` cat now
		or go to LoadFailed
	render DeviceEditorWebson in SheetContent
	attach DeviceEditorSheetEl to `device-editor-sheet`
	set style `display` of DeviceEditorSheetEl to `none`
	attach DeviceEditorRoomPill to `device-editor-room-pill`
	attach DeviceEditorRoomValue to `device-editor-room-value`
	attach DeviceEditorRoomChev to `device-editor-room-chev`
	attach DeviceEditorRoomPicker to `device-editor-room-picker`
	attach DeviceEditorSensor to `device-editor-sensor`
	attach DeviceEditorRtRBRNow to `device-editor-rt-rbrnow`
	attach DeviceEditorRtZigbee to `device-editor-rt-zigbee`
	attach DeviceEditorLinkedBtn to `device-editor-linked-btn`
	attach DeviceEditorRelays to `device-editor-relays`
	attach DeviceEditorRequest to `device-editor-request`
	attach DeviceEditorSaveBtn to `device-editor-save-btn`
	attach DeviceEditorCancelBtn to `device-editor-cancel-btn`

	on click DeviceEditorRoomPill gosub to ToggleDeviceRoomPicker

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
	on click DeviceEditorSaveBtn gosub to SaveDeviceEditor
	on click DeviceEditorCancelBtn gosub to CloseDeviceEditor

!	System type & name sheet — opened from the menu's "System type & name"
!	row. Edits the map's name + systemType fields.
	rest get SystemSheetWebson from `resources/webson/system-sheet.json?v=` cat now
		or go to LoadFailed
	render SystemSheetWebson in SheetContent
	attach SystemSheetEl to `system-sheet`
	set style `display` of SystemSheetEl to `none`
	attach SystemSheetName to `system-sheet-name`
	attach SystemSheetTypeBoiler to `system-sheet-type-boiler`
	attach SystemSheetTypeHeatPump to `system-sheet-type-heatpump`
	attach SystemSheetSaveBtn to `system-sheet-save-btn`
	attach SystemSheetCancelBtn to `system-sheet-cancel-btn`

	on click SystemSheetTypeBoiler
	begin
		put `Boiler` into EditingSystemType
		gosub to PaintSystemSheetType
	end
	on click SystemSheetTypeHeatPump
	begin
		put `Heat Pump` into EditingSystemType
		gosub to PaintSystemSheetType
	end
	on click SystemSheetSaveBtn gosub to SaveSystemSheet
	on click SystemSheetCancelBtn gosub to CloseSystemSheet

!	Outside thermometer + frost protection sheet — opened from the menu's
!	"Outside thermometer" row. Edits the sensor and ptemp on the legacy
!	"room with empty relays" slot of every profile.
	rest get OutsideSheetWebson from `resources/webson/outside-sheet.json?v=` cat now
		or go to LoadFailed
	render OutsideSheetWebson in SheetContent
	attach OutsideSheetEl to `outside-sheet`
	set style `display` of OutsideSheetEl to `none`
	attach OutsideSheetSensor to `outside-sheet-sensor`
	attach OutsideSheetFrost to `outside-sheet-frost`
	attach OutsideSheetSaveBtn to `outside-sheet-save-btn`
	attach OutsideSheetCancelBtn to `outside-sheet-cancel-btn`
	on click OutsideSheetSaveBtn gosub to SaveOutsideSheet
	on click OutsideSheetCancelBtn gosub to CloseOutsideSheet

!	Info sheet — opened from each room row's info button.
	rest get InfoSheetWebson from `resources/webson/info-sheet.json?v=` cat now
		or go to LoadFailed
	render InfoSheetWebson in SheetContent
	attach InfoSheetEl to `info-sheet`
	set style `display` of InfoSheetEl to `none`
	attach InfoRelayValue to `info-relay`
	attach InfoTempValue to `info-temp`
	attach InfoHumidityValue to `info-humidity`
	attach InfoBatteryValue to `info-battery`
	attach InfoAgeValue to `info-age`

!	About sheet — sibling sheet inside sheet-content. Auto-opens on first
!	visit when there are no credentials; tap the house mark in the topbar
!	to re-open at any time.
	rest get AboutSheetWebson from `resources/webson/about-sheet.json?v=` cat now
		or go to LoadFailed
	render AboutSheetWebson in SheetContent
	attach AboutSheetEl to `about-sheet`
	set style `display` of AboutSheetEl to `none`
	attach AboutTabAbout to `about-tab-about`
	attach AboutTabManual to `about-tab-manual`
	attach AboutBodyAbout to `about-body-about`
	attach AboutBodyManual to `about-body-manual`
	attach AboutCtaSetup to `about-cta-setup`

	on click AboutTabAbout gosub to ShowAboutTabAbout
	on click AboutTabManual gosub to ShowAboutTabManual
	on click AboutCtaSetup gosub to SetupMySystem

	attach HouseMark to `top-bar-mark`
	on click HouseMark gosub to OpenAboutSheet

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
	if InfoSheetOpen
	begin
		put element InfoSheetRoomIdx of RoomsList into Room
		gosub to PaintInfoSheet
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
	put property `systemType` of Map into SystemType
	if SystemType is empty put `Boiler` into SystemType
	put property `request` of Map into RequestRelay
	put property `rooms` of ActiveProfile into LegacyRooms
	put the json count of LegacyRooms into LegacyRoomCount

	put `[]` into RoomsList
	put 0 into RoomsListIdx
	put empty into OutsideTemp
	put empty into OutsideSensor
	put empty into FrostTrigger
	clear OutsideRoomFound
	put 0 into OutsideRoomLegacyIdx

	put 0 into LegacyIdx
	while LegacyIdx is less than LegacyRoomCount
	begin
		put element LegacyIdx of LegacyRooms into LegacyRoom
		put property `relays` of LegacyRoom into LegacyRelays
		put the json count of LegacyRelays into LegacyRelayCount
		if LegacyRelayCount is 0
		begin
!			Outdoor sensor entry: pin its slot index for the device editor,
!			capture its sensor name + frost trigger, take its temperature.
!			Skip the room (no card).
			set OutsideRoomFound
			put LegacyIdx into OutsideRoomLegacyIdx
			put property `sensor` of LegacyRoom into OutsideSensor
			put property `ptemp` of LegacyRoom into FrostTrigger
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
	set property `legacyIdx` of NewRoom to LegacyIdx
	set property `sensor` of NewRoom to `no`

!	Mode: legacy lowercase → new-UI title-case. The UI tracks the underlying
!	operating mode (Timed/On/Off); Boost is not a mode of its own, just a
!	transient overlay. When the controller reports `boost`, derive the
!	displayed mode from `prevmode` so the mode pill keeps its selection
!	while the boost is in effect. Anything unrecognised → Off.
	put property `mode` of LegacyRoom into LegacyMode
	put `Off` into Mode
	if LegacyMode is `timed` put `Timed` into Mode
	else if LegacyMode is `on` put `On` into Mode
	else if LegacyMode is `boost`
	begin
		put property `prevmode` of LegacyRoom into LegacyPrevMode
		if LegacyPrevMode is `timed` put `Timed` into Mode
		else if LegacyPrevMode is `on` put `On` into Mode
	end
	set property `mode` of NewRoom to Mode

!	Advance: controller stores `A` (advanced) or `-` (normal). Empty / missing
!	defaults to `-` so the toggle starts from a known off state.
	put property `advance` of LegacyRoom into Advance
	if Advance is empty put `-` into Advance
	set property `advance` of NewRoom to Advance

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

!	Target: number → "X.Y" string. Always populated (default 20.0) — Off
!	rooms keep a target so the user can adjust it before applying a Boost.
	put property `target` of LegacyRoom into LegacyTarget
	if LegacyTarget is empty set property `target` of NewRoom to `20.0`
	else if LegacyTarget is 0 set property `target` of NewRoom to `20.0`
	else
	begin
		put `` cat LegacyTarget into TempStr
		put the index of `.` in TempStr into DotIdx
		if DotIdx is less than 0 put TempStr cat `.0` into TempStr
		set property `target` of NewRoom to TempStr
	end

!	Offline: a relay that's not responding is a real fault — mark offline.
!	A stale sensor is *not* a fault by itself: the room may simply be at
!	a steady temperature that triggers no Zigbee reports. The controller
!	preserves the last known temperature in that case, and we keep showing
!	it with a soft "No recent change" warn message instead of
!	blanking the display. A linked room that has never reported is the
!	one sensor case that does go offline (no last-known value to show).
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
		if the index of `Relay` in LegacyStatusMessage is greater than -1
		begin
			set property `offline` of NewRoom to `yes`
			put `Relay not responding` into OfflineReason
		end
	end

	set property `offlineReason` of NewRoom to OfflineReason

!	Warn-state message: surface the controller's diagnostic for online
!	rooms. A stale-sensor message ("Sensor: no report for N min") is
!	softened to "No recent change" since the room may simply
!	be at a steady temperature; we keep displaying the last known value.
!	Other warn messages (e.g. relay failures shy of the offline threshold)
!	pass through verbatim. The same softening applies to a `fail`-status
!	room when the cause is sensor-side (we didn't go offline above).
	set property `warnMessage` of NewRoom to empty
	if property `offline` of NewRoom is `no`
	begin
		if LegacyStatus is `warn`
		begin
			if the index of `Sensor` in LegacyStatusMessage is greater than -1
				set property `warnMessage` of NewRoom to `No recent change`
			else if LegacyStatusMessage is not empty
				set property `warnMessage` of NewRoom to LegacyStatusMessage
		end
		else if LegacyStatus is `fail`
		begin
			if the index of `Sensor` in LegacyStatusMessage is greater than -1
				set property `warnMessage` of NewRoom to `No recent change`
		end
	end

!	Battery: flag low (≤20%) so the sub-line can warn during normal operation.
!	0 / empty means "no reading" — don't flag those. Also pass the raw
!	value through for the info sheet to display verbatim.
	set property `batteryLow` of NewRoom to `no`
	put property `battery` of LegacyRoom into LegacyBattery
	set property `battery` of NewRoom to LegacyBattery
	if LegacyBattery is not empty
	begin
		if LegacyBattery is greater than 0
		begin
			if LegacyBattery is less than 21 set property `batteryLow` of NewRoom to `yes`
		end
	end

!	Info-sheet extras: relay state, humidity, sensor-age (in ms since the
!	thermometer last reported). Humidity and sensorAge come from the
!	controller's RoomStatus pass; both are empty when not available.
	set property `relay` of NewRoom to property `relay` of LegacyRoom
	set property `humidity` of NewRoom to property `humidity` of LegacyRoom
	set property `sensorAge` of NewRoom to property `sensorAge` of LegacyRoom

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
!	nextTarget = current period's target. When advance is on, jump to the
!	next period (wrapping at end-of-day) so the subline reflects what the
!	controller is actually heating to. Both empty if no events or all
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
				if Advance is `A`
				begin
					increment LoopK
					if LoopK is LegacyEventCount put 0 into LoopK
					put element LoopK of LegacyEvents into LegacyEvent
					put property `until` of LegacyEvent into NextTimeStr
				end
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

!	Calling: take the controller's authoritative relay state. It already
!	accounts for unlinked relays, boost overlay, and hysteresis-free
!	temp-vs-target comparison — re-deriving from temp/target in the UI
!	gets it wrong (the UI's threshold doesn't match the controller's).
	set property `calling` of NewRoom to `no`
	if property `relay` of LegacyRoom is `on` set property `calling` of NewRoom to `yes`
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

!	Every sibling sheet under sheet-content lives at display:block when
!	visible. Each Open<X> routine must hide all the others first; calling
!	this before flipping a single sheet's display:block is the single
!	chokepoint that prevents one sheet bleeding through another.
HideAllSheets:
	set style `display` of MenuSheetEl to `none`
	set style `display` of ProfileSheetEl to `none`
	set style `display` of ScheduleSheetEl to `none`
	set style `display` of DeviceEditorSheetEl to `none`
	set style `display` of SystemSheetEl to `none`
	set style `display` of OutsideSheetEl to `none`
	set style `display` of InfoSheetEl to `none`
	set style `display` of AboutSheetEl to `none`
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

	index InfoBtn to RoomIndex
	attach InfoBtn to `room-` cat RoomIndex cat `-info-btn`
	on click InfoBtn
	begin
		put the index of InfoBtn into ClickIndex
		gosub to OpenInfoSheet
	end
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

	index AdvanceBlockEl to RoomIndex
	attach AdvanceBlockEl to `room-` cat RoomIndex cat `-advance-block`
	index AdvanceBtn to RoomIndex
	attach AdvanceBtn to `room-` cat RoomIndex cat `-advance-btn`
	on click AdvanceBtn
	begin
		put the index of AdvanceBtn into ClickIndex
		gosub to ToggleAdvance
	end

	index EditScheduleBtn to RoomIndex
	attach EditScheduleBtn to `room-` cat RoomIndex cat `-edit-schedule`
	on click EditScheduleBtn
	begin
		put the index of EditScheduleBtn into ClickIndex
		gosub to OpenScheduleEditor
	end
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Toggle expansion for ClickIndex. Closes any other open expansion first.
ToggleExpansion:
	if ExpandedIndex is not -1
	begin
		index ExpansionEl to ExpandedIndex
		set style `display` of ExpansionEl to `none`
		if ExpandedIndex is ClickIndex
		begin
			put -1 into ExpandedIndex
			return
		end
	end
	index ExpansionEl to ClickIndex
	set style `display` of ExpansionEl to `flex`
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

!	Mode segmented control — re-attach per click then style. Mode is always
!	one of Timed/On/Off (Boost is a separate transient overlay handled via
!	BoostDur, not a mode the pill ever shows as selected).
	index ModeTimedBtn to ClickIndex
	index ModeOnBtn to ClickIndex
	index ModeOffBtn to ClickIndex
	gosub to ResetModeBtn
	if Tmode is `Timed` gosub to ActivateModeTimed
	if Tmode is `On` gosub to ActivateModeOn
	if Tmode is `Off` gosub to ActivateModeOff

!	Target tile vs Advance row — Timed hides the manual target (schedule
!	provides it) and shows the Advance toggle. On / Off show the target
!	tile (Off keeps it visible so the user can pre-set a Boost target).
	index TargetBlockEl to ClickIndex
	index AdvanceBlockEl to ClickIndex
	if Tmode is `Timed`
	begin
		set style `display` of TargetBlockEl to `none`
		set style `display` of AdvanceBlockEl to `block`
		put property `advance` of Room into Advance
		if Advance is empty put `-` into Advance
		gosub to PaintAdvanceBtn
	end
	else
	begin
		set style `display` of AdvanceBlockEl to `none`
		set style `display` of TargetBlockEl to `block`
		index TargetValueEl to ClickIndex
		if Ttarget is empty set the content of TargetValueEl to `20.0`
		else set the content of TargetValueEl to Ttarget
	end

!	Boost — hidden in On (boost on top of On is meaningless; the user can
!	just adjust the target). Visible in Off and Timed so the user can
!	override the schedule (Timed) or fire a one-off heating burst (Off).
	index BoostBlockEl to ClickIndex
	if Tmode is `On` set style `display` of BoostBlockEl to `none`
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
!	Mode change. Always clears any active boost (an explicit mode pick is
!	a stronger signal than a transient boost). Target is preserved across
!	all mode changes — Off rooms keep their target so the user can still
!	adjust it. Sends an "Operating Mode" uirequest after the local mutation.
ChangeMode:
	put element ClickIndex of RoomsList into Room
	put property `mode` of Room into Tmode
	if Tmode is NewMode return
	set property `mode` of Room to NewMode
	set property `boost` of Room to empty
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

!	Apply boost duration BoostDur ("30 min" / "1 hr" / "2 hr"). The local
!	mode pill keeps its current selection — Boost is an overlay, not a
!	mode. The controller stores the current mode as `prevmode` and reverts
!	to it when the boost expires. Sends "Operating Mode" Mode=boost with
!	boost=B<minutes> and the local target temperature.
ApplyBoost:
	put element ClickIndex of RoomsList into Room
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

!	Cancel an active boost. The local mode is the underlying mode (the
!	one the user wants restored), so we just clear `boost` and ship the
!	current mode back to the controller. The controller's stored `until`
!	is left in place but is harmless since boost expiration only fires
!	when the controller's own mode is `boost`.
CancelBoost:
	put element ClickIndex of RoomsList into Room
	set property `boost` of Room to empty
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange

	put property `name` of Room into RoomNameForServer
	put property `mode` of Room into Mode
	gosub to LowercaseModeForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to ModeForServer
	set property `Boost` of Result to 0
	gosub to PostUiRequest
	return

!	Toggle the Advance state for the current room. Optimistic local flip,
!	then ship the new desired state in an "Operating Mode" uirequest. The
!	controller treats any non-empty `advance` field on a `timed` mode
!	command as a toggle, so sending the new state value moves it to that
!	state regardless of how the controller currently sees it. The next map
!	refresh reconciles. AdvanceBtn must already be indexed to ClickIndex.
ToggleAdvance:
	put element ClickIndex of RoomsList into Room
	put property `advance` of Room into Advance
	if Advance is empty put `-` into Advance
	if Advance is `A` put `-` into Advance
	else put `A` into Advance
	set property `advance` of Room to Advance
	set element ClickIndex of RoomsList to Room
	gosub to AfterStateChange

	put property `name` of Room into RoomNameForServer
	put `{}` into Result
	set property `Action` of Result to `Operating Mode`
	set property `Room` of Result to RoomNameForServer
	set property `Mode` of Result to `timed`
	set property `advance` of Result to Advance
	gosub to PostUiRequest
	return

!	Style the Advance button for the current Advance value. Reads Advance,
!	expects AdvanceBtn already indexed to the target row.
PaintAdvanceBtn:
	index AdvanceBtn to ClickIndex
	if Advance is `A`
	begin
		set the content of AdvanceBtn to `On`
		set style `background` of AdvanceBtn to `var(--color-accent-10)`
		set style `border` of AdvanceBtn to `1.5px solid var(--color-accent)`
		set style `color` of AdvanceBtn to `var(--color-accent)`
		set style `font-weight` of AdvanceBtn to `600`
	end
	else
	begin
		set the content of AdvanceBtn to `Off`
		set style `background` of AdvanceBtn to `var(--color-surface-card)`
		set style `border` of AdvanceBtn to `1px solid var(--color-border-hairline)`
		set style `color` of AdvanceBtn to `var(--color-text-primary)`
		set style `font-weight` of AdvanceBtn to `500`
	end
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
	gosub to HideAllSheets
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

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Schedule editor — per-room timed-mode events[] editor. Opens from each
!	room's "Edit schedule" button. Edits batch into EditingEvents; Save
!	sorts by `until` and ships an Update Profiles uirequest with the host
!	room's events replaced. Cancel discards.

!	Update the profile pill's value text from EditingProfileIdx.
PaintSchedProfilePill:
	put element EditingProfileIdx of Profiles into ProfileN
	put property `name` of ProfileN into EditingProfileName
	set the content of ScheduleProfileValue to EditingProfileName
	return

!	Toggle the profile picker open/closed. Renders pills on open.
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

!	Render one pill per profile into the picker. Tapping a pill swaps the
!	editor to that profile (after a confirm if there are unsaved edits).
!	Pill IDs use the same template as the calendar day-picker pills, so we
!	clear the picker first to avoid stale-DOM duplicate-id collisions.
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

!	Swap the editor to SchedProfilePillIdx. If there are unsaved edits,
!	confirm first; on cancel, leave everything alone.
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
	gosub to CloneEventsForEditing
	gosub to RenderSchedulePeriods
	gosub to PaintSchedProfilePill
	clear ScheduleProfilePickerOpen
	set style `display` of ScheduleProfilePicker to `none`
	set style `transform` of ScheduleProfileChev to `rotate(0deg)`
	return

!	Open: snapshot the room's events into EditingEvents (defaulting to the
!	active profile), render period cards, swap the visible sheet. The user
!	can then swap to a different profile via the profile-pill at the top.
OpenScheduleEditor:
	put element ClickIndex of RoomsList into Room
	put property `name` of Room into EditingRoomName
	put property `legacyIdx` of Room into EditingRoomLegacyIdx
	put CurrentProfile into EditingProfileIdx
	clear ScheduleDirty
	clear ScheduleProfilePickerOpen
	set style `display` of ScheduleProfilePicker to `none`
	set style `transform` of ScheduleProfileChev to `rotate(0deg)`
	gosub to CloneEventsForEditing
	gosub to RenderSchedulePeriods
	gosub to PaintSchedProfilePill
	gosub to HideAllSheets
	set style `display` of ScheduleSheetEl to `block`
	set the content of SheetTitleEl to `Schedule for ` cat EditingRoomName
	gosub to OpenSheet
	return

!	Cancel: just close. EditingEvents is left to rot; next open rebuilds.
CloseScheduleEditor:
	gosub to CloseSheet
	return

!	Convert the host room's events array into start-time display rows.
!	The map stores end-time + temp-up-to-then; the editor shows start-time
!	+ target-from-then. Conversion (cyclic):
!	    display[i].start  = events[i].until
!	    display[i].target = events[(i+1) mod N].temp
!	Each display row is a fresh {} so edits don't bleed back into the Map.
CloneEventsForEditing:
	put `[]` into EditingEvents
	put property `profiles` of Map into LiveProfiles
	put element EditingProfileIdx of LiveProfiles into LiveProfileForRoom
	put property `rooms` of LiveProfileForRoom into LiveRoomsForRoom
	put element EditingRoomLegacyIdx of LiveRoomsForRoom into LiveRoomForSchedule
	put property `events` of LiveRoomForSchedule into LegacyEvents
	if LegacyEvents is empty
	begin
		put 0 into EditingEventsCount
		return
	end
	put the json count of LegacyEvents into LegacyEventCount
	put 0 into LoopE
	while LoopE is less than LegacyEventCount
	begin
		put element LoopE of LegacyEvents into LegacyEvent
		put `{}` into ClonedEvent
		set property `start` of ClonedEvent to property `until` of LegacyEvent
		put LoopE into NewIdx
		increment NewIdx
		put NewIdx modulo LegacyEventCount into NewIdx
		put element NewIdx of LegacyEvents into EventA
		set property `target` of ClonedEvent to property `temp` of EventA
		set element LoopE of EditingEvents to ClonedEvent
		increment LoopE
	end
	put LegacyEventCount into EditingEventsCount
	return

!	Tear down + rebuild the period cards from EditingEvents. Each card
!	wires four steppers (time -/+, temp -/+) and a delete button.
RenderSchedulePeriods:
	clear SchedulePeriodList
	if EditingEventsCount is 0 return
	set the elements of PeriodCardEl to EditingEventsCount
	set the elements of PeriodTimeValue to EditingEventsCount
	set the elements of PeriodTempValue to EditingEventsCount
	set the elements of PeriodTimeMinusBtn to EditingEventsCount
	set the elements of PeriodTimePlusBtn to EditingEventsCount
	set the elements of PeriodTempMinusBtn to EditingEventsCount
	set the elements of PeriodTempPlusBtn to EditingEventsCount
	set the elements of PeriodDeleteBtn to EditingEventsCount

	put 0 into PeriodIdx
	while PeriodIdx is less than EditingEventsCount
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

		gosub to PaintPeriodValues

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

		increment PeriodIdx
	end
	return

!	Paint just the start + target values for PeriodIdx (avoid full re-render
!	on every stepper tap). Reads EditingEvents[PeriodIdx].
PaintPeriodValues:
	index PeriodTimeValue to PeriodIdx
	index PeriodTempValue to PeriodIdx
	put element PeriodIdx of EditingEvents into PeriodEvent
	put property `start` of PeriodEvent into PeriodTime
	set the content of PeriodTimeValue to PeriodTime
	put `` cat property `target` of PeriodEvent into PeriodTemp
	put the index of `.` in PeriodTemp into DotIdx
	if DotIdx is less than 0 put PeriodTemp cat `.0` into PeriodTemp
	set the content of PeriodTempValue to PeriodTemp cat `°`
	return

!	Step the period's start time by ScheduleM (±15) min, wrapping at 24:00.
!	Update the displayed value in place; don't re-sort here so the user can
!	drift through midnight without rows jumping.
StepPeriodTime:
	put element PeriodIdx of EditingEvents into PeriodEvent
	put property `start` of PeriodEvent into TempStr
	gosub to ParseTimeMinutes
	add TempTenths to ScheduleM
	if ScheduleM is less than 0 add 1440 to ScheduleM
	put ScheduleM modulo 1440 into ScheduleM
	gosub to MinutesToHHMM
	set property `start` of PeriodEvent to TempStr
	set element PeriodIdx of EditingEvents to PeriodEvent
	set ScheduleDirty
	gosub to PaintPeriodValues
	return

!	Step the period's target by PeriodTempTenths (±5 = ±0.5°), clamping
!	to [5.0, 30.0].
StepPeriodTemp:
	put element PeriodIdx of EditingEvents into PeriodEvent
	put `` cat property `target` of PeriodEvent into TempStr
	gosub to ToTenths
	add PeriodTempTenths to TempTenths
	if TempTenths is less than 50 put 50 into TempTenths
	if TempTenths is greater than 300 put 300 into TempTenths
	gosub to TenthsToString
	set property `target` of PeriodEvent to TempStr
	set element PeriodIdx of EditingEvents to PeriodEvent
	set ScheduleDirty
	gosub to PaintPeriodValues
	return

!	Add a new period starting at midnight, target 18.0°. Sort happens on
!	Save, so the new one slots into chronological order then.
AddSchedulePeriod:
	put `{}` into ClonedEvent
	set property `start` of ClonedEvent to `00:00`
	set property `target` of ClonedEvent to `18.0`
	set element EditingEventsCount of EditingEvents to ClonedEvent
	increment EditingEventsCount
	set ScheduleDirty
	gosub to RenderSchedulePeriods
	return

!	Delete period at PeriodIdx. Rebuild the array without it, re-render.
DeleteSchedulePeriod:
	put `[]` into NewProfilesArray
	put 0 into NewIdx
	put 0 into LoopE
	while LoopE is less than EditingEventsCount
	begin
		if LoopE is not PeriodIdx
		begin
			put element LoopE of EditingEvents into PeriodEvent
			set element NewIdx of NewProfilesArray to PeriodEvent
			increment NewIdx
		end
		increment LoopE
	end
	put NewProfilesArray into EditingEvents
	put NewIdx into EditingEventsCount
	set ScheduleDirty
	gosub to RenderSchedulePeriods
	return

!	Bubble-sort EditingEvents in place by `start` time (minutes). N is
!	small (typical schedules are ≤6 periods) so simple O(n²) is fine.
SortEvents:
	if EditingEventsCount is less than 2 return
	put 0 into SortI
	while SortI is less than EditingEventsCount
	begin
		put 0 into SortJ
		while SortJ is less than EditingEventsCount
		begin
			put SortJ into SortJplus1
			increment SortJplus1
			if SortJplus1 is less than EditingEventsCount
			begin
				put element SortJ of EditingEvents into EventA
				put element SortJplus1 of EditingEvents into EventB
				put property `start` of EventA into TempStr
				gosub to ParseTimeMinutes
				put TempTenths into SortAMinutes
				put property `start` of EventB into TempStr
				gosub to ParseTimeMinutes
				put TempTenths into SortBMinutes
				if SortAMinutes is greater than SortBMinutes
				begin
					set element SortJ of EditingEvents to EventB
					set element SortJplus1 of EditingEvents to EventA
				end
			end
			increment SortJ
		end
		increment SortI
	end
	return

!	Convert ScheduleM (0–1439 minutes) into TempStr "HH:MM" with zero-pad.
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

!	Save: sort by start time, convert display rows back to events form
!	(end-time + temp-up-to-then), splice into the host room's slot in the
!	live profiles array, ship Update Profiles. Conversion (cyclic):
!	    events[i].until = display[i].start
!	    events[i].temp  = display[(i-1+N) mod N].target
SaveScheduleEditor:
	gosub to SortEvents
	put `[]` into SortedEvents
	put 0 into LoopE
	while LoopE is less than EditingEventsCount
	begin
		put element LoopE of EditingEvents into PeriodEvent
		put `{}` into ClonedEvent
		set property `until` of ClonedEvent to property `start` of PeriodEvent
		put LoopE into NewIdx
		if NewIdx is 0 put EditingEventsCount into NewIdx
		take 1 from NewIdx
		put element NewIdx of EditingEvents into EventA
		set property `temp` of ClonedEvent to property `target` of EventA
		set element LoopE of SortedEvents to ClonedEvent
		increment LoopE
	end

	put property `profiles` of Map into LiveProfiles
	put element EditingProfileIdx of LiveProfiles into LiveProfileForRoom
	put property `rooms` of LiveProfileForRoom into LiveRoomsForRoom
	put element EditingRoomLegacyIdx of LiveRoomsForRoom into LiveRoomForSchedule
	set property `events` of LiveRoomForSchedule to SortedEvents
	set element EditingRoomLegacyIdx of LiveRoomsForRoom to LiveRoomForSchedule
	set property `rooms` of LiveProfileForRoom to LiveRoomsForRoom
	set element EditingProfileIdx of LiveProfiles to LiveProfileForRoom

	put `{}` into Result
	set property `Action` of Result to `Update Profiles`
	set property `profiles` of Result to LiveProfiles
	set property `profile` of Result to CurrentProfile
	if CalendarOn set property `calendar` of Result to `on`
	else set property `calendar` of Result to `off`
	put property `calendar-data` of Map into CalendarData
	if CalendarData is not empty set property `calendar-data` of Result to CalendarData
	gosub to PostUiRequest
	gosub to CloseScheduleEditor
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Room info sheet — opened from each room row's info button. Read-only
!	snapshot of the room's current readings (relay, temperature, humidity,
!	battery, last-report age). Refreshes whenever the next map arrives via
!	RefreshHomeScreen → PaintInfoSheet.
OpenInfoSheet:
	put ClickIndex into InfoSheetRoomIdx
	put element InfoSheetRoomIdx of RoomsList into Room
	gosub to PaintInfoSheet
	gosub to HideAllSheets
	set style `display` of InfoSheetEl to `block`
	set the content of SheetTitleEl to property `name` of Room
	set InfoSheetOpen
	gosub to OpenSheet
	return

CloseInfoSheet:
	clear InfoSheetOpen
	gosub to CloseSheet
	return

!	Format the readings for the open info sheet. Each value falls back to
!	`—` when the data isn't available (sensor never reported, no humidity
!	channel, etc).
PaintInfoSheet:
	put property `relay` of Room into InfoRelayVal
	if InfoRelayVal is `on` set the content of InfoRelayValue to `On`
	else if InfoRelayVal is `off` set the content of InfoRelayValue to `Off`
	else set the content of InfoRelayValue to `—`

	put property `temp` of Room into TempStr
	if TempStr is empty set the content of InfoTempValue to `—`
	else set the content of InfoTempValue to TempStr cat `°C`

	put property `humidity` of Room into InfoHumidityVal
	if InfoHumidityVal is empty set the content of InfoHumidityValue to `—`
	else set the content of InfoHumidityValue to `` cat InfoHumidityVal cat `%`

	put property `battery` of Room into InfoBatteryVal
	if InfoBatteryVal is empty set the content of InfoBatteryValue to `—`
	else if InfoBatteryVal is 0 set the content of InfoBatteryValue to `—`
	else set the content of InfoBatteryValue to `` cat InfoBatteryVal cat `%`

	put property `sensorAge` of Room into InfoAgeMs
	if InfoAgeMs is empty set the content of InfoAgeValue to `—`
	else
	begin
		put InfoAgeMs into InfoAgeMin
		divide InfoAgeMin by 60000
		if InfoAgeMin is less than 1 set the content of InfoAgeValue to `<1 min ago`
		else if InfoAgeMin is 1 set the content of InfoAgeValue to `1 min ago`
		else set the content of InfoAgeValue to `` cat InfoAgeMin cat ` min ago`
	end
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	System type & name sheet — opened from the menu's first row. Edits the
!	map root's `name` and `systemType` fields. Save ships System Name + a
!	separate Update message for systemType (the controller's System Name
!	handler doesn't yet read systemType; storing it on the map keeps the
!	field around for future controller-side fuel-aware logic).
OpenSystemSheet:
	put SystemName into EditingSystemName
	put SystemType into EditingSystemType
	if EditingSystemType is empty put `Boiler` into EditingSystemType
	set the content of SystemSheetName to EditingSystemName
	gosub to PaintSystemSheetType
	gosub to HideAllSheets
	set style `display` of SystemSheetEl to `block`
	set the content of SheetTitleEl to `System type & name`
	gosub to OpenSheet
	return

CloseSystemSheet:
	gosub to CloseSheet
	return

PaintSystemSheetType:
	gosub to ResetSystemSheetTypeBtns
	if EditingSystemType is `Boiler` gosub to ActivateSystemTypeBoiler
	else if EditingSystemType is `Heat Pump` gosub to ActivateSystemTypeHeatPump
	return

ResetSystemSheetTypeBtns:
	set style `background` of SystemSheetTypeBoiler to `transparent`
	set style `color` of SystemSheetTypeBoiler to `var(--color-text-muted)`
	set style `font-weight` of SystemSheetTypeBoiler to `500`
	set style `box-shadow` of SystemSheetTypeBoiler to `none`
	set style `background` of SystemSheetTypeHeatPump to `transparent`
	set style `color` of SystemSheetTypeHeatPump to `var(--color-text-muted)`
	set style `font-weight` of SystemSheetTypeHeatPump to `500`
	set style `box-shadow` of SystemSheetTypeHeatPump to `none`
	return

ActivateSystemTypeBoiler:
	set style `background` of SystemSheetTypeBoiler to `var(--color-surface-card)`
	set style `color` of SystemSheetTypeBoiler to `var(--color-text-primary)`
	set style `font-weight` of SystemSheetTypeBoiler to `600`
	set style `box-shadow` of SystemSheetTypeBoiler to `0 1px 3px rgba(0,0,0,0.08)`
	return

ActivateSystemTypeHeatPump:
	set style `background` of SystemSheetTypeHeatPump to `var(--color-surface-card)`
	set style `color` of SystemSheetTypeHeatPump to `var(--color-text-primary)`
	set style `font-weight` of SystemSheetTypeHeatPump to `600`
	set style `box-shadow` of SystemSheetTypeHeatPump to `0 1px 3px rgba(0,0,0,0.08)`
	return

!	Save: ship a System Name uirequest with both the name and the systemType.
!	The controller's existing System Name handler picks up `name`; systemType
!	is included as an additional map-root field that the controller can
!	preserve until it grows fuel-aware logic.
SaveSystemSheet:
	put the content of SystemSheetName into EditingSystemName
	set property `name` of Map to EditingSystemName
	set property `systemType` of Map to EditingSystemType
	put EditingSystemName into SystemName
	put EditingSystemType into SystemType
	gosub to PaintSummary

	put `{}` into Result
	set property `Action` of Result to `System Name`
	set property `name` of Result to EditingSystemName
	set property `systemType` of Result to EditingSystemType
	gosub to PostUiRequest
	gosub to CloseSystemSheet
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Outside thermometer + frost protection sheet — edits the sensor name
!	and ptemp on the "room with empty relays" slot of every profile.

OpenOutsideSheet:
	put OutsideSensor into EditingOutsideSensor
	put FrostTrigger into EditingFrostTrigger
	set the content of OutsideSheetSensor to EditingOutsideSensor
	set the content of OutsideSheetFrost to EditingFrostTrigger
	gosub to HideAllSheets
	set style `display` of OutsideSheetEl to `block`
	set the content of SheetTitleEl to `Outside thermometer`
	gosub to OpenSheet
	return

CloseOutsideSheet:
	gosub to CloseSheet
	return

!	Save: read inputs, fan out the sensor and ptemp/protect fields across
!	every profile's outside-room slot, ship Update Profiles. If no outside
!	room exists in the map yet, this is a no-op (the controller would need
!	to add the slot first — flagged in the spec, not handled here).
SaveOutsideSheet:
	if not OutsideRoomFound
	begin
		alert `No outside-thermometer slot found in the map. The controller needs to add one first.`
		return
	end
	put the content of OutsideSheetSensor into EditingOutsideSensor
	put the content of OutsideSheetFrost into EditingFrostTrigger

	put property `profiles` of Map into LiveProfiles
	put the json count of LiveProfiles into DeviceProfileCount
	put 0 into OutsideProfileLoopI
	while OutsideProfileLoopI is less than DeviceProfileCount
	begin
		put element OutsideProfileLoopI of LiveProfiles into LiveProfileForOutside
		put property `rooms` of LiveProfileForOutside into LiveRoomsForOutside
		put element OutsideRoomLegacyIdx of LiveRoomsForOutside into LiveRoomForOutside
		set property `sensor` of LiveRoomForOutside to EditingOutsideSensor
		if EditingFrostTrigger is empty
		begin
			set property `protect` of LiveRoomForOutside to `no`
			set property `ptemp` of LiveRoomForOutside to empty
		end
		else
		begin
			set property `protect` of LiveRoomForOutside to `yes`
			set property `ptemp` of LiveRoomForOutside to EditingFrostTrigger
		end
		set element OutsideRoomLegacyIdx of LiveRoomsForOutside to LiveRoomForOutside
		set property `rooms` of LiveProfileForOutside to LiveRoomsForOutside
		set element OutsideProfileLoopI of LiveProfiles to LiveProfileForOutside
		increment OutsideProfileLoopI
	end

	put `{}` into Result
	set property `Action` of Result to `Update Profiles`
	set property `profiles` of Result to LiveProfiles
	set property `profile` of Result to CurrentProfile
	if CalendarOn set property `calendar` of Result to `on`
	else set property `calendar` of Result to `off`
	put property `calendar-data` of Map into CalendarData
	if CalendarData is not empty set property `calendar-data` of Result to CalendarData
	gosub to PostUiRequest

	put EditingOutsideSensor into OutsideSensor
	put EditingFrostTrigger into FrostTrigger
	gosub to CloseOutsideSheet
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Device editor — per-room thermometer + relay configuration. Opens from
!	each room's "Edit devices" button. Edits are local until Save, which
!	writes the new sensor / relay-type / relays / linked fields onto every
!	profile's slot for this room (the device wiring is physical, shared
!	across profiles) and ships an Update Rooms uirequest.

!	Open from the menu: pick the first room in RoomsList as the default
!	(it's already filtered to non-sensor rooms), load its device fields,
!	swap the visible sheet. The room picker at the top lets the user
!	change selection without leaving the sheet.
OpenDeviceEditor:
	if RoomCount is 0
	begin
		alert `No rooms in the system yet.`
		return
	end
	put 0 into EditingDevicesRoomIdx
	gosub to LoadDeviceEditorRoom
!	Demand-relay name is system-wide — load it once on open, NOT in
!	LoadDeviceEditorRoom (which fires every time the room picker swaps).
	put RequestRelay into EditingRequestRelay
	set the content of DeviceEditorRequest to EditingRequestRelay
	clear DeviceRoomPickerOpen
	set style `display` of DeviceEditorRoomPicker to `none`
	set style `transform` of DeviceEditorRoomChev to `rotate(0deg)`
	gosub to HideAllSheets
	set style `display` of DeviceEditorSheetEl to `block`
	set the content of SheetTitleEl to `Devices`
	gosub to OpenSheet
	return

!	Pull device fields for room at RoomsList[EditingDevicesRoomIdx] into
!	the editing scratch vars and the input controls. Used on initial open
!	and again when the picker swaps rooms.
LoadDeviceEditorRoom:
	put element EditingDevicesRoomIdx of RoomsList into Room
	put property `name` of Room into EditingDevicesRoomName
	put property `legacyIdx` of Room into EditingDevicesRoomLegacyIdx

	put property `profiles` of Map into LiveProfiles
	put element CurrentProfile of LiveProfiles into LiveProfileForDevices
	put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
	put element EditingDevicesRoomLegacyIdx of LiveRoomsForDevices into LiveRoomForDevices

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

!	Toggle the room picker open/closed. Rebuild the pill list each open
!	(rooms can be added/removed between sessions; the picker contents
!	must reflect current state).
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

!	One pill per room in RoomsList. Tapping a pill loads that room's
!	device fields and closes the picker.
RenderDeviceRoomPicker:
	clear DeviceEditorRoomPicker
	if RoomCount is 0 return
	set the elements of DeviceRoomPill to RoomCount
	put 0 into DeviceRoomPillIdx
	while DeviceRoomPillIdx is less than RoomCount
	begin
		put DeviceRoomPillJson into DeviceRoomPillText
		put `` cat DeviceRoomPillIdx into DeviceRoomPillIdxStr
		replace `/I/` with DeviceRoomPillIdxStr in DeviceRoomPillText
		render DeviceRoomPillText in DeviceEditorRoomPicker

		index DeviceRoomPill to DeviceRoomPillIdx
		attach DeviceRoomPill to `device-room-pill-` cat DeviceRoomPillIdxStr
		put element DeviceRoomPillIdx of RoomsList into Room
		set the content of DeviceRoomPill to property `name` of Room
		if DeviceRoomPillIdx is EditingDevicesRoomIdx
		begin
			set style `border-color` of DeviceRoomPill to `var(--color-accent)`
			set style `color` of DeviceRoomPill to `var(--color-accent)`
		end

		on click DeviceRoomPill
		begin
			put the index of DeviceRoomPill into EditingDevicesRoomIdx
			gosub to LoadDeviceEditorRoom
			clear DeviceRoomPickerOpen
			set style `display` of DeviceEditorRoomPicker to `none`
			set style `transform` of DeviceEditorRoomChev to `rotate(0deg)`
		end

		increment DeviceRoomPillIdx
	end
	return

!	Cancel: just close. Editing scratch vars are left to rot; next open
!	rebuilds them from the live map.
CloseDeviceEditor:
	gosub to CloseSheet
	return

!	Style the relay-type pill — highlight the current EditingDevicesRelayType,
!	dim the other.
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

!	Style the linked toggle button — On (accent border) / Off (plain).
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

!	Save: read the current input values, splice the device fields into
!	every profile's slot for this room, ship Update Rooms with the rooms
!	array of the active profile (the controller's UpdateProfile applies
!	the same change to all profiles when fields are device-shaped).
SaveDeviceEditor:
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

!	Walk every profile and write the device fields onto its room slot.
	put property `profiles` of Map into LiveProfiles
	put the json count of LiveProfiles into DeviceProfileCount
	put 0 into DeviceProfileLoopI
	while DeviceProfileLoopI is less than DeviceProfileCount
	begin
		put element DeviceProfileLoopI of LiveProfiles into LiveProfileForDevices
		put property `rooms` of LiveProfileForDevices into LiveRoomsForDevices
		put element EditingDevicesRoomLegacyIdx of LiveRoomsForDevices into LiveRoomForDevices
		set property `sensor` of LiveRoomForDevices to EditingDevicesSensor
		set property `relayType` of LiveRoomForDevices to EditingDevicesRelayType
		set property `linked` of LiveRoomForDevices to EditingDevicesLinked
		set property `relays` of LiveRoomForDevices to RelayLinesArray
		set element EditingDevicesRoomLegacyIdx of LiveRoomsForDevices to LiveRoomForDevices
		set property `rooms` of LiveProfileForDevices to LiveRoomsForDevices
		set element DeviceProfileLoopI of LiveProfiles to LiveProfileForDevices
		increment DeviceProfileLoopI
	end

!	Ship the full profiles array via Update Profiles. The controller's
!	Update Rooms only touches the active profile, but device fields are
!	physical and shared across profiles, so we send the whole profiles
!	tree (already mutated in every slot above). Mirrors how the schedule
!	editor saves edits.
	put `{}` into Result
	set property `Action` of Result to `Update Profiles`
	set property `profiles` of Result to LiveProfiles
	set property `profile` of Result to CurrentProfile
	if CalendarOn set property `calendar` of Result to `on`
	else set property `calendar` of Result to `off`
	put property `calendar-data` of Map into CalendarData
	if CalendarData is not empty set property `calendar-data` of Result to CalendarData
	gosub to PostUiRequest

!	Demand-relay name — system-wide, lives at map root. Only ship a
!	`Request Relay` uirequest if the value actually changed, so reopening
!	the sheet and saving without touching the field is a no-op on the
!	server. Update the local mirror either way.
	put the content of DeviceEditorRequest into EditingRequestRelay
	if EditingRequestRelay is not RequestRelay
	begin
		set property `request` of Map to EditingRequestRelay
		put EditingRequestRelay into RequestRelay
		put `{}` into Result
		set property `Action` of Result to `Request Relay`
		set property `request` of Result to EditingRequestRelay
		gosub to PostUiRequest
	end

	gosub to CloseDeviceEditor
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
!	Wipe the stored MAC and reload — useful when a typo has stranded the
!	page on connect. Broker / username / password now come from the server
!	via credentials.php, so they're not in localStorage to clear.
!	Older keys (dev-broker / dev-username / dev-password) from the prior
!	four-prompt setup are also cleared, so an upgraded install is tidy.
ResetCredentialsAndReload:
	clear ConfirmFlag
	if confirm `Reset stored MAC and reload? You'll be prompted to re-enter it.` set ConfirmFlag
	if not ConfirmFlag return
	put empty into storage as `dev-broker`
	put empty into storage as `dev-username`
	put empty into storage as `dev-password`
	put empty into storage as `dev-mac`
	location the location
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	About sheet flow. Auto-opened in demo mode (no credentials) and on tap
!	of the house mark in the topbar at any time.

!	Open: hide other sheets, show About, set title, reveal the CTA only
!	when in demo mode (so existing users don't see a setup prompt).
OpenAboutSheet:
	gosub to HideAllSheets
	set style `display` of AboutSheetEl to `block`
	if DemoMode set style `display` of AboutCtaSetup to `block`
	else set style `display` of AboutCtaSetup to `none`
	gosub to ShowAboutTabAbout
	set the content of SheetTitleEl to `About`
	gosub to OpenSheet
	return

!	Tab swap: About body visible, Manual body hidden. Active tab pill gets
!	the surface-card background + drop shadow, inactive gets transparent.
ShowAboutTabAbout:
	set style `display` of AboutBodyAbout to `block`
	set style `display` of AboutBodyManual to `none`
	set style `background` of AboutTabAbout to `var(--color-surface-card)`
	set style `box-shadow` of AboutTabAbout to `0 1px 3px rgba(0,0,0,0.08)`
	set style `color` of AboutTabAbout to `var(--color-text-primary)`
	set style `font-weight` of AboutTabAbout to `600`
	set style `background` of AboutTabManual to `transparent`
	set style `box-shadow` of AboutTabManual to `none`
	set style `color` of AboutTabManual to `var(--color-text-muted)`
	set style `font-weight` of AboutTabManual to `500`
	return

ShowAboutTabManual:
	set style `display` of AboutBodyAbout to `none`
	set style `display` of AboutBodyManual to `block`
	set style `background` of AboutTabAbout to `transparent`
	set style `box-shadow` of AboutTabAbout to `none`
	set style `color` of AboutTabAbout to `var(--color-text-muted)`
	set style `font-weight` of AboutTabAbout to `500`
	set style `background` of AboutTabManual to `var(--color-surface-card)`
	set style `box-shadow` of AboutTabManual to `0 1px 3px rgba(0,0,0,0.08)`
	set style `color` of AboutTabManual to `var(--color-text-primary)`
	set style `font-weight` of AboutTabManual to `600`
	return

!	"Set up my system" CTA. Broker / username / password are now shared
!	and fetched from credentials.php, so the only thing the user has to
!	supply is their controller's MAC address. Stored in localStorage and
!	picked up on the next page load.
SetupMySystem:
	put prompt `Enter your controller's MAC address` cat newline cat `(printed on the device, format aa:bb:cc:dd:ee:ff):` into MAC
	if MAC is empty return
	if MAC is `null` return
	if MAC is `undefined` return
	put MAC into storage as `dev-mac`
	location the location
	return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!	Ship the Result JSON object to the controller as a uirequest. Optimistic
!	pattern: local state has already been mutated; on send failure we just
!	alert and let the user retry. The next refresh will reconcile. In
!	demo mode (no controller configured) the send is a no-op so visitors
!	can poke the UI without errors.
PostUiRequest:
	if DemoMode return
	log `Sending uirequest: ` cat Result
	send to ServerTopic
		sender MyTopic
		action `uirequest`
		message Result
		giving SendOK
	if SendOK
	begin
		put 0 into ConsecutiveSendFailures
		return
	end
	log `WARNING: MQTT send failed (no broker acknowledgment)`
	increment ConsecutiveSendFailures
!	Only surface a user-facing alert once the failure looks persistent —
!	transient hiccups (suspended WebSocket, brief network blip) clear up
!	on their own as the poll loop reconnects. Three strikes = noisy.
	if ConsecutiveSendFailures is greater than 2
	begin
		alert `Connection problem. Please reload the page if this persists.`
		put 0 into ConsecutiveSendFailures
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

!	Recompute `calling` for the current Room. A room can call for heat
!	when its underlying mode is not Off, OR when a Boost is active (which
!	can layer on top of Off and still drive the relay).
RecalcCalling:
	put `no` into NewCalling
	put property `sensor` of Room into Tsensor
	put property `offline` of Room into Toffline
	put property `mode` of Room into Tmode
	put property `temp` of Room into Ttemp
	put property `target` of Room into Ttarget
	put property `boost` of Room into Tboost
	if Tsensor is `no`
	begin
		if Toffline is `no`
		begin
			if Tmode is not `Off` gosub to ComputeCallingDiff
			else if Tboost is not empty gosub to ComputeCallingDiff
		end
	end
	set property `calling` of Room to NewCalling
	return

!	Inner branch of RecalcCalling: if the room is heating, compare temp
!	to target and flip NewCalling on if temp is below target. Mirrors the
!	controller's SetRelay: relay on when TempNow < Target, no threshold.
!	Reads Ttemp / Ttarget; writes NewCalling.
ComputeCallingDiff:
	if Ttemp is empty return
	if Ttarget is empty return
	put Ttemp into TempStr
	gosub to ToTenths
	put TempTenths into TempT
	put Ttarget into TempStr
	gosub to ToTenths
	put TempTenths into TargetT
	take TempT from TargetT giving Diff
	if Diff is greater than 0 put `yes` into NewCalling
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

!	Frost protection: trust the controller's `frostActive` flag if it sets
!	one, otherwise compute locally — active when a trigger is set, the
!	outdoor temperature is at-or-below it, and no rooms are calling.
	clear FrostActive
	if property `frostActive` of Map is `yes` set FrostActive
	else
	begin
		if FrostTrigger is not empty
		begin
			if OutsideTemp is not empty
			begin
				if HeatingCount is 0
				begin
					put OutsideTemp into TempStr
					gosub to ToTenths
					put TempTenths into OutsideTempTenths
					put FrostTrigger into TempStr
					gosub to ToTenths
					put TempTenths into FrostTriggerTenths
					if OutsideTempTenths is not greater than FrostTriggerTenths set FrostActive
				end
			end
		end
	end

	if FrostActive
	begin
		put `Frost protection active` into TitleText
		put `Demand relay firing` into SubtitleText
	end
	else if HeatingCount is 0
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

	if FrostActive set style `display` of SummaryOutsideFrost to `inline-block`
	else set style `display` of SummaryOutsideFrost to `none`

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

!	String "X.Y" → integer tenths (e.g. "20.5" → 205, "-1.7" → -17). Uses
!	TempStr in, TempTenths out. Negative inputs need a sign-strip pass
!	first because parsing "left 2 of '-0.5'" → "-0" → 0 silently loses
!	the sign for sub-1° magnitudes.
ToTenths:
	put 0 into TempTenths
	if TempStr is empty return
	clear NegativeFlag
	if left 1 of TempStr is `-`
	begin
		set NegativeFlag
		put from 1 of TempStr into TempStr
	end
	put the index of `.` in TempStr into DotIdx
	if DotIdx is less than 0
	begin
		put the value of TempStr into TempTenths
		multiply TempTenths by 10
	end
	else
	begin
		put the value of left DotIdx of TempStr into TempTenths
		multiply TempTenths by 10
		increment DotIdx
		put the value of from DotIdx of TempStr into DecPart
		add DecPart to TempTenths
	end
	if NegativeFlag multiply TempTenths by -1
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
	put property `advance` of Room into Advance
	if Advance is empty put `-` into Advance

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

	put empty into SublineText
	if Sensor is `yes` put `Outdoor sensor` into SublineText
	else if Offline is `yes` put property `offlineReason` of Room into SublineText
	else
	begin
		if Mode is `On`
		begin
			if TargetTemp is not empty put TargetTemp cat `°` into SublineText
		end
		else if Mode is `Timed`
		begin
			if NextTime is not empty
			begin
				put NextTarget cat `°→` cat NextTime into SublineText
				if Advance is `A` put SublineText cat ` (A)` into SublineText
			end
		end

!		Boost overlay — prepend so the active boost is the most prominent
!		bit of status. Layered on whatever the mode's own subline says.
		if BoostVal is not empty
		begin
			if SublineText is empty put `Boost · ` cat BoostVal cat ` left` into SublineText
			else put `Boost · ` cat BoostVal cat ` left · ` cat SublineText into SublineText
		end
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
!	Decide chip bg / fg / icon-url and apply. Priority: sensor > offline >
!	boost-active > Off > On > calling-for-heat > default (Timed, not heating).
!	Boost is detected via BoostVal so it can layer over Off or Timed.
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
	else if BoostVal is not empty
	begin
		put `var(--color-chip-heat-bg)` into ChipBg
		put `var(--color-chip-heat-fg)` into ChipFg
		put `resources/icon/boost.svg` into ChipIconUrl
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
